"""AI Council Workbench — local panel (v0.5, stdlib-only).

The first user-visible Workbench slice: a **localhost-only** HTML panel that renders
task progress and pending approval cards from `.council/runtime/`, and lets a human
**approve / reject / hold** an approval. Built on `http.server` + `json` + stdlib —
no framework, no npm, no external assets/CDN, no network egress.

**Non-executing.** Approving here records an `ApprovalDecision` and advances the task
lifecycle via the orchestrator; it **never** runs a command, edits a file, touches
git, promotes a decision, or calls a provider/model. Execution stays behind the
deterministic trust boundary in a later executor PR. The panel binds to `127.0.0.1`
only (no `0.0.0.0`/LAN/mobile), and POSTs require a startup token.

Pure functions (`build_state`, `handle_decision`, `render_html`) hold the logic and
are tested directly; the HTTP handler is a thin router over them.
"""

from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit, parse_qs

from . import workbench_runtime as wr
from . import workbench_orchestrator as wo
from . import workbench_auditor as wa

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


def build_state(project_root: Optional[Path] = None) -> Dict:
    """Read-only snapshot for the panel. Advisory-audits each pending approval
    (``save=False`` — no writes). Never mutates runtime state."""
    tasks = [_task_view(t, project_root) for t in wr.list_tasks(project_root=project_root)]
    approvals = []
    for ap in wo.list_pending_approvals(project_root):
        audit = wa.audit_approval_request(ap.id, project_root=project_root, save=False)
        approvals.append({
            "id": ap.id, "task_id": ap.task_id, "title": ap.title,
            "risk_level": audit.risk_level, "blocked": audit.blocked,
            "rewritten_prompt": audit.rewritten_prompt, "findings": audit.findings,
            "requested_action": ap.requested_action or "", "scope": ap.scope,
        })
    return {
        "product": "AI Council Workbench",
        "project": _project_name(project_root),
        "localhost_only": True,
        "executes_actions": False,       # panel records decisions only
        "tasks": tasks,
        "pending_approvals": approvals,
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


def create_demo_task(project_root: Optional[Path] = None) -> Dict:
    """Create a local demo task + pending approval for dogfooding the panel. Local
    only, no external effects, no execution."""
    task = wo.start_task("Demo: safe repo change", summary="a demo task for the panel",
                         source="panel-demo", project_root=project_root)
    wo.add_planning_stage(task.id, message="drafting the change", worker="claude",
                          model="sonnet", project_root=project_root)
    ap = wo.request_approval(task.id, title="Write docs/example.md",
                             prompt="Apply a small doc edit.",
                             requested_action="write_file:docs/example.md",
                             risk_level="medium", project_root=project_root)
    return {"ok": True, "task_id": task.id, "approval_id": ap.id}


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
        tasks_html = "<div class='muted'>No tasks. Use the runtime/orchestrator to create one.</div>"

    appr_html = ""
    for a in state["pending_approvals"]:
        findings = "".join(f"<li>{_esc(f)}</li>" for f in a["findings"]) or "<li>none</li>"
        blocked = " blocked" if a["blocked"] else ""
        appr_html += (
            f"<div class='card appr{blocked}'>"
            f"<div class='row'><b>{_esc(a['title'] or a['id'])}</b>"
            f"<span class='pill risk-{_esc(a['risk_level'])}'>{_esc(a['risk_level'])}</span></div>"
            f"<div class='prompt'>{_esc(a['rewritten_prompt'])}</div>"
            f"<div class='muted'>action: {_esc(a['requested_action'] or '-')}</div>"
            f"<ul class='findings'>{findings}</ul>"
            f"<div class='btns'>"
            f"<button onclick=\"decide('{_esc(a['id'])}','approve')\">Approve</button>"
            f"<button onclick=\"decide('{_esc(a['id'])}','reject')\">Reject</button>"
            f"<button onclick=\"decide('{_esc(a['id'])}','hold')\">Hold</button>"
            "</div></div>")
    if not state["pending_approvals"]:
        appr_html = "<div class='muted'>No pending approvals.</div>"

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>AI Council Workbench</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:820px;margin:1.5rem auto;padding:0 1rem;color:#1a1a1a}}
 h1{{margin:.2rem 0}} .muted{{color:#666;font-size:.9rem}}
 .banner{{background:#fff7e6;border:1px solid #ffd591;padding:.5rem .75rem;border-radius:6px;margin:.5rem 0}}
 .card{{border:1px solid #ddd;border-radius:8px;padding:.75rem;margin:.5rem 0}}
 .appr{{border-color:#91caff}} .appr.blocked{{border-color:#ff7875;background:#fff1f0}}
 .row{{display:flex;justify-content:space-between;align-items:center}}
 .pill{{font-size:.75rem;padding:.1rem .5rem;border-radius:999px;background:#eee}}
 .risk-low{{background:#f6ffed}} .risk-medium{{background:#fff7e6}} .risk-high{{background:#fff1f0}} .risk-blocked{{background:#ffccc7}}
 .prompt{{margin:.4rem 0}} .findings{{margin:.2rem 0;padding-left:1.1rem;color:#555;font-size:.85rem}}
 .btns button{{margin-right:.4rem;padding:.3rem .7rem;cursor:pointer}}
</style></head><body>
<h1>AI Council Workbench</h1>
<div class="muted">project: {_esc(state['project'])} · localhost only</div>
<div class="banner">Decisions are recorded only - <b>no action execution</b> happens here yet.</div>
<h2>Tasks</h2>{tasks_html}
<h2>Pending approvals</h2>{appr_html}
<script>
 const TOKEN={json.dumps(token)};
 async function decide(id, decision){{
   const r=await fetch(`/api/approvals/${{id}}/${{decision}}`,{{method:'POST',
     headers:{{'X-Workbench-Token':TOKEN}}}});
   if(!r.ok){{alert('decision failed: '+r.status);return;}}
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
    Ctrl-C. Non-executing; localhost-only."""
    token = secrets.token_urlsafe(16) if use_token else ""
    httpd = make_server(project_root, host="127.0.0.1", port=port, token=token)
    host, bound = httpd.server_address[0], httpd.server_address[1]
    url = f"http://{host}:{bound}/"
    print(url + (f"?token={token}" if token else ""))
    print(f"[workbench] localhost-only panel; decisions only, NO action execution.")
    if token:
        print(f"[workbench] POST token: {token}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
