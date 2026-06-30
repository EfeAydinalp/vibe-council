"""Tests for the context-pack builder (backend/context_pack.py) + the CLI.

Stdlib-only (`unittest`). Deterministic, no model/API/network. The fake key below
is a synthetic fixture, not a real key.
"""

import os
import unittest
import tempfile
from pathlib import Path

from backend import context_pack as cp
from backend import redaction
from tests.test_cli_smoke import run_cli

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40


def _rec(d: Path, stem: str, date: str, status: str = "accepted", extra: str = "") -> Path:
    content = (
        "---\n"
        f"id: DEC-{date.replace('-', '')}-{stem}\n"
        f"status: {status}\n"
        f"date: {date}\n"
        "tags: [t]\n"
        "related: []\n"
        "published: true\n"
        "---\n\n"
        f"# {stem} title\n\n"
        "## Context\n\nc\n\n"
        "## Decision\n\ndec\n\n"
        "## Rationale\n\nr\n\n"
        f"## Alternatives considered\n\n- **Alt {stem}** rejected for reasons\n\n"
        "## Consequences\n\nx\n\n"
        "## Next actions\n\nn\n\n"
        f"## Related links\n\nl\n{extra}"
    )
    p = d / f"{date}-{stem}.md"
    p.write_text(content, encoding="utf-8")
    return p


