"""Tests for the Workbench runtime store (backend/workbench_runtime.py).

Stdlib-only (`unittest`). Pure local JSON store over a **temp** project root — no
model/API/network, no server, no action execution. Every test uses a temp dir so no
`.council/runtime/` files are ever written into the real repo.
"""

import json
import unittest
import tempfile
from pathlib import Path

from backend import workbench_runtime as wr

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED = "2026-07-01T00:00:00Z"


class TestRuntimeStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # --- layout ------------------------------------------------------------- #

    def test_runtime_root_under_council_runtime(self):
        rr = wr.runtime_root(self.root)
        self.assertEqual(rr.parts[-2:], (".council", "runtime"))
        self.assertEqual(rr, self.root / ".council" / "runtime")

    def test_ensure_runtime_creates_dirs_and_index(self):
        rr = wr.ensure_runtime(self.root)
        for sub in ("tasks", "approvals", "audits", "actions"):
            self.assertTrue((rr / sub).is_dir(), sub)
        idx = json.loads((rr / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["tasks"], {})

    # --- tasks -------------------------------------------------------------- #

    def test_new_task_defaults(self):
        t = wr.new_task("My task", summary="s", source="cli", on=FIXED)
        self.assertTrue(t.id.startswith("task-"))
        self.assertEqual(t.status, "planning")
        self.assertEqual((t.created_at, t.updated_at), (FIXED, FIXED))
        self.assertEqual(t.title, "My task")

    def test_save_load_roundtrip(self):
        t = wr.new_task("Roundtrip", on=FIXED)
        wr.save_task(t, self.root)
        loaded = wr.load_task(t.id, self.root)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, t.id)
        self.assertEqual(loaded.title, "Roundtrip")
        self.assertEqual(loaded.status, "planning")

    def test_list_tasks_filters_by_status(self):
        a = wr.new_task("A", on=FIXED); wr.save_task(a, self.root)
        b = wr.new_task("B", on=FIXED); b.status = "completed"; wr.save_task(b, self.root)
        self.assertEqual(len(wr.list_tasks(project_root=self.root)), 2)
        done = wr.list_tasks(status="completed", project_root=self.root)
        self.assertEqual([t.id for t in done], [b.id])

    def test_append_stage_sets_current_stage(self):
        t = wr.new_task("Staged", on=FIXED); wr.save_task(t, self.root)
        st = wr.new_stage(t.id, "PLANNING", worker="claude", model="sonnet", on=FIXED)
        updated = wr.append_stage(t.id, st, self.root)
        self.assertEqual(updated.current_stage_id, st.id)
        reloaded = wr.load_task(t.id, self.root)
        self.assertEqual(len(reloaded.stages), 1)
        self.assertEqual(reloaded.stages[0].name, "PLANNING")

    # --- approvals ---------------------------------------------------------- #

    def test_create_approval_sets_task_awaiting(self):
        t = wr.new_task("Appr", on=FIXED); wr.save_task(t, self.root)
        ap = wr.create_approval(t.id, title="Write foo.py", risk_level="medium",
                                project_root=self.root, on=FIXED)
        self.assertEqual(ap.status, "pending")
        reloaded = wr.load_task(t.id, self.root)
        self.assertEqual(reloaded.status, "awaiting_approval")
        self.assertIn(ap.id, reloaded.approval_ids)

    def test_record_decision_approve_reject_hold(self):
        for decision, expect in (("approve", "approved"), ("reject", "rejected"),
                                 ("hold", "held")):
            t = wr.new_task("D", on=FIXED); wr.save_task(t, self.root)
            ap = wr.create_approval(t.id, project_root=self.root, on=FIXED)
            dec = wr.record_approval_decision(ap.id, decision, reason="r",
                                              project_root=self.root, on=FIXED)
            self.assertEqual(dec.decision, decision)
            self.assertEqual(wr.load_approval(ap.id, self.root).status, expect)

    def test_invalid_decision_rejected(self):
        t = wr.new_task("X", on=FIXED); wr.save_task(t, self.root)
        ap = wr.create_approval(t.id, project_root=self.root, on=FIXED)
        with self.assertRaises(ValueError):
            wr.record_approval_decision(ap.id, "maybe", project_root=self.root)

    # --- audits + actions --------------------------------------------------- #

    def test_audit_roundtrip(self):
        au = wr.new_audit("appr-x", risk_level="high", findings=["a", "b"],
                          rewritten_prompt="ok?", blocked=True, on=FIXED)
        wr.save_audit_result(au, self.root)
        loaded = wr.load_audit(au.id, self.root)
        self.assertEqual(loaded.risk_level, "high")
        self.assertEqual(loaded.findings, ["a", "b"])
        self.assertTrue(loaded.blocked)

    def test_action_roundtrip(self):
        act = wr.new_action("task-x", "write_file", command_or_path="foo.py", on=FIXED)
        wr.save_action(act, self.root)
        loaded = wr.load_action(act.id, self.root)
        self.assertEqual(loaded.kind, "write_file")
        self.assertEqual(loaded.status, "pending")

    def test_invalid_status_rejected_on_save(self):
        t = wr.new_task("bad", on=FIXED)
        t.status = "not_a_status"
        with self.assertRaises(ValueError):
            wr.save_task(t, self.root)

    # --- safety ------------------------------------------------------------- #

    def test_ids_are_sanitized(self):
        self.assertEqual(wr._safe_id("../../etc/passwd"), "etc-passwd")
        self.assertNotIn("/", wr._safe_id("a/b/c"))
        self.assertNotIn("..", wr._safe_id("..\\..\\evil"))
        self.assertEqual(wr._safe_id(""), "id")

    def test_path_traversal_rejected(self):
        # a traversal-y id can neither read nor write outside the runtime tree
        self.assertIsNone(wr.load_task("../../../etc/passwd", self.root))
        self.assertIsNone(wr.load_approval("../../secret", self.root))
        # nothing was created outside the runtime dir
        self.assertFalse((self.root / "etc").exists())

    def test_all_files_stay_under_runtime_root(self):
        t = wr.new_task("Contained", on=FIXED); wr.save_task(t, self.root)
        wr.create_approval(t.id, project_root=self.root, on=FIXED)
        wr.save_audit_result(wr.new_audit("appr-y", on=FIXED), self.root)
        wr.save_action(wr.new_action(t.id, "write_file", on=FIXED), self.root)
        rr = wr.runtime_root(self.root).resolve()
        created = [p for p in self.root.rglob("*") if p.is_file()]
        self.assertTrue(created)
        for p in created:
            self.assertTrue(str(p.resolve()).startswith(str(rr)),
                            f"{p} escaped {rr}")
        # never under docs/
        self.assertFalse((self.root / "docs").exists())

    def test_json_is_stable_and_sorted(self):
        t = wr.new_task("Stable", on=FIXED)
        p = wr.save_task(t, self.root, on=FIXED)
        first = p.read_bytes()
        # re-saving with the same timestamp yields byte-identical output
        second_path = wr.save_task(wr.load_task(t.id, self.root), self.root, on=FIXED)
        self.assertEqual(second_path.read_bytes(), first)
        text = first.decode("utf-8")
        self.assertLess(text.index('"created_at"'), text.index('"title"'))  # sorted keys

    def test_operations_use_temp_root_not_repo(self):
        # confirm operations write under the injected temp root (not the process
        # cwd / real repo). new_task is pure; ensure_runtime writes under self.root.
        wr.new_task("noop", on=FIXED)  # pure, no I/O
        rr = wr.ensure_runtime(self.root)
        self.assertTrue((self.root / ".council" / "runtime" / "tasks").is_dir())
        self.assertEqual(rr, self.root / ".council" / "runtime")

    def test_summary_counts(self):
        a = wr.new_task("a", on=FIXED); wr.save_task(a, self.root)
        b = wr.new_task("b", on=FIXED); b.status = "completed"; wr.save_task(b, self.root)
        s = wr.runtime_status_summary(self.root)
        self.assertEqual(s["tasks_total"], 2)
        self.assertEqual(s["by_status"]["completed"], 1)
        self.assertEqual(s["by_status"]["planning"], 1)
        self.assertNotIn(str(self.root), s["runtime_root"])  # no absolute local path


if __name__ == "__main__":
    unittest.main()
