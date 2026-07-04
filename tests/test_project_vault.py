"""Tests for the project vault scaffold (docs/context/project/*.md, v0.6.2).

Stdlib-only (`unittest`). These assert the committed vault files exist, are curated and
public-safe (frame `/council` as a future idea, carry no-stage/never-store guidance), and
that the context pack — which is a *budgeted projection* built only from STATUS.md +
decisions, not the whole vault — never leaks a private plan filename. No model/API/network.
"""

import unittest
from pathlib import Path

from backend import context_pack as cp

REPO = Path(__file__).resolve().parents[1]
VAULT = REPO / "docs" / "context" / "project"

VAULT_FILES = ("README.md", "STATUS.md", "ROADMAP.md", "DECISIONS.md", "PROGRESS.md",
               "RISKS.md", "WORKFLOWS.md", "NOTES.md")

PRIVATE_PLAN_NAMES = (
    "commercialization-and-hosted-platform-feasibility.md",
    "v0.3.1-hardening-and-dogfood.md",
)


def _read(name: str) -> str:
    return (VAULT / name).read_text(encoding="utf-8")


class TestVaultFilesExist(unittest.TestCase):
    def test_all_vault_files_exist(self):
        for name in VAULT_FILES:
            self.assertTrue((VAULT / name).is_file(), f"missing vault file: {name}")

    def test_vault_files_are_nonempty_markdown(self):
        for name in VAULT_FILES:
            text = _read(name)
            self.assertGreater(len(text.strip()), 0, name)
            self.assertTrue(text.lstrip().startswith("#"), f"{name} should start with a heading")

    def test_vault_file_set_is_deterministic(self):
        # The committed *.md set under the vault root is exactly the scaffold (stable,
        # explicit — no stray/generated files committed here).
        md = {p.name for p in VAULT.glob("*.md")}
        self.assertEqual(md, set(VAULT_FILES))


class TestVaultContentGuardrails(unittest.TestCase):
    def test_readme_explains_purpose_and_read_before_coding(self):
        r = _read("README.md")
        self.assertIn("project vault", r.lower())
        self.assertIn("read this vault before", r.lower())
        # never-store guidance
        self.assertIn("Never store", r)
        self.assertIn("secrets", r)

    def test_council_is_framed_as_future_not_real(self):
        # Any vault file mentioning /council must frame it as NOT a real command today.
        for name in ("ROADMAP.md", "RISKS.md"):
            t = _read(name)
            if "/council" in t:
                self.assertTrue(
                    ("does **not** exist" in t) or ("does not exist" in t)
                    or ("not a real" in t.lower()) or ("future" in t.lower()),
                    f"{name} mentions /council without framing it as future/not-real")
        # the real CLI is vibe
        self.assertIn("vibe", _read("WORKFLOWS.md"))

    def test_never_store_warnings_present(self):
        # The vault as a whole carries no-stage / never-store guidance.
        risks = _read("RISKS.md")
        workflows = _read("WORKFLOWS.md")
        self.assertIn(".council/", workflows)
        self.assertIn("No-stage checklist", workflows)
        self.assertIn("secrets", risks)
        self.assertIn("never", risks.lower())

    def test_decisions_is_index_not_canonical_store(self):
        d = _read("DECISIONS.md")
        self.assertIn("docs/decisions/", d)               # points at the canonical store
        self.assertIn("index", d.lower())
        # explicitly states it is not the canonical store
        self.assertIn("canonical store", d.lower())
        self.assertIn("not", d.lower().split("canonical store")[0][-40:])

    def test_decisions_records_key_high_level_decisions(self):
        d = _read("DECISIONS.md").lower()
        self.assertIn("approval is separate from execution", d)
        self.assertIn("local-first", d)
        self.assertIn("fable", d)                          # architect/lead policy
        self.assertIn("project-vault root", d)


class TestContextPackDoesNotLeakPrivatePlans(unittest.TestCase):
    def test_pack_built_from_real_repo_has_no_private_plan_names(self):
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        for name in PRIVATE_PLAN_NAMES:
            self.assertNotIn(name, res.text,
                             f"context pack leaked a private plan filename: {name}")

    def test_pack_check_still_passes_on_real_repo(self):
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        report = cp.check_pack(res.text)
        # all checks pass and no critical redaction; vault files present don't break it.
        self.assertTrue(report.ok, report.reasons)
        self.assertEqual(report.passed, report.total, report.reasons)


if __name__ == "__main__":
    unittest.main()
