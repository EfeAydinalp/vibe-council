"""Tests for the read-only preference-schema v1 validator (v0.8.2 PR 8).

Stdlib-only (`unittest`). The validator (`backend/preferences.py`) is **read-only, fail-closed,
findings-only, and advisory**: it reads exactly one file (`docs/context/project/PREFERENCES.md`)
inside the project root, validates the optional schema v1 ```json block, and returns findings —
never parsed settings, never applied to behavior. It writes nothing, creates no `.council/`, and
never reads a `.council/profile.*` store. Any anomaly fails closed to "invalid, ignored".
"""

import json
import os
import re
import unittest
import tempfile
from pathlib import Path

from backend import preferences as prefs

REPO = Path(__file__).resolve().parents[1]
REL = "docs/context/project/PREFERENCES.md"

CANONICAL = {
    "schema": 1,
    "default_review_preset": "balanced",
    "extra_sensitive_paths": ["infra/prod/", "ops/deploy/"],
    "never_stage_extra": ["notes/local-scratch.md"],
    "require_usage_flag": True,
}


def _levels(findings):
    return [f.level for f in findings]


def _text(findings):
    return "\n".join(f.message for f in findings)


class _TmpProject(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "docs/context/project").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_prefs(self, body: str) -> Path:
        p = self.root / REL
        p.write_text(body, encoding="utf-8")
        return p

    def _write_block(self, obj_text: str, prose: str = "# Project preferences\n\nintro\n") -> Path:
        return self._write_prefs(f"{prose}\n```json\n{obj_text}\n```\n")

    def _validate(self):
        return prefs.validate_preferences(self.root)

    def _suggest(self):
        return prefs.effective_suggestions(self.root)


class TestValidBlocks(_TmpProject):
    def test_canonical_block_is_ok(self):
        self._write_block(json.dumps(CANONICAL, indent=2))
        findings = self._validate()
        self.assertEqual(findings[0].level, "ok", _text(findings))
        self.assertNotIn("warn", _levels(findings))

    def test_minimal_schema_only_is_ok(self):
        self._write_block('{ "schema": 1 }')
        findings = self._validate()
        self.assertEqual(findings[0].level, "ok", _text(findings))

    def test_all_presets_valid(self):
        for preset in ("cheap", "balanced", "full"):
            self._write_block(json.dumps({"schema": 1, "default_review_preset": preset}))
            findings = self._validate()
            self.assertEqual(findings[0].level, "ok", f"{preset}: {_text(findings)}")


class TestMissingCases(_TmpProject):
    def test_missing_file_is_info(self):
        # no PREFERENCES.md at all
        findings = prefs.validate_preferences(self.root)
        self.assertEqual(_levels(findings), ["info"])
        self.assertIn("skipping", _text(findings).lower())

    def test_prose_only_no_block_is_info(self):
        self._write_prefs("# Project preferences\n\njust prose, no json block.\n")
        findings = self._validate()
        self.assertEqual(_levels(findings), ["info"])
        self.assertIn("prose-only", _text(findings).lower())


