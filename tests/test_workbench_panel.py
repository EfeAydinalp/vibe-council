"""Tests for the local Workbench panel (backend/workbench_panel.py).

Stdlib-only (`unittest`). Pure state/decision/render functions are tested directly; a
bounded threaded `http.server` smoke covers routing. Everything is localhost-only and
non-executing — no provider/model/network egress, no action execution, temp runtime
only (no `.council/runtime/` in the real repo).
"""

import json
import threading
import unittest
import tempfile
import http.client
from pathlib import Path

from backend import workbench_panel as wp
from backend import workbench_orchestrator as wo
from backend import workbench_runtime as wr

FIXED = "2026-07-01T00:00:00Z"


def _seed(root: Path):
    """A task in awaiting_approval with a pending, medium-risk write approval."""
    task = wo.start_task("Panel task", project_root=root, on=FIXED)
    ap = wo.request_approval(task.id, title="Write docs/foo.md",
                             prompt="apply doc edit",
                             requested_action="write_file:docs/foo.md",
                             risk_level="medium", project_root=root, on=FIXED)
    return task, ap


class TestPureState(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_state(self):
        st = wp.build_state(self.root)
        self.assertEqual(st["tasks"], [])
        self.assertEqual(st["pending_approvals"], [])
        self.assertTrue(st["localhost_only"])
        self.assertFalse(st["executes_actions"])

    def test_state_with_task_and_approval(self):
        task, ap = _seed(self.root)
        st = wp.build_state(self.root)
        self.assertEqual(len(st["tasks"]), 1)
        self.assertEqual(st["tasks"][0]["status"], "awaiting_approval")
        self.assertEqual(len(st["pending_approvals"]), 1)
        card = st["pending_approvals"][0]
        self.assertEqual(card["id"], ap.id)
        self.assertEqual(card["risk_level"], "medium")     # from advisory audit
        self.assertFalse(card["blocked"])
        self.assertIn("Approve", card["rewritten_prompt"])

    def test_build_state_does_not_mutate(self):
        _seed(self.root)
        before = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        wp.build_state(self.root)
        wp.build_state(self.root)
        after = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(after, before)  # advisory audits use save=False

    def test_render_html_has_headings_and_no_external_assets(self):
        _seed(self.root)
        html = wp.render_html(wp.build_state(self.root), token="tok")
        self.assertIn("AI Council Workbench", html)
        self.assertIn("Pending approvals", html)
        self.assertIn("does not execute actions", html.lower())
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("<script src", html)

    def test_empty_render_states(self):
        html = wp.render_html(wp.build_state(self.root), token="")
        self.assertIn("No pending approvals.", html)
        self.assertIn("No tasks", html)

    # --- decisions (record only; never execute) ----------------------------- #

    def test_approve_records_decision_not_executed(self):
        _task, ap = _seed(self.root)
        code, body = wp.handle_decision(ap.id, "approve", self.root)
        self.assertEqual(code, 200)
        self.assertFalse(body["executed"])
        self.assertEqual(wr.load_approval(ap.id, self.root).status, "approved")
        # no action ever created/run by a panel decision
        self.assertEqual(wr.load_task(ap.task_id, self.root).action_ids, [])

    def test_reject_and_hold(self):
        _t, ap = _seed(self.root)
        self.assertEqual(wp.handle_decision(ap.id, "reject", self.root)[0], 200)
        self.assertEqual(wr.load_approval(ap.id, self.root).status, "rejected")
        _t2, ap2 = _seed(self.root)
        self.assertEqual(wp.handle_decision(ap2.id, "hold", self.root)[0], 200)
        self.assertEqual(wr.load_approval(ap2.id, self.root).status, "held")

    def test_invalid_approval_id_and_decision(self):
        self.assertEqual(wp.handle_decision("appr-nope", "approve", self.root)[0], 404)
        _t, ap = _seed(self.root)
        self.assertEqual(wp.handle_decision(ap.id, "frobnicate", self.root)[0], 400)

    def test_decide_already_decided_conflicts(self):
        _t, ap = _seed(self.root)
        wp.handle_decision(ap.id, "approve", self.root)
        self.assertEqual(wp.handle_decision(ap.id, "approve", self.root)[0], 409)

    def test_make_server_is_localhost_only(self):
        with self.assertRaises(ValueError):
            wp.make_server(self.root, host="0.0.0.0")

    # --- dogfood usability polish (PR #71) ---------------------------------- #

    def test_empty_state_offers_demo(self):
        html = wp.render_html(wp.build_state(self.root), token="")
        self.assertIn("No tasks yet.", html)
        self.assertIn("Create demo task", html)
        self.assertIn("executes nothing", html)
        self.assertIn("createDemo()", html)

    def test_html_has_self_explanatory_notices(self):
        html = wp.render_html(wp.build_state(self.root), token="")
        self.assertIn("Local-only Workbench panel", html)
        self.assertIn("does not execute actions", html.lower())
        self.assertIn("Current workflow", html)
        self.assertIn("Future workflow", html)

    def test_create_demo_task_seeds_runtime_no_execution(self):
        res = wp.create_demo_task(self.root)
        self.assertTrue(res["ok"])
        self.assertFalse(res["executed"])
        # one task, one pending approval, one advisory audit result
        self.assertEqual(len(wr.list_tasks(project_root=self.root)), 1)
        pend = wo.list_pending_approvals(self.root)
        self.assertEqual(len(pend), 1)
        ap = wr.load_approval(res["approval_id"], self.root)
        self.assertIsNotNone(wr.load_audit(res["audit_id"], self.root))  # audit saved
        self.assertEqual(ap.audit_id, res["audit_id"])                   # attached
        # the demo created NO action (nothing to execute)
        self.assertEqual(wr.load_task(res["task_id"], self.root).action_ids, [])

    def test_demo_task_renders_in_state_and_cards(self):
        wp.create_demo_task(self.root)
        st = wp.build_state(self.root)
        self.assertEqual(len(st["tasks"]), 1)
        self.assertEqual(len(st["pending_approvals"]), 1)
        html = wp.render_html(st, token="")
        self.assertIn("No action will run from this panel", html)
        self.assertIn("risk: medium", html)

    def test_approve_after_demo(self):
        res = wp.create_demo_task(self.root)
        code, body = wp.handle_decision(res["approval_id"], "approve", self.root)
        self.assertEqual(code, 200)
        self.assertFalse(body["executed"])
        self.assertEqual(wr.load_approval(res["approval_id"], self.root).status, "approved")


class TestHttpSmoke(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task, self.ap = _seed(self.root)
        self.httpd = wp.make_server(self.root, host="127.0.0.1", port=0, token="T")
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self._tmp.cleanup()

    def _conn(self):
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)

    def test_binds_localhost(self):
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")

    def test_get_state_json(self):
        c = self._conn(); c.request("GET", "/api/state")
        r = c.getresponse(); data = json.loads(r.read())
        self.assertEqual(r.status, 200)
        self.assertEqual(len(data["pending_approvals"]), 1)

    def test_get_html(self):
        c = self._conn(); c.request("GET", "/")
        r = c.getresponse(); body = r.read().decode("utf-8")
        self.assertEqual(r.status, 200)
        self.assertIn("AI Council Workbench", body)

    def test_post_requires_token(self):
        c = self._conn(); c.request("POST", f"/api/approvals/{self.ap.id}/approve")
        r = c.getresponse(); r.read()
        self.assertEqual(r.status, 403)
        self.assertEqual(wr.load_approval(self.ap.id, self.root).status, "pending")  # unchanged

    def test_post_with_token_records_decision(self):
        c = self._conn()
        c.request("POST", f"/api/approvals/{self.ap.id}/hold",
                  headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 200)
        self.assertFalse(body["executed"])
        self.assertEqual(wr.load_approval(self.ap.id, self.root).status, "held")

    def test_unknown_route_404(self):
        c = self._conn(); c.request("GET", "/api/nope")
        r = c.getresponse(); r.read()
        self.assertEqual(r.status, 404)

    def test_demo_requires_token(self):
        c = self._conn(); c.request("POST", "/api/tasks/demo")
        r = c.getresponse(); r.read()
        self.assertEqual(r.status, 403)  # no token -> rejected

    def test_demo_with_token_creates_task(self):
        c = self._conn()
        c.request("POST", "/api/tasks/demo", headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 200)
        self.assertTrue(body["ok"])
        self.assertFalse(body["executed"])
        self.assertIsNotNone(wr.load_task(body["task_id"], self.root))


if __name__ == "__main__":
    unittest.main()
