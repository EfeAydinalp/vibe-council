"""Tests for the context-quality harness (backend/context_pack.check_pack) + CLI.

Stdlib-only (`unittest`). Deterministic, no model/API/network. The fake key below
is a synthetic fixture, not a real key.
"""

import json
import os
import unittest
import tempfile
from pathlib import Path

from backend import context_pack as cp
from tests.test_cli_smoke import run_cli

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40

# A synthetic pack that satisfies every check (21/21) and is redaction-clean.
GOOD_PACK = """## Metadata

- generated_at: 2026-06-30T00:00:00Z
- pack_version: 1
- sources: STATUS=project/STATUS.md, decisions=docs/decisions (3 records)
- redaction: critical=0, warning=0

## Project identity

vibe-council = local-first council workflow + linked project memory.

## Current status

A short, current snapshot. STATUS.md is the current snapshot. See docs/decisions/
for the canonical decision records. Recent: decision CLI, draft extraction
(from-run), decision promotion, and context build all exist. Human review before
promotion is required.

## Recent decisions (full)

### Decision memory CLI skeleton (accepted, 2026-06-30)
body

## Decision index (older)

- 2026-06-30 . accepted . 2026-06-30-decision-promote - Curated decision promotion MVP

## Rejected alternatives index

- 2026-06-30-x: Alt rejected for reasons

## Constraints / safety notes

- Raw `.council/` outputs stay local and gitignored; never committed.
- The public repo holds only curated/redacted docs.
- A redaction guard exists: `vibe lint --redaction` / `vibe decisions lint`.
- License/provenance remains "Question 0" before serious commercialization.
"""


class TestCheck(unittest.TestCase):
    def test_good_pack_passes(self):
        res = cp.check_pack(GOOD_PACK)
        self.assertTrue(res.ok, res.reasons)
        self.assertEqual(res.passed, res.total)
        self.assertEqual(res.score, 1.0)

    def test_missing_required_section_fails(self):
        bad = GOOD_PACK.replace("## Decision index (older)", "## Something else")
        res = cp.check_pack(bad)
        self.assertFalse(res.ok)
        self.assertTrue(any("decision-index" in r for r in res.reasons))

    def test_missing_constraint_fails(self):
        bad = GOOD_PACK.replace('"Question 0"', "later")
        res = cp.check_pack(bad)
        self.assertFalse(res.ok)
        self.assertFalse(any(c.name == "constraint:license-question-zero" and c.ok
                             for c in res.checks))

    def test_redaction_critical_fails(self):
        bad = GOOD_PACK + f"\nleaked {FAKE_OR_KEY}\n"
        res = cp.check_pack(bad)
        self.assertFalse(res.ok)
        self.assertTrue(any("critical redaction" in r for r in res.reasons))

    def test_strict_fails_on_warning(self):
        warned = GOOD_PACK + "\npricing was $19/seat/mo for pro\n"
        self.assertTrue(cp.check_pack(warned).ok)              # advisory by default
        self.assertFalse(cp.check_pack(warned, strict=True).ok)  # strict fails on warning

    def test_min_score_threshold(self):
        # only the required sections + constraints -> ~48% (advisory all miss)
        minimal = (
            "## Metadata\n\n## Project identity\n\n## Current status\n\n"
            "## Recent decisions\n\n## Decision index\n\n## Constraints\n\n"
            "raw .council gitignored; curated/redacted docs; redaction guard; "
            'license "Question 0".\n'
        )
        self.assertFalse(cp.check_pack(minimal).ok)             # below default 0.8
        loose = cp.check_pack(minimal, min_score=0.4)
        self.assertTrue(loose.ok, loose.reasons)               # required pass, score ok

    def test_no_api_key_required(self):
        saved = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            self.assertTrue(cp.check_pack(GOOD_PACK).ok)
        finally:
            if saved is not None:
                os.environ["OPENROUTER_API_KEY"] = saved


class TestCheckCLI(unittest.TestCase):
    def _seed(self, root: Path, n: int = 8):
        ddir = root / "docs" / "decisions"
        ddir.mkdir(parents=True)
        for i in range(n):  # >recent count, so the builder emits a Decision index
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

    def test_missing_pack_message(self):
        with tempfile.TemporaryDirectory() as t:
            r = run_cli(["context", "check", "--file",
                         str(Path(t) / "nope.md")], caller_cwd=Path(t))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("vibe context build", r.stderr)

    def test_build_then_check_default_path_json(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._seed(root)
            b = run_cli(["context", "build"], caller_cwd=root)
            self.assertEqual(b.returncode, 0, b.stderr)
            # a minimal seed legitimately lacks many advisory facts; use a tolerant
            # threshold so this exercises the round-trip + JSON, not the full score.
            c = run_cli(["context", "check", "--json", "--min-score", "0.3"],
                        caller_cwd=root)
            self.assertEqual(c.returncode, 0, c.stderr + c.stdout)
            data = json.loads(c.stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["redaction"]["critical"], 0)
            self.assertIn("checks", data)


if __name__ == "__main__":
    unittest.main()