class TestInvalidBlocksFailClosed(_TmpProject):
    def _assert_invalid(self, needle=None):
        findings = self._validate()
        self.assertNotIn("ok", _levels(findings), _text(findings))
        self.assertIn("warn", _levels(findings))
        self.assertIn("ignored", _text(findings).lower())
        if needle:
            self.assertIn(needle, _text(findings).lower())

    def test_malformed_json_fails_closed(self):
        self._write_block('{ "schema": 1, ')  # truncated
        self._assert_invalid("not valid json")

    def test_missing_schema_invalid(self):
        self._write_block('{ "default_review_preset": "balanced" }')
        self._assert_invalid("schema")

    def test_unknown_schema_version_invalid(self):
        self._write_block('{ "schema": 2 }')
        self._assert_invalid("unknown schema version")

    def test_schema_true_is_not_version_1(self):
        # JSON true == 1 in Python truthiness, but must be rejected as a non-integer version.
        self._write_block('{ "schema": true }')
        self._assert_invalid("unknown schema version")

    def test_unknown_key_invalid(self):
        self._write_block('{ "schema": 1, "allow_commands": ["rm -rf"] }')
        self._assert_invalid("unknown key")

    def test_premium_preset_invalid_as_loosening(self):
        self._write_block('{ "schema": 1, "default_review_preset": "premium" }')
        self._assert_invalid("premium")

    def test_invalid_preset_invalid(self):
        self._write_block('{ "schema": 1, "default_review_preset": "turbo" }')
        self._assert_invalid("default_review_preset")

    def test_require_usage_flag_non_bool_invalid(self):
        self._write_block('{ "schema": 1, "require_usage_flag": "yes" }')
        self._assert_invalid("boolean")

    def test_absolute_path_invalid(self):
        self._write_block('{ "schema": 1, "extra_sensitive_paths": ["/etc/passwd"] }')
        self._assert_invalid("absolute")

    def test_dotdot_traversal_invalid(self):
        self._write_block('{ "schema": 1, "never_stage_extra": ["../outside.md"] }')
        self._assert_invalid("traversal")

    def test_backslash_windows_traversal_invalid(self):
        self._write_block(r'{ "schema": 1, "extra_sensitive_paths": ["..\\win\\secret"] }')
        self._assert_invalid("backslash")

    def test_drive_letter_invalid(self):
        self._write_block(r'{ "schema": 1, "never_stage_extra": ["C:/Windows/system32"] }')
        self._assert_invalid("drive-letter")

    def test_non_string_path_invalid(self):
        self._write_block('{ "schema": 1, "extra_sensitive_paths": [123] }')
        self._assert_invalid("strings")

    def test_non_list_path_collection_invalid(self):
        self._write_block('{ "schema": 1, "never_stage_extra": "notes/x.md" }')
        self._assert_invalid("array")

    def test_top_level_not_object_invalid(self):
        self._write_block('[1, 2, 3]')
        self._assert_invalid("object")

    def test_multiple_json_blocks_invalid(self):
        body = ("# prefs\n\n```json\n{ \"schema\": 1 }\n```\n\nmore\n\n"
                "```json\n{ \"schema\": 1 }\n```\n")
        self._write_prefs(body)
        self._assert_invalid("at most one")

    def test_oversized_block_invalid(self):
        big = {"schema": 1, "extra_sensitive_paths": ["a/" * 3000]}
        self._write_block(json.dumps(big))
        self._assert_invalid("cap")


class TestSoftWarnings(_TmpProject):
    def test_empty_array_warns_but_block_still_valid(self):
        self._write_block('{ "schema": 1, "extra_sensitive_paths": [] }')
        findings = self._validate()
        self.assertEqual(findings[0].level, "ok", _text(findings))
        self.assertIn("warn", _levels(findings))
        self.assertIn("empty array", _text(findings).lower())

    def test_duplicate_path_warns_but_valid(self):
        self._write_block('{ "schema": 1, "never_stage_extra": ["a.md", "a.md"] }')
        findings = self._validate()
        self.assertEqual(findings[0].level, "ok", _text(findings))
        self.assertIn("duplicate", _text(findings).lower())


