"""Tests for the local Workbench panel (backend/workbench_panel.py).

Stdlib-only (`unittest`). Pure state/decision/render functions are tested directly; a
bounded threaded `http.server` smoke covers routing. Everything is localhost-only.
Approve/reject/hold never execute; execution (PR #77) is a separate, explicit
`/api/actions/<id>/execute` call that only ever accepts an action id from the browser
— never file content or patch text (the local payload artifact is loaded/verified
server-side) — no provider/model/network egress, temp runtime only (no
`.council/runtime/` in the real repo).
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
from backend import workbench_payloads as wpay

FIXED = "2026-07-01T00:00:00Z"


def _seed(root: Path):
    """A task in awaiting_approval with a pending, medium-risk write approval."""
    task = wo.start_task("Panel task", project_root=root, on=FIXED)
    ap = wo.request_approval(task.id, title="Write docs/foo.md",
                             prompt="apply doc edit",
                             requested_action="write_file:docs/foo.md",
                             risk_level="medium", project_root=root, on=FIXED)
    return task, ap


def _seed_action(root: Path, kind: str = "write_file", target: str = "docs/foo.md",
                 decision: str = "approve", payload=None, act_status: str = "pending"):
    """A task + approval (decided as ``decision``, or left ``pending`` if None) with a
    linked runtime ``Action`` of ``act_status``, and — if ``payload`` is given — a
    matching, saved payload artifact for it. Mirrors PR #76's executor test fixtures;
    does not go through ``mark_executing`` (a documented placeholder, unrelated to this
    panel wiring)."""
    task = wo.start_task("Panel exec task", project_root=root, on=FIXED)
    ap = wo.request_approval(task.id, title=f"{kind} {target}", prompt="apply change",
                             requested_action=f"{kind}:{target}", risk_level="medium",
                             project_root=root, on=FIXED)
    if decision:
        wo.decide_approval(ap.id, decision, project_root=root, on=FIXED)
    act = wr.new_action(task.id, kind, command_or_path=target, approval_id=ap.id, on=FIXED)
    act.status = act_status
    wr.save_action(act, root)
    t = wr.load_task(task.id, root)
    t.action_ids.append(act.id)
    wr.save_task(t, root)
    artifact = None
    if payload is not None:
        artifact = wpay.build_payload_artifact(act, payload, task=t, approval=ap, on=FIXED)
        wpay.save_payload_artifact(artifact, root)
    return task, ap, act, artifact


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
        self.assertEqual(st["actions"], [])
        self.assertTrue(st["localhost_only"])
        # PR #77: the panel can now execute an approved bounded file action (behind an
        # explicit Execute click + payload verification) — this flag now means "the
        # panel supports execution", not "approve auto-executes" (it never does).
        self.assertTrue(st["executes_actions"])

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
        self.assertIn("Actions", html)
        self.assertIn("it never executes anything", html.lower())
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
        self.assertIn("it never executes anything", html.lower())
        self.assertIn("Workflow:", html)
        self.assertIn("run_command", html)

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


class TestExecuteAction(unittest.TestCase):
    """Pure-function coverage for `_action_view` (state) and `handle_execute` — no HTTP.
    Temp dirs only; real execution stays bounded write_file/edit_file behind the full
    invariant (payload hash/scope + a fresh deterministic trust re-check)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # --- state reflects payload/executable status --------------------------- #

    def test_state_action_not_executable_without_payload(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/nopay.md")
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        self.assertFalse(a["payload_exists"])
        self.assertFalse(a["payload_verified"])
        self.assertFalse(a["executable"])

    def test_state_action_executable_with_valid_write_payload(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/pay.md",
                                          payload={"content": "hi\n"})
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        self.assertTrue(a["payload_exists"])
        self.assertTrue(a["payload_verified"])
        self.assertTrue(a["executable"])
        self.assertEqual(a["payload_summary"]["content_bytes"], len("hi\n"))

    def test_state_action_executable_with_valid_edit_payload(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "e.py").write_text("x = 1\n", encoding="utf-8")
        _t, _ap, act, _art = _seed_action(
            self.root, kind="edit_file", target="src/e.py",
            payload={"old_text": "x = 1", "new_text": "x = 2", "max_replacements": 1})
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        self.assertTrue(a["executable"])

    def test_state_action_not_executable_for_run_command(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short")
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        # PR #80 put run_command in REAL_EXEC_KINDS, but the panel's `executable` flag
        # also requires a verified payload artifact, and run_command actions never
        # have one (payloads are file-only, PR #76) — so the panel offers no new
        # execute affordance for commands, even though the executor could now run one.
        self.assertFalse(a["executable"])

    def test_state_no_raw_content_exposed(self):
        _seed_action(self.root, target="docs/secretcontent.md",
                     payload={"content": "TOP-SECRET-VALUE"})
        st = wp.build_state(self.root)
        self.assertNotIn("TOP-SECRET-VALUE", json.dumps(st))
        html = wp.render_html(st, token="")
        self.assertNotIn("TOP-SECRET-VALUE", html)

    def test_get_state_does_not_mutate(self):
        _seed_action(self.root, target="docs/pay2.md", payload={"content": "hi\n"})
        before = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        wp.build_state(self.root)
        wp.build_state(self.root)
        after = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    # --- handle_execute: fail-closed cases ----------------------------------- #

    def test_execute_missing_action_404(self):
        code, _body = wp.handle_execute("act-nope", self.root)
        self.assertEqual(code, 404)

    def test_execute_unapproved_action_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/u.md", decision=None,
                                          payload={"content": "x"})
        code, body = wp.handle_execute(act.id, self.root)
        self.assertEqual(code, 200)
        self.assertTrue(body["blocked"])
        self.assertFalse(body["executed"])

    def test_execute_rejected_approval_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/r.md", decision="reject",
                                          payload={"content": "x"})
        _code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])
        self.assertFalse(body["executed"])

    def test_execute_held_approval_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/h.md", decision="hold",
                                          payload={"content": "x"})
        _code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])

    def test_execute_completed_action_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/c.md",
                                          payload={"content": "x"}, act_status="completed")
        _code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])
        self.assertFalse(body["executed"])

    def test_execute_blocked_action_stays_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/b.md",
                                          payload={"content": "x"}, act_status="blocked")
        _code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])
        self.assertFalse(body["executed"])

    def test_execute_missing_payload_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/nop.md")
        _code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])
        self.assertFalse((self.root / "docs" / "nop.md").exists())

    def test_execute_tampered_payload_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/tamper.md",
                                          payload={"content": "orig"})
        path = wpay._entry_path(self.root, act.id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["payload"]["content"] = "rewritten"
        path.write_text(json.dumps(data), encoding="utf-8")
        _code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])
        self.assertFalse((self.root / "docs" / "tamper.md").exists())

    def test_execute_payload_target_mismatch_blocked(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/real.md")
        _ot, _oap, other_act, _oart = _seed_action(self.root, target="docs/other.md")
        artifact = wpay.build_payload_artifact(other_act, {"content": "x"})
        artifact.action_id = act.id  # claims to belong to `act`, but target differs
        wpay.save_payload_artifact(artifact, self.root)
        _code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])
        self.assertFalse((self.root / "docs" / "real.md").exists())
        self.assertFalse((self.root / "docs" / "other.md").exists())

    def test_execute_non_allowlisted_command_fails_closed(self):
        # PR #80 added real run_command execution for resolver-allowlisted commands
        # (see test_workbench_command_executor.py) — the panel gains no new UI/button
        # for it (no payload artifact ever exists for run_command, so `executable`
        # stays False; see test_state_action_not_executable_for_run_command), but the
        # shared execute_action() invariant still fail-closes a non-allowlisted command
        # even if called directly.
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="pip install evil")
        code, body = wp.handle_execute(act.id, self.root)
        self.assertEqual(code, 200)
        self.assertTrue(body["blocked"])
        self.assertFalse(body["executed"])

    # --- happy path ----------------------------------------------------------- #

    def test_execute_write_file_success(self):
        _t, _ap, act, _art = _seed_action(self.root, target="docs/success.md",
                                          payload={"content": "written by panel\n"})
        code, body = wp.handle_execute(act.id, self.root)
        self.assertEqual(code, 200)
        self.assertTrue(body["executed"])
        self.assertFalse(body["blocked"])
        self.assertEqual((self.root / "docs" / "success.md").read_text(encoding="utf-8"),
                         "written by panel\n")
        self.assertEqual(wr.load_action(act.id, self.root).status, "completed")

    def test_execute_edit_file_success(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "s.py").write_text("x = 1\n", encoding="utf-8")
        _t, _ap, act, _art = _seed_action(
            self.root, kind="edit_file", target="src/s.py",
            payload={"old_text": "x = 1", "new_text": "x = 2", "max_replacements": 1})
        code, body = wp.handle_execute(act.id, self.root)
        self.assertEqual(code, 200)
        self.assertTrue(body["executed"])
        self.assertEqual((self.root / "src" / "s.py").read_text(encoding="utf-8"), "x = 2\n")

    def test_approve_still_does_not_auto_execute(self):
        _t, ap, act, _art = _seed_action(self.root, target="docs/noauto.md", decision=None,
                                         payload={"content": "x"})
        code, body = wp.handle_decision(ap.id, "approve", self.root)
        self.assertEqual(code, 200)
        self.assertFalse(body["executed"])
        self.assertEqual(wr.load_action(act.id, self.root).status, "pending")  # unchanged
        self.assertFalse((self.root / "docs" / "noauto.md").exists())


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


