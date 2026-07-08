"""Tests for v0.9.0 PR 2 — the tighten-only preference **preset floor** for review/diff, plus
the ``--no-preferences`` escape hatch (plan §5.1/§5.3).

Stdlib-only (`unittest`). Two layers: (1) fast, deterministic unit tests of the pure
``cli._resolve_preset`` resolution matrix (no subprocess); (2) a few CLI-level checks via the
**empty-diff path** (`vibe diff` in a non-git dir returns "No changes to review" without any
model/API/network call), proving the notice reaches stderr — never stdout — and that
``--no-preferences`` / an explicit ``--preset`` suppress it. No model/API/network anywhere.
"""

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from backend import cli
from tests.test_cli_smoke import run_cli

REPO = Path(__file__).resolve().parents[1]

# A stable substring of the pinned full-floor notice (asserted instead of the whole string so a
# future wording tweak in one place doesn't scatter across tests — but the exact string is
# pinned once in test_full_floor_notice_is_pinned).
NOTICE_SUBSTR = "full-council review floor"


def _resolve(root, *, preset=None, no_preferences=False, usage=False, command="review"):
    """Call the pure resolver, capturing anything it writes to stderr."""
    ns = argparse.Namespace(preset=preset, no_preferences=no_preferences, usage=usage)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        out = cli._resolve_preset(ns, command, root)
    return out, err.getvalue()


