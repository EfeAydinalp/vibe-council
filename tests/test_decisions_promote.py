"""Tests for `vibe decisions promote` (backend/decisions_docs.promote).

Stdlib-only (`unittest`). Pure functions over a draft + decisions dir — no model,
API key, or network. The fake key below is a synthetic fixture, not a real key.
"""

import os
import unittest
import tempfile
from pathlib import Path

from backend import decisions_docs as dd

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40

FM = (
    "---\n"
    "id: DEC-20260630-sample\n"
    "status: accepted\n"
    "date: 2026-06-30\n"
    "tags: [a]\n"
    "related: []\n"
    "published: true\n"
    "---\n\n"
    "# Sample decision\n\n"
)
BODY = "\n\n".join(f"## {h}\n\nx" for h in dd.REQUIRED_HEADINGS) + "\n"
VALID_DRAFT = FM + BODY


def _draft(d: Path, content: str = VALID_DRAFT, name: str = "draft.md") -> Path:
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


class TestPromote(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ddir = self.root / "docs" / "decisions"
        self.ddir.mkdir(parents=True)
        self.drafts = self.root / "drafts"
        self.drafts.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_promotes_valid_draft(self):
        draft = _draft(self.drafts)
        res = dd.promote(draft, self.ddir)
        self.assertTrue(res.ok)
        self.assertTrue(res.written)
        self.assertTrue(res.out_path.is_file())
        self.assertEqual(res.out_path.name, "DEC-20260630-sample.md")
        self.assertEqual(res.out_path.parent, self.ddir.resolve())

    def test_refuses_missing_headings(self):
        bad = FM + "## Context\n\nonly one heading\n"
        res = dd.promote(_draft(self.drafts, bad), self.ddir)
        self.assertFalse(res.ok)
        self.assertFalse(res.written)
        self.assertTrue(any("heading-missing" in e for e in res.errors))
        self.assertEqual(list(self.ddir.iterdir()), [])  # nothing written

    def test_refuses_missing_frontmatter(self):
        bad = "# No frontmatter\n\n" + BODY
        res = dd.promote(_draft(self.drafts, bad), self.ddir)
        self.assertFalse(res.ok)
        self.assertTrue(any("frontmatter" in e for e in res.errors))

    def test_refuses_redaction_finding(self):
        bad = FM + BODY + f"\nleaked {FAKE_OR_KEY}\n"
        res = dd.promote(_draft(self.drafts, bad), self.ddir)
        self.assertFalse(res.ok)
        self.assertFalse(res.written)
        self.assertTrue(any("redaction:" in e for e in res.errors))

    def test_sanitizes_unsafe_id_and_no_traversal(self):
        evil = VALID_DRAFT.replace("id: DEC-20260630-sample",
                                   "id: ../../../etc/pwned")
        res = dd.promote(_draft(self.drafts, evil), self.ddir)
        self.assertTrue(res.ok)
        # filename sanitized: basename only, no separators / traversal
        self.assertNotIn("/", res.out_path.name)
        self.assertNotIn("\\", res.out_path.name)
        self.assertNotIn("..", res.out_path.name)
        self.assertEqual(res.out_path.parent, self.ddir.resolve())
        # nothing escaped outside the decisions dir
        self.assertFalse((self.root / "etc" / "pwned.md").exists())
        self.assertFalse((self.root.parent / "pwned.md").exists())

    def test_refuses_overwrite_without_force(self):
        draft = _draft(self.drafts)
        first = dd.promote(draft, self.ddir)
        self.assertTrue(first.written)
        second = dd.promote(draft, self.ddir)
        self.assertFalse(second.ok)
        self.assertTrue(any("exists" in e for e in second.errors))
        # with --force it succeeds
        forced = dd.promote(draft, self.ddir, force=True)
        self.assertTrue(forced.written)

    def test_dry_run_does_not_write(self):
        draft = _draft(self.drafts)
        res = dd.promote(draft, self.ddir, dry_run=True)
        self.assertTrue(res.ok)
        self.assertFalse(res.written)
        self.assertIsNotNone(res.out_path)
        self.assertEqual(list(self.ddir.iterdir()), [])  # nothing on disk

    def test_promoted_output_passes_decision_lint(self):
        dd.promote(_draft(self.drafts), self.ddir)
        issues = dd.lint(self.ddir)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [], f"unexpected lint errors: {errors}")

    def test_only_writes_one_file_no_side_effects(self):
        # promote does not stage/commit/touch anything else: only the one record.
        dd.promote(_draft(self.drafts), self.ddir)
        self.assertEqual([p.name for p in self.ddir.iterdir()],
                         ["DEC-20260630-sample.md"])

    def test_no_api_key_required(self):
        saved = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            res = dd.promote(_draft(self.drafts), self.ddir)
            self.assertTrue(res.written)
        finally:
            if saved is not None:
                os.environ["OPENROUTER_API_KEY"] = saved

    def test_bom_draft_is_tolerated_and_output_is_clean(self):
        # a draft saved with a UTF-8 BOM still promotes, and the result is BOM-free
        p = self.drafts / "bom.md"
        p.write_bytes(b"\xef\xbb\xbf" + VALID_DRAFT.encode("utf-8"))
        res = dd.promote(p, self.ddir)
        self.assertTrue(res.written)
        self.assertFalse(res.out_path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
