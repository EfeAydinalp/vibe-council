"""Tests for `vibe decisions new --from-run` draft extraction
(backend/decisions_docs.extract_draft).

Stdlib-only (`unittest`). Pure functions over a source file + drafts dir — no
model, API key, or network. The fake key below is a synthetic fixture.
"""

import os
import unittest
import tempfile
from pathlib import Path

from backend import decisions_docs as dd

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40

SIMPLE_REVIEW = (
    "# Sample Review\n\n"
    "## Verdict\nProceed with changes.\n\n"
    "## Risks\n- risk one\n- risk two\n\n"
    "## Final action list\n- do a\n- do b\n"
)
LEAK_REVIEW = (
    "# Leaky Review\n\n"
    "## Verdict\nstop.\n\n"
    f"## Risks\n- found a key {FAKE_OR_KEY} in logs\n"
)


def _src(d: Path, content: str = SIMPLE_REVIEW, name: str = "review.md") -> Path:
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


class TestExtract(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.drafts = self.root / ".council" / "decisions" / "drafts"

    def tearDown(self):
        self._tmp.cleanup()

    def test_extracts_draft_to_drafts_dir(self):
        res = dd.extract_draft(_src(self.root), self.drafts, on="2026-06-30")
        self.assertTrue(res.ok and res.written)
        self.assertEqual(res.out_path.parent, self.drafts.resolve())
        self.assertEqual(res.out_path.name, "2026-06-30-sample-review.md")

    def test_draft_has_frontmatter_and_headings(self):
        res = dd.extract_draft(_src(self.root), self.drafts, on="2026-06-30")
        text = res.out_path.read_text(encoding="utf-8")
        fm, _ = dd._split_frontmatter(text)
        for field in dd.REQUIRED_FRONTMATTER:
            self.assertIn(field, fm)
        self.assertEqual(fm["status"], "proposed")
        self.assertEqual(fm["published"], "false")
        for h in dd.REQUIRED_HEADINGS:
            self.assertIn(f"## {h}", text)
        # extracted bits surfaced
        self.assertIn("Proceed with changes.", text)
        self.assertIn("risk one", text)
        self.assertIn("do a", text)
        self.assertIn("review.md", text)  # source reference

    def test_output_filename_sanitized(self):
        res = dd.extract_draft(_src(self.root, name="weird name!.md"),
                               self.drafts, title="Has /slash & *bad* chars",
                               on="2026-06-30")
        self.assertTrue(res.written)
        self.assertNotIn("/", res.out_path.name)
        self.assertNotIn("*", res.out_path.name)
        self.assertEqual(res.out_path.parent, self.drafts.resolve())

    def test_rejects_write_under_docs_decisions(self):
        bad_out = self.root / "docs" / "decisions" / "x.md"
        res = dd.extract_draft(_src(self.root), self.drafts, out_path=bad_out)
        self.assertFalse(res.ok)
        self.assertFalse(res.written)
        self.assertTrue(any("docs/decisions" in e for e in res.errors))
        self.assertFalse(bad_out.exists())

    def test_out_path_name_is_basename_only(self):
        # a traversal-y out name is reduced to a safe basename in the given dir
        target_dir = self.root / "safe"
        res = dd.extract_draft(_src(self.root), self.drafts,
                               out_path=target_dir / "..-..-evil.md")
        self.assertTrue(res.written)
        self.assertNotIn("..", res.out_path.name)
        self.assertEqual(res.out_path.parent, target_dir.resolve())

    def test_refuses_overwrite_without_force(self):
        s = _src(self.root)
        first = dd.extract_draft(s, self.drafts, on="2026-06-30")
        self.assertTrue(first.written)
        second = dd.extract_draft(s, self.drafts, on="2026-06-30")
        self.assertFalse(second.ok)
        self.assertTrue(any("exists" in e for e in second.errors))
        forced = dd.extract_draft(s, self.drafts, on="2026-06-30", force=True)
        self.assertTrue(forced.written)

    def test_dry_run_writes_nothing(self):
        res = dd.extract_draft(_src(self.root), self.drafts, dry_run=True,
                               on="2026-06-30")
        self.assertTrue(res.ok)
        self.assertFalse(res.written)
        self.assertFalse(self.drafts.exists())  # not created

    def test_redaction_findings_reported_and_masked(self):
        res = dd.extract_draft(_src(self.root, LEAK_REVIEW), self.drafts,
                               on="2026-06-30")
        self.assertTrue(res.written)  # local draft still written (advisory)
        self.assertTrue(res.redaction_findings)
        joined = " ".join(res.redaction_findings)
        self.assertIn("openrouter-key", joined)
        self.assertNotIn(FAKE_OR_KEY, joined)  # full secret never printed
        self.assertIn("***", joined)

    def test_does_not_write_to_repo_docs_decisions(self):
        # default extraction targets the drafts dir, never docs/decisions
        res = dd.extract_draft(_src(self.root), self.drafts, on="2026-06-30")
        self.assertNotIn("docs", [p.lower() for p in res.out_path.parts])

    def test_no_api_key_required(self):
        saved = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            res = dd.extract_draft(_src(self.root), self.drafts, on="2026-06-30")
            self.assertTrue(res.written)
        finally:
            if saved is not None:
                os.environ["OPENROUTER_API_KEY"] = saved

    def test_clean_draft_can_be_promoted(self):
        # extract a clean source -> draft -> promote into a curated dir succeeds
        res = dd.extract_draft(_src(self.root), self.drafts, on="2026-06-30")
        ddir = self.root / "docs" / "decisions"
        ddir.mkdir(parents=True)
        prom = dd.promote(res.out_path, ddir)
        self.assertTrue(prom.ok and prom.written)
        lint_errors = [i for i in dd.lint(ddir) if i.severity == "error"]
        self.assertEqual(lint_errors, [])


if __name__ == "__main__":
    unittest.main()
