"""Provider abstraction seam (v0.2, PR 1).

A deliberately minimal interface around model providers. This first PR introduces
the seam *without* changing behavior: only OpenRouter is implemented, and the
legacy ``backend.openrouter`` helpers delegate here while preserving their exact
historical return shapes.

Out of scope for this PR (later v0.2 work): provider *selection*/config/env, the
Ollama/local provider, health checks, model discovery, retries, and streaming.
The protocol is intentionally trimmed to ``name`` + ``requires_api_key`` +
``chat``; richer capability/health methods are deferred to the ``vibe doctor`` PR.
"""

from __future__ import annotations

import os
import sys
import httpx
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from . import config
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL

DEFAULT_TIMEOUT = 120.0


# --------------------------------------------------------------------------- #
# Normalized request / result shapes
# --------------------------------------------------------------------------- #

@dataclass
class ChatRequest:
    """A normalized single-turn chat request. Adapters translate this into their
    own wire format. Provider-specific kwargs (temperature, JSON mode, …) are
    intentionally not modeled yet."""
    model: str
    messages: List[Dict[str, str]]
    timeout: float = DEFAULT_TIMEOUT


@dataclass
class ChatResult:
    """A normalized chat result.

    On success ``error`` is ``None`` and ``content``/``reasoning_details``/``usage``
    carry the provider output (``usage`` may include a provider ``cost``). On
    failure ``error`` holds the safe, key-free error dict and the content fields
    are empty. ``raw`` is an escape hatch (the unparsed provider body) that callers
    are not required to use and that is never persisted via ``to_legacy_dict``.
    """
    content: Optional[str] = None
    reasoning_details: Any = None
    usage: Optional[Dict[str, Any]] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_legacy_dict(self) -> Optional[Dict[str, Any]]:
        """The historical success-result dict, or ``None`` on failure — the exact
        shape ``backend.openrouter`` callers have always consumed."""
        if self.error is not None:
            return None
        return {
            "content": self.content,
            "reasoning_details": self.reasoning_details,
            "usage": self.usage,
        }


@runtime_checkable
class Provider(Protocol):
    """Minimal provider protocol. Kept small on purpose for v0.2 PR 1."""
    name: str

    def requires_api_key(self) -> bool: ...

    async def chat(self, request: ChatRequest) -> ChatResult: ...


# --------------------------------------------------------------------------- #
# OpenRouter-specific safe error mapping (moved verbatim from openrouter.py)
# --------------------------------------------------------------------------- #

def _safe_body_message(response: httpx.Response) -> Optional[str]:
    """Extract OpenRouter's error message from a response body, truncated.

    The response BODY never contains the API key (the key only travels in the
    request Authorization header), so this is safe to surface/log.
    """
    try:
        data = response.json()
        msg = data.get("error", {}).get("message")
        if msg:
            return str(msg)[:200]
    except Exception:
        pass
    text = (response.text or "").strip()
    return text[:200] if text else None


def _safe_reason(status: Optional[int], exc_type: str, body_msg: Optional[str]) -> str:
    """Map an HTTP status / exception into a short, safe, human reason.

    Never includes the API key (we only ever see status codes and response
    bodies here, not request headers).
    """
    mapping = {
        400: "OpenRouter 400 bad request",
        401: "OpenRouter 401 unauthorized (check API key)",
        402: "insufficient credits (OpenRouter 402)",
        403: "OpenRouter 403 forbidden",
        404: "model not found (OpenRouter 404)",
        408: "OpenRouter 408 request timeout",
        429: "rate limited (OpenRouter 429)",
    }
    if status in mapping:
        reason = mapping[status]
    elif status is not None:
        reason = f"OpenRouter error {status}"
    else:
        return f"network error ({exc_type})"

    if body_msg:
        reason = f"{reason}: {body_msg}"
    return reason


# --------------------------------------------------------------------------- #
# OpenRouter provider
# --------------------------------------------------------------------------- #

