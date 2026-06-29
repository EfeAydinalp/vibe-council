"""Tests for the local Ollama provider (v0.2 PR 3).

Stdlib-only (`unittest` + `unittest.mock`), no live Ollama server — httpx is mocked
at the provider boundary, so CI needs neither Ollama installed nor a running server.
Cover: request shape (/api/chat, stream:false), content parsing, raw preservation,
local usage-stat mapping (no cost), HTTP/network error mapping, and strict
loopback-only OLLAMA_HOST validation.
"""

import os
import asyncio
import unittest
from unittest import mock

import httpx

from backend import providers


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
                request=httpx.Request("POST", "http://127.0.0.1:11434/api/chat"),
                response=self,
            )

    def json(self):
        return self._json


class _FakeClient:
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


OLLAMA_BODY = {
    "model": "llama3.1",
    "message": {"role": "assistant", "content": "local hello"},
    "prompt_eval_count": 11,
    "eval_count": 7,
    "total_duration": 123456,
    "load_duration": 1000,
    "prompt_eval_duration": 2000,
    "eval_duration": 3000,
    "done": True,
}


class _MockedBase(unittest.TestCase):
    def setUp(self):
        _FakeClient.captured = None
        _FakeClient.response = _FakeResp(OLLAMA_BODY)
        _FakeClient.raise_exc = None
        self._patch = mock.patch("backend.providers.httpx.AsyncClient", _FakeClient)
        self._patch.start()
        # Ensure a clean, default loopback host for request tests.
        self._env = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                                  if k != "OLLAMA_HOST"}, clear=True)
        self._env.start()

    def tearDown(self):
        self._patch.stop()
        self._env.stop()
        _FakeClient.captured = None
        _FakeClient.response = None
        _FakeClient.raise_exc = None


class TestOllamaBasics(unittest.TestCase):
    def test_identity_and_no_key(self):
        prov = providers.OllamaProvider()
        self.assertEqual(prov.name, "ollama")
        self.assertFalse(prov.requires_api_key())


class TestOllamaChat(_MockedBase):
    def test_builds_api_chat_request_with_stream_false(self):
        prov = providers.OllamaProvider()
        msgs = [{"role": "user", "content": "hi"}]
        result = run(prov.chat(providers.ChatRequest("llama3.1", msgs)))

        cap = _FakeClient.captured
        self.assertEqual(cap["url"], "http://127.0.0.1:11434/api/chat")
        self.assertEqual(cap["json"],
                         {"model": "llama3.1", "messages": msgs, "stream": False})
        # No Authorization header is sent for local Ollama.
        self.assertIsNone(cap["headers"])
        self.assertTrue(result.ok)

    def test_parses_message_content_and_preserves_raw(self):
        prov = providers.OllamaProvider()
        result = run(prov.chat(providers.ChatRequest("llama3.1", [{"role": "user", "content": "x"}])))
        self.assertEqual(result.content, "local hello")
        self.assertEqual(result.raw, OLLAMA_BODY)
        self.assertIsNone(result.reasoning_details)

    def test_maps_usage_stats_without_cost(self):
        prov = providers.OllamaProvider()
        result = run(prov.chat(providers.ChatRequest("llama3.1", [{"role": "user", "content": "x"}])))
        self.assertEqual(result.usage["prompt_tokens"], 11)
        self.assertEqual(result.usage["completion_tokens"], 7)
        self.assertEqual(result.usage["total_tokens"], 18)
        self.assertEqual(result.usage["total_duration"], 123456)
        self.assertNotIn("cost", result.usage)  # never fabricate cost

    def test_http_error_maps_to_clear_error(self):
        _FakeClient.response = _FakeResp({"error": "model 'x' not found"}, status_code=404)
        prov = providers.OllamaProvider()
        result = run(prov.chat(providers.ChatRequest("x", [{"role": "user", "content": "y"}])))
        self.assertFalse(result.ok)
        self.assertEqual(result.error["status"], 404)
        self.assertIn("Ollama HTTP 404", result.error["reason"])
        self.assertIn("not found", result.error["reason"])
        self.assertIsNone(result.to_legacy_dict())

    def test_network_error_maps_to_status_none(self):
        _FakeClient.raise_exc = RuntimeError("connection refused")
        prov = providers.OllamaProvider()
        result = run(prov.chat(providers.ChatRequest("llama3.1", [{"role": "user", "content": "x"}])))
        self.assertFalse(result.ok)
        self.assertIsNone(result.error["status"])
        self.assertIn("network error", result.error["reason"])


class TestOllamaHostValidation(unittest.TestCase):
    def test_default_is_loopback(self):
        with mock.patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                          if k != "OLLAMA_HOST"}, clear=True):
            self.assertEqual(providers.resolve_ollama_host(), "http://127.0.0.1:11434")

    def test_loopback_hosts_accepted(self):
        for host in ("http://localhost:11434", "http://127.0.0.1:11434", "http://[::1]:11434"):
            with self.subTest(host=host):
                with mock.patch.dict(os.environ, {"OLLAMA_HOST": host}):
                    self.assertTrue(providers.resolve_ollama_host().startswith("http"))

    def test_non_loopback_rejected(self):
        for host in ("http://evil.example.com:11434", "http://10.0.0.5:11434",
                     "http://169.254.169.254"):
            with self.subTest(host=host):
                with mock.patch.dict(os.environ, {"OLLAMA_HOST": host}):
                    with self.assertRaises(providers.OllamaHostError):
                        providers.resolve_ollama_host()

    def test_invalid_url_rejected(self):
        with mock.patch.dict(os.environ, {"OLLAMA_HOST": "not-a-url"}):
            with self.assertRaises(providers.OllamaHostError):
                providers.resolve_ollama_host()

    def test_bad_host_makes_chat_return_error_not_raise(self):
        with mock.patch.dict(os.environ, {"OLLAMA_HOST": "http://evil.example.com"}):
            prov = providers.OllamaProvider()
            result = run(prov.chat(providers.ChatRequest("llama3.1", [{"role": "user", "content": "x"}])))
            self.assertFalse(result.ok)
            self.assertIn("non-loopback", result.error["reason"])


if __name__ == "__main__":
    unittest.main()
