"""AI Council Workbench — local panel (v0.5, stdlib-only).

The first user-visible Workbench slice: a **localhost-only** HTML panel that renders
task progress and pending approval cards from `.council/runtime/`, lets a human
**approve / reject / hold** an approval, and — for an already-approved action the
executor can actually run — lets them explicitly **execute** it via the guarded
executor: a bounded `write_file`/`edit_file` action with a verified local payload
artifact (PR #77), or an exact allowlisted `run_command` action the PR #79 resolver
resolves (PR #81). Built on `http.server` + `json` + stdlib — no framework, no npm, no
external assets/CDN, no network egress.

**Approval and execution stay separate.** Approving here only records an
`ApprovalDecision`; it never executes anything. Execution is a **distinct, explicit**
POST (`/api/actions/<action_id>/execute`) that the browser can only trigger by action
id — it never sends file content, patch text, a command string, argv, cwd, env, or a
timeout. The executor (`backend/workbench_executor.py`) is the sole source of truth: for
file kinds it loads/verifies the local payload artifact (`backend/workbench_payloads.py`);
for `run_command` it resolves the label via `backend/workbench_commands.py` — either way
it re-runs the deterministic trust boundary and only then performs real, bounded
execution. Any mismatch/missing artifact/unresolvable label/blocked kind fails closed,
with no subprocess started and no file touched. Command output shown by the panel is
already bounded and redaction-checked by the executor (PR #80) — the panel never widens
what's exposed. The panel binds to `127.0.0.1` only (no `0.0.0.0`/LAN/mobile), and POSTs
require a startup token.

Pure functions (`build_state`, `handle_decision`, `handle_execute`, `render_html`) hold
the logic and are tested directly; the HTTP handler is a thin router over them.
"""

from __future__ import annotations

import json
import secrets
import sys
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


