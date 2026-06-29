"""Tests for `vibe doctor` provider diagnostics (v0.2 PR 4).

Stdlib-only (`unittest` + `unittest.mock`). No inference, no token spend, and no
live network: httpx is mocked at the doctor boundary for unit tests, and the CLI
subprocess tests use ``--offline`` so they never touch the network. Secret values
are never asserted-on or expected in output.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from backend import doctor, providers

REPO_ROOT = Path(__file__).resolve().parent.parent
EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2


class _FakeResp:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "http://x"),
                response=self,
            )

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class _FakeClient:
    captured = []
    response = None
    raise_exc = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, headers=None):
        _FakeClient.captured.append({"url": url, "headers": headers})
        if _FakeClient.raise_exc is not None:
            raise _FakeClient.raise_exc
        return _FakeClient.response


class _HttpMockBase(unittest.TestCase):
    def setUp(self):
        _FakeClient.captured = []
        _FakeClient.response = _FakeResp({})
        _FakeClient.raise_exc = None
        self._p = mock.patch("backend.doctor.httpx.Client", _FakeClient)
        self._p.start()

    def tearDown(self):
        self._p.stop()
        _FakeClient.captured = []
        _FakeClient.response = None
        _FakeClient.raise_exc = None

    def _statuses(self, checks):
        return {c.name: c.status for c in checks}


class TestCheckOpenRouter(_HttpMockBase):
    def test_missing_key_fails_and_makes_no_call(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            checks = doctor.check_openrouter(online=True)
        self.assertEqual(checks[0].name, "openrouter:key")
        self.assertEqual(checks[0].status, doctor.STATUS_FAIL)
        self.assertEqual(_FakeClient.captured, [])  # no network on missing key

    def test_placeholder_key_fails(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": doctor.PLACEHOLDER_KEY}):
            checks = doctor.check_openrouter(online=True)
        self.assertEqual(checks[0].status, doctor.STATUS_FAIL)
        self.assertIn("placeholder", checks[0].detail)
        self.assertEqual(_FakeClient.captured, [])

    def test_valid_key_online_reachable(self):
        _FakeClient.response = _FakeResp({"data": []}, status_code=200)
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-fake-valid"}):
            checks = doctor.check_openrouter(online=True)
        st = self._statuses(checks)
        self.assertEqual(st["openrouter:key"], doctor.STATUS_OK)
        self.assertEqual(st["openrouter:reachability"], doctor.STATUS_OK)
        # Probed the model-list endpoint with a Bearer header (value not asserted).
        cap = _FakeClient.captured[0]
        self.assertEqual(cap["url"], doctor.OPENROUTER_MODELS_URL)
        self.assertTrue(cap["headers"]["Authorization"].startswith("Bearer "))

    def test_valid_key_http_error_reports_failure(self):
        _FakeClient.response = _FakeResp(None, status_code=401)
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-fake-valid"}):
            checks = doctor.check_openrouter(online=True)
        self.assertEqual(self._statuses(checks)["openrouter:reachability"], doctor.STATUS_FAIL)

    def test_network_error_reports_failure(self):
        _FakeClient.raise_exc = RuntimeError("dns")
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-fake-valid"}):
            checks = doctor.check_openrouter(online=True)
        self.assertEqual(self._statuses(checks)["openrouter:reachability"], doctor.STATUS_FAIL)

    def test_offline_skips_reachability(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-fake-valid"}):
            checks = doctor.check_openrouter(online=False)
        self.assertEqual(self._statuses(checks)["openrouter:reachability"], doctor.STATUS_WARN)
        self.assertEqual(_FakeClient.captured, [])


class TestCheckOllama(_HttpMockBase):
    def setUp(self):
        super().setUp()
        # Default loopback host for these tests.
        self._env = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                                 if k != "OLLAMA_HOST"}, clear=True)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        super().tearDown()

    def test_reachable_with_models(self):
        _FakeClient.response = _FakeResp(
            {"models": [{"name": "llama3.1"}, {"name": "qwen2.5"}]}, status_code=200)
        checks = doctor.check_ollama(online=True)
        st = self._statuses(checks)
        self.assertEqual(st["ollama:host"], doctor.STATUS_OK)
        self.assertEqual(st["ollama:reachability"], doctor.STATUS_OK)
        self.assertEqual(st["ollama:models"], doctor.STATUS_OK)
        models_detail = next(c.detail for c in checks if c.name == "ollama:models")
        self.assertIn("llama3.1", models_detail)
        self.assertEqual(_FakeClient.captured[0]["url"], "http://127.0.0.1:11434/api/tags")

    def test_reachable_no_models_warns(self):
        _FakeClient.response = _FakeResp({"models": []}, status_code=200)
        checks = doctor.check_ollama(online=True)
        self.assertEqual(self._statuses(checks)["ollama:models"], doctor.STATUS_WARN)

    def test_server_unreachable_fails(self):
        _FakeClient.raise_exc = RuntimeError("connection refused")
        checks = doctor.check_ollama(online=True)
        self.assertEqual(self._statuses(checks)["ollama:reachability"], doctor.STATUS_FAIL)

    def test_non_loopback_host_fails_without_network_call(self):
        with mock.patch.dict(os.environ, {"OLLAMA_HOST": "http://evil.example.com"}):
            checks = doctor.check_ollama(online=True)
        self.assertEqual(checks[0].name, "ollama:host")
        self.assertEqual(checks[0].status, doctor.STATUS_FAIL)
        self.assertEqual(_FakeClient.captured, [])  # never probes a remote host

    def test_offline_skips_reachability(self):
        checks = doctor.check_ollama(online=False)
        self.assertEqual(self._statuses(checks)["ollama:reachability"], doctor.STATUS_WARN)
        self.assertEqual(_FakeClient.captured, [])


class TestRunDoctorAndExit(unittest.TestCase):
    def test_unsupported_provider_raises(self):
        with mock.patch.dict(os.environ, {"VIBE_PROVIDER": "openai"}):
            with self.assertRaises(providers.UnsupportedProviderError):
                doctor.run_doctor(online=False)

    def test_exit_code_fail_and_pass(self):
        self.assertEqual(doctor.doctor_exit_code(
            [doctor.DoctorCheck("a", doctor.STATUS_FAIL)]), 1)
        self.assertEqual(doctor.doctor_exit_code(
            [doctor.DoctorCheck("a", doctor.STATUS_OK),
             doctor.DoctorCheck("b", doctor.STATUS_WARN)]), 0)


def _run_doctor_cli(*, key="sk-test-fake", provider=None, offline=True):
    env = dict(os.environ)
    env["OPENROUTER_API_KEY"] = "" if key is None else key
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    if provider is None:
        env.pop("VIBE_PROVIDER", None)
    else:
        env["VIBE_PROVIDER"] = provider
    args = ["doctor"] + (["--offline"] if offline else [])
    with tempfile.TemporaryDirectory() as cwd:
        return subprocess.run([sys.executable, "-m", "backend.cli", *args],
                              cwd=cwd, env=env, capture_output=True, text=True)


class TestCliDoctor(unittest.TestCase):
    def test_doctor_command_exists_and_reports_provider(self):
        r = _run_doctor_cli(key="sk-test-fake", provider="openrouter")
        self.assertIn("Selected provider:", r.stdout)
        self.assertIn("openrouter", r.stdout)

    def test_default_openrouter_missing_key_fails(self):
        r = _run_doctor_cli(key=None, provider=None)  # no key, offline
        self.assertEqual(r.returncode, EXIT_RUNTIME)
        self.assertIn("OPENROUTER_API_KEY is not set", r.stdout)

    def test_ollama_needs_no_openrouter_key(self):
        r = _run_doctor_cli(key=None, provider="ollama")  # no key, offline
        self.assertEqual(r.returncode, EXIT_OK)
        self.assertNotIn("OPENROUTER_API_KEY is not set", r.stdout)
        self.assertIn("ollama", r.stdout)

    def test_unsupported_provider_usage_error(self):
        r = _run_doctor_cli(key="sk-test-fake", provider="openai")
        self.assertEqual(r.returncode, EXIT_USAGE)
        self.assertIn("Unsupported provider 'openai'", r.stderr)

    def test_does_not_print_key_value(self):
        secret = "sk-test-SECRETVALUE123"
        r = _run_doctor_cli(key=secret, provider="openrouter")  # offline, key looks valid
        self.assertNotIn("SECRETVALUE123", r.stdout)
        self.assertNotIn("SECRETVALUE123", r.stderr)


if __name__ == "__main__":
    unittest.main()
