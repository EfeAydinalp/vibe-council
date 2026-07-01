"""AI Council Workbench — deterministic task orchestrator (v0.5, stdlib-only).

A thin, deterministic **lifecycle** over the runtime store (:mod:`backend.
workbench_runtime`): create a task, plan, request approval, decide, (optionally)
move to executing, and complete / fail / hold. It also exposes a small,
panel-friendly **progress** view and a **pending-approvals** query.

**Lifecycle only — no side effects beyond runtime state.** This module does **not**
execute actions, run shell/git, call models/providers/network, promote decisions,
touch anything outside ``.council/runtime/``, or add any panel/server/auditor. On an
approved+executing task it creates an ``Action`` in ``pending`` status (a record for
a later executor PR) but never runs it. The deterministic path/command trust boundary
and the Approval Auditor are separate, later layers.

State machine::

    planning → awaiting_approval → executing → completed
                     │
      (reject) ──────┼──────────────────────────► failed
      (hold)   ──────┘  → held
    any state → failed (fail_task) / held (hold_task)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from . import workbench_runtime as wr


class OrchestratorError(Exception):
    """A clean lifecycle error (unknown id, invalid transition, missing approval)."""


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _load_task_or_raise(task_id: str, project_root: Optional[Path]) -> wr.Task:
    task = wr.load_task(task_id, project_root)
    if task is None:
        raise OrchestratorError("task not found")
    return task


def _current_stage(task: wr.Task) -> Optional[wr.Stage]:
    if task.current_stage_id:
        for s in task.stages:
            if s.id == task.current_stage_id:
                return s
    return task.stages[-1] if task.stages else None


def _finish_current_stage(task: wr.Task, status: str, on: Optional[str]) -> None:
    cur = _current_stage(task)
    if cur is not None and cur.status in ("pending", "running"):
        cur.status = status
        cur.completed_at = wr._now(on)


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #

def start_task(title: str, summary: Optional[str] = None, source: Optional[str] = None,
               project_root: Optional[Path] = None, on: Optional[str] = None) -> wr.Task:
    """Create a ``planning`` task with an active initial ``planning`` stage."""
    task = wr.new_task(title, summary=summary, source=source, on=on)
    wr.save_task(task, project_root, on=on)
    stage = wr.new_stage(task.id, "planning", on=on)
    stage.status = "running"
    stage.started_at = wr._now(on)
    wr.append_stage(task.id, stage, project_root, on=on)
    return _load_task_or_raise(task.id, project_root)


def add_planning_stage(task_id: str, message: Optional[str] = None,
                       worker: Optional[str] = None, model: Optional[str] = None,
                       project_root: Optional[Path] = None,
                       on: Optional[str] = None) -> wr.Task:
    """Record planning detail. Updates the active planning stage in place, or
    appends a new running planning stage. Only allowed while ``planning``."""
    task = _load_task_or_raise(task_id, project_root)
    if task.status != "planning":
        raise OrchestratorError("can only add a planning stage while task is planning")
    cur = _current_stage(task)
    if cur is not None and cur.name == "planning" and cur.status == "running":
        if message is not None:
            cur.message = wr._clean(message)
        if worker is not None:
            cur.worker = wr._clean(worker)
        if model is not None:
            cur.model = wr._clean(model)
        wr.save_task(task, project_root, on=on)
        return _load_task_or_raise(task_id, project_root)
    stage = wr.new_stage(task_id, "planning", worker=worker or "", model=model or "",
                         message=message or "", on=on)
    stage.status = "running"
    stage.started_at = wr._now(on)
    wr.append_stage(task_id, stage, project_root, on=on)
    return _load_task_or_raise(task_id, project_root)


def request_approval(task_id: str, title: str, prompt: str,
                     requested_action: Optional[str] = None, scope: Optional[Dict] = None,
                     risk_level: str = "medium", cloud_egress: Optional[Dict] = None,
                     project_root: Optional[Path] = None,
                     on: Optional[str] = None) -> wr.ApprovalRequest:
    """Complete planning, create a pending ``ApprovalRequest``, and move the task to
    ``awaiting_approval`` with an active ``awaiting_approval`` stage. No execution."""
    task = _load_task_or_raise(task_id, project_root)
    if task.status != "planning":
        raise OrchestratorError(f"cannot request approval from status '{task.status}'")
    _finish_current_stage(task, "completed", on)
    wr.save_task(task, project_root, on=on)

    ap = wr.create_approval(task_id, stage_id=task.current_stage_id, title=title,
                            prompt=prompt, risk_level=risk_level,
                            requested_action=requested_action, scope=scope,
                            cloud_egress=cloud_egress, project_root=project_root, on=on)
    if ap is None:
        raise OrchestratorError("task not found")

    stage = wr.new_stage(task_id, "awaiting_approval", on=on)
    stage.status = "running"
    stage.started_at = wr._now(on)
    stage.next_action = "await human approval"
    wr.append_stage(task_id, stage, project_root, on=on)
    return ap


def decide_approval(approval_id: str, decision: str, reason: Optional[str] = None,
                    decided_by: str = "user", project_root: Optional[Path] = None,
                    on: Optional[str] = None) -> wr.ApprovalDecision:
    """Record approve / reject / hold on a pending approval and advance the task.

    - **approve** → decision recorded, approval-stage completed; task stays
      ``awaiting_approval`` (approved, pending execution — call ``mark_executing``).
    - **reject** → task → ``failed`` (approval-stage failed).
    - **hold**   → task → ``held``.

    Raises if the approval is unknown or already decided (cannot approve twice)."""
    ap = wr.load_approval(approval_id, project_root)
    if ap is None:
        raise OrchestratorError("approval not found")
    if ap.status != "pending":
        raise OrchestratorError(f"approval already decided ('{ap.status}')")

    dec = wr.record_approval_decision(approval_id, decision, reason=reason,
                                      decided_by=decided_by, project_root=project_root, on=on)
    task = wr.load_task(ap.task_id, project_root)
    if task is not None:
        if decision == "approve":
            _finish_current_stage(task, "completed", on)
        elif decision == "reject":
            _finish_current_stage(task, "failed", on)
            task.status = "failed"
            task.summary = wr._clean(reason or "approval rejected", 4000)
        elif decision == "hold":
            task.status = "held"
            task.summary = wr._clean(reason or task.summary, 4000)
        wr.save_task(task, project_root, on=on)
    return dec


def mark_executing(task_id: str, approval_id: Optional[str] = None,
                   action_kind: str = "deferred", project_root: Optional[Path] = None,
                   on: Optional[str] = None) -> wr.Task:
    """Move an approved task to ``executing`` and record a ``pending`` Action (a
    placeholder for a later executor PR — **it is never run here**). Requires an
    approved approval on the task; raises otherwise."""
    task = _load_task_or_raise(task_id, project_root)
    if task.status != "awaiting_approval":
        raise OrchestratorError(f"cannot execute from status '{task.status}'")
    approved = None
    for aid in task.approval_ids:
        a = wr.load_approval(aid, project_root)
        if a is not None and a.status == "approved" and (approval_id is None or a.id == approval_id):
            approved = a
            break
    if approved is None:
        raise OrchestratorError("cannot mark executing without an approved approval")

    task.status = "executing"
    stage = wr.new_stage(task_id, "executing", on=on)
    stage.status = "running"
    stage.started_at = wr._now(on)
    task.stages.append(stage)
    task.current_stage_id = stage.id

    action = wr.new_action(task_id, kind=action_kind,
                           command_or_path=(approved.requested_action or ""),
                           approval_id=approved.id, on=on)
    # action.status is 'pending' by default — recorded, NOT executed.
    task.action_ids.append(action.id)
    wr.save_task(task, project_root, on=on)
    wr.save_action(action, project_root)
    return task


def complete_task(task_id: str, summary: Optional[str] = None,
                  project_root: Optional[Path] = None, on: Optional[str] = None) -> wr.Task:
    """Complete a task. Refuses to complete a task still ``awaiting_approval``."""
    task = _load_task_or_raise(task_id, project_root)
    if task.status == "awaiting_approval":
        raise OrchestratorError("cannot complete a task awaiting approval")
    if task.status in ("completed", "failed"):
        raise OrchestratorError(f"task already {task.status}")
    _finish_current_stage(task, "completed", on)
    task.status = "completed"
    if summary is not None:
        task.summary = wr._clean(summary, 4000)
    wr.save_task(task, project_root, on=on)
    return _load_task_or_raise(task_id, project_root)


def fail_task(task_id: str, reason: str, project_root: Optional[Path] = None,
              on: Optional[str] = None) -> wr.Task:
    """Mark a task ``failed`` and record the reason."""
    task = _load_task_or_raise(task_id, project_root)
    _finish_current_stage(task, "failed", on)
    task.status = "failed"
    task.summary = wr._clean(reason, 4000)
    wr.save_task(task, project_root, on=on)
    return _load_task_or_raise(task_id, project_root)


def hold_task(task_id: str, reason: Optional[str] = None,
              project_root: Optional[Path] = None, on: Optional[str] = None) -> wr.Task:
    """Mark a task ``held`` (paused; can be resumed by later PRs)."""
    task = _load_task_or_raise(task_id, project_root)
    task.status = "held"
    if reason is not None:
        task.summary = wr._clean(reason, 4000)
    wr.save_task(task, project_root, on=on)
    return _load_task_or_raise(task_id, project_root)


# --------------------------------------------------------------------------- #
# Read-only views (panel-facing)
# --------------------------------------------------------------------------- #

def get_task_progress(task_id: str, project_root: Optional[Path] = None) -> Dict:
    """A small, panel-friendly progress summary for a task. Read-only."""
    task = _load_task_or_raise(task_id, project_root)
    cur = _current_stage(task)
    pending = []
    for aid in task.approval_ids:
        a = wr.load_approval(aid, project_root)
        if a is not None and a.status == "pending":
            pending.append({"id": a.id, "title": a.title, "risk_level": a.risk_level})
    return {
        "task_id": task.id,
        "title": task.title,
        "status": task.status,
        "current_stage": (
            {"id": cur.id, "name": cur.name, "status": cur.status,
             "worker": cur.worker, "model": cur.model, "next_action": cur.next_action}
            if cur is not None else None),
        "completed_stages": [s.name for s in task.stages if s.status == "completed"],
        "stage_count": len(task.stages),
        "pending_approvals": pending,
        "next_action": (cur.next_action if cur is not None else ""),
        "active_worker": (cur.worker if cur is not None else ""),
        "active_model": (cur.model if cur is not None else ""),
    }


def list_pending_approvals(project_root: Optional[Path] = None) -> List[wr.ApprovalRequest]:
    """All pending approval requests across tasks (for the future approval inbox)."""
    out: List[wr.ApprovalRequest] = []
    for task in wr.list_tasks(project_root=project_root):
        for aid in task.approval_ids:
            a = wr.load_approval(aid, project_root)
            if a is not None and a.status == "pending":
                out.append(a)
    return out