def _display_argv(argv: List[str]) -> List[str]:
    """Display-only sanitization: swap the local interpreter's absolute path for a
    generic placeholder (matches `_project_name`'s no-absolute-local-path convention).
    Never used for actual execution — the executor always resolves the real argv
    itself, independent of anything the panel renders."""
    return ["<python>" if tok == sys.executable else tok for tok in argv]


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
    payload verification (file kinds) or a resolved command preview (``run_command``),
    a fresh (dry-run) risk/trust preview for still-pending actions, and whether/why the
    panel may offer to execute it. Never includes raw ``content``/``old_text``/
    ``new_text`` (only the payload artifact's redacted summary) and never includes an
    absolute local path (a command's argv is display-sanitized via `_display_argv`,
    matching `_project_name`'s no-path-leakage convention)."""
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
    preview = None
    if action.status == "pending":
        # Dry-run only — re-runs the deterministic trust boundary (and, for
        # run_command, the command resolver), mutates nothing.
        preview = we.preview_action(action, approval, task, project_root)
        risk_level, findings, would_execute = (
            preview.risk_level, preview.findings, preview.would_execute)

    command_preview: Optional[Dict] = None
    if action.kind == "run_command" and preview is not None and preview.command_label:
        command_preview = {
            "label": preview.command_label,
            "argv": _display_argv(preview.command_argv),
            "timeout_seconds": preview.command_timeout_seconds,
            "output_limit_bytes": preview.command_output_limit_bytes,
            "shell": preview.command_shell,
        }

    if action.kind in ("write_file", "edit_file"):
        executable = (action.status == "pending" and artifact is not None
                      and payload_verified and would_execute)
        if action.status != "pending":
            executable_reason = f"action not pending (status '{action.status}')"
        elif artifact is None:
            executable_reason = "no payload artifact found for this action"
        elif not payload_verified:
            executable_reason = "payload artifact failed verification"
        elif not would_execute:
            executable_reason = "blocked by the guard/invariant"
        else:
            executable_reason = "approved, payload verified, ready to execute"
    elif action.kind == "run_command":
        # No payload artifact involved — the resolver + trust boundary gate it.
        executable = action.status == "pending" and would_execute
        if action.status != "pending":
            executable_reason = f"action not pending (status '{action.status}')"
        elif not would_execute:
            executable_reason = ("command label does not resolve to an allowlisted "
                                 "command, or is blocked by the trust boundary")
        else:
            executable_reason = "exact allowlisted command, approved, ready to execute"
    else:
        executable = False
        executable_reason = f"kind '{action.kind}' cannot be executed from the panel"

    return {
        "id": action.id, "task_id": action.task_id, "approval_id": action.approval_id,
        "kind": action.kind, "target": action.command_or_path, "status": action.status,
        "result_summary": action.result_summary,
        "payload_exists": artifact is not None,
        "payload_verified": payload_verified,
        "payload_summary": payload_summary,
        "command_preview": command_preview,
        "risk_level": risk_level, "findings": findings,
        "executable": executable,
        "executable_reason": executable_reason,
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
    """Execute an already-approved action via the guarded executor: a bounded
    ``write_file``/``edit_file`` action with a verified local payload artifact, or an
    exact allowlisted ``run_command`` action the resolver resolves. The caller supplies
    **only** the action id — this function never reads a request body, so the browser
    cannot send file content, patch text, a command string, argv, cwd, env, or a
    timeout; every one of those comes from the executor's own local, server-side
    resolution (``backend/workbench_payloads.py`` / ``backend/workbench_commands.py``),
    never from the caller. Fails closed (``blocked``/error, no mutation, no subprocess
    started) on a missing action, an unsupported kind, an unapproved/rejected/held
    approval, a non-pending action, a missing/tampered/mismatched payload artifact, or
    a non-allowlisted/unresolvable command label — all handled by the executor's
    existing invariant, not re-implemented here. Returns (http_status, body); body
    carries no raw file content and only the executor's own bounded/redaction-checked
    command output summary (never huge/raw)."""
    action = wr.load_action(action_id, project_root)
    if action is None:
        return 404, {"error": "action not found", "action_id": action_id}
    try:
        result = we.execute_action(action_id, project_root=project_root, dry_run=False)
    except we.ExecutorError as e:
        return 400, {"error": str(e), "action_id": action_id, "executed": False}
    body = {
        "executed": result.executed, "dry_run": result.dry_run, "allowed": result.allowed,
        "blocked": result.blocked, "action_id": result.action_id, "kind": result.kind,
        "risk_level": result.risk_level, "findings": result.findings,
        "preview": result.preview, "reason": result.reason,
    }
    if result.kind == "run_command":
        body.update({
            "command_label": result.command_label,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "output_truncated": result.output_truncated,
            "stdout_summary": result.stdout_summary,
            "stderr_summary": result.stderr_summary,
        })
    return 200, body


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
        result_html = (f"<div class='muted'>result: {_esc(act['result_summary'])}</div>"
                        if act["result_summary"] else "")
        detail_html = ""
        if act["kind"] in ("write_file", "edit_file"):
            payload_label = ("verified" if act["payload_verified"]
                              else ("present but NOT verified" if act["payload_exists"]
                                    else "no payload artifact"))
            summary = act.get("payload_summary") or {}
            summary_html = (f"<div class='muted'>payload: {_esc(json.dumps(summary))}</div>"
                             if summary else "")
            detail_html = f"<div class='muted'>payload: {payload_label}</div>{summary_html}"
            btn_label = "Execute approved file action"
        elif act["kind"] == "run_command":
            cp = act.get("command_preview")
            if cp:
                detail_html = (
                    f"<div class='muted'>command: {_esc(cp['label'])} "
                    "(exact allowlisted command only)</div>"
                    f"<div class='muted'>argv: {_esc(json.dumps(cp['argv']))}</div>"
                    f"<div class='muted'>timeout: {_esc(cp['timeout_seconds'])}s &middot; "
                    f"output cap: {_esc(cp['output_limit_bytes'])}B &middot; "
                    f"shell={_esc(cp['shell'])} &middot; runs in the project root</div>")
            elif act["status"] == "pending":
                detail_html = "<div class='muted'>command does not resolve to an allowlisted argv</div>"
            else:
                # A command_preview is only ever built for a pending action (dry-run
                # preview) — a completed/blocked/failed action has no preview to show,
                # and reusing the "does not resolve" text here would misreport a command
                # that actually ran (see `result_html` below for the real outcome).
                detail_html = f"<div class='muted'>command: {_esc(act['target'])}</div>"
            btn_label = "Execute approved command"
        else:
            btn_label = "Execute"
        btn_html = (
            f"<button onclick=\"execAction('{_esc(act['id'])}','{_esc(act['kind'])}')\">"
            f"{btn_label}</button>"
            if act["executable"] else "")
        actions_html += (
            f"<div class='card action'>"
            f"<div class='row'><b>{_esc(act['kind'])}: {_esc(act['target'])}</b>"
            f"<span class='pill risk-{_esc(act['risk_level'])}'>"
            f"status: {_esc(act['status'])}</span></div>"
            f"{detail_html}"
            f"<div class='muted'>executable: {_esc(act['executable'])} "
            f"({_esc(act['executable_reason'])})</div>"
            f"{result_html}"
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
 Execution of an approved, bounded file action or an exact allowlisted command requires
 a separate, explicit <b>Execute</b> click below and a confirmation prompt.</div>
<div class="muted">Workflow: task &rarr; approval card &rarr; approve/reject/hold &rarr; (if a bounded
 file action with a verified payload, or an exact allowlisted command, exists) explicit
 Execute.</div>
<div class="muted">Commands: only an exact allowlisted label resolves to a fixed argv (no shell, no
 dynamic args); execution always runs in the project root and its output is bounded/redacted.</div>
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
 async function execAction(id, kind){{
   const msg = kind==='run_command'
     ? 'This will run an exact allowlisted command in the project root. Continue?'
     : 'This will apply an approved bounded file change. Continue?';
   if(!confirm(msg))return;
   const r=await fetch(`/api/actions/${{id}}/execute`,{{method:'POST',
     headers:{{'X-Workbench-Token':TOKEN}}}});
   const body=await r.json();
   if(!r.ok){{alert('execute failed: '+(body.error||r.status));return;}}
   if(body.blocked){{alert('blocked: '+(body.reason||'blocked by guard'));}}
   else if(kind==='run_command'){{
     const out=(body.stdout_summary||'').slice(0,500);
     const err=(body.stderr_summary||'').slice(0,500);
     alert('command '+(body.executed?'ran':'did not run')+' - exit='+body.exit_code+
       ' timed_out='+body.timed_out+' truncated='+body.output_truncated+
       (out?('\\nstdout: '+out):'')+(err?('\\nstderr: '+err):''));
   }}
   location.reload();
 }}
</script>
</body></html>"""


# --------------------------------------------------------------------------- #
# HTTP server (localhost-only; POST + /api/state require the startup token)
# --------------------------------------------------------------------------- #

def host_header_is_local(host_header: Optional[str]) -> bool:
    """True only if the HTTP ``Host`` header names a loopback host (``127.0.0.1``,
    ``localhost``, or ``::1``), ignoring any ``:port`` suffix.

    This is the **DNS-rebinding defense**: the socket already binds ``127.0.0.1``, but
    that alone does not stop a malicious page whose domain re-resolves to ``127.0.0.1``
    — the browser still sends that page's *original* ``Host`` (the attacker's domain),
    so refusing any ``Host`` that isn't a literal loopback name blocks the rebind while
    letting the real localhost panel URL through. A missing, malformed, or non-loopback
    ``Host`` is rejected (fail closed). Parsing via ``urlsplit`` handles the ``:port``
    suffix and bracketed IPv6 (``[::1]:port``) forms and never raises for our inputs."""
    if not host_header:
        return False
    try:
        hostname = urlsplit("//" + host_header).hostname
    except ValueError:
        return False
    return hostname in _LOCAL_HOSTS


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

    def _host_ok(self) -> bool:
        """Reject any request whose ``Host`` header isn't a literal loopback host, or
        that carries more than one ``Host`` header (ambiguous — a request-smuggling/
        rebinding smell). See ``host_header_is_local``."""
        hosts = self.headers.get_all("Host") or []
        if len(hosts) > 1:
            return False
        return host_header_is_local(self.headers.get("Host", ""))

    def do_GET(self):
        if not self._host_ok():
            self._json(403, {"error": "invalid host header"})
            return
        path = urlsplit(self.path).path
        if path == "/":
            html = render_html(build_state(self._root()), getattr(self.server, "token", ""))
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/state":
            # State can reveal the panel's runtime tasks/approvals/actions — gate it on
            # the same startup token as the POST endpoints (accepted via header or the
            # ?token= query the panel URL already uses). The token is never echoed back.
            if not self._token_ok():
                self._json(403, {"error": "missing or invalid token"})
                return
            self._json(200, build_state(self._root()))
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok():
            self._json(403, {"error": "invalid host header"})
            return
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


_LOOPBACK_ADDRS = ("127.0.0.1", "::1")


def effective_bind_host(httpd: HTTPServer) -> str:
    """The address a bound server is actually listening on (``httpd.server_address[0]``)
    — the single place tests/callers should read this from, rather than reaching into
    ``server_address`` directly everywhere."""
    return httpd.server_address[0]


def make_server(project_root: Optional[Path] = None, host: str = "127.0.0.1",
                port: int = 0, token: Optional[str] = None) -> HTTPServer:
    """Create (bind) a localhost-only panel server. Refuses non-local hosts. Does not
    call ``serve_forever`` — the caller controls the loop.

    Belt-and-suspenders: even though only ``_LOCAL_HOSTS`` values are accepted as input,
    the **actual bound address is re-checked after ``bind()``** — if ``host="localhost"``
    ever resolved to something other than a loopback address (e.g. a misconfigured
    ``hosts`` file), the socket is closed immediately and this raises rather than
    silently serving on an unexpected interface."""
    if host not in _LOCAL_HOSTS:
        raise ValueError("workbench panel is localhost-only (host must be 127.0.0.1)")
    httpd = HTTPServer((host, port), _Handler)
    bound = effective_bind_host(httpd)
    if bound not in _LOOPBACK_ADDRS:
        httpd.server_close()
        raise ValueError(
            f"workbench panel refuses to serve on non-loopback bind address {bound!r} "
            f"(requested host {host!r})")
    httpd.project_root = project_root  # type: ignore[attr-defined]
    httpd.token = token or ""          # type: ignore[attr-defined]
    return httpd


def _startup_lines(httpd: HTTPServer, token: str) -> List[str]:
    """The lines `serve()` prints at startup — a pure, testable helper so the printed
    URL's host can be asserted without blocking on `serve_forever()`. The URL is built
    from the server's *actual* bound address (`effective_bind_host`), never a hardcoded
    string, so it can never drift from what was really bound."""
    host, bound = effective_bind_host(httpd), httpd.server_address[1]
    url = f"http://{host}:{bound}/"
    lines = [url + (f"?token={token}" if token else "")]
    lines.append("[workbench] localhost-only panel; approving never executes. Executing an "
                 "approved bounded file action or an exact allowlisted command requires an "
                 "explicit Execute click.")
    lines.append("[workbench] the panel starts empty; use the 'Create demo task' button to seed a "
                 "safe local approval (demo does not create an executable action).")
    if token:
        lines.append(f"[workbench] POST token: {token}")
    return lines


def serve(project_root: Optional[Path] = None, port: int = 8765,
          use_token: bool = True) -> int:
    """Blocking CLI entry point: bind localhost, print the URL (+ token), serve until
    Ctrl-C. Localhost-only; approve/reject/hold never execute; execution of an
    approved, bounded write_file/edit_file action with a verified payload artifact, or
    an exact allowlisted run_command action, requires a separate, explicit Execute
    click (PR #77/#81). ``KeyboardInterrupt`` (Ctrl-C) always reaches ``server_close()``
    via the ``finally`` block, so the listening socket is released even on interrupt."""
    token = secrets.token_urlsafe(16) if use_token else ""
    httpd = make_server(project_root, host="127.0.0.1", port=port, token=token)
    for line in _startup_lines(httpd, token):
        print(line)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
