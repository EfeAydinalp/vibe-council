"""Tests for the advisory Approval Auditor (backend/workbench_auditor.py).

Stdlib-only (`unittest`). The auditor is advisory and derives entirely from the
deterministic trust boundary — these tests assert it never relaxes a blocked/high-risk
trust result, produces panel-friendly prompts that keep critical findings, and (with
``save``) writes only under a temp ``.council/runtime/``. No model/API/network, no
execution.
"""

import unittest
import tempfile
from pathlib import Path

from backend import workbench_auditor as wa
from backend import workbench_trust as wt
from backend import workbench_runtime as wr

FIXED = "2026-07-01T00:00:00Z"


class TestAuditor(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _au(self, **kw):
        return wa.audit_action_payload(project_root=self.root, policy=self.policy,
                                       on=FIXED, **kw)

    # --- basic audits ------------------------------------------------------- #

    def test_audit_safe_read(self):
        a = self._au(kind="read_file", target="src/module.py")
        self.assertFalse(a.blocked)
        self.assertEqual(a.risk_level, "low")
        self.assertEqual(a.model, "deterministic")
        self.assertIn("Allowed", a.rewritten_prompt)

    def test_audit_write_requires_approval(self):
        a = self._au(kind="write_file", target="docs/foo.md")
        self.assertFalse(a.blocked)
        self.assertEqual(a.risk_level, "medium")
        self.assertIn("Approve", a.rewritten_prompt)

    def test_audit_unknown_blocked(self):
        a = self._au(kind="frobnicate", target="x")
        self.assertTrue(a.blocked)
        self.assertEqual(a.risk_level, "blocked")
        self.assertIn("Blocked", a.rewritten_prompt)

    def test_audit_secret_path_blocked(self):
        a = self._au(kind="write_file", target="secrets/app.key")
        self.assertTrue(a.blocked)
        # the blocked prompt surfaces the critical finding
        self.assertTrue(any(".key" in f or "secret" in f.lower() for f in a.findings))
        self.assertIn(a.findings[0], a.rewritten_prompt)

    def test_audit_shell_metacharacter_blocked(self):
        a = self._au(kind="run_command", command="git status --short && rm -rf /")
        self.assertTrue(a.blocked)
        self.assertIn("metacharacter", " ".join(a.findings))

    def test_audit_cloud_without_consent_blocked(self):
        a = self._au(kind="cloud_call", target="anthropic")
        self.assertTrue(a.blocked)
        self.assertIn("consent", a.rewritten_prompt.lower())

    def test_audit_cloud_with_consent_is_approval_prompt(self):
        a = self._au(kind="cloud_call", target="openrouter",
                     metadata={"cloud_egress": {"consent": True,
                                                "data_shared": ["src/module.py"]}})
        self.assertFalse(a.blocked)
        self.assertIn("Approve cloud call", a.rewritten_prompt)
        self.assertIn("leave this machine", a.rewritten_prompt)

    # --- safety invariant (advisory cannot relax the guard) ----------------- #

    def test_blocked_trust_stays_blocked_in_audit(self):
        for kind, kw in (("frobnicate", {"target": "x"}),
                         ("write_file", {"target": ".env"}),
                         ("run_command", {"command": "pip install evil"}),
                         ("cloud_call", {"target": "api"})):
            ev = wt.evaluate_action_payload(kind, project_root=self.root,
                                            policy=self.policy, **kw)
            a = self._au(kind=kind, **kw)
            self.assertTrue(ev.blocked)
            self.assertEqual(a.blocked, ev.blocked)
            self.assertEqual(a.risk_level, ev.risk_level)

    def test_high_risk_not_lowered(self):
        kw = {"kind": "write_file", "target": "src/module.py",
              "scope": {"files_changed": 99, "lines_changed": 9999}}
        ev = wt.evaluate_action_payload(kw["kind"], target=kw["target"],
                                        scope=kw["scope"], project_root=self.root,
                                        policy=self.policy)
        a = self._au(**kw)
        self.assertEqual(ev.risk_level, "high")
        self.assertEqual(a.risk_level, "high")  # auditor cannot lower it

    def test_audit_mirrors_findings(self):
        ev = wt.evaluate_action_payload("write_file", target="secrets/app.key",
                                        project_root=self.root, policy=self.policy)
        a = self._au(kind="write_file", target="secrets/app.key")
        self.assertEqual(a.findings, list(ev.findings))  # nothing dropped

    def test_deterministic_output(self):
        a = self._au(kind="write_file", target="src/module.py")
        b = self._au(kind="write_file", target="src/module.py")
        self.assertEqual((a.risk_level, a.blocked, a.rewritten_prompt, a.findings),
                         (b.risk_level, b.blocked, b.rewritten_prompt, b.findings))

    # --- runtime integration (save) ----------------------------------------- #

    def test_audit_action_references_approval_id(self):
        act = wr.new_action("task-x", "write_file", command_or_path="src/module.py",
                            approval_id="appr-123", on=FIXED)
        a = wa.audit_action(act, project_root=self.root, policy=self.policy, on=FIXED)
        self.assertEqual(a.approval_id, "appr-123")
        self.assertEqual(a.risk_level, "medium")

    def test_audit_approval_request_saves_and_attaches(self):
        task = wr.new_task("T", on=FIXED)
        wr.save_task(task, self.root)
        ap = wr.create_approval(task.id, title="Write foo",
                                requested_action="write_file:docs/foo.md",
                                risk_level="medium", project_root=self.root, on=FIXED)
        before = {p for p in self.root.rglob("*")}
        audit = wa.audit_approval_request(ap.id, project_root=self.root, save=True, on=FIXED)
        self.assertEqual(audit.approval_id, ap.id)
        self.assertIsNotNone(wr.load_audit(audit.id, self.root))          # saved
        self.assertEqual(wr.load_approval(ap.id, self.root).audit_id, audit.id)  # attached
        after = {p for p in self.root.rglob("*")}
        self.assertTrue(after.issuperset(before))  # only additions, no deletions
        # all writes stayed under the runtime root
        rr = wr.runtime_root(self.root).resolve()
        for p in self.root.rglob("*"):
            if p.is_file():
                self.assertTrue(str(p.resolve()).startswith(str(rr)))

    def test_audit_approval_request_no_save_writes_nothing(self):
        task = wr.new_task("T", on=FIXED)
        wr.save_task(task, self.root)
        ap = wr.create_approval(task.id, requested_action="read_file:src/x.py",
                                project_root=self.root, on=FIXED)
        before = {p for p in self.root.rglob("*")}
        wa.audit_approval_request(ap.id, project_root=self.root, save=False, on=FIXED)
        self.assertEqual({p for p in self.root.rglob("*")}, before)  # nothing written

    def test_unknown_approval_raises(self):
        with self.assertRaises(wa.AuditorError):
            wa.audit_approval_request("appr-nope", project_root=self.root)

    def test_audit_summary(self):
        blocked = self._au(kind="frobnicate", target="x")
        self.assertIn("BLOCKED", wa.audit_summary(blocked))
        ok = self._au(kind="write_file", target="docs/foo.md")
        self.assertIn("medium", wa.audit_summary(ok))


if __name__ == "__main__":
    unittest.main()
