"""Structural guards for the examples/ docs.

Stdlib-only (`unittest`), OS-agnostic, no model calls — these are file-content
assertions that catch the most likely rot in a docs/examples PR:
- an example file referenced by the README or examples index going missing,
- the README forgetting to link to examples/,
- a committed example accidentally embedding a `.council/`/`data/`/`.env` artifact
  path as if it were safe to commit.

They do NOT validate command output (that drifts and would need real model calls);
the examples themselves are clearly labeled "illustrative".
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"

EXPECTED_EXAMPLE_FILES = [
    "README.md",
    "plans/small-doc-fix.md",
    "plans/feature-plan.md",
    "workflows/review-diff-extract.md",
    "workflows/claude-code-loop.md",
]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestExampleFilesExist(unittest.TestCase):
    def test_all_expected_examples_present(self):
        for rel in EXPECTED_EXAMPLE_FILES:
            self.assertTrue((EXAMPLES / rel).is_file(), f"missing examples/{rel}")


class TestExamplesIndexLinks(unittest.TestCase):
    """The examples/README links must point at files that actually exist."""

    def test_index_links_resolve(self):
        index = EXAMPLES / "README.md"
        text = read(index)
        # Markdown links to local .md files, e.g. (plans/feature-plan.md)
        targets = re.findall(r"\]\((?!https?://)([^)]+\.md)\)", text)
        self.assertTrue(targets, "examples/README.md should link to example files")
        for t in targets:
            self.assertTrue((EXAMPLES / t).is_file(),
                            f"examples/README.md links to missing examples/{t}")


class TestReadmeLinksToExamples(unittest.TestCase):
    def test_readme_mentions_examples_dir(self):
        readme = read(REPO_ROOT / "README.md")
        self.assertIn("examples/", readme,
                      "README.md should link to the examples/ directory")


class TestExamplesDoNotCommitArtifacts(unittest.TestCase):
    """Examples must not present a `.council/`/`data/`/`.env` path as committable.

    Each example file must contain a 'do not commit' style warning if it mentions
    those local-only paths, so a reader copying commands isn't misled.
    """

    def test_local_paths_are_flagged_not_endorsed(self):
        sensitive = (".council/", "data/", ".env")
        for rel in EXPECTED_EXAMPLE_FILES:
            text = read(EXAMPLES / rel)
            if any(s in text for s in sensitive):
                lowered = text.lower()
                self.assertTrue(
                    ("not commit" in lowered) or ("gitignore" in lowered)
                    or ("local-only" in lowered) or ("local only" in lowered),
                    f"examples/{rel} mentions a local-only path but never warns "
                    f"against committing it",
                )


if __name__ == "__main__":
    unittest.main()
