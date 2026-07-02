"""Tests for the command allowlist -> fixed argv resolver (backend/workbench_commands.py).

Stdlib-only (`unittest`). This module never imports/calls `subprocess` and never
executes anything — it only resolves an exact, allowlisted command label to a fixed,
pre-built argv and previews it. No shell, no string-to-argv parsing, no dynamic args.
"""

import sys
import unittest
from pathlib import Path

from backend import workbench_commands as wc
from backend import workbench_trust as wt

_SHELL_META = ("; ", "&&", "||", "|", ">", "<", "`", "$(")


class TestAllowlistShape(unittest.TestCase):
    def test_allowlist_has_expected_labels(self):
        labels = {spec.label for spec in wc.list_command_allowlist()}
        for expected in (
            "python -m unittest discover -s tests -t .",
            "vibe lint --redaction",
            "vibe decisions lint",
            "vibe context build",
            "vibe context check",
            "vibe mcp inspect --context --health",
            "git status --short",
        ):
            self.assertIn(expected, labels)

    def test_every_entry_has_fixed_nonempty_argv(self):
        for spec in wc.list_command_allowlist():
            self.assertIsInstance(spec.argv, tuple)
            self.assertGreater(len(spec.argv), 0)
            for token in spec.argv:
                self.assertIsInstance(token, str)
                self.assertTrue(token)

    def test_every_argv_avoids_shell_metacharacter_tokens(self):
        for spec in wc.list_command_allowlist():
            for token in spec.argv:
                for meta in _SHELL_META:
                    self.assertNotIn(meta.strip() or meta, token)

    def test_every_entry_has_positive_timeout_and_output_cap(self):
        for spec in wc.list_command_allowlist():
            self.assertGreater(spec.timeout_seconds, 0)
            self.assertGreater(spec.output_limit_bytes, 0)

    def test_resolver_allowlist_is_a_subset_of_trust_allowlist(self):
        # Two independent gates, both required: the resolver must never claim to know
        # a command the deterministic trust boundary hasn't already allowlisted.
        policy = wt.default_policy()
        for spec in wc.list_command_allowlist():
            ok, _reason = wt.is_command_allowed(spec.label, policy)
            self.assertTrue(ok, f"resolver label not trust-allowlisted: {spec.label!r}")

    def test_python_unittest_label_uses_sys_executable(self):
        spec = wc.resolve_command_label("python -m unittest discover -s tests -t .")
        self.assertEqual(spec.argv[0], sys.executable)
        self.assertEqual(spec.argv[1:], ("-m", "unittest", "discover", "-s", "tests", "-t", "."))

    def test_vibe_labels_use_sys_executable_module_invocation(self):
        for label, expected_tail in (
            ("vibe lint --redaction", ("lint", "--redaction")),
            ("vibe decisions lint", ("decisions", "lint")),
            ("vibe context build", ("context", "build")),
            ("vibe context check", ("context", "check")),
            ("vibe mcp inspect --context --health",
             ("mcp", "inspect", "--context", "--health")),
        ):
            spec = wc.resolve_command_label(label)
            self.assertEqual(spec.argv[0], sys.executable)
            self.assertEqual(spec.argv[1:3], ("-m", "backend.cli"))
            self.assertEqual(spec.argv[3:], expected_tail)

    def test_no_os_specific_vibe_launcher_in_any_argv(self):
        for spec in wc.list_command_allowlist():
            joined = " ".join(spec.argv).lower()
            self.assertNotIn("vibe.ps1", joined)
            self.assertNotIn("vibe.cmd", joined)
            self.assertNotIn("vibe.sh", joined)


class TestLabelResolution(unittest.TestCase):
    def test_known_label_resolves(self):
        self.assertTrue(wc.is_command_label_allowed("git status --short"))
        spec = wc.resolve_command_label("git status --short")
        self.assertEqual(spec.argv, ("git", "status", "--short"))

    def test_unknown_label_blocked(self):
        self.assertFalse(wc.is_command_label_allowed("pip install evil"))
        with self.assertRaises(wc.CommandResolutionError):
            wc.resolve_command_label("pip install evil")

    def test_known_label_with_extra_arg_blocked(self):
        self.assertFalse(wc.is_command_label_allowed("git status --short --extra"))

    def test_known_label_with_shell_metachar_blocked(self):
        self.assertFalse(wc.is_command_label_allowed("git status --short; rm -rf /"))
        self.assertFalse(wc.is_command_label_allowed("git status --short && echo hi"))

    def test_case_mutation_blocked(self):
        self.assertFalse(wc.is_command_label_allowed("GIT STATUS --short"))
        self.assertFalse(wc.is_command_label_allowed("Git Status --Short"))

    def test_whitespace_is_normalized_like_trust(self):
        # mirrors workbench_trust.is_command_allowed's whitespace collapsing
        self.assertTrue(wc.is_command_label_allowed("git   status    --short"))
        self.assertTrue(wc.is_command_label_allowed("  git status --short  "))

    def test_empty_and_none_label_blocked(self):
        self.assertFalse(wc.is_command_label_allowed(""))
        self.assertFalse(wc.is_command_label_allowed(None))  # type: ignore[arg-type]


class TestPreviewCommand(unittest.TestCase):
    def test_preview_allowed_label_is_executed_false_shell_false(self):
        p = wc.preview_command("git status --short", project_root=Path("."))
        self.assertTrue(p.would_execute)
        self.assertFalse(p.executed)
        self.assertFalse(p.shell)
        self.assertFalse(p.blocked)

    def test_preview_sets_timeout_and_output_cap(self):
        p = wc.preview_command("vibe context check", project_root=Path("."))
        self.assertEqual(p.timeout_seconds, wc.DEFAULT_TIMEOUT_SECONDS)
        self.assertEqual(p.output_limit_bytes, wc.DEFAULT_OUTPUT_LIMIT_BYTES)

    def test_preview_unknown_label_blocked_no_argv(self):
        p = wc.preview_command("curl http://example.com", project_root=Path("."))
        self.assertTrue(p.blocked)
        self.assertFalse(p.would_execute)
        self.assertEqual(p.argv, [])

    def test_preview_cwd_reflects_project_root(self):
        p = wc.preview_command("git status --short", project_root=Path("/tmp/somewhere"))
        self.assertEqual(p.cwd, str(Path("/tmp/somewhere")))

    def test_preview_never_touches_subprocess(self):
        import subprocess

        def _boom(*a, **k):
            raise AssertionError("preview_command must never call subprocess.run")

        orig = subprocess.run
        subprocess.run = _boom
        try:
            wc.preview_command("git status --short", project_root=Path("."))
            wc.preview_command("not-a-real-label", project_root=Path("."))
        finally:
            subprocess.run = orig

    def test_summarize_preview_has_no_secrets_and_is_a_string(self):
        p = wc.preview_command("vibe lint --redaction", project_root=Path("."))
        s = wc.summarize_command_preview(p)
        self.assertIsInstance(s, str)
        self.assertIn("WOULD-EXECUTE", s)


class TestNoShellStringParsing(unittest.TestCase):
    def test_resolver_never_imports_subprocess_module(self):
        import sys as _sys
        # workbench_commands must not import subprocess at module load time.
        self.assertNotIn("subprocess", getattr(wc, "__dict__", {}))

    def test_resolve_does_not_shlex_split_the_label(self):
        # A label that LOOKS like it could be split into a valid-ish argv by shlex
        # must still be rejected outright if it isn't an exact allowlist entry.
        self.assertFalse(wc.is_command_label_allowed("git  status  --short  extra"))


if __name__ == "__main__":
    unittest.main()
