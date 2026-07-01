"""Tests for the Workbench orchestrator (backend/workbench_orchestrator.py).

Stdlib-only (`unittest`). Deterministic lifecycle over a **temp** runtime store —
no action execution, no model/API/network, no git/shell. Every test uses a temp
project root so no `.council/runtime/` files land in the real repo.
"""

import unittest
import tempfile
from pathlib import Path

from backend import workbench_orchestrator as wo
from backend import workbench_runtime as wr

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED = "2026-07-01T00:00:00Z"


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # --- start / plan ------------------------------------------------------- #

    def test_start_task_creates_planning_task_and_stage(self):
        t = wo.start_task("Task A", summary="s", source="cli",
                          project_root=self.root, on=FIXED)
        self.assertEqual(t.status, "planning")
        self.assertEqual(len(t.stages), 1)
        self.assertEqual(t.stages[0].name, "planning")
        self.assertEqual(t.stages[0].status, "running")
        self.assertEqual(t.current_stage_id, t.stages[0].id)

    def test_add_planning_stage_updates_current(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        wo.add_planning_stage(t.id, message="drafting", worker="claude", model="sonnet",
                              project_root=self.root, on=FIXED)
        reloaded = wr.load_task(t.id, self.root)
        self.assertEqual(len(reloaded.stages), 1)  # updated in place, not appended
        self.assertEqual(reloaded.stages[0].worker, "claude")
        self.assertEqual(reloaded.stages[0].message, "drafting")

    def test_add_planning_stage_rejected_after_approval(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        with self.assertRaises(wo.OrchestratorError):
            wo.add_planning_stage(t.id, message="late", project_root=self.root)

    # --- approval flow ------------------------------------------------------ #

    def test_request_approval_moves_to_awaiting(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "Write foo.py", "apply diff",
                                 requested_action="write_file:foo.py", risk_level="medium",
                                 project_root=self.root, on=FIXED)
        self.assertEqual(ap.status, "pending")
        reloaded = wr.load_task(t.id, self.root)
        self.assertEqual(reloaded.status, "awaiting_approval")
        self.assertIn(ap.id, reloaded.approval_ids)
        # planning stage completed, awaiting stage active
        names = [(s.name, s.status) for s in reloaded.stages]
        self.assertIn(("planning", "completed"), names)
        self.assertIn(("awaiting_approval", "running"), names)

    def test_list_pending_approvals(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "Approve me", "p", project_root=self.root, on=FIXED)
        pend = wo.list_pending_approvals(self.root)
        self.assertEqual([a.id for a in pend], [ap.id])

    def test_approve_records_decision(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        dec = wo.decide_approval(ap.id, "approve", reason="ok",
                                 project_root=self.root, on=FIXED)
        self.assertEqual(dec.decision, "approve")
        self.assertEqual(wr.load_approval(ap.id, self.root).status, "approved")
        # task stays awaiting_approval (approved, pending execution)
        self.assertEqual(wr.load_task(t.id, self.root).status, "awaiting_approval")
        self.assertEqual(wo.list_pending_approvals(self.root), [])

    def test_reject_moves_task_to_failed(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        wo.decide_approval(ap.id, "reject", reason="too broad",
                           project_root=self.root, on=FIXED)
        reloaded = wr.load_task(t.id, self.root)
        self.assertEqual(reloaded.status, "failed")
        self.assertEqual(wr.load_approval(ap.id, self.root).status, "rejected")

    def test_hold_moves_task_to_held(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        wo.decide_approval(ap.id, "hold", reason="later", project_root=self.root, on=FIXED)
        self.assertEqual(wr.load_task(t.id, self.root).status, "held")
        self.assertEqual(wr.load_approval(ap.id, self.root).status, "held")

    def test_cannot_approve_twice(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        wo.decide_approval(ap.id, "approve", project_root=self.root, on=FIXED)
        with self.assertRaises(wo.OrchestratorError):
            wo.decide_approval(ap.id, "approve", project_root=self.root)

    def test_unknown_approval_fails_cleanly(self):
        with self.assertRaises(wo.OrchestratorError):
            wo.decide_approval("appr-nope", "approve", project_root=self.root)

    # --- executing (no real execution) -------------------------------------- #

    def test_mark_executing_creates_pending_action_not_run(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "x", "y", requested_action="write_file:foo.py",
                                 project_root=self.root, on=FIXED)
        wo.decide_approval(ap.id, "approve", project_root=self.root, on=FIXED)
        ex = wo.mark_executing(t.id, ap.id, project_root=self.root, on=FIXED)
        self.assertEqual(ex.status, "executing")
        self.assertEqual(len(ex.action_ids), 1)
        act = wr.load_action(ex.action_ids[0], self.root)
        self.assertEqual(act.status, "pending")           # recorded, NOT run
        self.assertEqual(act.approval_id, ap.id)

    def test_cannot_mark_executing_without_approval(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        with self.assertRaises(wo.OrchestratorError):
            wo.mark_executing(t.id, project_root=self.root)

    # --- complete / fail ---------------------------------------------------- #

    def test_cannot_complete_awaiting_approval(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        with self.assertRaises(wo.OrchestratorError):
            wo.complete_task(t.id, project_root=self.root)

    def test_complete_task_marks_completed(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        wo.decide_approval(ap.id, "approve", project_root=self.root, on=FIXED)
        wo.mark_executing(t.id, ap.id, project_root=self.root, on=FIXED)
        done = wo.complete_task(t.id, summary="applied", project_root=self.root, on=FIXED)
        self.assertEqual(done.status, "completed")
        self.assertEqual(done.summary, "applied")

    def test_fail_task_marks_failed_with_reason(self):
        t = wo.start_task("A", project_root=self.root, on=FIXED)
        failed = wo.fail_task(t.id, "model refused", project_root=self.root, on=FIXED)
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.summary, "model refused")

    def test_unknown_task_fails_cleanly(self):
        with self.assertRaises(wo.OrchestratorError):
            wo.get_task_progress("task-nope", self.root)
        with self.assertRaises(wo.OrchestratorError):
            wo.fail_task("task-nope", "x", project_root=self.root)

    # --- progress view ------------------------------------------------------ #

    def test_get_task_progress_is_panel_friendly(self):
        t = wo.start_task("Panel task", project_root=self.root, on=FIXED)
        wo.add_planning_stage(t.id, worker="claude", model="sonnet",
                              project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "Write foo", "p", risk_level="high",
                                 project_root=self.root, on=FIXED)
        p = wo.get_task_progress(t.id, self.root)
        self.assertEqual(p["task_id"], t.id)
        self.assertEqual(p["status"], "awaiting_approval")
        self.assertEqual(p["current_stage"]["name"], "awaiting_approval")
        self.assertIn("planning", p["completed_stages"])
        self.assertEqual(len(p["pending_approvals"]), 1)
        self.assertEqual(p["pending_approvals"][0]["risk_level"], "high")

    # --- containment / no repo writes --------------------------------------- #

    def test_all_writes_stay_under_temp_runtime(self):
        t = wo.start_task("Contained", project_root=self.root, on=FIXED)
        ap = wo.request_approval(t.id, "x", "y", project_root=self.root, on=FIXED)
        wo.decide_approval(ap.id, "approve", project_root=self.root, on=FIXED)
        wo.mark_executing(t.id, ap.id, project_root=self.root, on=FIXED)
        rr = wr.runtime_root(self.root).resolve()
        for p in self.root.rglob("*"):
            if p.is_file():
                self.assertTrue(str(p.resolve()).startswith(str(rr)), f"{p} escaped {rr}")
        self.assertFalse((self.root / "docs").exists())

    def test_operations_do_not_touch_real_repo(self):
        wo.start_task("noop", project_root=self.root, on=FIXED)
        self.assertTrue((self.root / ".council" / "runtime" / "tasks").is_dir())


if __name__ == "__main__":
    unittest.main()
