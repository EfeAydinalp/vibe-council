"""AI Council Workbench — local panel (v0.5, stdlib-only).

The first user-visible Workbench slice: a **localhost-only** HTML panel that renders
task progress and pending approval cards from `.council/runtime/`, lets a human
**approve / reject / hold** an approval, and — for an already-approved, bounded
`write_file`/`edit_file` action with a verified local payload artifact — lets them
explicitly **execute** it via the guarded executor (PR #77). Built on `http.server` +
`json` + stdlib — no framework, no npm, no external assets/CDN, no network egress.

**Approval and execution stay separate.** Approving here only records an
`ApprovalDecision`; it never executes anything. Execution is a **distinct, explicit**
POST (`/api/actions/<action_id>/execute`) that the browser can only trigger by action
id — it never sends file content or patch text. The executor
(`backend/workbench_executor.py`) loads and verifies the local payload artifact
(`backend/workbench_payloads.py`), re-runs the deterministic trust boundary, and only
then performs bounded real execution; any mismatch/missing artifact/blocked kind fails
closed. The panel offers **no UI/affordance for `run_command`** — the `executable` flag
in `build_state()` requires a verified payload artifact, and `run_command` actions never
have one (payloads are file-only, PR #76), regardless of PR #80 adding real allowlisted
command execution at the executor level. The panel binds to `127.0.0.1` only (no
`0.0.0.0`/LAN/mobile), and POSTs require a startup token.

Pure functions (`build_state`, `handle_decision`, `handle_execute`, `render_html`) hold
the logic and are tested directly; the HTTP handler is a thin router over them.
"""

from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit, parse_qs

from . import workbench_runtime as wr
from . import workbench_orchestrator as wo
from . import workbench_auditor as wa
from . import workbench_executor as we
from . import workbench_payloads as wpay

_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
DECISIONS = ("approve", "reject", "hold")


# --------------------------------------------------------------------------- #
# Pure state + decision logic (no HTTP)
# --------------------------------------------------------------------------- #

def _project_name(project_root: Optional[Path]) -> str:
    # only the directory *name*, never an absolute local path (no path leakage).
    p = Path(project_root) if project_root is not None else Path.cwd()
    return p.name or "project"


def _task_view(task, project_root: Optional[Path]) -> Dict:
    p = wo.get_task_progress(task.id, project_root)
    cur = p.get("current_stage") or {}
    return {
        "id": p["task_id"], "title": p["title"], "status": p["status"],
        "current_stage": cur.get("name", ""), "current_stage_status": cur.get("status", ""),
        "completed_stages": p["completed_stages"], "next_action": p["next_action"],
        "active_worker": p["active_worker"], "active_model": p["active_model"],
    }


def _action_view(action, project_root: Optional[Path]) -> Dict:
    """Read-only, content-free view of one runtime ``Action`` for the panel: status,
    payload verification, a fresh (dry-run) risk/trust preview for still-pending
    actions, and whether the panel may offer to execute it. Never includes raw
    ``content``/``old_text``/``new_text`` — only the payload artifact's redacted
    summary (byte counts / flags / kind), matching the executor's own log style."""
    approval = (wr.load_approval(action.approval_id, project_root)
                if action.approval_id else None)
    task = wr.load_task(action.task_id, project_root)

    artifact = wpay.load_payload_artifact(action.id, project_root)
    payload_verified = False
    payload_summary: Optional[Dict] = None
    if artifact is not None:
        payload_summary = artifact.redacted_summary
        payload_verified = wpay.verify_payload_against_action(
            artifact, action, approval, task).ok

    risk_level, findings, would_execute = "blocked", [], False
    if action.status == "pending":
        # Dry-run only — re-runs the deterministic trust boundary, mutates nothing.
        preview = we.preview_action(action, approval, task, project_root)
        risk_level, findings, would_execute = (
            preview.risk_level, preview.findings, preview.would_execute)

    executable = (
        action.status == "pending"
        and action.kind in we.REAL_EXEC_KINDS
        and artifact is not None
        and payload_verified
        and would_execute
    )
    return {
        "id": action.id, "task_id": action.task_id, "approval_id": action.approval_id,
        "kind": action.kind, "target": action.command_or_path, "status": action.status,
        "result_summary": action.result_summary,
        "payload_exists": artifact is not None,
        "payload_verified": payload_verified,
        "payload_summary": payload_summary,
        "risk_level": risk_level, "findings": findings,
        "executable": executable,
    }


