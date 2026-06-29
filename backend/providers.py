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

import sys
import httpx
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

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


# Default provider instance. Provider *selection* is a later PR; for now the
# default is always OpenRouter, so existing behavior is unchanged.
_default_provider: Provider = OpenRouterProvider()


def get_default_provider() -> Provider:
    """Return the process-wide default provider (OpenRouter for v0.2 PR 1)."""
    return _default_provider