class OpenRouterProvider:
    """The default provider. Owns the OpenRouter HTTP/wire details that previously
    lived directly in ``backend.openrouter``; behavior is unchanged."""

    name = "openrouter"

    def requires_api_key(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResult:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"model": request.model, "messages": request.messages}

        try:
            async with httpx.AsyncClient(timeout=request.timeout) as client:
                response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
                response.raise_for_status()

                data = response.json()
                message = data['choices'][0]['message']
                return ChatResult(
                    content=message.get('content'),
                    reasoning_details=message.get('reasoning_details'),
                    # Token usage (and provider 'cost' if present). Safe to surface;
                    # contains no secrets. None when the provider omits it.
                    usage=data.get('usage'),
                    raw=data,
                )

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body_msg = _safe_body_message(e.response)
            reason = _safe_reason(status, type(e).__name__, body_msg)
            error = {
                "model": request.model,
                "status": status,
                "reason": reason,
                "exception": type(e).__name__,
            }
            print(f"[model-error] model={request.model} status={status} reason={reason}",
                  file=sys.stderr)
            return ChatResult(error=error)

        except Exception as e:
            reason = _safe_reason(None, type(e).__name__, None)
            error = {
                "model": request.model,
                "status": None,
                "reason": reason,
                "exception": type(e).__name__,
            }
            print(f"[model-error] model={request.model} status=NA reason={reason}",
                  file=sys.stderr)
            return ChatResult(error=error)


# --------------------------------------------------------------------------- #
# Ollama provider (local, v0.2 PR 3)
#
# Talks to a local Ollama server's POST /api/chat (non-streaming). No API key,
# no dollar cost. The host is loopback-only by default to avoid SSRF surprises;
# model discovery and `vibe doctor` are intentionally out of scope here.
# --------------------------------------------------------------------------- #

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

# Only loopback hosts are permitted (no escape hatch in this PR).
_LOOPBACK_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}


class OllamaHostError(ValueError):
    """Raised when OLLAMA_HOST is malformed or not a loopback address."""


def resolve_ollama_host() -> str:
    """Resolve and validate the Ollama base URL.

    Reads ``OLLAMA_HOST`` (default ``http://127.0.0.1:11434``) and accepts only
    loopback hosts (``localhost``/``127.0.0.1``/``::1``) over http/https, with no
    path/query. Anything else raises ``OllamaHostError`` so we never silently make
    requests to an arbitrary remote URL.
    """
    from urllib.parse import urlparse

    raw = os.getenv("OLLAMA_HOST")
    if raw is None or not raw.strip():
        raw = DEFAULT_OLLAMA_HOST
    candidate = raw.strip()

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise OllamaHostError(
            f"Invalid OLLAMA_HOST '{candidate}'. Use a loopback URL like "
            f"'{DEFAULT_OLLAMA_HOST}'."
        )
    if parsed.hostname not in _LOOPBACK_HOSTNAMES:
        raise OllamaHostError(
            f"Refusing non-loopback OLLAMA_HOST '{candidate}'. Only loopback hosts "
            f"are allowed (localhost, 127.0.0.1, ::1)."
        )
    # Normalize: scheme://host[:port], no trailing slash/path.
    netloc = parsed.netloc
    return f"{parsed.scheme}://{netloc}"


def resolve_ollama_model(request_model: str) -> str:
    """Return the local model name to send to Ollama.

    Presets still carry OpenRouter-style IDs, which a local Ollama server won't
    recognize. When ``VIBE_OLLAMA_MODEL`` is set (non-empty), use it for Ollama
    requests so users can point at a model they've pulled locally. Otherwise fall
    through to ``request_model`` (current behavior). This only affects Ollama; the
    incoming ``ChatRequest`` is never mutated and OpenRouter is unaffected.
    """
    override = os.getenv("VIBE_OLLAMA_MODEL")
    if override and override.strip():
        return override.strip()
    return request_model


