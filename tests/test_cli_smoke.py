"""Smoke tests for the vibe-council CLI.

Stdlib-only (`unittest`), so they run with no extra dependencies via
`python -m unittest discover -s tests -t .` and are also collectable by pytest.

These tests never make real OpenRouter calls and never require a real key:
- no-model commands (version/help/presets/models/status/decisions) need no key;
- the missing-key guard is exercised with an empty key;
- premium/token guards block *before* any model call (a clearly fake key is used
  only so the key guard does not fire first in the token-guard test).
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Exit codes (mirror backend.cli)
EXIT_OK = 0
EXIT_PREMIUM = 3
EXIT_TOKEN = 4
EXIT_NOKEY = 7


def run_cli(args, key="sk-test-fake", caller_cwd=None):
    """Run `python -m backend.cli <args>` with a controlled environment.

    The API key is set EXPLICITLY in the env, and config calls
    `load_dotenv(override=False)`, so the explicit value always wins — even though
    load_dotenv still discovers the repo `.env` (it searches from config.py's
    location, not the cwd). That override=False behavior is what makes the
    missing-key test deterministic, NOT the temp cwd. The throwaway temp cwd is
    only used to keep any workspace/run artifacts out of the repo.
      key=None  -> OPENROUTER_API_KEY="" (simulates missing)
      key=<str> -> that clearly fake value
    """
    env = dict(os.environ)
    env["OPENROUTER_API_KEY"] = "" if key is None else key
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    if caller_cwd is not None:
        env["VIBE_CALLER_CWD"] = str(caller_cwd)
    with tempfile.TemporaryDirectory() as run_cwd:
        return subprocess.run(
            [sys.executable, "-m", "backend.cli", *args],
            cwd=run_cwd, env=env, capture_output=True, text=True,
        )


class TestImport(unittest.TestCase):
    def test_imports(self):
        import backend.cli  # noqa: F401
        import backend.guards  # noqa: F401
        import backend.project_workspace  # noqa: F401
        from backend import __version__
        self.assertTrue(__version__)


class TestNoModelCommands(unittest.TestCase):
    def test_version(self):
        r = run_cli(["--version"])
        self.assertEqual(r.returncode, EXIT_OK)
        self.assertIn("vibe-council", r.stdout)

    def test_help(self):
        r = run_cli(["help"])
        self.assertEqual(r.returncode, EXIT_OK)
        self.assertIn("vibe-council", r.stdout)

    def test_presets(self):
        r = run_cli(["presets"])
        self.assertEqual(r.returncode, EXIT_OK)
        for p in ("cheap", "balanced", "premium"):
            self.assertIn(p, r.stdout)

    def test_models(self):
        r = run_cli(["models"])
        self.assertEqual(r.returncode, EXIT_OK)
        self.assertIn("council", r.stdout)
        self.assertIn("/", r.stdout)  # at least one provider/model id

    def test_status_no_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_cli(["status"], caller_cwd=d)
            self.assertEqual(r.returncode, EXIT_OK)
            self.assertIn("No active council workspace", r.stdout)

    def test_decisions_list_empty(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_cli(["decisions", "list"], caller_cwd=d)
            self.assertEqual(r.returncode, EXIT_OK)
            self.assertIn("No", r.stdout)  # "No active workspace" or "No decisions"


class TestGuards(unittest.TestCase):
    def test_missing_key_guard(self):
        r = run_cli(["mini", "--no-project", "--yes", "--prompt", "x"], key=None)
        self.assertEqual(r.returncode, EXIT_NOKEY)
        self.assertIn("OPENROUTER_API_KEY", r.stderr)
        self.assertNotIn("Traceback", r.stderr)  # friendly, no traceback

    def test_placeholder_key_guard(self):
        # The .env.example placeholder must be treated as not configured.
        r = run_cli(["mini", "--no-project", "--yes", "--prompt", "x"],
                    key="sk-or-v1-...")
        self.assertEqual(r.returncode, EXIT_NOKEY)
        self.assertIn("placeholder", r.stderr.lower())
        self.assertNotIn("Traceback", r.stderr)

    def test_premium_guard_blocks_before_key(self):
        # premium guard runs before the key guard, so even with no key it returns 3.
        r = run_cli(["full", "--preset", "premium", "--no-project", "--yes",
                     "--prompt", "x"], key=None)
        self.assertEqual(r.returncode, EXIT_PREMIUM)
        self.assertIn("allow-premium", r.stderr)

    def test_token_guard_blocks_before_call(self):
        # Fake key so the key guard passes; --max-tokens 1 blocks before any call.
        r = run_cli(["review", "--preset", "cheap", "--no-project", "--max-tokens",
                     "1", "--yes", "--prompt", "Review this tiny plan."],
                    key="sk-test-fake")
        self.assertEqual(r.returncode, EXIT_TOKEN)
        self.assertIn("Token guard", r.stderr)


if __name__ == "__main__":
    unittest.main()
