"""Tests for the v0.2 provider seam (PR 1: interface + OpenRouter adapter).

Stdlib-only (`unittest` + `unittest.mock`), no live API calls — httpx is mocked at
the provider boundary. These assert that:
- the OpenRouter adapter builds the same request payload/header as before,
- ChatResult preserves content/reasoning/usage(+cost)/raw,
- the legacy `backend.openrouter` wrappers still return the historical dict shapes,
- HTTP/network error behavior is preserved (graceful None + safe error dict),
- only OpenRouter exists (no provider selection / Ollama yet).

The API key value is never asserted on or printed.
"""

import asyncio
import unittest
from unittest import mock

import httpx

from backend import providers, openrouter
from backend.config import OPENROUTER_API_URL


def run(coro):
    return asyncio.run(coro)


class _FakeResp:
    def __init__(self, json_data=None, status_code=200, text=""):
        self._json = json_data if json_data is not None else {}
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", OPENROUTER_API_URL),
                response=self,
            )

    def json(self):
        return self._json


class _FakeClient:
    """Async-context-manager stand-in for httpx.AsyncClient."""
    captured = None
    response = None
    raise_exc = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeClient.captured = {"url": url, "headers": headers, "json": json}
        if _FakeClient.raise_exc is not None:
            raise _FakeClient.raise_exc
        return _FakeClient.response


SUCCESS_BODY = {
    "choices": [{"message": {"content": "hello", "reasoning_details": {"r": 1}}}],
    "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8, "cost": 0.001},
}


class ProviderSeamTestBase(unittest.TestCase):
    def setUp(self):
        _FakeClient.captured = None
        _FakeClient.response = _FakeResp(SUCCESS_BODY)
        _FakeClient.raise_exc = None
        self._patch = mock.patch("backend.providers.httpx.AsyncClient", _FakeClient)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        _FakeClient.captured = None
        _FakeClient.response = None
        _FakeClient.raise_exc = None


class TestShapesAndDefaults(unittest.TestCase):
    def test_chat_request_fields(self):
        req = providers.ChatRequest("m", [{"role": "user", "content": "hi"}])
        self.assertEqual(req.model, "m")
        self.assertEqual(req.timeout, providers.DEFAULT_TIMEOUT)

    def test_default_provider_is_openrouter_only(self):
        prov = providers.get_default_provider()
        self.assertIsInstance(prov, providers.OpenRouterProvider)
        self.assertEqual(prov.name, "openrouter")
        self.assertTrue(prov.requires_api_key())

    def test_chatresult_to_legacy_dict_success_and_error(self):
        ok = providers.ChatResult(content="x", reasoning_details=None,
                                  usage={"total_tokens": 1})
        self.assertTrue(ok.ok)
        self.assertEqual(ok.to_legacy_dict(),
                         {"content": "x", "reasoning_details": None,
                          "usage": {"total_tokens": 1}})
        err = providers.ChatResult(error={"reason": "boom"})
        self.assertFalse(err.ok)
        self.assertIsNone(err.to_legacy_dict())


class TestOpenRouterAdapter(ProviderSeamTestBase):
    def test_builds_expected_payload_and_bearer_header(self):
        prov = providers.OpenRouterProvider()
        msgs = [{"role": "user", "content": "hi"}]
        result = run(prov.chat(providers.ChatRequest("some/model", msgs)))

        cap = _FakeClient.captured
        self.assertEqual(cap["url"], OPENROUTER_API_URL)
        self.assertEqual(cap["json"], {"model": "some/model", "messages": msgs})
        # Auth header is present and Bearer-shaped; value (the key) is never asserted.
        self.assertTrue(cap["headers"]["Authorization"].startswith("Bearer "))
        self.assertEqual(cap["headers"]["Content-Type"], "application/json")
        # Result preserves content / reasoning / usage(+cost) / raw.
        self.assertEqual(result.content, "hello")
        self.assertEqual(result.reasoning_details, {"r": 1})
        self.assertEqual(result.usage["cost"], 0.001)
        self.assertEqual(result.usage["total_tokens"], 8)
        self.assertEqual(result.raw, SUCCESS_BODY)
        self.assertTrue(result.ok)

    def test_http_status_error_maps_to_safe_error(self):
        _FakeClient.response = _FakeResp({"error": {"message": "no funds"}}, status_code=402)
        prov = providers.OpenRouterProvider()
        result = run(prov.chat(providers.ChatRequest("m", [{"role": "user", "content": "x"}])))
        self.assertFalse(result.ok)
        self.assertEqual(result.error["status"], 402)
        self.assertEqual(result.error["model"], "m")
        self.assertIn("credits", result.error["reason"])  # 402 -> insufficient credits
        self.assertIsNone(result.to_legacy_dict())

    def test_network_error_maps_to_status_none(self):
        _FakeClient.raise_exc = RuntimeError("boom")
        prov = providers.OpenRouterProvider()
        result = run(prov.chat(providers.ChatRequest("m", [{"role": "user", "content": "x"}])))
        self.assertFalse(result.ok)
        self.assertIsNone(result.error["status"])
        self.assertIn("network error", result.error["reason"])


class TestLegacyWrappersUnchanged(ProviderSeamTestBase):
    def test_query_model_detailed_success_shape(self):
        result, error = run(openrouter.query_model_detailed("m", [{"role": "user", "content": "x"}]))
        self.assertIsNone(error)
        self.assertEqual(set(result.keys()), {"content", "reasoning_details", "usage"})
        self.assertEqual(result["content"], "hello")
        self.assertEqual(result["usage"]["cost"], 0.001)

    def test_query_model_detailed_failure_returns_none_and_error(self):
        _FakeClient.raise_exc = RuntimeError("down")
        result, error = run(openrouter.query_model_detailed("m", [{"role": "user", "content": "x"}]))
        self.assertIsNone(result)
        self.assertEqual(error["model"], "m")
        self.assertIsNone(error["status"])

    def test_query_model_returns_dict_or_none(self):
        ok = run(openrouter.query_model("m", [{"role": "user", "content": "x"}]))
        self.assertEqual(ok["content"], "hello")
        _FakeClient.raise_exc = RuntimeError("down")
        self.assertIsNone(run(openrouter.query_model("m", [{"role": "user", "content": "x"}])))

    def test_query_models_parallel_maps_models_to_results(self):
        out = run(openrouter.query_models_parallel(
            ["a/1", "b/2"], [{"role": "user", "content": "x"}]))
        self.assertEqual(set(out.keys()), {"a/1", "b/2"})
        self.assertEqual(out["a/1"]["content"], "hello")
        self.assertEqual(out["b/2"]["content"], "hello")


if __name__ == "__main__":
    unittest.main()
