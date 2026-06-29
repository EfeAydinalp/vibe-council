"""Tests for v0.2 provider-selection plumbing (PR 2).

Stdlib-only (`unittest` + `unittest.mock`), no live API calls. Cover:
- default provider is OpenRouter when VIBE_PROVIDER is unset/empty,
- VIBE_PROVIDER=openrouter (and case/whitespace/alias) selects OpenRouter,
- unsupported providers raise a clear, actionable error,
- legacy wrappers still resolve to the default provider,
- the CLI fails clearly (exit 2) for an unsupported provider, before the key guard,
- no Ollama provider exists yet.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend import providers

REPO_ROOT = Path(__file__).resolve().parent.parent
EXIT_USAGE = 2
EXIT_TOKEN = 4
EXIT_NOKEY = 7


def _env_without_provider():
    """patch.dict context that removes VIBE_PROVIDER from the environment."""
    env = {k: v for k, v in os.environ.items() if k != "VIBE_PROVIDER"}
    return mock.patch.dict(os.environ, env, clear=True)


class TestResolveProviderName(unittest.TestCase):
    def test_default_when_unset(self):
        with _env_without_provider():
            self.assertEqual(providers.resolve_provider_name(), "openrouter")

    def test_empty_or_whitespace_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {"VIBE_PROVIDER": "   "}):
            self.assertEqual(providers.resolve_provider_name(), "openrouter")

    def test_explicit_openrouter(self):
        with mock.patch.dict(os.environ, {"VIBE_PROVIDER": "openrouter"}):
            self.assertEqual(providers.resolve_provider_name(), "openrouter")

    def test_case_and_whitespace_normalization(self):
        self.assertEqual(providers.resolve_provider_name("  OpenRouter  "), "openrouter")

    def test_alias_open_router(self):
        self.assertEqual(providers.resolve_provider_name("open-router"), "openrouter")

    def test_explicit_arg_overrides_env(self):
        with mock.patch.dict(os.environ, {"VIBE_PROVIDER": "ollama"}):
            # Explicit valid arg wins over an (otherwise unsupported) env value.
            self.assertEqual(providers.resolve_provider_name("openrouter"), "openrouter")

    def test_unsupported_values_raise_clear_error(self):
        # "ollama" is now supported (PR 3); these remain unsupported.
        for bad in ("openai", "anthropic", "local", "garbage"):
            with self.subTest(bad=bad):
                with self.assertRaises(providers.UnsupportedProviderError) as ctx:
                    providers.resolve_provider_name(bad)
                msg = str(ctx.exception)
                self.assertIn(f"Unsupported provider '{bad}'", msg)
                self.assertIn("Supported providers: openrouter, ollama", msg)


class TestGetProvider(unittest.TestCase):
    def test_default_provider_is_openrouter(self):
        with _env_without_provider():
            self.assertIsInstance(providers.get_default_provider(), providers.OpenRouterProvider)
            self.assertIsInstance(providers.get_provider(), providers.OpenRouterProvider)
            self.assertEqual(providers.get_provider().name, "openrouter")

    def test_env_openrouter_selects_openrouter(self):
        with mock.patch.dict(os.environ, {"VIBE_PROVIDER": "openrouter"}):
            self.assertIsInstance(providers.get_provider(), providers.OpenRouterProvider)

    def test_env_ollama_selects_ollama(self):
        with mock.patch.dict(os.environ, {"VIBE_PROVIDER": "ollama"}):
            prov = providers.get_provider()
            self.assertIsInstance(prov, providers.OllamaProvider)
            self.assertEqual(prov.name, "ollama")
            self.assertFalse(prov.requires_api_key())

    def test_openrouter_still_requires_api_key(self):
        with _env_without_provider():
            self.assertTrue(providers.get_provider().requires_api_key())

    def test_get_provider_caches_stable_instance(self):
        with _env_without_provider():
            self.assertIs(providers.get_provider(), providers.get_provider())

    def test_unsupported_provider_raises(self):
        with mock.patch.dict(os.environ, {"VIBE_PROVIDER": "openai"}):
            with self.assertRaises(providers.UnsupportedProviderError):
                providers.get_provider()


class TestProvidersRegistered(unittest.TestCase):
    def test_openrouter_and_ollama_supported(self):
        self.assertEqual(providers.SUPPORTED_PROVIDERS, ("openrouter", "ollama"))

    def test_ollama_provider_class_exists(self):
        self.assertTrue(hasattr(providers, "OllamaProvider"))


def _run_cli(args, *, key="sk-test-fake", provider=None):
    env = dict(os.environ)
    env["OPENROUTER_API_KEY"] = "" if key is None else key
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    if provider is None:
        env.pop("VIBE_PROVIDER", None)
    else:
        env["VIBE_PROVIDER"] = provider
    with tempfile.TemporaryDirectory() as run_cwd:
        return subprocess.run(
            [sys.executable, "-m", "backend.cli", *args],
            cwd=run_cwd, env=env, capture_output=True, text=True,
        )


class TestCliProviderGuard(unittest.TestCase):
    def test_unsupported_provider_fails_clearly_before_key_guard(self):
        # Even with a fake key present, an unsupported provider fails with EXIT_USAGE
        # and a clear message — it does not reach the key guard. ("openai" is not a
        # supported provider; "ollama" now is.)
        r = _run_cli(["mini", "--no-project", "--yes", "--prompt", "x"],
                     key="sk-test-fake", provider="openai")
        self.assertEqual(r.returncode, EXIT_USAGE)
        self.assertIn("Unsupported provider 'openai'", r.stderr)
        self.assertIn("Supported providers: openrouter, ollama", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_default_openrouter_still_hits_key_guard(self):
        # With no VIBE_PROVIDER and no key, behavior is unchanged: the key guard fires.
        r = _run_cli(["mini", "--no-project", "--yes", "--prompt", "x"],
                     key=None, provider=None)
        self.assertEqual(r.returncode, EXIT_NOKEY)
        self.assertIn("OPENROUTER_API_KEY", r.stderr)

    def test_ollama_skips_openrouter_key_guard(self):
        # With VIBE_PROVIDER=ollama and NO OpenRouter key, the key guard is skipped.
        # The token guard (--max-tokens 1) then blocks BEFORE any provider call, so
        # no live Ollama request is made. Proves the key guard didn't fire (would be 7).
        r = _run_cli(["review", "--preset", "cheap", "--no-project", "--max-tokens", "1",
                      "--yes", "--prompt", "Review this tiny plan."],
                     key=None, provider="ollama")
        self.assertEqual(r.returncode, EXIT_TOKEN)
        self.assertNotIn("OPENROUTER_API_KEY is not set", r.stderr)


if __name__ == "__main__":
    unittest.main()
