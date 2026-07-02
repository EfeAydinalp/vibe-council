"""Tests for executor-side payload artifact loading/verification (PR #76).

Stdlib-only (`unittest`). When `execute_action(..., payload=None)` (the default), the
executor loads the matching `backend.workbench_payloads` artifact for the action,
verifies its hash and its agreement with the live action/approval/task, and only then
performs bounded real `write_file`/`edit_file` execution. The explicit `payload=...`
path from PR #74 keeps working unchanged. `run_command` real execution and dry-run
behavior are unaffected. Temp dirs only; no real-repo `.council/runtime/` artifacts.
No shell/git/provider/model/network calls.
"""

import json
import unittest
import tempfile
from pathlib import Path

from backend import workbench_executor as we
from backend import workbench_payloads as wp
from backend import workbench_runtime as wr
from backend import workbench_trust as wt

FIXED = "2026-07-02T00:00:00Z"


def _setup(root, kind="write_file", target="docs/foo.md", appr_status="approve",
          act_status="pending", requested_action=None):
    task = wr.new_task("T", on=FIXED)
    wr.save_task(task, root)
    ra = requested_action if requested_action is not None else f"{kind}:{target}"
    ap = wr.create_approval(task.id, title="x", requested_action=ra, risk_level="medium",
                            project_root=root, on=FIXED)
    if appr_status != "pending":
        wr.record_approval_decision(ap.id, appr_status, project_root=root, on=FIXED)
    act = wr.new_action(task.id, kind, command_or_path=target, approval_id=ap.id, on=FIXED)
    act.status = act_status
    wr.save_action(act, root)
    t = wr.load_task(task.id, root)
    t.action_ids.append(act.id)
    wr.save_task(t, root)
    return task, ap, act


def _store_payload(root, action, task=None, approval=None, **payload):
    artifact = wp.build_payload_artifact(action, payload, task=task, approval=approval,
                                         on=FIXED)
    wp.save_payload_artifact(artifact, root)
    return artifact


class TestExecutorLoadsPayloadFromStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _exec(self, action_id):
        return we.execute_action(action_id, project_root=self.root, policy=self.policy,
                                 dry_run=False)  # payload omitted -> load from store

    def test_write_file_via_stored_payload(self):
        task, ap, act = _setup(self.root, target="docs/store.md")
        _store_payload(self.root, act, task=task, approval=ap,
                       content="from store\n", overwrite=False)
        r = self._exec(act.id)
        self.assertTrue(r.executed)
        self.assertFalse(r.blocked)
        fp = self.root / "docs" / "store.md"
        self.assertEqual(fp.read_text(encoding="utf-8"), "from store\n")
        self.assertEqual(wr.load_action(act.id, self.root).status, "completed")

    def test_edit_file_via_stored_payload(self):
        task, ap, act = _setup(self.root, kind="edit_file", target="src/store.py")
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "store.py").write_text("x = 1\n", encoding="utf-8")
        _store_payload(self.root, act, task=task, approval=ap,
                       old_text="x = 1", new_text="x = 2", max_replacements=1)
        r = self._exec(act.id)
        self.assertTrue(r.executed)
        self.assertEqual((self.root / "src" / "store.py").read_text(encoding="utf-8"),
                         "x = 2\n")

    def test_dry_run_with_stored_payload_is_non_mutating(self):
        task, ap, act = _setup(self.root, target="docs/drystore.md")
        _store_payload(self.root, act, task=task, approval=ap, content="x")
        r = we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=True)
        self.assertFalse(r.executed)
        self.assertFalse((self.root / "docs" / "drystore.md").exists())
        self.assertEqual(wr.load_action(act.id, self.root).status, "pending")

    def test_missing_payload_artifact_blocks(self):
        task, ap, act = _setup(self.root, target="docs/nopayload.md")
        r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertFalse(r.executed)
        self.assertFalse((self.root / "docs" / "nopayload.md").exists())

    def test_tampered_payload_hash_blocks(self):
        task, ap, act = _setup(self.root, target="docs/tampered.md")
        _store_payload(self.root, act, task=task, approval=ap, content="orig")
        path = wp._entry_path(self.root, act.id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["payload"]["content"] = "rewritten"  # tamper after write, hash now stale
        path.write_text(json.dumps(data), encoding="utf-8")
        r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertFalse(r.executed)
        self.assertFalse((self.root / "docs" / "tampered.md").exists())

    def test_payload_target_mismatch_blocks(self):
        task, ap, act = _setup(self.root, target="docs/real.md")
        # build an artifact for a different target, then force-save it under this action id
        other_act = wr.new_action(task.id, "write_file", command_or_path="docs/other.md",
                                  approval_id=ap.id, on=FIXED)
        artifact = wp.build_payload_artifact(other_act, {"content": "x"})
        artifact.action_id = act.id  # artifact now claims to belong to `act`, but target differs
        wp.save_payload_artifact(artifact, self.root)
        r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertFalse((self.root / "docs" / "real.md").exists())
        self.assertFalse((self.root / "docs" / "other.md").exists())

    def test_payload_kind_mismatch_blocks(self):
        task, ap, act = _setup(self.root, kind="write_file", target="docs/kindmix.md")
        other_act = wr.new_action(task.id, "edit_file", command_or_path="docs/kindmix.md",
                                  approval_id=ap.id, on=FIXED)
        artifact = wp.build_payload_artifact(other_act, {"old_text": "a", "new_text": "b"})
        artifact.action_id = act.id
        wp.save_payload_artifact(artifact, self.root)
        r = self._exec(act.id)
        self.assertTrue(r.blocked)

    def test_payload_approval_id_mismatch_blocks(self):
        task, ap, act = _setup(self.root, target="docs/apmix.md")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        artifact.approval_id = "appr-someone-else"
        wp.save_payload_artifact(artifact, self.root)
        r = self._exec(act.id)
        self.assertTrue(r.blocked)

    def test_payload_task_id_mismatch_blocks(self):
        task, ap, act = _setup(self.root, target="docs/taskmix.md")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        artifact.task_id = "task-someone-else"
        wp.save_payload_artifact(artifact, self.root)
        r = self._exec(act.id)
        self.assertTrue(r.blocked)

    def test_unapproved_action_with_valid_payload_still_blocks(self):
        # payload verification never substitutes for approval/trust checks
        task, ap, act = _setup(self.root, appr_status="pending", target="docs/notapproved.md")
        _store_payload(self.root, act, task=task, approval=ap, content="x")
        r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertFalse((self.root / "docs" / "notapproved.md").exists())

    def test_stale_advisory_audit_cannot_authorize_with_stored_payload(self):
        task, ap, act = _setup(self.root, target="secrets/app.key")
        good = wr.new_audit(ap.id, risk_level="low", blocked=False, on=FIXED)
        wr.save_audit_result(good, self.root)
        _store_payload(self.root, act, task=task, approval=ap, content="x")
        r = self._exec(act.id)
        self.assertTrue(r.blocked)  # fresh deterministic guard still wins
        self.assertFalse((self.root / "secrets" / "app.key").exists())

    def test_non_allowlisted_run_command_still_blocked(self):
        # PR #80: real run_command execution exists for resolver-allowlisted commands
        # (see test_workbench_command_executor.py); a non-allowlisted command still
        # fails closed (blocked, no subprocess started) — payload verification is
        # irrelevant to run_command anyway (no payload artifact involved).
        task, ap, act = _setup(self.root, kind="run_command", target="pip install evil")
        r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertFalse(r.executed)

    def test_explicit_payload_path_still_works_and_ignores_store(self):
        # Backward-compatible PR #74 path: explicit payload bypasses the store entirely,
        # even if no artifact is saved.
        task, ap, act = _setup(self.root, target="docs/explicit.md")
        r = we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=False, payload={"content": "explicit\n"})
        self.assertTrue(r.executed)
        self.assertEqual((self.root / "docs" / "explicit.md").read_text(encoding="utf-8"),
                         "explicit\n")


if __name__ == "__main__":
    unittest.main()