class TestExecuteHttp(unittest.TestCase):
    """HTTP-level coverage for `POST /api/actions/<id>/execute` — token gate, routing,
    and confirmation the browser cannot inject payload content (the handler never
    reads the request body; only the local, pre-verified payload artifact is used)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _t, self.ap, self.act, self.artifact = _seed_action(
            self.root, target="docs/http.md", payload={"content": "hello\n"})
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

    def test_execute_requires_token(self):
        c = self._conn()
        c.request("POST", f"/api/actions/{self.act.id}/execute")
        r = c.getresponse(); r.read()
        self.assertEqual(r.status, 403)
        self.assertEqual(wr.load_action(self.act.id, self.root).status, "pending")
        self.assertFalse((self.root / "docs" / "http.md").exists())

    def test_execute_rejects_invalid_action_id(self):
        c = self._conn()
        c.request("POST", "/api/actions/act-nope/execute", headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 404)

    def test_execute_with_token_writes_file(self):
        c = self._conn()
        c.request("POST", f"/api/actions/{self.act.id}/execute",
                  headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 200)
        self.assertTrue(body["executed"])
        self.assertEqual(body["action_id"], self.act.id)
        self.assertEqual(body["kind"], "write_file")
        self.assertEqual((self.root / "docs" / "http.md").read_text(encoding="utf-8"),
                         "hello\n")

    def test_execute_ignores_browser_supplied_body_content(self):
        # The handler never reads the POST body for this route — only action id from
        # the URL is used; the local, pre-verified payload artifact supplies content.
        payload = json.dumps({"content": "malicious-injected-content\n"}).encode("utf-8")
        c = self._conn()
        c.request("POST", f"/api/actions/{self.act.id}/execute", body=payload,
                  headers={"X-Workbench-Token": "T", "Content-Type": "application/json"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 200)
        self.assertTrue(body["executed"])
        written = (self.root / "docs" / "http.md").read_text(encoding="utf-8")
        self.assertEqual(written, "hello\n")
        self.assertNotIn("malicious-injected-content", written)

    def test_execute_response_has_no_raw_content(self):
        c = self._conn()
        c.request("POST", f"/api/actions/{self.act.id}/execute",
                  headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); raw = r.read()
        self.assertNotIn(b"hello", raw)  # only safe summary fields, no file content

    def test_get_state_shows_executable_action(self):
        c = self._conn(); c.request("GET", "/api/state")
        r = c.getresponse(); data = json.loads(r.read())
        a = next(x for x in data["actions"] if x["id"] == self.act.id)
        self.assertTrue(a["executable"])


if __name__ == "__main__":
    unittest.main()
