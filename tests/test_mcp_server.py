"""Tests for the read-only MCP server skeleton (backend/mcp_server.py) + CLI.

Stdlib-only (`unittest`). Pure read layer over a temp tree — no server, no socket,
no MCP dependency, no model/API/network, nothing written. Asserts the PR-#57 surface
(status + curated decisions only), the path/`.council`/private-plan guards, and that
forbidden + deferred tools are not reachable.
"""

import json
import os
import unittest
import tempfile
from pathlib import Path

from backend import mcp_server as ms
from backend import mcp_contract as mc
from tests.test_cli_smoke import run_cli

DECISION = (
    "---\n"
    "id: DEC-20260101-sample\n"
    "status: accepted\n"
    "date: 2026-01-01\n"
    "tags: [t]\n"
    "related: []\n"
    "published: true\n"
    "---\n\n"
    "# Sample decision\n\n"
    "## Context\n\nc\n\n## Decision\n\nd\n\n## Rationale\n\nr\n\n"
    "## Alternatives considered\n\n- **Alt** rejected\n\n## Consequences\n\nx\n\n"
    "## Next actions\n\nn\n\n## Related links\n\nl\n"
)


def _make_repo(root: Path) -> None:
    ddir = root / "docs" / "decisions"
    ddir.mkdir(parents=True)
    (ddir / "2026-01-01-sample.md").write_text(DECISION, encoding="utf-8")
    sd = root / "docs" / "context" / "project"
    sd.mkdir(parents=True)
    (sd / "STATUS.md").write_text("# Status\n\nCurrent focus: testing.\n", encoding="utf-8")
    # decoys that must NEVER be read by the read layer:
    drafts = root / ".council" / "decisions" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "2026-01-02-draft.md").write_text(DECISION.replace("sample", "draft"),
                                                encoding="utf-8")
    plans = root / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "private-thing.md").write_text("# Private\n\nsecret-ish plan\n", encoding="utf-8")


class TestReadLayer(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_enabled_surface_is_status_and_decisions_only(self):
        self.assertEqual(set(ms.ENABLED_TOOLS),
                         {"get_project_status", "list_decisions", "show_decision"})
        self.assertEqual(set(ms.ENABLED_RESOURCES),
                         {"vibe://status", "vibe://decisions", "vibe://decisions/{id}"})

    def test_server_contract_valid(self):
        self.assertEqual(ms.validate_server_contract(), [])

    def test_forbidden_tools_not_enabled_or_dispatchable(self):
        for n in mc.FORBIDDEN_TOOLS:
            self.assertNotIn(n, ms.ENABLED_TOOLS)
            with self.assertRaises(ms.ReadError):
                ms.dispatch(n, self.root)

    def test_deferred_tools_not_enabled_or_dispatchable(self):
        for n in ("get_context_pack", "check_context_health", "list_rejected_alternatives"):
            self.assertNotIn(n, ms.ENABLED_TOOLS)
            with self.assertRaises(ms.ReadError):
                ms.dispatch(n, self.root)

    def test_get_project_status_reads_curated_status(self):
        text = ms.get_project_status(self.root)
        self.assertIn("Current focus: testing.", text)

    def test_list_decisions_reads_curated_records(self):
        recs = ms.list_decisions(self.root)
        ids = {r["id"] for r in recs}
        self.assertIn("DEC-20260101-sample", ids)
        # the .council/ draft must NOT appear
        self.assertFalse(any("draft" in str(r["stem"]) for r in recs))

    def test_show_decision_returns_known_record(self):
        rec = ms.show_decision(self.root, "2026-01-01-sample")
        self.assertEqual(rec["id"], "DEC-20260101-sample")
        self.assertIn("# Sample decision", rec["text"])

    def test_show_decision_rejects_unknown_id(self):
        with self.assertRaises(ms.ReadError):
            ms.show_decision(self.root, "no-such-decision")

    def test_show_decision_blocks_path_traversal(self):
        for evil in ("../../../etc/passwd", "../plans/private-thing",
                     "../context/project/STATUS"):
            with self.assertRaises(ms.ReadError):
                ms.show_decision(self.root, evil)

    def test_does_not_read_council_drafts(self):
        # the draft exists on disk but is unreachable via the read layer
        self.assertTrue((self.root / ".council" / "decisions" / "drafts"
                         / "2026-01-02-draft.md").is_file())
        with self.assertRaises(ms.ReadError):
            ms.show_decision(self.root, "2026-01-02-draft")

    def test_does_not_expose_private_plans(self):
        with self.assertRaises(ms.ReadError):
            ms.show_decision(self.root, "private-thing")

    def test_dispatch_writes_nothing(self):
        before = {p for p in self.root.rglob("*")}
        ms.dispatch("get_project_status", self.root)
        ms.dispatch("list_decisions", self.root)
        ms.dispatch("show_decision", self.root, id="2026-01-01-sample")
        self.assertEqual({p for p in self.root.rglob("*")}, before)  # nothing created


class TestMcpInspectCLI(unittest.TestCase):
    def _seed(self, root: Path):
        _make_repo(root)

    def test_inspect_exits_zero_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._seed(root)
            before = {p for p in root.rglob("*")}
            r = run_cli(["mcp", "inspect"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("status + decisions", r.stdout)
            self.assertIn("list_decisions", r.stdout)
            self.assertEqual({p for p in root.rglob("*")}, before)  # nothing written

    def test_inspect_json_is_read_only_subset(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._seed(root)
            r = run_cli(["mcp", "inspect", "--json"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertTrue(data["read_only"])
            self.assertFalse(data["server_implemented"])
            self.assertEqual(set(data["enabled_tools"]),
                             {"get_project_status", "list_decisions", "show_decision"})
            self.assertGreaterEqual(data["decision_count"], 1)

    def test_inspect_id_traversal_is_safe(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._seed(root)
            r = run_cli(["mcp", "inspect", "--id", "../plans/private-thing"],
                        caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("not found", r.stdout)
            self.assertNotIn("secret-ish", r.stdout)


if __name__ == "__main__":
    unittest.main()
