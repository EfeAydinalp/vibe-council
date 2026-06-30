"""UX-output tests for the v0.3.1 CLI polish (PR #51).

Stdlib-only (`unittest`); drives the CLI as a subprocess via the shared
``run_cli`` helper. No model/API/network. The fake key below is a synthetic
fixture, not a real key.
"""

import tempfile
import unittest
from pathlib import Path

from tests.test_cli_smoke import run_cli

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40


def _seed_repo(root: Path, n: int = 3) -> None:
    ddir = root / "docs" / "decisions"
    ddir.mkdir(parents=True)
    for i in range(n):
        stem = f"rec{i:02d}"
        (ddir / f"2026-06-{10 + i:02d}-{stem}.md").write_text(
            f"---\nid: DEC-202606{10 + i:02d}-{stem}\nstatus: accepted\n"
            f"date: 2026-06-{10 + i:02d}\ntags: [t]\nrelated: []\npublished: true\n"
            f"---\n\n# {stem}\n\n## Context\n\nc\n\n## Decision\n\nd\n\n"
            "## Rationale\n\nr\n\n## Alternatives considered\n\n- **Alt** rejected\n\n"
            "## Consequences\n\nx\n\n## Next actions\n\nn\n\n## Related links\n\nl\n",
            encoding="utf-8")
    sd = root / "docs" / "context" / "project"
    sd.mkdir(parents=True)
    (sd / "STATUS.md").write_text("# Status\n\nok\n", encoding="utf-8")


class TestRedactionLintVerdict(unittest.TestCase):
    def test_passed_verdict(self):
        with tempfile.TemporaryDirectory() as t:
            doc = Path(t) / "clean.md"
            doc.write_text("# Clean\n\nNothing secret here.\n", encoding="utf-8")
            r = run_cli(["lint", "--redaction", str(doc)], caller_cwd=Path(t))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("redaction lint passed:", r.stderr)
            self.assertIn("0 critical", r.stderr)

    def test_failed_verdict(self):
        with tempfile.TemporaryDirectory() as t:
            doc = Path(t) / "leak.md"
            doc.write_text(f"# Leak\n\nkey {FAKE_OR_KEY} oops\n", encoding="utf-8")
            r = run_cli(["lint", "--redaction", str(doc)], caller_cwd=Path(t))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("redaction lint FAILED:", r.stderr)
            self.assertNotIn(FAKE_OR_KEY, r.stderr + r.stdout)  # secret stays masked


class TestContextBuildBudgetNote(unittest.TestCase):
    def test_budget_note_on_trim(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_repo(root, n=4)
            r = run_cli(["context", "build", "--max-chars", "1500"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("exceeded the 1500-char budget", r.stderr)
            self.assertIn("--max-chars", r.stderr)

    def test_no_budget_note_when_roomy(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_repo(root, n=2)
            r = run_cli(["context", "build", "--max-chars", "50000"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("exceeded the", r.stderr)


class TestContextCheckAdvisorySuffix(unittest.TestCase):
    def test_advisory_miss_suffix(self):
        # a pack with required sections/constraints but missing advisory signals
        with tempfile.TemporaryDirectory() as t:
            pack = Path(t) / "pack.md"
            pack.write_text(
                "## Metadata\n\n## Project identity\n\n## Current status\n\n"
                "## Recent decisions\n\n## Decision index\n\n## Constraints\n\n"
                "raw .council gitignored; curated/redacted docs; redaction guard; "
                'license "Question 0".\n',
                encoding="utf-8")
            r = run_cli(["context", "check", "--file", str(pack),
                         "--min-score", "0.3"], caller_cwd=Path(t))
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("advisory miss(es)", r.stdout)


class TestDecisionsHelpBoundary(unittest.TestCase):
    def test_help_mentions_promotion_boundary(self):
        r = run_cli(["decisions", "--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("Promotion boundary", out)
        self.assertIn("LOCAL", out)
        self.assertIn("human-reviewed", out)


if __name__ == "__main__":
    unittest.main()
