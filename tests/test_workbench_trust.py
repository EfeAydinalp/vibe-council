"""Tests for the deterministic Workbench trust boundary (backend/workbench_trust.py).

Stdlib-only (`unittest`). Pure evaluation — no execution, no model/API/network, no
git/shell. Path checks are lexical (targets need not exist). The temp dir is used as
a concrete, absolute project root; the read-only ``evaluate_pending_actions`` helper
uses a temp runtime store.
"""

import unittest
import tempfile
from pathlib import Path

from backend import workbench_trust as wt


class TestTrustBoundary(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _ev(self, **kw):
        return wt.evaluate_action_payload(project_root=self.root, policy=self.policy, **kw)

    # --- unknown / defaults ------------------------------------------------- #

    def test_unknown_kind_blocked(self):
        e = self._ev(kind="frobnicate", target="x")
        self.assertTrue(e.blocked)
        self.assertFalse(e.allowed)
        self.assertEqual(e.normalized_kind, "unknown")
        self.assertEqual(e.risk_level, "blocked")

    # --- reads -------------------------------------------------------------- #

    def test_read_inside_project_allowed_low(self):
        e = self._ev(kind="read_file", target="src/module.py")
        self.assertTrue(e.allowed)
        self.assertFalse(e.blocked)
        self.assertEqual(e.risk_level, "low")

    def test_read_outside_project_blocked(self):
        outside = str(self.root.parent / "outside.txt")
        e = self._ev(kind="read_file", target=outside)
        self.assertTrue(e.blocked)

    def test_path_traversal_blocked(self):
        e = self._ev(kind="read_file", target="../../etc/shadow")
        self.assertTrue(e.blocked)

    def test_env_blocked(self):
        self.assertTrue(self._ev(kind="read_file", target=".env").blocked)
        self.assertTrue(self._ev(kind="write_file", target=".env.local").blocked)

    def test_key_and_pem_blocked(self):
        self.assertTrue(self._ev(kind="write_file", target="certs/server.pem").blocked)
        self.assertTrue(self._ev(kind="write_file", target="secrets/app.key").blocked)
        self.assertTrue(self._ev(kind="read_file", target="id_ed25519").blocked)

    def test_git_and_council_blocked(self):
        self.assertTrue(self._ev(kind="write_file", target=".git/config").blocked)
        self.assertTrue(self._ev(kind="write_file", target=".council/runtime/x.json").blocked)

    def test_private_plan_files_blocked(self):
        for rp in ("docs/plans/commercialization-and-hosted-platform-feasibility.md",
                   "docs/plans/v0.3.1-hardening-and-dogfood.md"):
            self.assertTrue(self._ev(kind="write_file", target=rp).blocked, rp)

    # --- writes ------------------------------------------------------------- #

    def test_write_normal_requires_approval(self):
        e = self._ev(kind="write_file", target="src/module.py")
        self.assertFalse(e.blocked)
        self.assertFalse(e.allowed)
        self.assertTrue(e.requires_approval)
        self.assertEqual(e.risk_level, "medium")

    def test_write_denied_path_blocked(self):
        self.assertTrue(self._ev(kind="write_file", target="node_modules/x.js").blocked)
        self.assertTrue(self._ev(kind="write_file", target="data/dump.sql").blocked)

    def test_oversize_write_is_high_risk(self):
        e = self._ev(kind="write_file", target="src/module.py",
                     scope={"files_changed": 99, "lines_changed": 9999})
        self.assertEqual(e.risk_level, "high")
        self.assertTrue(e.requires_approval)

    # --- commands ----------------------------------------------------------- #

    def test_allowlisted_command_permitted(self):
        e = self._ev(kind="run_command", command="git status --short")
        self.assertTrue(e.allowed)
        self.assertEqual(e.risk_level, "low")

    def test_command_with_shell_metacharacters_blocked(self):
        for cmd in ("git status --short && rm -rf /", "ls | grep x", "cat a > b",
                    "echo `whoami`", "python -c \"$(evil)\""):
            self.assertTrue(self._ev(kind="run_command", command=cmd).blocked, cmd)

    def test_non_allowlisted_command_blocked(self):
        e = self._ev(kind="run_command", command="pip install something")
        self.assertTrue(e.blocked)
        self.assertFalse(e.allowed)

    # --- cloud egress ------------------------------------------------------- #

    def test_cloud_without_consent_blocked(self):
        e = self._ev(kind="cloud_call", target="anthropic")
        self.assertTrue(e.blocked)
        self.assertTrue(e.cloud_egress_required)
        self.assertFalse(e.cloud_egress_approved)

    def test_cloud_consent_with_secret_blocked(self):
        e = self._ev(kind="cloud_call", target="anthropic",
                     metadata={"cloud_egress": {"consent": True, "data_shared": [".env"]}})
        self.assertTrue(e.blocked)

    def test_cloud_consent_safe_requires_approval(self):
        e = self._ev(kind="cloud_call", target="anthropic",
                     metadata={"cloud_egress": {"consent": True,
                                                "data_shared": ["src/module.py"]}})
        self.assertFalse(e.blocked)
        self.assertTrue(e.requires_approval)   # never auto-allowed
        self.assertTrue(e.cloud_egress_required)
        self.assertTrue(e.cloud_egress_approved)

    def test_requires_cloud_egress_consent_helper(self):
        self.assertTrue(wt.requires_cloud_egress_consent({"kind": "cloud_call"}))
        self.assertTrue(wt.requires_cloud_egress_consent(
            {"kind": "write_file", "metadata": {"data_shared": ["x"]}}))
        self.assertFalse(wt.requires_cloud_egress_consent({"kind": "read_file"}))

    # --- determinism + helpers ---------------------------------------------- #

    def test_evaluation_is_deterministic(self):
        a = self._ev(kind="write_file", target="src/module.py")
        b = self._ev(kind="write_file", target="src/module.py")
        self.assertEqual(a, b)
        self.assertEqual(a.guard_version, wt.GUARD_VERSION)

    def test_summarize_evaluation(self):
        e = self._ev(kind="run_command", command="git status --short")
        self.assertIn("ALLOWED", wt.summarize_evaluation(e))
        blocked = self._ev(kind="unknown", target="x")
        self.assertIn("BLOCKED", wt.summarize_evaluation(blocked))

    def test_evaluate_action_maps_runtime_action(self):
        from backend import workbench_runtime as wr
        act = wr.new_action("task-x", "write_file", command_or_path="src/module.py")
        e = wt.evaluate_action(act, project_root=self.root, policy=self.policy)
        self.assertEqual(e.normalized_kind, "write_file")
        self.assertTrue(e.requires_approval)


class TestEvaluatePendingActions(unittest.TestCase):
    def test_read_only_evaluation_writes_nothing(self):
        from backend import workbench_runtime as wr
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            task = wr.new_task("T", on="2026-07-01T00:00:00Z")
            wr.save_task(task, root)
            act = wr.new_action(task.id, "write_file", command_or_path="src/x.py",
                                on="2026-07-01T00:00:00Z")
            wr.save_action(act, root)
            task.action_ids.append(act.id)
            wr.save_task(task, root)
            before = {p for p in root.rglob("*")}
            pairs = wt.evaluate_pending_actions(project_root=root)
            self.assertEqual(len(pairs), 1)
            _, ev = pairs[0]
            self.assertTrue(ev.requires_approval)
            self.assertEqual({p for p in root.rglob("*")}, before)  # nothing written


if __name__ == "__main__":
    unittest.main()
