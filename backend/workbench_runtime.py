"""AI Council Workbench — local runtime store (v0.5 foundation, stdlib-only).

The **canonical live workflow state** for the future Workbench: tasks, stages,
approval requests/decisions, actions, and audit results, stored as JSON under a
gitignored ``.council/runtime/`` tree. This is *not* the curated memory — committed
``docs/decisions/*.md`` remains the long-term source-of-truth; this store is
**local, ephemeral runtime state** and is never committed.

**This module is data + store only.** No panel, no orchestrator, no Approval
Auditor model call, no action execution, no server, no git/shell, no model/API/
network. Deterministic and stdlib-only.

Store layout (all local/gitignored)::

    .council/runtime/
      tasks/<task_id>.json
      approvals/<approval_id>.json
      audits/<audit_id>.json
      actions/<action_id>.json
      index.json          # task_id -> {status, title, updated_at}

Safety: ids are sanitized, path traversal is impossible (containment-checked), and
reads/writes stay under ``.council/runtime/`` — never under ``docs/``. Writes are
atomic-ish (temp file then replace) and JSON is stable (UTF-8, sorted keys, indent 2).
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass, field, asdict, fields as dc_fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

VERSION = 1

# --------------------------------------------------------------------------- #
# Status vocabularies
# --------------------------------------------------------------------------- #

TASK_STATUS = ("planning", "awaiting_approval", "executing", "completed", "failed", "held")
STAGE_STATUS = ("pending", "running", "completed", "failed", "skipped")
APPROVAL_STATUS = ("pending", "approved", "rejected", "held", "expired")
ACTION_STATUS = ("pending", "running", "completed", "failed", "blocked")
RISK = ("low", "medium", "high", "blocked")
DECISIONS = ("approve", "reject", "hold")
_DECISION_TO_APPROVAL = {"approve": "approved", "reject": "rejected", "hold": "held"}

MAX_FIELD = 2000
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _now(on: Optional[str] = None) -> str:
    return on or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(s: Optional[str], cap: int = MAX_FIELD) -> str:
    if not s:
        return ""
    s = _CONTROL_RE.sub("", str(s))
    s = " ".join(s.split())
    return s[:cap]


def _safe_id(s: object) -> str:
    """Reduce an id to a safe filename stem: only ``[A-Za-z0-9._-]``, no path
    separators or traversal. Never raises."""
    out = _ID_RE.sub("-", str(s or "")).strip("-.")
    return out[:120] or "id"


def _new_id(prefix: str, on: Optional[str] = None) -> str:
    ts = (on or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ts = _ID_RE.sub("", ts)
    return f"{_safe_id(prefix)}-{ts}-{secrets.token_hex(3)}"


def _require(value: str, allowed, name: str) -> str:
    if value not in allowed:
        raise ValueError(f"invalid {name} '{value}' (allowed: {', '.join(allowed)})")
    return value


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #

@dataclass
class Stage:
    id: str
    task_id: str
    name: str
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    worker: str = ""
    model: str = ""
    message: str = ""
    next_action: str = ""


@dataclass
class Task:
    id: str
    title: str
    status: str = "planning"
    created_at: str = ""
    updated_at: str = ""
    source: str = ""
    summary: str = ""
    current_stage_id: Optional[str] = None
    stages: List[Stage] = field(default_factory=list)
    approval_ids: List[str] = field(default_factory=list)
    action_ids: List[str] = field(default_factory=list)
    audit_ids: List[str] = field(default_factory=list)


@dataclass
class ApprovalRequest:
    id: str
    task_id: str
    stage_id: Optional[str] = None
    title: str = ""
    prompt: str = ""
    risk_level: str = "low"
    requested_action: Optional[str] = None
    scope: Optional[Dict] = None
    status: str = "pending"
    created_at: str = ""
    decided_at: Optional[str] = None
    decision_id: Optional[str] = None
    cloud_egress: Optional[Dict] = None
    audit_id: Optional[str] = None


@dataclass
class ApprovalDecision:
    id: str
    approval_id: str
    decision: str
    decided_at: str = ""
    reason: str = ""
    decided_by: str = ""


@dataclass
class Action:
    id: str
    task_id: str
    approval_id: Optional[str] = None
    kind: str = ""
    status: str = "pending"
    command_or_path: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None
    result_summary: str = ""


@dataclass
class AuditResult:
    id: str
    approval_id: str
    risk_level: str = "low"
    findings: List[str] = field(default_factory=list)
    rewritten_prompt: str = ""
    blocked: bool = False
    created_at: str = ""
    auditor: str = ""
    model: str = ""


def _from_dict(cls, d: Dict):
    """Build a dataclass from a dict, ignoring unknown keys (forward/backward
    compatible). Stages are reconstructed for Task."""
    if not isinstance(d, dict):
        raise ValueError("expected a JSON object")
    known = {f.name for f in dc_fields(cls)}
    kwargs = {k: v for k, v in d.items() if k in known}
    if cls is Task:
        kwargs["stages"] = [_from_dict(Stage, s) for s in (d.get("stages") or [])
                            if isinstance(s, dict)]
    return cls(**kwargs)


# --------------------------------------------------------------------------- #
# Store paths + containment
# --------------------------------------------------------------------------- #

_SUBDIRS = ("tasks", "approvals", "audits", "actions")


def runtime_root(project_root: Optional[Path] = None) -> Path:
    root = Path(project_root) if project_root is not None else Path.cwd()
    return root / ".council" / "runtime"


def ensure_runtime(project_root: Optional[Path] = None) -> Path:
    rr = runtime_root(project_root)
    for sub in _SUBDIRS:
        (rr / sub).mkdir(parents=True, exist_ok=True)
    idx = rr / "index.json"
    if not idx.is_file():
        _dump(idx, {"version": VERSION, "tasks": {}})
    return rr


def _entry_path(rr: Path, subdir: str, ident: str) -> Path:
    """Resolve ``<runtime>/<subdir>/<safe-id>.json`` and hard-guard containment —
    the result must live directly inside the intended subdir (never under docs/,
    never escaping the runtime root)."""
    sub = (rr / subdir).resolve()
    p = (sub / (_safe_id(ident) + ".json"))
    rp = p.resolve()
    if rp.parent != sub:
        raise ValueError("unsafe runtime path (containment violation)")
    return rp


def _dump(path: Path, obj: Dict) -> None:
    """Atomic-ish, stable JSON write (temp file then replace; UTF-8, sorted keys)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def _load_json(path: Path) -> Optional[Dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


# --------------------------------------------------------------------------- #
# index
# --------------------------------------------------------------------------- #

def _index_path(project_root: Optional[Path] = None) -> Path:
    return runtime_root(project_root) / "index.json"


def _read_index(project_root: Optional[Path] = None) -> Dict:
    data = _load_json(_index_path(project_root))
    if not data or not isinstance(data.get("tasks"), dict):
        return {"version": VERSION, "tasks": {}}
    return data


def _update_index(task: "Task", project_root: Optional[Path] = None) -> None:
    idx = _read_index(project_root)
    idx["tasks"][task.id] = {"status": task.status, "title": task.title,
                             "updated_at": task.updated_at}
    _dump(_index_path(project_root), idx)


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #

def new_task(title: str, summary: Optional[str] = None, source: Optional[str] = None,
             on: Optional[str] = None) -> Task:
    """Construct a fresh Task (pure; no I/O). Status starts at ``planning``."""
    now = _now(on)
    return Task(
        id=_new_id("task", on), title=_clean(title), status="planning",
        created_at=now, updated_at=now, source=_clean(source),
        summary=_clean(summary, 4000),
    )


def save_task(task: Task, project_root: Optional[Path] = None,
              on: Optional[str] = None) -> Path:
    _require(task.status, TASK_STATUS, "task status")
    for st in task.stages:
        _require(st.status, STAGE_STATUS, "stage status")
    ensure_runtime(project_root)
    task.updated_at = _now(on)
    rr = runtime_root(project_root)
    path = _entry_path(rr, "tasks", task.id)
    _dump(path, asdict(task))
    _update_index(task, project_root)
    return path


def load_task(task_id: str, project_root: Optional[Path] = None) -> Optional[Task]:
    rr = runtime_root(project_root)
    try:
        path = _entry_path(rr, "tasks", task_id)
    except ValueError:
        return None
    data = _load_json(path)
    return _from_dict(Task, data) if data else None


def list_tasks(status: Optional[str] = None,
               project_root: Optional[Path] = None) -> List[Task]:
    rr = runtime_root(project_root)
    tdir = rr / "tasks"
    if not tdir.is_dir():
        return []
    out: List[Task] = []
    for p in sorted(tdir.glob("*.json")):
        data = _load_json(p)
        if not data:
            continue
        t = _from_dict(Task, data)
        if status is None or t.status == status:
            out.append(t)
    return out


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #

def new_stage(task_id: str, name: str, worker: str = "", model: str = "",
              message: str = "", next_action: str = "", on: Optional[str] = None) -> Stage:
    return Stage(id=_new_id("stage", on), task_id=task_id, name=_clean(name),
                 status="pending", worker=_clean(worker), model=_clean(model),
                 message=_clean(message), next_action=_clean(next_action))


def append_stage(task_id: str, stage: Stage, project_root: Optional[Path] = None,
                 on: Optional[str] = None) -> Optional[Task]:
    """Append a stage to a task and make it the current stage. Returns the updated
    Task, or None if the task is missing."""
    _require(stage.status, STAGE_STATUS, "stage status")
    task = load_task(task_id, project_root)
    if task is None:
        return None
    stage.task_id = task.id
    task.stages.append(stage)
    task.current_stage_id = stage.id
    save_task(task, project_root, on=on)
    return task


# --------------------------------------------------------------------------- #
# Approvals
# --------------------------------------------------------------------------- #

def create_approval(task_id: str, stage_id: Optional[str] = None, title: str = "",
                    prompt: str = "", risk_level: str = "low",
                    requested_action: Optional[str] = None,
                    scope: Optional[Dict] = None, cloud_egress: Optional[Dict] = None,
                    audit_id: Optional[str] = None,
                    project_root: Optional[Path] = None,
                    on: Optional[str] = None) -> Optional[ApprovalRequest]:
    """Create a pending ApprovalRequest and move its task to ``awaiting_approval``.
    Returns None if the task is missing."""
    _require(risk_level, RISK, "risk level")
    task = load_task(task_id, project_root)
    if task is None:
        return None
    ap = ApprovalRequest(
        id=_new_id("appr", on), task_id=task.id, stage_id=stage_id,
        title=_clean(title), prompt=_clean(prompt, 4000), risk_level=risk_level,
        requested_action=(_clean(requested_action) if requested_action else None),
        scope=scope, status="pending", created_at=_now(on),
        cloud_egress=cloud_egress, audit_id=audit_id,
    )
    _save_entry("approvals", ap, project_root)
    if ap.id not in task.approval_ids:
        task.approval_ids.append(ap.id)
    task.status = "awaiting_approval"
    save_task(task, project_root, on=on)
    return ap


def load_approval(approval_id: str,
                  project_root: Optional[Path] = None) -> Optional[ApprovalRequest]:
    return _load_entry("approvals", ApprovalRequest, approval_id, project_root)


def record_approval_decision(approval_id: str, decision: str,
                             reason: Optional[str] = None,
                             decided_by: str = "user",
                             project_root: Optional[Path] = None,
                             on: Optional[str] = None) -> Optional[ApprovalDecision]:
    """Record approve/reject/hold on an approval; updates the approval status.
    Returns None if the approval is missing."""
    _require(decision, DECISIONS, "decision")
    ap = load_approval(approval_id, project_root)
    if ap is None:
        return None
    now = _now(on)
    dec = ApprovalDecision(id=_new_id("dec", on), approval_id=ap.id, decision=decision,
                           decided_at=now, reason=_clean(reason), decided_by=_clean(decided_by))
    ap.status = _DECISION_TO_APPROVAL[decision]
    ap.decision_id = dec.id
    ap.decided_at = now
    _save_entry("approvals", ap, project_root)
    _save_entry("approvals", dec, project_root, ident=dec.id)  # decisions live beside approvals
    return dec


# --------------------------------------------------------------------------- #
# Audits + actions
# --------------------------------------------------------------------------- #

def new_audit(approval_id: str, risk_level: str = "low", findings: Optional[List[str]] = None,
              rewritten_prompt: str = "", blocked: bool = False, auditor: str = "",
              model: str = "", on: Optional[str] = None) -> AuditResult:
    _require(risk_level, RISK, "risk level")
    return AuditResult(id=_new_id("audit", on), approval_id=approval_id,
                       risk_level=risk_level, findings=[_clean(f) for f in (findings or [])],
                       rewritten_prompt=_clean(rewritten_prompt, 4000), blocked=bool(blocked),
                       created_at=_now(on), auditor=_clean(auditor), model=_clean(model))


def save_audit_result(audit: AuditResult, project_root: Optional[Path] = None) -> Path:
    _require(audit.risk_level, RISK, "risk level")
    return _save_entry("audits", audit, project_root)


def load_audit(audit_id: str, project_root: Optional[Path] = None) -> Optional[AuditResult]:
    return _load_entry("audits", AuditResult, audit_id, project_root)


def new_action(task_id: str, kind: str, command_or_path: str = "",
               approval_id: Optional[str] = None, on: Optional[str] = None) -> Action:
    return Action(id=_new_id("act", on), task_id=task_id, approval_id=approval_id,
                  kind=_clean(kind), status="pending",
                  command_or_path=_clean(command_or_path), created_at=_now(on))


def save_action(action: Action, project_root: Optional[Path] = None) -> Path:
    _require(action.status, ACTION_STATUS, "action status")
    return _save_entry("actions", action, project_root)


def load_action(action_id: str, project_root: Optional[Path] = None) -> Optional[Action]:
    return _load_entry("actions", Action, action_id, project_root)


# --------------------------------------------------------------------------- #
# Generic entry save/load (approvals/audits/actions)
# --------------------------------------------------------------------------- #

def _save_entry(subdir: str, obj, project_root: Optional[Path] = None,
                ident: Optional[str] = None) -> Path:
    ensure_runtime(project_root)
    rr = runtime_root(project_root)
    path = _entry_path(rr, subdir, ident or obj.id)
    _dump(path, asdict(obj))
    return path


def _load_entry(subdir: str, cls, ident: str, project_root: Optional[Path] = None):
    rr = runtime_root(project_root)
    try:
        path = _entry_path(rr, subdir, ident)
    except ValueError:
        return None
    data = _load_json(path)
    return _from_dict(cls, data) if data else None


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #

def runtime_status_summary(project_root: Optional[Path] = None) -> Dict:
    """A small, read-only summary of runtime state (task counts by status)."""
    rr = runtime_root(project_root)
    counts = {s: 0 for s in TASK_STATUS}
    total = 0
    for t in list_tasks(project_root=project_root):
        total += 1
        counts[t.status] = counts.get(t.status, 0) + 1
    return {
        "version": VERSION,
        "runtime_root": f"{rr.parent.name}/{rr.name}",  # never an absolute path
        "tasks_total": total,
        "by_status": counts,
    }