def _ollama_usage(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map Ollama's local stats into a usage dict. No `cost` is ever added."""
    usage: Dict[str, Any] = {}
    prompt = data.get("prompt_eval_count")
    completion = data.get("eval_count")
    if isinstance(prompt, int):
        usage["prompt_tokens"] = prompt
    if isinstance(completion, int):
        usage["completion_tokens"] = completion
    if isinstance(prompt, int) and isinstance(completion, int):
        usage["total_tokens"] = prompt + completion
    for k in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration"):
        v = data.get(k)
        if isinstance(v, (int, float)):
            usage[k] = v
    return usage or None


def _ollama_body_message(response: httpx.Response) -> Optional[str]:
    """Extract Ollama's error message from a response body, truncated. Ollama
    returns {"error": "<string>"}; never contains a secret (no key is sent)."""
    try:
        data = response.json()
        err = data.get("error")
        if isinstance(err, str) and err:
            return err[:200]
    except Exception:
        pass
    text = (response.text or "").strip()
    return text[:200] if text else None


class OllamaProvider:
    """Local Ollama provider. Requires no API key and reports no dollar cost."""

    name = "ollama"

    def requires_api_key(self) -> bool:
        return False

    async def chat(self, request: ChatRequest) -> ChatResult:
        try:
            host = resolve_ollama_host()
        except OllamaHostError as e:
            return self._error(request.model, None, str(e), type(e).__name__)

        url = f"{host}/api/chat"
        payload = {
            # VIBE_OLLAMA_MODEL override (if set) -> a local model name; else the
            # request model. ChatRequest itself is never mutated.
            "model": resolve_ollama_model(request.model),
            "messages": request.messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=request.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            message = data.get("message") or {}
            return ChatResult(
                content=message.get("content"),
                reasoning_details=None,
                usage=_ollama_usage(data),
                raw=data,
            )

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body_msg = _ollama_body_message(e.response)
            reason = f"Ollama HTTP {status}" + (f": {body_msg}" if body_msg else "")
            return self._error(request.model, status, reason, type(e).__name__)

        except Exception as e:
            reason = f"network error ({type(e).__name__})"
            return self._error(request.model, None, reason, type(e).__name__)

    @staticmethod
    def _error(model: str, status: Optional[int], reason: str, exc: str) -> ChatResult:
        error = {"model": model, "status": status, "reason": reason, "exception": exc}
        status_str = status if status is not None else "NA"
        print(f"[model-error] model={model} status={status_str} reason={reason}",
              file=sys.stderr)
        return ChatResult(error=error)


# --------------------------------------------------------------------------- #
# Provider selection (v0.2, PR 2; Ollama registered in PR 3)
#
# Selection is read from the VIBE_PROVIDER env var at call time (default
# "openrouter"), so existing behavior is unchanged. Unsupported values fail
# clearly. Ollama is local-only (loopback host, no API key, no cost).
# --------------------------------------------------------------------------- #

# Canonical supported provider names.
SUPPORTED_PROVIDERS = ("openrouter", "ollama")

# Friendly aliases that normalize to a canonical name.
_PROVIDER_ALIASES = {
    "open-router": "openrouter",
}


class UnsupportedProviderError(ValueError):
    """Raised when VIBE_PROVIDER (or an explicit name) is not a supported provider."""


def resolve_provider_name(name: Optional[str] = None) -> str:
    """Resolve and validate a provider name.

    Precedence: explicit ``name`` arg → ``VIBE_PROVIDER`` env → config default.
    The value is normalized (trimmed, lower-cased, aliases applied). Raises
    ``UnsupportedProviderError`` with a clear, actionable message otherwise.
    """
    raw = name if name is not None else os.getenv("VIBE_PROVIDER")
    if raw is None or not raw.strip():
        raw = config.DEFAULT_PROVIDER
    normalized = raw.strip().lower()
    normalized = _PROVIDER_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_PROVIDERS:
        raise UnsupportedProviderError(
            f"Unsupported provider '{raw.strip()}'. Supported providers: "
            f"{', '.join(SUPPORTED_PROVIDERS)}."
        )
    return normalized


# Cached provider instances (stable identity for callers/tests).
_openrouter_provider: Provider = OpenRouterProvider()
_ollama_provider: Provider = OllamaProvider()

_PROVIDER_INSTANCES = {
    "openrouter": _openrouter_provider,
    "ollama": _ollama_provider,
}


def get_provider(name: Optional[str] = None) -> Provider:
    """Return the selected provider instance.

    With no selection (or ``VIBE_PROVIDER=openrouter``) this returns the cached
    OpenRouter provider, so default behavior is identical to before.
    ``VIBE_PROVIDER=ollama`` returns the local Ollama provider. An unsupported
    selection raises ``UnsupportedProviderError``.
    """
    resolved = resolve_provider_name(name)
    return _PROVIDER_INSTANCES[resolved]


def get_default_provider() -> Provider:
    """Return the process-wide default/selected provider (honors VIBE_PROVIDER)."""
    return get_provider()