def build_state(project_root: Optional[Path] = None) -> Dict:
    """Read-only snapshot for the panel. Advisory-audits each pending approval
    (``save=False`` — no writes); action views are dry-run previews only. Never
    mutates runtime state."""
    all_tasks = wr.list_tasks(project_root=project_root)
    tasks = [_task_view(t, project_root) for t in all_tasks]
    approvals = []
    for ap in wo.list_pending_approvals(project_root):
        audit = wa.audit_approval_request(ap.id, project_root=project_root, save=False)
        approvals.append({
            "id": ap.id, "task_id": ap.task_id, "title": ap.title,
            "risk_level": audit.risk_level, "blocked": audit.blocked,
            "rewritten_prompt": audit.rewritten_prompt, "findings": audit.findings,
            "requested_action": ap.requested_action or "", "scope": ap.scope,
        })
    actions: List[Dict] = []
    for t in all_tasks:
        for aid in t.action_ids:
            act = wr.load_action(aid, project_root)
            if act is not None:
                actions.append(_action_view(act, project_root))
    return {
        "product": "AI Council Workbench",
        "project": _project_name(project_root),
        "localhost_only": True,
        "executes_actions": True,        # PR #77: explicit execute is now possible
        "tasks": tasks,
        "pending_approvals": approvals,
        "actions": actions,
    }


def handle_decision(approval_id: str, decision: str,
                    project_root: Optional[Path] = None,
                    reason: Optional[str] = None) -> Tuple[int, Dict]:
    """Record approve/reject/hold on a pending approval (decision only — **no action
    execution**). Returns (http_status, body). Validates decision + id."""
    if decision not in DECISIONS:
        return 400, {"error": f"unknown decision '{decision}'"}
    ap = wr.load_approval(approval_id, project_root)
    if ap is None:
        return 404, {"error": "approval not found"}
    if ap.status != "pending":
        return 409, {"error": f"approval already decided ('{ap.status}')"}
    try:
        dec = wo.decide_approval(approval_id, decision, reason=reason,
                                 decided_by="panel", project_root=project_root)
    except wo.OrchestratorError as e:
        return 400, {"error": str(e)}
    return 200, {"ok": True, "approval_id": approval_id, "decision": dec.decision,
                 "executed": False, "state": build_state(project_root)}


def handle_execute(action_id: str, project_root: Optional[Path] = None) -> Tuple[int, Dict]:
    """Execute an already-approved, bounded ``write_file``/``edit_file`` action via the
    guarded executor. The caller supplies **only** the action id — never file content
    or patch text; the executor loads and verifies the local payload artifact itself
    (``backend/workbench_payloads.py``) and re-runs the deterministic trust boundary
    before any real write/edit. Fails closed (``blocked``/error, no mutation) on a
    missing action, an unsupported kind (e.g. ``run_command``), an unapproved/
    rejected/held approval, a non-pending action, or a missing/tampered/mismatched
    payload artifact — all handled by the executor's existing invariant, not
    re-implemented here. Returns (http_status, body); body carries no raw content."""
    action = wr.load_action(action_id, project_root)
    if action is None:
        return 404, {"error": "action not found", "action_id": action_id}
    try:
        result = we.execute_action(action_id, project_root=project_root, dry_run=False)
    except we.ExecutorError as e:
        return 400, {"error": str(e), "action_id": action_id, "executed": False}
    return 200, {
        "executed": result.executed, "dry_run": result.dry_run, "allowed": result.allowed,
        "blocked": result.blocked, "action_id": result.action_id, "kind": result.kind,
        "risk_level": result.risk_level, "findings": result.findings,
        "preview": result.preview, "reason": result.reason,
    }


