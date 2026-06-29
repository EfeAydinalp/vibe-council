"""Tests for the redaction guard (backend/redaction.py).

Stdlib-only (`unittest`). Verifies critical-pattern detection, masking, clean
passes, explicit-path scanning, and default-scan directory exclusions. The fake
secrets below are synthetic test fixtures, not real keys.
"""

import unittest
from pathlib import Path
import tempfile

from backend import redaction


def _rule_ids(findings):
    return {f.rule_id for f in findings}


# Synthetic, clearly-fake values (never real secrets).
FAKE_OR_KEY = "sk-or-v1-" + "a" * 40
FAKE_LONG = "b" * 40


class TestDetection(unittest.TestCase):
    def test_detects_openrouter_key(self):
        f = redaction.scan_text(f"the key is {FAKE_OR_KEY} here")
        self.assertIn("openrouter-key", _rule_ids(f))
        self.assertTrue(all(x.severity == redaction.CRITICAL
                            for x in f if x.rule_id == "openrouter-key"))

    def test_detects_openrouter_api_key_assignment(self):
        f = redaction.scan_text(f"OPENROUTER_API_KEY={FAKE_OR_KEY}")
        self.assertIn("api-key-assignment", _rule_ids(f))

    def test_detects_generic_api_key_assignment(self):
        f = redaction.scan_text(f"ANTHROPIC_API_KEY={FAKE_LONG}")
        self.assertIn("api-key-assignment", _rule_ids(f))

    def test_detects_private_key_block(self):
        f = redaction.scan_text("-----BEGIN RSA PRIVATE KEY-----")
        self.assertIn("private-key-block", _rule_ids(f))

    def test_detects_windows_local_path(self):
        f = redaction.scan_text(r"see C:\Users\alice\Desktop\notes.md")
        self.assertIn("windows-user-path", _rule_ids(f))

    def test_detects_unix_local_paths(self):
        f = redaction.scan_text("at /Users/alice/x and /home/bob/y")
        ids = _rule_ids(f)
        self.assertIn("unix-user-path", ids)
        # two distinct user paths on the line
        self.assertEqual(sum(1 for x in f if x.rule_id == "unix-user-path"), 2)

    def test_placeholder_unix_path_is_allowed(self):
        f = redaction.scan_text("example path /home/dev/vibe-demo is fine")
        self.assertNotIn("unix-user-path", _rule_ids(f))

    def test_placeholder_windows_path_is_allowed(self):
        f = redaction.scan_text(r"e.g. C:\Users\you\project")
        self.assertNotIn("windows-user-path", _rule_ids(f))

    def test_detects_concrete_council_reviews_path(self):
        f = redaction.scan_text(".council/reviews/2026-06-29T12-00-00_review.md")
        self.assertIn("council-artifact-path", _rule_ids(f))

    def test_council_convention_mention_is_allowed(self):
        # benign convention references (no date-stamped file) must not fire
        f = redaction.scan_text("records land in `.council/decisions/index.jsonl`")
        self.assertNotIn("council-artifact-path", _rule_ids(f))

    def test_detects_obsidian_workspace(self):
        f = redaction.scan_text("do not commit .obsidian/workspace.json")
        self.assertIn("obsidian-workspace", _rule_ids(f))


class TestMasking(unittest.TestCase):
    def test_masks_secret_output(self):
        f = redaction.scan_text(FAKE_OR_KEY)
        key_findings = [x for x in f if x.rule_id == "openrouter-key"]
        self.assertTrue(key_findings)
        for x in key_findings:
            self.assertNotIn(FAKE_OR_KEY, x.match)   # full secret never printed
            self.assertIn("***", x.match)

    def test_masks_windows_username(self):
        f = redaction.scan_text(r"C:\Users\alice\x")
        m = [x for x in f if x.rule_id == "windows-user-path"][0]
        self.assertNotIn("alice", m.match)
        self.assertIn("***", m.match)


class TestCleanAndSeverity(unittest.TestCase):
    def test_clean_markdown_passes(self):
        text = ("# Title\n\nThis is a normal doc with a [link](docs/x.md) and "
                "a code span `vibe review`. Nothing risky here.\n")
        f = redaction.scan_text(text)
        self.assertEqual(f, [])
        self.assertFalse(redaction.has_blocking(f))

    def test_has_blocking_critical(self):
        f = redaction.scan_text(FAKE_OR_KEY)
        self.assertTrue(redaction.has_blocking(f))

    def test_warning_not_blocking_unless_strict(self):
        f = redaction.scan_text("pricing was $19/seat/mo for the pro tier")
        self.assertIn("cost-pricing", _rule_ids(f))
        self.assertFalse(redaction.has_blocking(f))            # advisory by default
        self.assertTrue(redaction.has_blocking(f, strict=True))  # fails under strict


class TestPathScanning(unittest.TestCase):
    def test_explicit_path_scanning(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "leak.md"
            p.write_text(f"oops {FAKE_OR_KEY}\n", encoding="utf-8")
            findings = redaction.scan_paths([str(p)], Path(d))
            self.assertIn("openrouter-key", _rule_ids(findings))

    def test_default_scan_excludes_council_and_venv(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            (root / "docs" / "ok.md").write_text("# clean\n", encoding="utf-8")
            for excluded in (".council", ".venv"):
                sub = root / "docs" / excluded
                sub.mkdir()
                (sub / "leak.md").write_text(f"{FAKE_OR_KEY}\n", encoding="utf-8")
            # No git repo in the tmp dir -> filesystem-walk fallback.
            targets = [t.as_posix() for t in redaction.default_targets(root)]
            self.assertTrue(any(t.endswith("docs/ok.md") for t in targets))
            self.assertFalse(any(".council" in t for t in targets))
            self.assertFalse(any(".venv" in t for t in targets))


if __name__ == "__main__":
    unittest.main()
