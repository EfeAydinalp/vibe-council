"""Tests for the curated decision-records layer (backend/decisions_docs.py).

Stdlib-only (`unittest`). Pure functions over a decisions directory — no model,
API key, or network. The fake key below is a synthetic fixture, not a real key.
"""

import unittest
import tempfile
from pathlib import Path

from backend import decisions_docs as dd

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_DECISIONS = REPO_ROOT / "docs" / "decisions"

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40

VALID_FM = (
    "---\n"
    "id: DEC-20260630-sample\n"
    "status: accepted\n"
    "date: 2026-06-30\n"
    "tags: [a, b]\n"
    "related: []\n"
    "published: true\n"
    "---\n\n"
    "# Sample\n\n"
)
VALID_BODY = "\n\n".join(f"## {h}\n\nx" for h in dd.REQUIRED_HEADINGS) + "\n"


def _write(d: Path, name: str, content: str) -> Path:
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


class TestListing(unittest.TestCase):
    def test_list_ignores_readme(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            _write(d, "README.md", "# index\n")
            _write(d, "2026-06-30-sample.md", VALID_FM + VALID_BODY)
            stems = [r.stem for r in dd.list_records(d)]
            self.assertIn("2026-06-30-sample", stems)
            self.assertNotIn("README", stems)

    def test_parses_frontmatter(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            p = _write(d, "2026-06-30-sample.md", VALID_FM + VALID_BODY)
            rec = dd.load_record(p)
            self.assertEqual(rec.frontmatter["id"], "DEC-20260630-sample")
            self.assertEqual(rec.frontmatter["status"], "accepted")
            self.assertEqual(rec.frontmatter["tags"], ["a", "b"])
            self.assertEqual(rec.frontmatter["related"], [])
            self.assertEqual(rec.title, "Sample")

    def test_empty_dir_lists_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(dd.list_records(Path(t) / "nope"), [])


class TestShow(unittest.TestCase):
    def test_find_by_stem(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            _write(d, "2026-06-30-sample.md", VALID_FM + VALID_BODY)
            self.assertIsNotNone(dd.find_record(d, "2026-06-30-sample"))

    def test_find_by_filename(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            _write(d, "2026-06-30-sample.md", VALID_FM + VALID_BODY)
            self.assertIsNotNone(dd.find_record(d, "2026-06-30-sample.md"))

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "docs" / "decisions"
            d.mkdir(parents=True)
            (d.parent.parent / "secret.md").write_text("top secret\n", encoding="utf-8")
            _write(d, "2026-06-30-sample.md", VALID_FM + VALID_BODY)
            # traversal / outside-dir identifiers must not resolve
            self.assertIsNone(dd.find_record(d, "../../secret"))
            self.assertIsNone(dd.find_record(d, "../../secret.md"))
            self.assertIsNone(dd.find_record(d, "nonexistent"))


class TestTemplate(unittest.TestCase):
    def test_template_has_required_frontmatter_and_headings(self):
        out = dd.template(title="My Choice", status="proposed", tags=["x"])
        for field in dd.REQUIRED_FRONTMATTER:
            self.assertRegex(out, rf"(?m)^{field}:")
        for h in dd.REQUIRED_HEADINGS:
            self.assertIn(f"## {h}", out)
        self.assertIn("# My Choice", out)
        self.assertIn("DEC-", out)


class TestLint(unittest.TestCase):
    def test_lint_passes_current_curated_decisions(self):
        # Guards the real repo records (must stay clean).
        issues = dd.lint(REPO_DECISIONS)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [], f"unexpected lint errors: {errors}")

    def test_lint_fails_on_missing_headings(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            _write(d, "2026-06-30-bad.md", VALID_FM + "## Context\n\nonly one heading\n")
            issues = dd.lint(d)
            self.assertTrue(dd.has_errors(issues))
            self.assertTrue(any(i.rule == "heading-missing" for i in issues))

    def test_lint_fails_on_missing_frontmatter(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            _write(d, "2026-06-30-bad.md", "# No frontmatter\n\n" + VALID_BODY)
            issues = dd.lint(d)
            self.assertTrue(dd.has_errors(issues))
            self.assertTrue(any(i.rule == "frontmatter-missing" for i in issues))

    def test_lint_catches_redaction_findings(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            body = VALID_BODY + f"\nleaked: {FAKE_OR_KEY}\n"
            _write(d, "2026-06-30-leak.md", VALID_FM + body)
            issues = dd.lint(d)
            self.assertTrue(dd.has_errors(issues))
            self.assertTrue(any(i.rule.startswith("redaction:") and i.severity == "error"
                                for i in issues))

    def test_lint_detects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            _write(d, "2026-06-30-a.md", VALID_FM + VALID_BODY)
            _write(d, "2026-06-30-b.md", VALID_FM + VALID_BODY)  # same id
            issues = dd.lint(d)
            self.assertTrue(any(i.rule == "duplicate-id" for i in issues))


if __name__ == "__main__":
    unittest.main()