def create_demo_task(project_root: Optional[Path] = None) -> Dict:
    """Create a local demo task + pending approval for dogfooding the panel. Local
    only, no external effects, no execution.

    Deliberately creates **no Action and no payload artifact** (PR #77): the panel's
    ``project_root`` is normally the user's real project, and there is no path that is
    both a real, writable target the trust boundary would allow *and* guaranteed
    harmless to write to by reflex-clicking a demo button. The full approve-then-
    execute path is proven by temp-dir tests instead (``tests/test_workbench_panel.py``,
    ``TestExecuteAction``), not by this live demo."""
    task = wo.start_task("Demo: safe repo change", summary="a demo task for the panel",
                         source="panel-demo", project_root=project_root)
    wo.add_planning_stage(task.id, message="drafting the change", worker="claude",
                          model="sonnet", project_root=project_root)
    ap = wo.request_approval(task.id, title="Write docs/example.md",
                             prompt="Apply a small doc edit.",
                             requested_action="write_file:docs/example.md",
                             risk_level="medium", project_root=project_root)
    # save one advisory audit result (deterministic; no execution, no provider call)
    audit = wa.audit_approval_request(ap.id, project_root=project_root, save=True)
    return {"ok": True, "task_id": task.id, "approval_id": ap.id, "audit_id": audit.id,
            "executed": False}


# --------------------------------------------------------------------------- #
# HTML (inline CSS/JS only — no external assets, no CDN, no network)
# --------------------------------------------------------------------------- #

