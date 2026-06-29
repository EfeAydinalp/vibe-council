"""Provider diagnostics for ``vibe doctor`` (v0.2 PR 4).

Safe, read-only checks of the *current* provider configuration and reachability.
This module never runs chat/completion/inference and never spends tokens:
- OpenRouter: checks the API key presence/placeholder, and (when online) probes the
  **model-list** endpoint (GET /models), not chat/completions.
- Ollama: validates the loopback-only host, then (when online) probes GET /api/tags
  to report server reachability and the locally installed model list.

The API key is read for the Bearer header sent over the wire but is **never**
returned or printed by these functions. HTTP uses a short timeout and tests mock
``backend.doctor.httpx`` so CI needs neither network nor a running Ollama server.
"""

from __future__ import annotations

import os
import httpx
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from . import providers

# The .env.example placeholder; treated as "not configured" (mirrors backend.cli).
PLACEHOLDER_KEY = "sk-or-v1-..."
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
DOCTOR_TIMEOUT = 5.0

STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"


@dataclass
class DoctorCheck:
    name: str
    status: str  # STATUS_OK | STATUS_WARN | STATUS_FAIL
    detail: str = ""


def _http_get_json(url: str, headers: Optional[dict] = None
                   ) -> Tuple[Optional[int], Any, Optional[str]]:
    """GET ``url`` and return (status_code, json_or_None, error_reason).

    On success error_reason is None. Never raises; never includes any secret
    (only status codes/exception type names are surfaced)."""
    try:
        with httpx.Client(timeout=DOCTOR_TIMEOUT) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                data = None
            return resp.status_code, data, None
    except httpx.HTTPStatusError as e:
        return e.response.status_code, None, f"HTTP {e.response.status_code}"
    except Exception as e:
        return None, None, f"network error ({type(e).__name__})"


def check_openrouter(*, online: bool = True) -> List[DoctorCheck]:
    """Diagnose the OpenRouter provider. The key value is never returned/printed."""
    out: List[DoctorCheck] = []
    key = (os.getenv("OPENROUTER_API_KEY", "") or "").strip()
    if not key:
        out.append(DoctorCheck("openrouter:key", STATUS_FAIL,
                               "OPENROUTER_API_KEY is not set"))
        return out
    if key == PLACEHOLDER_KEY:
        out.append(DoctorCheck("openrouter:key", STATUS_FAIL,
                               "OPENROUTER_API_KEY is still the .env.example placeholder"))
        return out
    out.append(DoctorCheck("openrouter:key", STATUS_OK, "OPENROUTER_API_KEY is set"))

    if not online:
        out.append(DoctorCheck("openrouter:reachability", STATUS_WARN,
                               "skipped (--offline)"))
        return out

    status, _data, err = _http_get_json(
        OPENROUTER_MODELS_URL, headers={"Authorization": f"Bearer {key}"})
    if err is None and status is not None and 200 <= status < 300:
        out.append(DoctorCheck("openrouter:reachability", STATUS_OK,
                               "model-list endpoint reachable (no tokens spent)"))
    else:
        out.append(DoctorCheck("openrouter:reachability", STATUS_FAIL,
                               f"model-list endpoint check failed: {err or f'HTTP {status}'}"))
    return out


def check_ollama(*, online: bool = True) -> List[DoctorCheck]:
    """Diagnose the local Ollama provider. Never calls a non-loopback URL."""
    out: List[DoctorCheck] = []
    try:
        host = providers.resolve_ollama_host()
    except providers.OllamaHostError as e:
        # Invalid / non-loopback host: report and make NO network call.
        out.append(DoctorCheck("ollama:host", STATUS_FAIL, str(e)))
        return out
    out.append(DoctorCheck("ollama:host", STATUS_OK, f"loopback host OK ({host})"))

    override = (os.getenv("VIBE_OLLAMA_MODEL") or "").strip()
    if override:
        out.append(DoctorCheck("ollama:model-override", STATUS_OK,
                               f"VIBE_OLLAMA_MODEL set: {override}"))
    else:
        out.append(DoctorCheck(
            "ollama:model-override", STATUS_WARN,
            "VIBE_OLLAMA_MODEL not set; presets pass OpenRouter-style model IDs — "
            "set VIBE_OLLAMA_MODEL=<a model you pulled locally> for Ollama runs"))

    if not online:
        out.append(DoctorCheck("ollama:reachability", STATUS_WARN,
                               "skipped (--offline)"))
        return out

    status, data, err = _http_get_json(f"{host}/api/tags")
    if err is not None or status is None or not (200 <= status < 300):
        out.append(DoctorCheck("ollama:reachability", STATUS_FAIL,
                               f"server not reachable at {host}: {err or f'HTTP {status}'}"))
        return out
    out.append(DoctorCheck("ollama:reachability", STATUS_OK,
                           f"server reachable ({host}/api/tags)"))

    models: List[str] = []
    if isinstance(data, dict):
        for m in data.get("models") or []:
            name = m.get("name") if isinstance(m, dict) else None
            if name:
                models.append(name)
    if models:
        out.append(DoctorCheck("ollama:models", STATUS_OK,
                               f"{len(models)} local model(s): {', '.join(models)}"))
    else:
        out.append(DoctorCheck("ollama:models", STATUS_WARN,
                               "no local models installed (run e.g. `ollama pull llama3.1`)"))

    if override:
        if override in models:
            out.append(DoctorCheck("ollama:model-availability", STATUS_OK,
                                   f"VIBE_OLLAMA_MODEL '{override}' is installed locally"))
        else:
            out.append(DoctorCheck(
                "ollama:model-availability", STATUS_WARN,
                f"VIBE_OLLAMA_MODEL '{override}' is not installed locally "
                f"(run `ollama pull {override}`)"))
    return out


def run_doctor(*, online: bool = True) -> Tuple[List[DoctorCheck], str]:
    """Resolve the selected provider and run its checks.

    Returns (checks, provider_name). Raises ``providers.UnsupportedProviderError``
    for an unsupported provider (the CLI maps that to a usage/config exit code).
    """
    provider_name = providers.resolve_provider_name()
    if provider_name == "openrouter":
        checks = check_openrouter(online=online)
    elif provider_name == "ollama":
        checks = check_ollama(online=online)
    else:  # pragma: no cover - resolve_provider_name guarantees a known name
        checks = []
    return checks, provider_name


def doctor_exit_code(checks: List[DoctorCheck]) -> int:
    """0 if no check failed (warnings are fine), 1 if any check failed."""
    return 1 if any(c.status == STATUS_FAIL for c in checks) else 0