class _PrefsDir(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def _write_block(self, obj):
        d = self.root / "docs/context/project"
        d.mkdir(parents=True, exist_ok=True)
        (d / "PREFERENCES.md").write_text(
            f"# prefs\n\n```json\n{json.dumps(obj)}\n```\n", encoding="utf-8")

    def _write_raw(self, text):
        d = self.root / "docs/context/project"
        d.mkdir(parents=True, exist_ok=True)
        (d / "PREFERENCES.md").write_text(text, encoding="utf-8")


class TestResolvePresetMatrix(_PrefsDir):
    """The pure resolution matrix — CLI wins, tighten-only, never lowers, full = notice-only."""

    def test_no_block_is_baseline_no_notice(self):
        self._write_raw("# just prose, no machine block.\n")
        preset, err = _resolve(self.root, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)
        self.assertEqual(err, "")

    def test_missing_file_is_baseline_no_notice(self):
        preset, err = _resolve(self.root, command="review")   # no PREFERENCES.md at all
        self.assertEqual(preset, cli.DEFAULT_PRESET)
        self.assertEqual(err, "")

    def test_invalid_block_is_baseline_no_notice(self):
        self._write_raw("```json\n{ \"schema\": 1, \"default_review_preset\": \"premium\" }\n```\n")
        preset, err = _resolve(self.root, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)          # fail-closed -> baseline
        self.assertEqual(err, "")

    def test_minimal_schema_is_baseline_no_notice(self):
        self._write_block({"schema": 1})
        preset, err = _resolve(self.root, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)
        self.assertEqual(err, "")

    def test_cheap_block_never_lowers(self):
        # "cheap" is below the balanced baseline -> inert (floor None) -> baseline, no notice.
        self._write_block({"schema": 1, "default_review_preset": "cheap"})
        preset, err = _resolve(self.root, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)          # never lowered to cheap
        self.assertEqual(err, "")

    def test_balanced_block_is_noop_at_baseline(self):
        self._write_block({"schema": 1, "default_review_preset": "balanced"})
        preset, err = _resolve(self.root, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)
        self.assertEqual(err, "")

    def test_full_block_is_baseline_plus_notice(self):
        self._write_block({"schema": 1, "default_review_preset": "full"})
        preset, err = _resolve(self.root, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)          # never silently becomes "full"
        self.assertIn(NOTICE_SUBSTR, err)

    def test_full_notice_for_diff_too(self):
        self._write_block({"schema": 1, "default_review_preset": "full"})
        _, err = _resolve(self.root, command="diff")
        self.assertIn(NOTICE_SUBSTR, err)

    def test_explicit_cheap_wins_over_full_floor(self):
        self._write_block({"schema": 1, "default_review_preset": "full"})
        preset, err = _resolve(self.root, preset="cheap", command="review")
        self.assertEqual(preset, "cheap")                     # explicit CLI wins
        self.assertEqual(err, "")                             # preferences not consulted

    def test_explicit_balanced_wins_no_notice(self):
        self._write_block({"schema": 1, "default_review_preset": "full"})
        preset, err = _resolve(self.root, preset="balanced", command="review")
        self.assertEqual(preset, "balanced")
        self.assertEqual(err, "")

    def test_no_preferences_suppresses_everything(self):
        self._write_block({"schema": 1, "default_review_preset": "full"})
        preset, err = _resolve(self.root, no_preferences=True, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)
        self.assertEqual(err, "")

    def test_unrelated_commands_never_consult_preferences(self):
        # extract / mini / full modes must not read the preference floor (review/diff only).
        self._write_block({"schema": 1, "default_review_preset": "full"})
        for command in ("extract", "mini", "full"):
            preset, err = _resolve(self.root, command=command)
            self.assertEqual(preset, cli.DEFAULT_PRESET, command)
            self.assertEqual(err, "", command)

    def test_full_notice_is_pinned_and_leaks_no_raw_json(self):
        # a full-floor block WITH paths: the notice is the fixed string and never echoes any
        # block content (paths / raw JSON).
        self._write_block({"schema": 1, "default_review_preset": "full",
                           "extra_sensitive_paths": ["infra/secret-marker/"],
                           "never_stage_extra": ["notes/leak-canary.md"]})
        _, err = _resolve(self.root, command="review")
        self.assertEqual(err.strip(), cli._PREF_FULL_FLOOR_NOTICE)   # exact pinned wording
        self.assertNotIn("secret-marker", err)
        self.assertNotIn("leak-canary", err)
        self.assertNotIn("{", err)                                   # no raw JSON

    def test_premium_is_never_resolvable_from_a_preference(self):
        # premium is unrepresentable in the schema; a block naming it is invalid -> baseline.
        self._write_block({"schema": 1, "default_review_preset": "premium"})
        preset, err = _resolve(self.root, command="review")
        self.assertEqual(preset, cli.DEFAULT_PRESET)
        self.assertNotEqual(preset, "premium")
        self.assertEqual(err, "")

    def test_genuine_raise_is_announced(self):
        # Guards the "unreachable at the balanced baseline" raise branch: simulate a LOWER
        # baseline so a "balanced" floor is strictly above it -> the preset is raised AND the
        # raise is announced on stderr (upholds "every non-no-op is announced"). Also proves
        # a preference can never lower (baseline cheap -> balanced is a raise, not a drop).
        self._write_block({"schema": 1, "default_review_preset": "balanced"})
        import backend.preferences as _prefs
        orig_cli, orig_prefs = cli.DEFAULT_PRESET, _prefs.DEFAULT_PRESET
        try:
            cli.DEFAULT_PRESET = "cheap"
            _prefs.DEFAULT_PRESET = "cheap"          # the reader compares against its own baseline
            preset, err = _resolve(self.root, command="review")
        finally:
            cli.DEFAULT_PRESET, _prefs.DEFAULT_PRESET = orig_cli, orig_prefs
        self.assertEqual(preset, "balanced")         # raised from cheap
        self.assertIn("raises the review preset floor to 'balanced'", err)
        self.assertNotIn("{", err)                   # no raw JSON

    def test_reader_exception_falls_back_to_baseline(self):
        # Defense in depth: if the (fail-closed) reader ever raised, review/diff must not crash.
        import backend.cli as _cli

        def _boom(_root):
            raise RuntimeError("unexpected")

        orig = _cli.preferences_mod.effective_suggestions
        try:
            _cli.preferences_mod.effective_suggestions = _boom
            preset, err = _resolve(self.root, command="review")
        finally:
            _cli.preferences_mod.effective_suggestions = orig
        self.assertEqual(preset, cli.DEFAULT_PRESET)
        self.assertEqual(err, "")


class TestRequireUsageWarning(_PrefsDir):
    """v0.9.0 PR 3 — the advisory `require_usage_flag` warning (review/diff only). It never adds
    --usage, never fails, is stderr-only, at most once, and leaks no raw JSON."""

    USAGE_SUBSTR = "sets require_usage_flag"

    def test_warns_on_review_without_usage(self):
        self._write_block({"schema": 1, "require_usage_flag": True})
        _, err = _resolve(self.root, command="review", usage=False)
        self.assertIn(self.USAGE_SUBSTR, err)

    def test_warns_on_diff_without_usage(self):
        self._write_block({"schema": 1, "require_usage_flag": True})
        _, err = _resolve(self.root, command="diff", usage=False)
        self.assertIn(self.USAGE_SUBSTR, err)

    def test_no_warning_with_usage(self):
        self._write_block({"schema": 1, "require_usage_flag": True})
        _, err = _resolve(self.root, command="review", usage=True)
        self.assertEqual(err, "")

    def test_no_warning_with_no_preferences(self):
        self._write_block({"schema": 1, "require_usage_flag": True})
        _, err = _resolve(self.root, command="review", usage=False, no_preferences=True)
        self.assertEqual(err, "")

    def test_require_usage_false_no_warning(self):
        self._write_block({"schema": 1, "require_usage_flag": False})
        _, err = _resolve(self.root, command="review", usage=False)
        self.assertEqual(err, "")

    def test_no_warning_for_missing_invalid_minimal(self):
        # missing file
        _, err = _resolve(self.root, command="review", usage=False)
        self.assertEqual(err, "")
        # minimal schema (key absent)
        self._write_block({"schema": 1})
        self.assertEqual(_resolve(self.root, command="review", usage=False)[1], "")
        # invalid block (fail-closed -> no warning)
        self._write_raw("```json\n{ \"schema\": 1, \"require_usage_flag\": \"yes\" }\n```\n")
        self.assertEqual(_resolve(self.root, command="review", usage=False)[1], "")

    def test_unrelated_commands_do_not_warn(self):
        self._write_block({"schema": 1, "require_usage_flag": True})
        for command in ("extract", "mini", "full"):
            _, err = _resolve(self.root, command=command, usage=False)
            self.assertEqual(err, "", command)

    def test_warning_is_pinned_and_leaks_no_raw_json(self):
        self._write_block({"schema": 1, "require_usage_flag": True,
                           "never_stage_extra": ["notes/leak-canary.md"]})
        _, err = _resolve(self.root, command="review", usage=False)
        self.assertEqual(err.strip(), cli._PREF_USAGE_WARNING)   # exact pinned wording
        self.assertNotIn("leak-canary", err)
        self.assertNotIn("{", err)                               # no raw JSON

    def test_warning_appears_at_most_once(self):
        self._write_block({"schema": 1, "require_usage_flag": True})
        _, err = _resolve(self.root, command="review", usage=False)
        self.assertEqual(err.count("require_usage_flag"), 1)


class TestUsageWarningCli(unittest.TestCase):
    """CLI-level (empty-diff path, no model call): the usage warning is stderr-only and is
    suppressed by --usage / --no-preferences."""

    USAGE_SUBSTR = "sets require_usage_flag"

    def _mk(self, obj):
        d = tempfile.mkdtemp()
        p = Path(d) / "docs/context/project"
        p.mkdir(parents=True)
        (p / "PREFERENCES.md").write_text(
            f"# prefs\n\n```json\n{json.dumps(obj)}\n```\n", encoding="utf-8")
        return d

    def test_usage_warning_on_stderr_not_stdout(self):
        d = self._mk({"schema": 1, "require_usage_flag": True})
        r = run_cli(["diff"], caller_cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("No changes to review", r.stdout)
        self.assertIn(self.USAGE_SUBSTR, r.stderr)
        self.assertNotIn(self.USAGE_SUBSTR, r.stdout)

    def test_usage_flag_suppresses_warning(self):
        d = self._mk({"schema": 1, "require_usage_flag": True})
        r = run_cli(["diff", "--usage"], caller_cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn(self.USAGE_SUBSTR, r.stderr)

    def test_no_preferences_suppresses_warning(self):
        d = self._mk({"schema": 1, "require_usage_flag": True})
        r = run_cli(["diff", "--no-preferences"], caller_cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn(self.USAGE_SUBSTR, r.stderr)


class TestDiffCliNoticeSurface(unittest.TestCase):
    """CLI-level via the empty-diff path (no model call): the notice is stderr-only, and
    --no-preferences / explicit --preset suppress it. Byte-identity for the no-block case."""

    def _mk(self, obj=None):
        d = tempfile.mkdtemp()
        if obj is not None:
            p = Path(d) / "docs/context/project"
            p.mkdir(parents=True)
            (p / "PREFERENCES.md").write_text(
                f"# prefs\n\n```json\n{json.dumps(obj)}\n```\n", encoding="utf-8")
        return d

    def test_full_floor_notice_on_stderr_not_stdout(self):
        d = self._mk({"schema": 1, "default_review_preset": "full"})
        r = run_cli(["diff"], caller_cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)     # empty diff -> clean exit
        self.assertIn("No changes to review", r.stdout)
        self.assertIn(NOTICE_SUBSTR, r.stderr)                     # notice -> stderr
        self.assertNotIn(NOTICE_SUBSTR, r.stdout)                  # never stdout

    def test_no_block_has_no_notice(self):
        d = self._mk(None)
        r = run_cli(["diff"], caller_cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("No changes to review", r.stdout)
        self.assertNotIn(NOTICE_SUBSTR, r.stderr)

    def test_no_preferences_suppresses_notice(self):
        d = self._mk({"schema": 1, "default_review_preset": "full"})
        r = run_cli(["diff", "--no-preferences"], caller_cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn(NOTICE_SUBSTR, r.stderr)

    def test_explicit_preset_suppresses_notice(self):
        d = self._mk({"schema": 1, "default_review_preset": "full"})
        r = run_cli(["diff", "--preset", "cheap"], caller_cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn(NOTICE_SUBSTR, r.stderr)

    def test_help_lists_no_preferences_flag(self):
        for command in ("review", "diff"):
            r = run_cli([command, "--help"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("--no-preferences", r.stdout)


if __name__ == "__main__":
    unittest.main()
