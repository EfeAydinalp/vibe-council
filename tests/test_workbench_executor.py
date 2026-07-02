"""Tests for the dry-run guarded executor (backend/workbench_executor.py).

Stdlib-only (`unittest`). The executor is **dry-run only**: it validates the full
execution invariant, re-runs the deterministic trust boundary, and previews what
*would* happen — it never writes a file, edits, runs a command, or calls a
provider/model. Fail-closed on `dry_run=False`. Temp dirs only; no real-repo
`.council/runtime/` artifacts.
"""

import unittest
import tempfile
from pathlib import Path

from backend import workbench_executor as we
from backend import workbench_runtime as wr
from backend import workbench_trust as wt

FIXED = "2026-07-01T00:00:00Z"


def _setup(root, kind="write_file", target="docs/foo.md", appr_status="approve",
           act_status="pending", link=True, requested_action=None):
    """Seed a task + approval (decided) + action, wired for the executor."""
    task = wr.new_task("T", on=FIXED)
    wr.save_task(task, root)
    ra = requested_action if requested_action is not None else f"{kind}:{target}"
    ap = wr.create_approval(task.id, title="x", requested_action=ra, risk_level="medium",
                            project_root=root, on=FIXED)
    if appr_status != "pending":
        wr.record_approval_decision(ap.id, appr_status, project_root=root, on=FIXED)
    act = wr.new_action(task.id, kind, command_or_path=target,
                        approval_id=(ap.id if link else "appr-other"), on=FIXED)
    act.status = act_status
    wr.save_action(act, root)
    t = wr.load_task(task.id, root)
    t.action_ids.append(act.id)
    wr.save_task(t, root)
    return task, ap, act