class TestBuild(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ddir = self.root / "docs" / "decisions"
        self.ddir.mkdir(parents=True)
        self.status = self.root / "STATUS.md"
        self.status.write_text("# Status\n\nCurrent focus: testing.\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _seed(self, n=8):
        for i in range(n):
            _rec(self.ddir, f"rec{i:02d}", f"2026-06-{10 + i:02d}")

    def test_builds_pack_with_sections(self):
        self._seed(8)
        res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
        t = res.text
        self.assertIn("## Metadata", t)
        self.assertIn("pack_version: 1", t)
        self.assertIn(cp.PROJECT_IDENTITY, t)
        self.assertIn("Current focus: testing.", t)          # status content
        self.assertIn("## Recent decisions (full)", t)
        self.assertIn("## Decision index (older)", t)         # 8 recs -> some indexed
        self.assertIn("## Constraints / safety notes", t)
        self.assertIn("Question 0", t)

    def test_respects_char_budget(self):
        self._seed(8)
        res = cp.build_pack(self.ddir, self.status, max_chars=2500,
                            on="2026-06-30T00:00:00Z")
        self.assertLessEqual(len(res.text), 2500)
        self.assertTrue(res.warnings)  # trimming happened

    def test_rejected_alternatives_index(self):
        self._seed(3)
        res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
        self.assertIn("## Rejected alternatives index", res.text)
        self.assertIn("Alt rec00", res.text)

    # --- budget headroom / trim-order stabilization (PR #55) ----------------- #

    def _seed_big(self, n=10, pad_lines=16):
        # sizeable bodies so a moderate budget forces trimming of recent bodies
        filler = "\n\n" + ("padding context line for budget testing.\n" * pad_lines)
        for i in range(n):
            _rec(self.ddir, f"rec{i:02d}", f"2026-06-{10 + i:02d}", extra=filler)

    def test_critical_signals_survive_normal_trim(self):
        # under budget pressure the build trims recent bodies / the older index
        # but KEEPS the dedicated rejected-alternatives index and the always-present
        # human-review constraint (critical signals are not dropped first).
        self._seed_big(10)
        res = cp.build_pack(self.ddir, self.status, max_chars=5000,
                            on="2026-06-30T00:00:00Z")
        self.assertTrue(res.warnings)  # trimming happened
        self.assertIn("## Rejected alternatives index", res.text)
        self.assertIn("human-reviewed", res.text)
        self.assertFalse(any("dropped rejected-alternatives index" in w
                             for w in res.warnings))

    def test_rejected_index_drawn_from_all_records(self):
        # even with only one recent full body, an alternative from a non-recent
        # record still surfaces (the rejected index is built from ALL records).
        self._seed_big(8)
        res = cp.build_pack(self.ddir, self.status, max_chars=20000, recent=1,
                            on="2026-06-30T00:00:00Z")
        self.assertIn("## Rejected alternatives index", res.text)
        self.assertIn("Alt rec00", res.text)  # oldest record, not in the single body
        self.assertEqual(res.text.count("### rec00 title"), 0)  # its body isn't included

    def test_rejected_index_dropped_only_as_last_resort(self):
        # with a punishing budget the rejected index is the LAST thing dropped —
        # only after recent/index/status have already been trimmed.
        self._seed_big(10)
        long_status = self.root / "LONGSTATUS.md"
        long_status.write_text("# Status\n\n" + ("status detail line.\n" * 80),
                               encoding="utf-8")
        res = cp.build_pack(self.ddir, long_status, max_chars=1300,
                            on="2026-06-30T00:00:00Z")
        ws = res.warnings
        self.assertTrue(any("dropped rejected-alternatives index" in w
                            and "last resort" in w for w in ws))
        status_i = next(i for i, w in enumerate(ws) if "truncated status" in w)
        rej_i = next(i for i, w in enumerate(ws)
                     if "dropped rejected-alternatives" in w)
        self.assertLess(status_i, rej_i)  # status trimmed before rejected dropped

    def test_status_truncation_is_one_shot(self):
        # status truncation must not loop forever (it would block the last resort)
        self._seed_big(10)
        long_status = self.root / "LONGSTATUS.md"
        long_status.write_text("# Status\n\n" + ("status detail line.\n" * 80),
                               encoding="utf-8")
        res = cp.build_pack(self.ddir, long_status, max_chars=1300,
                            on="2026-06-30T00:00:00Z")
        self.assertEqual(sum(1 for w in res.warnings
                             if "truncated status" in w), 1)

    def test_pinned_decisions_first(self):
        _rec(self.ddir, "normal", "2026-06-20")
        _rec(self.ddir, "important", "2026-06-10",
             extra="")  # older date, but pinned below
        # mark one pinned via frontmatter
        p = self.ddir / "2026-06-10-important.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "tags: [t]", "tags: [t]\npinned: true"), encoding="utf-8")
        res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
        self.assertIn("## Pinned / high-priority decisions", res.text)
        # pinned section appears before the recent-decisions section
        self.assertLess(res.text.index("## Pinned"), res.text.index("## Recent decisions"))

    def test_redaction_blocks_via_findings(self):
        _rec(self.ddir, "leak", "2026-06-20", extra=f"\nleaked {FAKE_OR_KEY}\n")
        res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
        self.assertTrue(any(f.severity == redaction.CRITICAL
                            for f in res.redaction_findings))

    def test_clean_pack_passes_redaction(self):
        self._seed(3)
        res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
        crit = [f for f in res.redaction_findings if f.severity == redaction.CRITICAL]
        self.assertEqual(crit, [])

    def test_missing_status_handled(self):
        self._seed(2)
        res = cp.build_pack(self.ddir, self.root / "nope.md",
                            on="2026-06-30T00:00:00Z")
        self.assertTrue(any("STATUS" in w for w in res.warnings))
        self.assertIn("_No STATUS.md found._", res.text)

    def test_missing_decisions_handled(self):
        empty = self.root / "empty"
        empty.mkdir()
        res = cp.build_pack(empty, self.status, on="2026-06-30T00:00:00Z")
        self.assertTrue(any("no curated decision records" in w for w in res.warnings))
        self.assertIn("## Metadata", res.text)
        self.assertIn("Current focus: testing.", res.text)

    def test_no_api_key_required(self):
        self._seed(2)
        saved = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
            self.assertIn("## Metadata", res.text)
        finally:
            if saved is not None:
                os.environ["OPENROUTER_API_KEY"] = saved

    def test_pack_includes_human_review_signal(self):
        # the generated pack must carry the promotion human-review boundary so the
        # context-check `memory:human-review` advisory is satisfied (v0.3.1 dogfood).
        self._seed(3)
        res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
        self.assertIn("human-reviewed", res.text)
        chk = cp.check_pack(res.text)
        hr = next(c for c in chk.checks if c.name == "memory:human-review")
        self.assertTrue(hr.ok)

    def test_human_review_check_fails_without_signal(self):
        # if the signal is absent the check must still fail (don't weaken the check)
        self._seed(3)
        res = cp.build_pack(self.ddir, self.status, on="2026-06-30T00:00:00Z")
        stripped = res.text
        for ph in ("human-reviewed", "human review", "review before", "before promotion"):
            stripped = stripped.replace(ph, "X")
        chk = cp.check_pack(stripped)
        hr = next(c for c in chk.checks if c.name == "memory:human-review")
        self.assertFalse(hr.ok)
        # redaction still runs over the (modified) pack
        self.assertIsInstance(chk.redaction_findings, list)


class TestContextCLI(unittest.TestCase):
    def test_default_output_path(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            ddir = root / "docs" / "decisions"
            ddir.mkdir(parents=True)
            _rec(ddir, "one", "2026-06-20")
            status_dir = root / "docs" / "context" / "project"
            status_dir.mkdir(parents=True)
            (status_dir / "STATUS.md").write_text("# Status\n\nok\n", encoding="utf-8")
            r = run_cli(["context", "build"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            pack = root / ".council" / "context" / "pack-latest.md"
            self.assertTrue(pack.is_file())
            self.assertIn("## Metadata", pack.read_text(encoding="utf-8"))

    def test_refuses_output_under_docs(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs" / "decisions").mkdir(parents=True)
            r = run_cli(["context", "build", "--output", "docs/pack.md"],
                        caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("refusing", r.stderr.lower())
            self.assertFalse((root / "docs" / "pack.md").exists())


if __name__ == "__main__":
    unittest.main()
