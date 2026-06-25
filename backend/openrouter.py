"""OpenRouter API client for making LLM requests."""

import sys
import httpx
from typing import List, Dict, Any, Optional, Tuple
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL


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


async def query_model_detailed(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Query a single model. Returns (result, error).

    On success: ({'content': ..., 'reasoning_details': ...}, None)
    On failure: (None, {'model', 'status', 'reason', 'exception'})

    A safe one-line error is also printed to the backend console. The API key
    is never logged.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details'),
                # Token usage (and provider 'cost' if present). Safe to surface;
                # contains no secrets. None when the provider omits it.
                'usage': data.get('usage'),
            }, None

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body_msg = _safe_body_message(e.response)
        reason = _safe_reason(status, type(e).__name__, body_msg)
        error = {
            "model": model,
            "status": status,
            "reason": reason,
            "exception": type(e).__name__,
        }
        print(f"[model-error] model={model} status={status} reason={reason}", file=sys.stderr)
        return None, error

    except Exception as e:
        reason = _safe_reason(None, type(e).__name__, None)
        error = {
            "model": model,
            "status": None,
            "reason": reason,
            "exception": type(e).__name__,
        }
        print(f"[model-error] model={model} status=NA reason={reason}", file=sys.stderr)
        return None, error


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query a single model via OpenRouter. Returns the result dict or None.

    Thin wrapper over query_model_detailed for callers that only need the
    content and rely on None for graceful degradation.
    """
    result, _ = await query_model_detailed(model, messages, timeout)
    return result


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