class TestDryRunExecutor(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _dry(self, action_id, **kw):
        return we.dry_run_action(action_id, project_root=self.root, policy=self.policy, **kw)

    # --- happy path (dry-run only) ------------------------------------------ #

    def test_write_file_would_execute_but_writes_nothing(self):
        _t, _ap, act = _setup(self.root, kind="write_file", target="docs/foo.md")
        r = self._dry(act.id)
        self.assertTrue(r.dry_run)
        self.assertFalse(r.executed)
        self.assertTrue(r.would_execute)
        self.assertFalse(r.blocked)
        self.assertIn("would WRITE", r.preview)
        self.assertFalse((self.root / "docs" / "foo.md").exists())        # nothing written

    def test_edit_file_preview_no_edit(self):
        _t, _ap, act = _setup(self.root, kind="edit_file", target="src/mod.py")
        r = self._dry(act.id)
        self.assertTrue(r.would_execute)
        self.assertIn("would EDIT", r.preview)
        self.assertFalse((self.root / "src" / "mod.py").exists())

    def test_allowlisted_command_preview_not_run(self):
        _t, _ap, act = _setup(self.root, kind="run_command", target="git status --short")
        r = self._dry(act.id)
        self.assertTrue(r.would_execute)
        self.assertIn("would RUN", r.preview)

    def test_dry_run_does_not_mark_action_or_task_completed(self):
        _t, ap, act = _setup(self.root)
        self._dry(act.id)
        self.assertEqual(wr.load_action(act.id, self.root).status, "pending")
        self.assertNotEqual(wr.load_task(act.task_id, self.root).status, "completed")

    # --- fail-closed --------------------------------------------------------- #

    def test_real_command_execution_fails_closed(self):
        # bounded file execution exists (PR #74), but run_command real execution does
        # not — dry_run=False for a command still fails closed.
        _t, _ap, act = _setup(self.root, kind="run_command", target="git status --short")
        with self.assertRaises(we.ExecutorError):
            we.execute_action(act.id, project_root=self.root, policy=self.policy, dry_run=False)

    def test_execute_action_dry_run_delegates(self):
        _t, _ap, act = _setup(self.root)
        r = we.execute_action(act.id, project_root=self.root, policy=self.policy, dry_run=True)
        self.assertTrue(r.dry_run)
        self.assertTrue(r.would_execute)

    # --- invariant: blocked cases ------------------------------------------- #

    def test_missing_action_blocks(self):
        r = self._dry("act-nope")
        self.assertTrue(r.blocked)
        self.assertFalse(r.would_execute)

    def test_unapproved_approval_blocks(self):
        _t, _ap, act = _setup(self.root, appr_status="pending")
        self.assertTrue(self._dry(act.id).blocked)

    def test_rejected_and_held_approval_block(self):
        for status in ("reject", "hold"):
            _t, _ap, act = _setup(self.root, appr_status=status)
            self.assertTrue(self._dry(act.id).blocked, status)

    def test_action_not_pending_blocks(self):
        _t, _ap, act = _setup(self.root, act_status="completed")
        self.assertTrue(self._dry(act.id).blocked)

    def test_action_approval_mismatch_blocks(self):
        _t, _ap, act = _setup(self.root, link=False)
        self.assertTrue(self._dry(act.id).blocked)

    def test_scope_mismatch_blocks(self):
        # approval approved a different target than the action now carries
        _t, _ap, act = _setup(self.root, kind="write_file", target="docs/foo.md",
                              requested_action="write_file:docs/OTHER.md")
        r = self._dry(act.id)
        self.assertTrue(r.blocked)
        self.assertIn("approved scope", r.reason)

    def test_unknown_kind_blocks(self):
        _t, _ap, act = _setup(self.root, kind="frobnicate", target="x")
        self.assertTrue(self._dry(act.id).blocked)

    def test_cloud_call_unsupported_blocks(self):
        _t, _ap, act = _setup(self.root, kind="cloud_call", target="api")
        self.assertTrue(self._dry(act.id).blocked)

    def test_secret_path_blocks(self):
        _t, _ap, act = _setup(self.root, kind="write_file", target="secrets/app.key")
        self.assertTrue(self._dry(act.id).blocked)

    def test_out_of_project_path_blocks(self):
        outside = str(self.root.parent / "evil.txt")
        _t, _ap, act = _setup(self.root, kind="write_file", target=outside)
        self.assertTrue(self._dry(act.id).blocked)

    def test_shell_metacharacter_command_blocks(self):
        _t, _ap, act = _setup(self.root, kind="run_command", target="git status && rm -rf /")
        self.assertTrue(self._dry(act.id).blocked)

    def test_non_allowlisted_command_blocks(self):
        _t, _ap, act = _setup(self.root, kind="run_command", target="pip install evil")
        self.assertTrue(self._dry(act.id).blocked)

    # --- trust re-run + stale audit ----------------------------------------- #

    def test_trust_reevaluated_at_dry_run_stale_audit_cannot_authorize(self):
        # a saved (advisory) audit that says low/allowed must NOT let a secret-path
        # action through; the fresh deterministic evaluation blocks it.
        _t, ap, act = _setup(self.root, kind="write_file", target="secrets/app.key")
        fake_ok = wr.new_audit(ap.id, risk_level="low", rewritten_prompt="looks fine",
                               blocked=False, on=FIXED)
        wr.save_audit_result(fake_ok, self.root)
        r = self._dry(act.id)
        self.assertTrue(r.blocked)           # fresh trust wins over the stale audit
        self.assertFalse(r.would_execute)

    # --- record option ------------------------------------------------------ #

    def test_default_no_mutation(self):
        _t, _ap, act = _setup(self.root)
        before = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        self._dry(act.id)  # record=False (default)
        after = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_record_writes_only_result_summary_status_unchanged(self):
        _t, _ap, act = _setup(self.root)
        self._dry(act.id, record=True)
        reloaded = wr.load_action(act.id, self.root)
        self.assertIn("dry-run", reloaded.result_summary)
        self.assertEqual(reloaded.status, "pending")   # not completed/executed
        # only runtime files exist (record wrote under .council/runtime, not docs/)
        self.assertFalse((self.root / "docs").exists())

    def test_summary_helper(self):
        _t, _ap, act = _setup(self.root)
        r = self._dry(act.id)
        self.assertIn("WOULD-EXECUTE", we.summarize_execution_result(r))
        blocked = self._dry("nope")
        self.assertIn("BLOCKED", we.summarize_execution_result(blocked))


if __name__ == "__main__":
    unittest.main()