class TestHardeningAndReadOnly(_TmpProject):
    def test_validator_writes_nothing_and_no_council(self):
        self._write_block(json.dumps(CANONICAL))
        before = sorted(p.relative_to(self.root).as_posix()
                        for p in self.root.rglob("*") if p.is_file())
        self._validate()
        after = sorted(p.relative_to(self.root).as_posix()
                       for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(before, after)                       # nothing written
        self.assertFalse((self.root / ".council").exists())    # no .council/ created

    def test_validator_never_reads_local_profile(self):
        # A .council/profile.* with a secret must never be read into the findings.
        self._write_block(json.dumps(CANONICAL))
        (self.root / ".council").mkdir()
        (self.root / ".council" / "profile.json").write_text(
            '{"secret": "SUPERSECRET_do_not_leak"}\n', encoding="utf-8")
        findings = self._validate()
        self.assertNotIn("SUPERSECRET_do_not_leak", _text(findings))

    def test_undecodable_file_warns_cleanly(self):
        p = self.root / REL
        p.write_bytes(b"\xff\xfe\x00\x01 not utf-8 \x80\x81")
        findings = self._validate()
        self.assertEqual(_levels(findings), ["warn"])
        self.assertIn("utf-8", _text(findings).lower())

    def test_findings_are_findings_only_not_settings(self):
        # The public API returns Finding(level, message) tuples — no parsed values leak.
        self._write_block(json.dumps(CANONICAL))
        findings = self._validate()
        for f in findings:
            self.assertIsInstance(f, prefs.Finding)
            self.assertEqual(set(f._fields), {"level", "message"})
            self.assertIn(f.level, ("ok", "warn", "info"))
            # the concrete parsed preset value must not be echoed back as a field/attr
            self.assertFalse(hasattr(f, "value"))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unsupported")
    def test_symlink_escape_out_of_root_is_generic_warn(self):
        # PREFERENCES.md is a symlink pointing OUTSIDE the project root -> generic warn,
        # no content/target leak. Skips gracefully if the OS forbids symlink creation.
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "evil-prefs.md"
            target.write_text('```json\n{ "schema": 1 }\n```\n', encoding="utf-8")
            link = self.root / REL
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not permitted on this platform")
            findings = self._validate()
            self.assertEqual(_levels(findings), ["warn"])
            low = _text(findings).lower()
            self.assertIn("outside the project root", low)
            # must not leak the target path or its content
            self.assertNotIn("evil-prefs", _text(findings))
            self.assertNotIn(outside, _text(findings))


class TestRealRepo(unittest.TestCase):
    def test_real_repo_block_is_valid(self):
        findings = prefs.validate_preferences(REPO)
        self.assertEqual(findings[0].level, "ok", _text(findings))
        self.assertNotIn("warn", _levels(findings))


class TestEffectiveSuggestions(_TmpProject):
    """v0.9.0 PR 1 — the clamped, fail-closed `effective_suggestions()` reader.

    It returns only clamped `Suggestions` (never raw JSON), `NEUTRAL` on any anomaly, a floor
    only STRICTLY above the baseline preset, re-validated path tuples, and applies nothing.
    """

    def test_neutral_shape(self):
        n = prefs.NEUTRAL
        self.assertIsNone(n.review_preset_floor)
        self.assertFalse(n.require_usage)
        self.assertEqual(n.extra_sensitive_paths, ())
        self.assertEqual(n.never_stage_extra, ())

    def test_canonical_block_clamps_correctly(self):
        # baseline is "balanced", so a "balanced" default_review_preset is NOT above baseline
        # -> no floor; paths + usage still surface.
        self._write_block(json.dumps(CANONICAL))
        s = self._suggest()
        self.assertIsNone(s.review_preset_floor)                       # balanced == baseline
        self.assertTrue(s.require_usage)
        self.assertEqual(s.extra_sensitive_paths, ("infra/prod/", "ops/deploy/"))
        self.assertEqual(s.never_stage_extra, ("notes/local-scratch.md",))

    def test_full_is_the_only_floor_above_baseline(self):
        # "full" is strictly above the "balanced" baseline -> it is the floor value. (The CLI
        # layer, PR 2, renders this as a notice-only recommendation to run `vibe full`; the
        # reader's job is only to represent it, per plan §5.1/§5.2.)
        self._write_block(json.dumps({"schema": 1, "default_review_preset": "full"}))
        self.assertEqual(self._suggest().review_preset_floor, "full")

    def test_cheap_and_balanced_never_produce_a_floor(self):
        # tighten-only: a value at/below baseline can never lower anything -> no floor.
        for preset in ("cheap", "balanced"):
            self._write_block(json.dumps({"schema": 1, "default_review_preset": preset}))
            self.assertIsNone(self._suggest().review_preset_floor, preset)

    def test_premium_never_escapes_as_a_floor(self):
        # premium is not in the enum -> the block is invalid -> NEUTRAL (never a floor).
        self._write_block(json.dumps({"schema": 1, "default_review_preset": "premium"}))
        self.assertEqual(self._suggest(), prefs.NEUTRAL)

    def test_minimal_schema_only_is_neutral(self):
        self._write_block('{ "schema": 1 }')
        self.assertEqual(self._suggest(), prefs.NEUTRAL)

    def test_missing_file_is_neutral(self):
        self.assertEqual(prefs.effective_suggestions(self.root), prefs.NEUTRAL)

    def test_missing_block_is_neutral(self):
        self._write_prefs("# prefs\n\njust prose.\n")
        self.assertEqual(self._suggest(), prefs.NEUTRAL)

    def test_require_usage_only_when_true(self):
        self._write_block(json.dumps({"schema": 1, "require_usage_flag": True}))
        self.assertTrue(self._suggest().require_usage)
        self._write_block(json.dumps({"schema": 1, "require_usage_flag": False}))
        self.assertFalse(self._suggest().require_usage)

    def test_paths_deduped_and_ordered(self):
        self._write_block(json.dumps(
            {"schema": 1, "never_stage_extra": ["a.md", "b.md", "a.md"]}))
        self.assertEqual(self._suggest().never_stage_extra, ("a.md", "b.md"))

    def test_empty_arrays_are_valid_and_yield_empty_tuples(self):
        # empty array is a soft warn (block still valid) -> tuples are ().
        self._write_block(json.dumps({"schema": 1, "extra_sensitive_paths": []}))
        s = self._suggest()
        self.assertEqual(s.extra_sensitive_paths, ())
        self.assertEqual(s, prefs.NEUTRAL)

    def test_fail_closed_matrix_matches_the_validator(self):
        # Every block the VALIDATOR rejects (invalid -> ignored) must read as NEUTRAL. This is
        # the shared anti-drift matrix (plan §8.8): validator "ignored" <=> reader NEUTRAL.
        invalid_blocks = [
            '{ "default_review_preset": "balanced" }',              # missing schema
            '{ "schema": 2 }',                                      # unknown version
            '{ "schema": true }',                                   # bool schema
            '{ "schema": 1, "allow_commands": ["rm -rf"] }',        # unknown key
            '{ "schema": 1, "default_review_preset": "premium" }',  # premium
            '{ "schema": 1, "default_review_preset": "turbo" }',    # bad enum
            '{ "schema": 1, "require_usage_flag": "yes" }',         # non-bool
            '{ "schema": 1, "extra_sensitive_paths": ["/etc/passwd"] }',  # absolute
            '{ "schema": 1, "never_stage_extra": ["../out.md"] }',  # traversal
            r'{ "schema": 1, "extra_sensitive_paths": ["a\\b"] }',  # backslash
            '{ "schema": 1, "never_stage_extra": [123] }',          # non-string
            '{ "schema": 1, "never_stage_extra": "x.md" }',         # non-list
            '[1, 2, 3]',                                            # not an object
            '{ "schema": 1, ',                                      # malformed JSON
        ]
        for body in invalid_blocks:
            self._write_block(body)
            findings = self._validate()
            invalid = any("ignored" in f.message.lower() for f in findings)
            self.assertTrue(invalid, f"validator should reject: {body}")
            self.assertEqual(self._suggest(), prefs.NEUTRAL, f"reader not NEUTRAL for: {body}")

    def test_multiple_blocks_and_oversize_are_neutral(self):
        self._write_prefs("```json\n{ \"schema\": 1 }\n```\n\n```json\n{ \"schema\": 1 }\n```\n")
        self.assertEqual(self._suggest(), prefs.NEUTRAL)                      # >1 block
        big = {"schema": 1, "extra_sensitive_paths": ["a/" * 3000]}
        self._write_block(json.dumps(big))
        self.assertEqual(self._suggest(), prefs.NEUTRAL)                      # oversized

    def test_returns_no_raw_json_or_settings(self):
        # The public shape is exactly four clamped fields — no dict, no get(), no raw block.
        self._write_block(json.dumps(CANONICAL))
        s = self._suggest()
        self.assertIsInstance(s, prefs.Suggestions)
        self.assertEqual(set(s._fields),
                         {"review_preset_floor", "require_usage",
                          "extra_sensitive_paths", "never_stage_extra"})
        self.assertFalse(hasattr(s, "get"))
        self.assertFalse(hasattr(s, "keys"))
        # no field carries a dict / arbitrary parsed object
        for v in s:
            self.assertNotIsInstance(v, dict)

    def test_suggestions_are_immutable(self):
        s = self._suggest()
        with self.assertRaises(AttributeError):
            s.require_usage = True            # NamedTuple fields are read-only

    def test_reader_writes_nothing_and_no_council(self):
        self._write_block(json.dumps(CANONICAL))
        before = sorted(p.relative_to(self.root).as_posix()
                        for p in self.root.rglob("*") if p.is_file())
        self._suggest()
        after = sorted(p.relative_to(self.root).as_posix()
                       for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(before, after)
        self.assertFalse((self.root / ".council").exists())

    def test_reader_never_reads_local_profile(self):
        self._write_block(json.dumps(CANONICAL))
        (self.root / ".council").mkdir()
        (self.root / ".council" / "profile.json").write_text(
            '{"default_review_preset": "cheap", "secret": "LEAK_ME"}\n', encoding="utf-8")
        s = self._suggest()
        # the local profile is never consulted: canonical (balanced) still yields no floor,
        # and nothing from the secret file influences the result.
        self.assertIsNone(s.review_preset_floor)
        self.assertEqual(s, prefs.effective_suggestions(self.root))   # deterministic, unaffected

    def test_deterministic(self):
        self._write_block(json.dumps(CANONICAL))
        self.assertEqual(self._suggest(), self._suggest())


class TestRealRepoSuggestions(unittest.TestCase):
    def test_real_repo_block_is_clamped(self):
        # The committed PREFERENCES.md sets default_review_preset=balanced (== baseline) -> no
        # floor; whatever paths/usage it declares are validated tuples/bool. Never raises.
        s = prefs.effective_suggestions(REPO)
        self.assertIsInstance(s, prefs.Suggestions)
        self.assertIn(s.review_preset_floor, (None, "full"))
        self.assertIsInstance(s.require_usage, bool)
        self.assertIsInstance(s.extra_sensitive_paths, tuple)


class TestNoOutsideImport(unittest.TestCase):
    """Contract: no module outside the doctor path (cli.py) imports backend.preferences —
    the validator/reader has exactly one consumer (cli.py), never a behavior path. This is the
    allowlist-first scan (plan §5.2): the importer set must equal exactly {"cli.py"}."""

    _IMPORT_RE = re.compile(
        r"(from\s+\.\s+import\s+[^\n]*\bpreferences\b"
        r"|from\s+\.preferences\s+import"
        r"|import\s+backend\.preferences"
        r"|from\s+backend\s+import\s+[^\n]*\bpreferences\b"
        r"|from\s+backend\.preferences\s+import)")

    def test_importer_set_is_exactly_cli(self):
        # Allowlist-first: scan EVERY backend/*.py (except preferences.py itself) and assert the
        # set of modules importing backend.preferences is exactly {"cli.py"}. Any new importer
        # anywhere — a workbench_*, council, providers, guards, mcp_*, context_pack module —
        # fails the suite by construction (a preference must never reach a behavior/trust path).
        backend = REPO / "backend"
        importers = set()
        for py in backend.glob("*.py"):
            if py.name == "preferences.py":
                continue
            if self._IMPORT_RE.search(py.read_text(encoding="utf-8")):
                importers.add(py.name)
        self.assertEqual(importers, {"cli.py"},
                         f"backend.preferences importer set must be exactly {{'cli.py'}}; "
                         f"got: {sorted(importers)}")

    def test_cli_does_import_it(self):
        # sanity: the doctor path is the one legitimate consumer.
        text = (REPO / "backend" / "cli.py").read_text(encoding="utf-8")
        self.assertTrue(self._IMPORT_RE.search(text), "cli.py should import backend.preferences")


if __name__ == "__main__":
    unittest.main()
