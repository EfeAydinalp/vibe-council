"""OpenRouter helper surface (compatibility wrappers).

The OpenRouter HTTP/wire logic now lives in
``backend.providers.OpenRouterProvider``. These functions remain as thin
compatibility wrappers that delegate to the default provider and return the exact
historical dict shapes, so existing callers (``council.py``, ``decision_memory.py``)
are unchanged. Provider *selection* is a later v0.2 PR; the default is OpenRouter.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from .providers import ChatRequest, get_default_provider


async def query_model_detailed(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Query a single model. Returns (result, error).

    On success: ({'content': ..., 'reasoning_details': ..., 'usage': ...}, None)
    On failure: (None, {'model', 'status', 'reason', 'exception'})

    A safe one-line error is printed to stderr by the provider. The API key is
    never logged.
    """
    result = await get_default_provider().chat(ChatRequest(model, messages, timeout))
    return result.to_legacy_dict(), result.error


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
) -> Optional[Dict[str, Any]]:
    """Query a single model. Returns the result dict or None.

    Thin wrapper over query_model_detailed for callers that only need the content
    and rely on None for graceful degradation.
    """
    result, _ = await query_model_detailed(model, messages, timeout)
    return result


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Query multiple models in parallel.

    Args:
        models: List of model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    tasks = [query_model(model, messages) for model in models]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}
