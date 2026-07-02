"""Tests for the bounded file executor (backend/workbench_executor.py, PR #74).

Stdlib-only (`unittest`). Real execution is limited to bounded `write_file`/`edit_file`
behind the full invariant + a fresh deterministic trust re-check. Atomic, path-guarded,
size/line-limited. `run_command` real execution and unsupported kinds fail closed;
dry-run never mutates. Temp dirs only; no real-repo `.council/runtime/` artifacts.
"""

import os
import unittest
import tempfile
from pathlib import Path

from backend import workbench_executor as we
from backend import workbench_runtime as wr
from backend import workbench_trust as wt

FIXED = "2026-07-01T00:00:00Z"


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
    return act


class TestBoundedFileExecutor(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _exec(self, action_id, **payload):
        return we.execute_action(action_id, project_root=self.root, policy=self.policy,
                                 dry_run=False, payload=payload)

    # --- write_file --------------------------------------------------------- #

    def test_write_file_creates_new_file(self):
        act = _setup(self.root, target="docs/new.md")
        r = self._exec(act.id, content="hello\n")
        self.assertTrue(r.executed)
        self.assertFalse(r.blocked)
        fp = self.root / "docs" / "new.md"
        self.assertTrue(fp.is_file())
        self.assertEqual(fp.read_text(encoding="utf-8"), "hello\n")
        self.assertEqual(wr.load_action(act.id, self.root).status, "completed")

    def test_write_file_dry_run_creates_nothing(self):
        act = _setup(self.root, target="docs/dry.md")
        r = we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=True, payload={"content": "x"})
        self.assertFalse(r.executed)
        self.assertFalse((self.root / "docs" / "dry.md").exists())
        self.assertEqual(wr.load_action(act.id, self.root).status, "pending")

    def test_write_unapproved_blocks(self):
        act = _setup(self.root, appr_status="pending", target="docs/x.md")
        r = self._exec(act.id, content="x")
        self.assertTrue(r.blocked)
        self.assertFalse((self.root / "docs" / "x.md").exists())

    def test_write_rejected_and_held_block(self):
        for status in ("reject", "hold"):
            act = _setup(self.root, appr_status=status, target=f"docs/{status}.md")
            r = self._exec(act.id, content="x")
            self.assertTrue(r.blocked, status)
            self.assertFalse((self.root / "docs" / f"{status}.md").exists())

    def test_write_secret_path_blocks(self):
        act = _setup(self.root, target="secrets/app.key")
        r = self._exec(act.id, content="k")
        self.assertTrue(r.blocked)
        self.assertFalse((self.root / "secrets" / "app.key").exists())

    def test_write_out_of_project_blocks(self):
        outside = str(self.root.parent / "evil.txt")
        act = _setup(self.root, target=outside)
        r = self._exec(act.id, content="x")
        self.assertTrue(r.blocked)
        self.assertFalse(Path(outside).exists())

    def test_write_traversal_blocks(self):
        act = _setup(self.root, target="../evil.md")
        r = self._exec(act.id, content="x")
        self.assertTrue(r.blocked)

    def test_write_symlink_blocks(self):
        real = self.root / "real.md"
        real.write_text("orig", encoding="utf-8")
        link = self.root / "docs" / "link.md"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(str(real), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not supported on this platform/privilege")
        act = _setup(self.root, target="docs/link.md")
        r = self._exec(act.id, content="pwned")
        self.assertTrue(r.blocked)
        self.assertEqual(real.read_text(encoding="utf-8"), "orig")  # target untouched

    def test_write_existing_without_overwrite_blocks(self):
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        fp = self.root / "docs" / "exists.md"
        fp.write_text("keep", encoding="utf-8")
        act = _setup(self.root, target="docs/exists.md")
        r = self._exec(act.id, content="new")
        self.assertTrue(r.blocked)
        self.assertEqual(fp.read_text(encoding="utf-8"), "keep")  # unchanged

    def test_write_existing_with_overwrite_works(self):
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        fp = self.root / "docs" / "ow.md"
        fp.write_text("old", encoding="utf-8")
        act = _setup(self.root, target="docs/ow.md")
        r = self._exec(act.id, content="new\n", overwrite=True)
        self.assertTrue(r.executed)
        self.assertEqual(fp.read_text(encoding="utf-8"), "new\n")

    def test_write_over_size_limit_blocks(self):
        act = _setup(self.root, target="docs/big.md")
        r = self._exec(act.id, content="a" * (we.MAX_WRITE_BYTES + 1))
        self.assertTrue(r.blocked)
        self.assertFalse((self.root / "docs" / "big.md").exists())

    def test_write_binary_content_blocks(self):
        act = _setup(self.root, target="docs/bin.md")
        r = self._exec(act.id, content="a\x00b")
        self.assertTrue(r.blocked)

    def test_failed_write_leaves_action_not_completed(self):
        act = _setup(self.root, target="secrets/x.key")
        self._exec(act.id, content="x")
        self.assertNotEqual(wr.load_action(act.id, self.root).status, "completed")

    # --- edit_file ---------------------------------------------------------- #

    def _seed_file(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_edit_exact_replacement(self):
        fp = self._seed_file("src/a.py", "x = 1\ny = 2\n")
        act = _setup(self.root, kind="edit_file", target="src/a.py")
        r = self._exec(act.id, old_text="x = 1", new_text="x = 42")
        self.assertTrue(r.executed)
        self.assertEqual(fp.read_text(encoding="utf-8"), "x = 42\ny = 2\n")

    def test_edit_no_match_fails_without_mutation(self):
        fp = self._seed_file("src/b.py", "hello\n")
        act = _setup(self.root, kind="edit_file", target="src/b.py")
        r = self._exec(act.id, old_text="NOPE", new_text="q")
        self.assertFalse(r.executed)
        self.assertEqual(fp.read_text(encoding="utf-8"), "hello\n")

    def test_edit_multiple_matches_blocks_unless_allowed(self):
        fp = self._seed_file("src/c.py", "a\na\na\n")
        act = _setup(self.root, kind="edit_file", target="src/c.py")
        r = self._exec(act.id, old_text="a", new_text="b")  # 3 matches, max=1
        self.assertTrue(r.blocked)
        self.assertEqual(fp.read_text(encoding="utf-8"), "a\na\na\n")  # unchanged
        # explicitly allowing more replacements works
        act2 = _setup(self.root, kind="edit_file", target="src/c.py")
        r2 = self._exec(act2.id, old_text="a", new_text="b", max_replacements=3)
        self.assertTrue(r2.executed)
        self.assertEqual(fp.read_text(encoding="utf-8"), "b\nb\nb\n")

    def test_edit_secret_path_blocks(self):
        act = _setup(self.root, kind="edit_file", target=".env")
        r = self._exec(act.id, old_text="A", new_text="B")
        self.assertTrue(r.blocked)

    def test_edit_missing_file_fails(self):
        act = _setup(self.root, kind="edit_file", target="src/missing.py")
        r = self._exec(act.id, old_text="a", new_text="b")
        self.assertFalse(r.executed)

    def test_edit_over_size_limit_blocks(self):
        self._seed_file("src/huge.py", "a" * (we.MAX_EDIT_BYTES + 1))
        act = _setup(self.root, kind="edit_file", target="src/huge.py")
        r = self._exec(act.id, old_text="a", new_text="b")
        self.assertTrue(r.blocked)

    # --- invariant / fail-closed still hold --------------------------------- #

    def test_run_command_real_execution_rejected(self):
        act = _setup(self.root, kind="run_command", target="git status --short")
        with self.assertRaises(we.ExecutorError):
            we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=False, payload={})

    def test_unsupported_kind_dry_run_false_fails_closed(self):
        act = _setup(self.root, kind="cloud_call", target="api")
        # cloud_call is blocked by the invariant -> blocked result, no raise, no mutation
        r = we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=False, payload={})
        self.assertTrue(r.blocked)
        self.assertFalse(r.executed)

    def test_trust_reevaluated_stale_audit_cannot_authorize(self):
        act = _setup(self.root, kind="write_file", target="secrets/app.key")
        good = wr.new_audit(act.approval_id, risk_level="low", blocked=False, on=FIXED)
        wr.save_audit_result(good, self.root)
        r = self._exec(act.id, content="x")
        self.assertTrue(r.blocked)  # fresh deterministic guard wins
        self.assertFalse((self.root / "secrets" / "app.key").exists())

    def test_scope_mismatch_blocks(self):
        act = _setup(self.root, kind="write_file", target="docs/foo.md",
                     requested_action="write_file:docs/OTHER.md")
        r = self._exec(act.id, content="x")
        self.assertTrue(r.blocked)
        self.assertFalse((self.root / "docs" / "foo.md").exists())

    def test_atomic_no_temp_left_behind(self):
        act = _setup(self.root, target="docs/atomic.md")
        self._exec(act.id, content="data\n")
        leftovers = list((self.root / "docs").glob(".wbx-*"))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
