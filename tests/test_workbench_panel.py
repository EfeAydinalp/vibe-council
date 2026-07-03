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

    # --- Windows shutdown/bind hardening (PR #88) ---------------------------- #

    def test_make_server_default_host_is_127_0_0_1(self):
        httpd = wp.make_server(self.root, port=0)
        try:
            self.assertEqual(wp.effective_bind_host(httpd), "127.0.0.1")
            self.assertEqual(httpd.server_address[0], "127.0.0.1")
        finally:
            httpd.server_close()

    def test_make_server_rejects_0_0_0_0(self):
        with self.assertRaises(ValueError):
            wp.make_server(self.root, host="0.0.0.0", port=0)

    def test_make_server_rejects_empty_string_host(self):
        # an empty host string is how socketserver spells "bind all interfaces" -- must
        # never be accepted, even though it isn't literally the string "0.0.0.0".
        with self.assertRaises(ValueError):
            wp.make_server(self.root, host="", port=0)

    def test_startup_lines_use_the_actual_bound_host(self):
        httpd = wp.make_server(self.root, port=0)
        try:
            lines = wp._startup_lines(httpd, token="tok")
            self.assertTrue(lines[0].startswith("http://127.0.0.1:"))
            self.assertIn("?token=tok", lines[0])
            self.assertIn(str(httpd.server_address[1]), lines[0])
        finally:
            httpd.server_close()

    def test_startup_lines_omit_token_query_when_no_token(self):
        httpd = wp.make_server(self.root, port=0)
        try:
            lines = wp._startup_lines(httpd, token="")
            self.assertNotIn("?token=", lines[0])
            self.assertFalse(any("POST token" in line for line in lines))
        finally:
            httpd.server_close()

    def test_serve_closes_the_socket_on_keyboard_interrupt(self):
        # Simulate Ctrl-C without blocking on a real serve_forever() loop or spawning a
        # thread: make the created server's serve_forever raise KeyboardInterrupt
        # immediately, and confirm serve() still reaches server_close() via `finally`.
        created = {}
        real_make_server = wp.make_server

        def spy_make_server(*args, **kwargs):
            httpd = real_make_server(*args, **kwargs)
            httpd.serve_forever = lambda: (_ for _ in ()).throw(KeyboardInterrupt())
            created["httpd"] = httpd
            return httpd

        wp.make_server = spy_make_server
        try:
            rc = wp.serve(self.root, port=0, use_token=False)
        finally:
            wp.make_server = real_make_server
        self.assertEqual(rc, 0)
        self.assertEqual(created["httpd"].socket.fileno(), -1)  # closed

    # --- Host-header validation (PR #92; DNS-rebinding defense) -------------- #

    def test_host_header_is_local_accepts_loopback(self):
        for h in ("127.0.0.1:8765", "localhost:8765", "127.0.0.1", "localhost",
                  "[::1]:8765", "LOCALHOST:8765"):
            self.assertTrue(wp.host_header_is_local(h), h)

    def test_host_header_is_local_rejects_non_loopback(self):
        for h in ("evil.example.com", "attacker.test:8765", "0.0.0.0:8765",
                  "10.0.0.5:8765", "example.com", "127.0.0.1.evil.com", "", None,
                  "127.0.0.2:8765"):
            self.assertFalse(wp.host_header_is_local(h), h)

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
        self.assertIn("exact allowlisted", html.lower())

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

    def test_state_action_executable_for_approved_allowlisted_command(self):
        # PR #81: an approved, pending, resolver-allowlisted run_command action is now
        # executable from the panel — no payload artifact is required for commands
        # (that's a file-only concept); the resolver + trust boundary gate it instead.
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short")
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        self.assertTrue(a["executable"])
        self.assertIsNotNone(a["command_preview"])
        self.assertEqual(a["command_preview"]["label"], "git status --short")
        self.assertEqual(a["command_preview"]["argv"], ["git", "status", "--short"])
        self.assertFalse(a["command_preview"]["shell"])

    def test_state_action_not_executable_for_non_allowlisted_command(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="pip install evil")
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        self.assertFalse(a["executable"])
        self.assertIsNone(a["command_preview"])
        self.assertIn("does not resolve", a["executable_reason"])

    def test_state_action_not_executable_for_unapproved_command(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short", decision=None)
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        self.assertFalse(a["executable"])

    def test_state_no_raw_content_exposed(self):
        _seed_action(self.root, target="docs/secretcontent.md",
                     payload={"content": "TOP-SECRET-VALUE"})
        st = wp.build_state(self.root)
        self.assertNotIn("TOP-SECRET-VALUE", json.dumps(st))
        html = wp.render_html(st, token="")
        self.assertNotIn("TOP-SECRET-VALUE", html)

    def test_html_renders_command_card_with_execute_button(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short")
        html = wp.render_html(wp.build_state(self.root), token="tok")
        self.assertIn("git status --short", html)
        self.assertIn("exact allowlisted command only", html)
        self.assertIn("Execute approved command", html)
        self.assertIn(f"execAction('{act.id}','run_command')", html)

    def test_html_hides_execute_button_for_non_allowlisted_command(self):
        _seed_action(self.root, kind="run_command", target="pip install evil")
        html = wp.render_html(wp.build_state(self.root), token="tok")
        self.assertNotIn("Execute approved command", html)

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
        # A non-allowlisted command is never executable (see
        # test_state_action_not_executable_for_non_allowlisted_command), but the shared
        # execute_action() invariant still fail-closes it even if called directly.
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="pip install evil")
        code, body = wp.handle_execute(act.id, self.root)
        self.assertEqual(code, 200)
        self.assertTrue(body["blocked"])
        self.assertFalse(body["executed"])

    def test_execute_unapproved_command_blocks(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short", decision=None)
        code, body = wp.handle_execute(act.id, self.root)
        self.assertEqual(code, 200)
        self.assertTrue(body["blocked"])
        self.assertFalse(body["executed"])

    def test_execute_rejected_command_blocks(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short", decision="reject")
        code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])

    def test_execute_held_command_blocks(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short", decision="hold")
        code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])

    def test_execute_completed_command_blocks(self):
        _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                          target="git status --short", act_status="completed")
        code, body = wp.handle_execute(act.id, self.root)
        self.assertTrue(body["blocked"])

    # --- happy path (monkeypatched subprocess) --------------------------------- #

    def test_execute_allowlisted_command_runs_via_executor(self):
        import subprocess as _subprocess

        class _Fake:
            returncode = 0
            stdout = "clean\n"
            stderr = ""

        orig = _subprocess.run
        calls = []

        def _fake_run(*a, **k):
            calls.append((a, k))
            return _Fake()

        _subprocess.run = _fake_run
        try:
            _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                              target="git status --short")
            code, body = wp.handle_execute(act.id, self.root)
        finally:
            _subprocess.run = orig
        self.assertEqual(code, 200)
        self.assertTrue(body["executed"])
        self.assertEqual(body["exit_code"], 0)
        self.assertFalse(body["timed_out"])
        self.assertFalse(body["output_truncated"])
        self.assertEqual(body["command_label"], "git status --short")
        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        self.assertEqual(args[0], ["git", "status", "--short"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(wr.load_action(act.id, self.root).status, "completed")

    def test_command_result_appears_in_state_after_execution(self):
        import subprocess as _subprocess

        class _Fake:
            returncode = 0
            stdout = "clean\n"
            stderr = ""

        orig = _subprocess.run
        _subprocess.run = lambda *a, **k: _Fake()
        try:
            _t, _ap, act, _art = _seed_action(self.root, kind="run_command",
                                              target="git status --short")
            wp.handle_execute(act.id, self.root)
        finally:
            _subprocess.run = orig
        st = wp.build_state(self.root)
        a = next(x for x in st["actions"] if x["id"] == act.id)
        self.assertEqual(a["status"], "completed")
        self.assertIn("git status --short", a["result_summary"])
        self.assertFalse(a["executable"])  # already completed, not pending anymore

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

    def test_get_state_json_with_token(self):
        # /api/state is now token-gated (via the ?token= the panel URL already uses).
        c = self._conn(); c.request("GET", "/api/state?token=T")
        r = c.getresponse(); data = json.loads(r.read())
        self.assertEqual(r.status, 200)
        self.assertEqual(len(data["pending_approvals"]), 1)

    def test_get_state_json_via_token_header(self):
        c = self._conn()
        c.request("GET", "/api/state", headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); data = json.loads(r.read())
        self.assertEqual(r.status, 200)
        self.assertEqual(len(data["pending_approvals"]), 1)

    def test_get_state_without_token_rejected(self):
        c = self._conn(); c.request("GET", "/api/state")
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 403)
        self.assertIn("token", body["error"])

    def test_get_html(self):
        c = self._conn(); c.request("GET", "/")
        r = c.getresponse(); body = r.read().decode("utf-8")
        self.assertEqual(r.status, 200)
        self.assertIn("AI Council Workbench", body)

    def test_get_html_needs_no_token(self):
        # GET / stays tokenless so the panel URL loads normally; Host validation is its
        # guard. (The token is embedded in the returned HTML for the panel's own POSTs.)
        c = self._conn(); c.request("GET", "/")
        r = c.getresponse(); r.read()
        self.assertEqual(r.status, 200)

    def test_invalid_host_rejects_root(self):
        c = self._conn(); c.request("GET", "/", headers={"Host": "evil.example.com"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 403)
        self.assertIn("host", body["error"])

    def test_invalid_host_rejects_state_even_with_token(self):
        # Host check runs before the token check — a rebinding page that somehow had the
        # token still can't read state.
        c = self._conn()
        c.request("GET", "/api/state?token=T", headers={"Host": "attacker.test"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 403)
        self.assertIn("host", body["error"])

    def test_invalid_host_rejects_post_even_with_token(self):
        c = self._conn()
        c.request("POST", f"/api/approvals/{self.ap.id}/approve",
                  headers={"Host": "attacker.test", "X-Workbench-Token": "T"})
        r = c.getresponse(); body = json.loads(r.read())
        self.assertEqual(r.status, 403)
        self.assertIn("host", body["error"])
        self.assertEqual(wr.load_approval(self.ap.id, self.root).status, "pending")  # unchanged

    def test_valid_localhost_host_accepted(self):
        c = self._conn()
        c.request("GET", "/api/state?token=T",
                  headers={"Host": f"localhost:{self.port}"})
        r = c.getresponse(); r.read()
        self.assertEqual(r.status, 200)

    def test_multiple_host_headers_rejected(self):
        # http.client can't send duplicate headers via a dict, so craft the request on a
        # raw socket: a valid loopback Host *and* an attacker Host is ambiguous -> reject.
        import socket as _socket
        raw = (f"GET /api/state?token=T HTTP/1.1\r\n"
               f"Host: 127.0.0.1:{self.port}\r\n"
               f"Host: evil.test\r\n"
               f"Connection: close\r\n\r\n").encode("ascii")
        s = _socket.create_connection(("127.0.0.1", self.port), timeout=5)
        try:
            s.sendall(raw)
            resp = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                resp += chunk
        finally:
            s.close()
        status_line = resp.split(b"\r\n", 1)[0].decode("ascii", "replace")
        self.assertIn("403", status_line)

    def test_token_never_appears_in_state_json(self):
        # Use a distinctive token (the class default "T" is too short to detect) on a
        # throwaway server, and confirm it never leaks into the state response body.
        token = "ZZ-workbench-secret-9x7q"
        httpd = wp.make_server(self.root, host="127.0.0.1", port=0, token=token)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            port = httpd.server_address[1]
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.request("GET", "/api/state", headers={"X-Workbench-Token": token})
            r = c.getresponse(); raw = r.read().decode("utf-8")
            self.assertEqual(r.status, 200)
            self.assertNotIn(token, raw)
        finally:
            httpd.shutdown(); httpd.server_close()

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
        c = self._conn()
        c.request("GET", "/api/state", headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); data = json.loads(r.read())
        a = next(x for x in data["actions"] if x["id"] == self.act.id)
        self.assertTrue(a["executable"])


class TestExecuteCommandHttp(unittest.TestCase):
    """HTTP-level coverage for executing an approved run_command action via the panel.
    subprocess.run is monkeypatched so this stays fast/deterministic (the real
    subprocess wiring is already smoke-tested in test_workbench_command_executor.py)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _t, self.ap, self.act, _art = _seed_action(
            self.root, kind="run_command", target="git status --short")
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

    def test_execute_command_requires_token(self):
        c = self._conn()
        c.request("POST", f"/api/actions/{self.act.id}/execute")
        r = c.getresponse(); r.read()
        self.assertEqual(r.status, 403)
        self.assertEqual(wr.load_action(self.act.id, self.root).status, "pending")

    def test_execute_command_ignores_browser_supplied_body(self):
        import subprocess as _subprocess

        class _Fake:
            returncode = 0
            stdout = "clean\n"
            stderr = ""

        orig = _subprocess.run
        calls = []

        def _fake_run(*a, **k):
            calls.append((a, k))
            return _Fake()

        _subprocess.run = _fake_run
        try:
            malicious = json.dumps({
                "command": "rm -rf /", "argv": ["rm", "-rf", "/"], "cwd": "/tmp",
                "env": {"EVIL": "1"}, "timeout": 999999, "shell": True,
            }).encode("utf-8")
            c = self._conn()
            c.request("POST", f"/api/actions/{self.act.id}/execute", body=malicious,
                      headers={"X-Workbench-Token": "T", "Content-Type": "application/json"})
            r = c.getresponse(); body = json.loads(r.read())
        finally:
            _subprocess.run = orig
        self.assertEqual(r.status, 200)
        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        # only the server-side resolved argv ever reaches subprocess.run, regardless
        # of whatever the request body claimed.
        self.assertEqual(args[0], ["git", "status", "--short"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(body["command_label"], "git status --short")

    def test_execute_command_response_has_no_huge_raw_output(self):
        import subprocess as _subprocess

        class _Fake:
            returncode = 0
            stdout = "x" * 5000
            stderr = ""

        orig = _subprocess.run
        _subprocess.run = lambda *a, **k: _Fake()
        try:
            c = self._conn()
            c.request("POST", f"/api/actions/{self.act.id}/execute",
                      headers={"X-Workbench-Token": "T"})
            r = c.getresponse(); body = json.loads(r.read())
        finally:
            _subprocess.run = orig
        self.assertEqual(r.status, 200)
        self.assertIn("stdout_summary", body)
        self.assertLessEqual(len(body["stdout_summary"]), 5000)

    def test_get_state_shows_command_preview(self):
        c = self._conn()
        c.request("GET", "/api/state", headers={"X-Workbench-Token": "T"})
        r = c.getresponse(); data = json.loads(r.read())
        a = next(x for x in data["actions"] if x["id"] == self.act.id)
        self.assertTrue(a["executable"])
        self.assertEqual(a["command_preview"]["label"], "git status --short")


class TestAgentProposalDisplay(unittest.TestCase):
    """The panel surfaces safe 'proposed by agent' metadata for imported proposals
    (PR: panel agent-proposal visibility) — display-only, never raw payload content,
    always HTML-escaped."""

    def setUp(self):
        from backend import workbench_proposal_importer as wimp
        self.wimp = wimp
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _import(self, **over):
        prop = {
            "proposal_schema": 1,
            "proposal_id": over.get("proposal_id", "prop-panel-1"),
            "agent": {"name": over.get("agent_name", "claude-code"),
                      "role": over.get("agent_role", "coder"),
                      "session": "sess-1"},
            "title": over.get("title", "Write a note"),
            "summary": over.get("summary", "adds a small note"),
            "action": {"kind": "write_file",
                       "target": over.get("target", "docs/note.md"),
                       "payload": {"content": over.get("content", "hello agent\n")}},
        }
        return self.wimp.import_proposal(prop, project_root=self.root)

    def test_state_includes_safe_agent_metadata(self):
        self._import()
        state = wp.build_state(self.root)
        tv = next(t for t in state["tasks"])
        prop = tv["proposal"]
        self.assertIsNotNone(prop)
        self.assertTrue(prop["proposed_by_agent"])
        self.assertEqual(prop["agent_name"], "claude-code")
        self.assertEqual(prop["agent_role"], "coder")
        self.assertEqual(prop["proposal_id"], "prop-panel-1")

    def test_html_shows_agent_badge(self):
        self._import()
        html = wp.render_html(wp.build_state(self.root), token="")
        self.assertIn("proposed by agent: claude-code", html)
        self.assertIn("role: coder", html)
        self.assertIn("proposal id: prop-panel-1", html)

    def test_demo_and_manual_tasks_have_no_agent_badge(self):
        # a manual (non-agent) task: source is not "agent:*"
        wo.start_task("manual task", source="panel-demo", project_root=self.root)
        state = wp.build_state(self.root)
        tv = next(t for t in state["tasks"])
        self.assertIsNone(tv["proposal"])
        html = wp.render_html(state, token="")
        self.assertNotIn("proposed by agent", html)

    def test_agent_source_without_proposal_record_degrades_gracefully(self):
        # A task tagged agent:<name> but whose proposals index record is gone (deleted/
        # never written) still shows the badge with the source-derived name; role and
        # proposal_id are simply omitted rather than erroring.
        wo.start_task("orphaned agent task", source="agent:codex",
                      project_root=self.root)
        state = wp.build_state(self.root)
        tv = next(t for t in state["tasks"])
        self.assertIsNotNone(tv["proposal"])
        self.assertTrue(tv["proposal"]["proposed_by_agent"])
        self.assertEqual(tv["proposal"]["agent_name"], "codex")
        self.assertEqual(tv["proposal"]["agent_role"], "")
        self.assertEqual(tv["proposal"]["proposal_id"], "")
        html = wp.render_html(state, token="")
        self.assertIn("proposed by agent: codex", html)

    def test_raw_payload_not_in_html_or_json_state(self):
        self._import(content="DISTINCTIVE-PANEL-PAYLOAD-7f\n")
        state = wp.build_state(self.root)
        self.assertNotIn("DISTINCTIVE-PANEL-PAYLOAD-7f", json.dumps(state))
        html = wp.render_html(state, token="")
        self.assertNotIn("DISTINCTIVE-PANEL-PAYLOAD-7f", html)

    def test_malicious_agent_name_is_escaped(self):
        self._import(agent_name="<script>alert(1)</script>")
        state = wp.build_state(self.root)
        html = wp.render_html(state, token="")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)  # escaped, not executable

    def test_malicious_title_is_escaped(self):
        self._import(title="<img src=x onerror=alert(1)>")
        html = wp.render_html(wp.build_state(self.root), token="")
        self.assertNotIn("<img src=x onerror=alert(1)>", html)
        self.assertIn("&lt;img", html)

    def test_state_token_gate_and_no_payload_over_http(self):
        # /api/state stays token-gated; agent metadata is present, payload is not.
        import http.client
        self._import(content="HTTP-DISTINCTIVE-PAYLOAD-9q\n")
        httpd = wp.make_server(self.root, host="127.0.0.1", port=0, token="T")
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            port = httpd.server_address[1]
            # no token -> 403 (unchanged behavior)
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.request("GET", "/api/state")
            self.assertEqual(c.getresponse().status, 403)
            # with token -> 200, agent metadata present, no raw payload
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.request("GET", "/api/state", headers={"X-Workbench-Token": "T"})
            r = c.getresponse(); raw = r.read().decode("utf-8")
            self.assertEqual(r.status, 200)
            self.assertIn("claude-code", raw)
            self.assertNotIn("HTTP-DISTINCTIVE-PAYLOAD-9q", raw)
        finally:
            httpd.shutdown(); httpd.server_close()


if __name__ == "__main__":
    unittest.main()