def _esc(s: object) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def render_html(state: Dict, token: str = "") -> str:
    tasks_html = ""
    for t in state["tasks"]:
        done = ", ".join(t["completed_stages"]) or "-"
        tasks_html += (
            "<div class='card'>"
            f"<div class='row'><b>{_esc(t['title'])}</b>"
            f"<span class='pill'>{_esc(t['status'])}</span></div>"
            f"<div class='muted'>stage: {_esc(t['current_stage'] or '-')} "
            f"({_esc(t['current_stage_status'] or '-')}) · done: {_esc(done)}</div>"
            f"<div class='muted'>next: {_esc(t['next_action'] or '-')}</div>"
            "</div>")
    if not state["tasks"]:
        tasks_html = (
            "<div class='empty'>"
            "<b>No tasks yet.</b><br>"
            "Create a safe demo approval to test the Workbench loop - "
            "the demo creates <b>local runtime state only</b> and <b>executes nothing</b>."
            "<div class='btns'><button onclick=\"createDemo()\">Create demo task</button></div>"
            "</div>")

    appr_html = ""
    for a in state["pending_approvals"]:
        findings = "".join(f"<li>{_esc(f)}</li>" for f in a["findings"]) or "<li>none</li>"
        blocked = " blocked" if a["blocked"] else ""
        block_label = "BLOCKED by trust boundary" if a["blocked"] else "not blocked"
        scope = a.get("scope")
        scope_html = (f"<div class='muted'>scope: {_esc(json.dumps(scope))}</div>"
                      if scope else "")
        appr_html += (
            f"<div class='card appr{blocked}'>"
            f"<div class='row'><b>{_esc(a['title'] or a['id'])}</b>"
            f"<span class='pill risk-{_esc(a['risk_level'])}'>risk: {_esc(a['risk_level'])}</span></div>"
            f"<div class='prompt'>{_esc(a['rewritten_prompt'])}</div>"
            f"<div class='muted'>action: {_esc(a['requested_action'] or '-')} &middot; {block_label}</div>"
            f"{scope_html}"
            f"<ul class='findings'>{findings}</ul>"
            "<div class='muted'>No action will run from this panel (executed: false).</div>"
            f"<div class='btns'>"
            f"<button onclick=\"decide('{_esc(a['id'])}','approve')\">Approve</button>"
            f"<button onclick=\"decide('{_esc(a['id'])}','reject')\">Reject</button>"
            f"<button onclick=\"decide('{_esc(a['id'])}','hold')\">Hold</button>"
            "</div></div>")
    if not state["pending_approvals"]:
        appr_html = "<div class='muted'>No pending approvals.</div>"

    actions_html = ""
    for act in state.get("actions", []):
        findings = "".join(f"<li>{_esc(f)}</li>" for f in act["findings"]) or "<li>none</li>"
        payload_label = ("verified" if act["payload_verified"]
                          else ("present but NOT verified" if act["payload_exists"]
                                else "no payload artifact"))
        summary = act.get("payload_summary") or {}
        summary_html = (f"<div class='muted'>payload: {_esc(json.dumps(summary))}</div>"
                         if summary else "")
        result_html = (f"<div class='muted'>result: {_esc(act['result_summary'])}</div>"
                        if act["result_summary"] else "")
        btn_html = (
            f"<button onclick=\"execAction('{_esc(act['id'])}')\">"
            "Execute approved file action</button>"
            if act["executable"] else "")
        actions_html += (
            f"<div class='card action'>"
            f"<div class='row'><b>{_esc(act['kind'])}: {_esc(act['target'])}</b>"
            f"<span class='pill risk-{_esc(act['risk_level'])}'>"
            f"status: {_esc(act['status'])}</span></div>"
            f"<div class='muted'>payload: {payload_label} &middot; "
            f"executable: {_esc(act['executable'])}</div>"
            f"{summary_html}{result_html}"
            f"<ul class='findings'>{findings}</ul>"
            f"<div class='btns'>{btn_html}</div></div>")
    if not state.get("actions"):
        actions_html = "<div class='muted'>No actions yet.</div>"

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>AI Council Workbench</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:820px;margin:1.5rem auto;padding:0 1rem;color:#1a1a1a}}
 h1{{margin:.2rem 0}} .muted{{color:#666;font-size:.9rem}}
 .banner{{background:#fff7e6;border:1px solid #ffd591;padding:.5rem .75rem;border-radius:6px;margin:.5rem 0}}
 .card{{border:1px solid #ddd;border-radius:8px;padding:.75rem;margin:.5rem 0}}
 .appr{{border-color:#91caff}} .appr.blocked{{border-color:#ff7875;background:#fff1f0}}
 .action{{border-color:#b7eb8f}}
 .row{{display:flex;justify-content:space-between;align-items:center}}
 .pill{{font-size:.75rem;padding:.1rem .5rem;border-radius:999px;background:#eee}}
 .risk-low{{background:#f6ffed}} .risk-medium{{background:#fff7e6}} .risk-high{{background:#fff1f0}} .risk-blocked{{background:#ffccc7}}
 .prompt{{margin:.4rem 0}} .findings{{margin:.2rem 0;padding-left:1.1rem;color:#555;font-size:.85rem}}
 .btns button{{margin-right:.4rem;padding:.3rem .7rem;cursor:pointer}}
 .empty{{border:1px dashed #bbb;border-radius:8px;padding:.9rem;color:#444}}
 .controls{{margin:.5rem 0}}
</style></head><body>
<h1>AI Council Workbench</h1>
<div class="muted">Local-only Workbench panel &middot; project: {_esc(state['project'])} &middot; 127.0.0.1</div>
<div class="banner">Approving <b>only records a decision — it never executes anything.</b>
 Execution of an approved, bounded file action requires a separate, explicit
 <b>Execute</b> click below and a confirmation prompt.</div>
<div class="muted">Workflow: task &rarr; approval card &rarr; approve/reject/hold &rarr; (if a bounded
 file action with a verified payload exists) explicit Execute.</div>
<div class="muted">This panel offers no `run_command` UI — only bounded file actions with a verified payload can be executed here.</div>
<div class="controls"><button onclick="createDemo()">Create demo task</button>
 <span class="muted">Seeds a safe local approval (runtime-only; executes nothing).</span></div>
<h2>Tasks</h2>{tasks_html}
<h2>Pending approvals</h2>{appr_html}
<h2>Actions</h2>{actions_html}
<script>
 const TOKEN={json.dumps(token)};
 async function decide(id, decision){{
   const r=await fetch(`/api/approvals/${{id}}/${{decision}}`,{{method:'POST',
     headers:{{'X-Workbench-Token':TOKEN}}}});
   if(!r.ok){{alert('decision failed: '+r.status);return;}}
   location.reload();
 }}
 async function createDemo(){{
   const r=await fetch('/api/tasks/demo',{{method:'POST',
     headers:{{'X-Workbench-Token':TOKEN}}}});
   if(!r.ok){{alert('demo failed: '+r.status);return;}}
   location.reload();
 }}
 async function execAction(id){{
   if(!confirm('This will apply an approved bounded file change. Continue?'))return;
   const r=await fetch(`/api/actions/${{id}}/execute`,{{method:'POST',
     headers:{{'X-Workbench-Token':TOKEN}}}});
   const body=await r.json();
   if(!r.ok){{alert('execute failed: '+(body.error||r.status));return;}}
   if(body.blocked){{alert('blocked: '+(body.reason||'blocked by guard'));}}
   location.reload();
 }}
</script>
</body></html>"""


# --------------------------------------------------------------------------- #
# HTTP server (localhost-only; POST requires the startup token)
# --------------------------------------------------------------------------- #

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the server quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: Dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _root(self):
        return getattr(self.server, "project_root", None)

    def _token_ok(self) -> bool:
        want = getattr(self.server, "token", "") or ""
        if not want:
            return True
        got = self.headers.get("X-Workbench-Token", "")
        if not got:
            got = (parse_qs(urlsplit(self.path).query).get("token") or [""])[0]
        return secrets.compare_digest(got, want)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            html = render_html(build_state(self._root()), getattr(self.server, "token", ""))
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/state":
            self._json(200, build_state(self._root()))
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._token_ok():
            self._json(403, {"error": "missing or invalid token"})
            return
        path = urlsplit(self.path).path
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "approvals":
            code, body = handle_decision(parts[2], parts[3], self._root())
            self._json(code, body)
        elif (len(parts) == 4 and parts[0] == "api" and parts[1] == "actions"
              and parts[3] == "execute"):
            code, body = handle_execute(parts[2], self._root())
            self._json(code, body)
        elif path == "/api/tasks/demo":
            self._json(200, create_demo_task(self._root()))
        else:
            self._json(404, {"error": "not found"})


def make_server(project_root: Optional[Path] = None, host: str = "127.0.0.1",
                port: int = 0, token: Optional[str] = None) -> HTTPServer:
    """Create (bind) a localhost-only panel server. Refuses non-local hosts. Does not
    call ``serve_forever`` — the caller controls the loop."""
    if host not in _LOCAL_HOSTS:
        raise ValueError("workbench panel is localhost-only (host must be 127.0.0.1)")
    httpd = HTTPServer((host, port), _Handler)
    httpd.project_root = project_root  # type: ignore[attr-defined]
    httpd.token = token or ""          # type: ignore[attr-defined]
    return httpd


def serve(project_root: Optional[Path] = None, port: int = 8765,
          use_token: bool = True) -> int:
    """Blocking CLI entry point: bind localhost, print the URL (+ token), serve until
    Ctrl-C. Localhost-only; approve/reject/hold never execute; execution of an
    approved, bounded write_file/edit_file action with a verified payload artifact
    requires a separate, explicit Execute click (PR #77)."""
    token = secrets.token_urlsafe(16) if use_token else ""
    httpd = make_server(project_root, host="127.0.0.1", port=port, token=token)
    host, bound = httpd.server_address[0], httpd.server_address[1]
    url = f"http://{host}:{bound}/"
    print(url + (f"?token={token}" if token else ""))
    print(f"[workbench] localhost-only panel; approving never executes. Executing an "
          f"approved bounded file action requires an explicit Execute click.")
    print(f"[workbench] the panel starts empty; use the 'Create demo task' button to seed a "
          f"safe local approval (demo does not create an executable action).")
    if token:
        print(f"[workbench] POST token: {token}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
