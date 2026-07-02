"""AI Council Workbench — guarded executor skeleton (v0.5, dry-run only, stdlib-only).

The first step of guarded execution — **dry-run only**. It validates the full
**execution invariant**, **re-runs the deterministic trust boundary at execution
time** (a stored `AuditResult` is advisory and cannot authorize), and returns a
preview of what *would* happen. It performs **no real execution**: no file write/
edit, no command run, no git/shell, no provider/model/network. See
``docs/plans/v0.5-guarded-executor.md``.

Fail-closed: `execute_action(..., dry_run=False)` raises — real execution is not
implemented yet. Any invalid/unsupported/blocked case yields ``would_execute=False``.
Approval and execution stay separate; the panel does not auto-execute. By default the
executor mutates nothing (optional ``record=True`` writes only a non-final result
summary to the runtime action; it never marks the action/task completed or runs
anything).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import workbench_runtime as wr
from . import workbench_trust as wt

EXECUTOR = "workbench-executor"
EXECUTOR_VERSION = 1
SUPPORTED_KINDS = ("write_file", "edit_file", "run_command")  # dry-run preview only


class ExecutorError(Exception):
    """Raised when real execution is requested (not implemented yet) or on misuse."""


@dataclass
class ExecutionResult:
    action_id: str
    approval_id: str
    task_id: str
    kind: str
    dry_run: bool = True
    executed: bool = False
    allowed: bool = False
    blocked: bool = False
    would_execute: bool = False
    risk_level: str = "blocked"
    findings: List[str] = field(default_factory=list)
    preview: str = ""
    reason: str = ""
    executor: str = EXECUTOR
    executor_version: int = EXECUTOR_VERSION
    started_at: str = ""
    completed_at: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _approved_target(approval) -> tuple:
    """Parse the approval's ``requested_action`` (``kind:target`` convention) into
    (kind, target). Missing/opaque -> ('', '') which cannot match a real action."""
    ra = (getattr(approval, "requested_action", None) or "").strip()
    if ":" in ra:
        k, t = ra.split(":", 1)
        return k.strip().lower(), t.strip()
    return ra.lower(), ""


def _preview(kind: str, target: str) -> str:
    if kind == "write_file":
        return f"[dry-run] would WRITE file `{target}` (no write performed)."
    if kind == "edit_file":
        return f"[dry-run] would EDIT file `{target}` (no edit performed)."
    if kind == "run_command":
        return f"[dry-run] would RUN allowlisted command `{target}` (not executed)."
    return f"[dry-run] would handle `{target}` (no side effect)."


def validate_execution_invariant(action, approval, task, project_root: Optional[Path] = None,
                                 policy: Optional[wt.TrustPolicy] = None) -> ExecutionResult:
    """Check the full execution invariant + re-run the deterministic trust guard, and
    return a dry-run ExecutionResult. Never executes; fail-closed on any gap."""
    now = _now()
    aid = getattr(action, "id", "") if action else ""
    apid = (getattr(action, "approval_id", "") if action else "") or \
           (getattr(approval, "id", "") if approval else "")
    tid = getattr(action, "task_id", "") if action else ""
    kind = ((getattr(action, "kind", "") or "").strip().lower()) if action else ""
    target = getattr(action, "command_or_path", "") if action else ""

    def blocked(reason: str, findings=None, risk: str = "blocked") -> ExecutionResult:
        return ExecutionResult(
            action_id=aid, approval_id=apid, task_id=tid, kind=kind, dry_run=True,
            executed=False, allowed=False, blocked=True, would_execute=False,
            risk_level=risk, findings=list(findings or []),
            preview=f"[dry-run] BLOCKED: {reason} (nothing would run).", reason=reason,
            started_at=now, completed_at=now)

    if action is None:
        return blocked("action not found")
    if getattr(action, "status", None) != "pending":
        return blocked(f"action not pending (status '{getattr(action, 'status', None)}')")
    if approval is None:
        return blocked("approval not found")
    if approval.status != "approved":
        return blocked(f"approval not approved (status '{approval.status}')")
    if action.approval_id != approval.id or action.task_id != approval.task_id:
        return blocked("action is not linked to the approved approval")
    if task is None or action.id not in getattr(task, "action_ids", []):
        return blocked("action is not linked to its task")
    if kind not in SUPPORTED_KINDS:
        return blocked(f"unsupported action kind '{kind}'")
    ak, at = _approved_target(approval)
    if (kind, target) != (ak, at):
        return blocked("action does not match the approved scope (modified after approval)")

    # Re-run the DETERMINISTIC trust boundary at execution time (never trust a stale
    # advisory audit). If it blocks, we block.
    ev = wt.evaluate_action(action, project_root=project_root, policy=policy)
    if ev.blocked:
        return blocked(ev.reason or "trust boundary blocked", findings=ev.findings,
                       risk=ev.risk_level)

    return ExecutionResult(
        action_id=aid, approval_id=apid, task_id=tid, kind=kind, dry_run=True,
        executed=False, allowed=ev.allowed, blocked=False, would_execute=True,
        risk_level=ev.risk_level, findings=list(ev.findings), preview=_preview(kind, target),
        reason="invariant satisfied; dry-run only (nothing executed)",
        started_at=now, completed_at=now)


def preview_action(action, approval=None, task=None, project_root: Optional[Path] = None,
                   policy: Optional[wt.TrustPolicy] = None) -> ExecutionResult:
    """Dry-run preview for an in-hand Action (loads the linked approval/task if not
    given). Never executes."""
    if action is not None:
        if approval is None and getattr(action, "approval_id", None):
            approval = wr.load_approval(action.approval_id, project_root)
        if task is None and getattr(action, "task_id", None):
            task = wr.load_task(action.task_id, project_root)
    return validate_execution_invariant(action, approval, task, project_root, policy)


def dry_run_action(action_id: str, project_root: Optional[Path] = None,
                   policy: Optional[wt.TrustPolicy] = None,
                   record: bool = False) -> ExecutionResult:
    """Load an action by id and produce a dry-run ExecutionResult. Executes nothing.

    Default ``record=False`` mutates nothing. ``record=True`` writes only a non-final
    ``result_summary`` on the runtime action (status stays ``pending``) — it never
    marks the action/task completed and never executes."""
    action = wr.load_action(action_id, project_root)
    approval = (wr.load_approval(action.approval_id, project_root)
                if action and action.approval_id else None)
    task = wr.load_task(action.task_id, project_root) if action else None
    result = validate_execution_invariant(action, approval, task, project_root, policy)
    if record and action is not None:
        action.result_summary = result.preview[:2000]  # non-final; status remains pending
        wr.save_action(action, project_root)
    return result


def execute_action(action_id: str, project_root: Optional[Path] = None,
                   policy: Optional[wt.TrustPolicy] = None, dry_run: bool = True,
                   record: bool = False) -> ExecutionResult:
    """Single entry point. **Fail-closed:** real execution is not implemented, so
    ``dry_run=False`` raises. ``dry_run=True`` returns a preview (executes nothing)."""
    if not dry_run:
        raise ExecutorError("Real execution is not implemented yet.")
    return dry_run_action(action_id, project_root=project_root, policy=policy, record=record)


def summarize_execution_result(result: ExecutionResult) -> str:
    verdict = ("WOULD-EXECUTE" if result.would_execute
               else ("BLOCKED" if result.blocked else "NO-OP"))
    return (f"[{verdict}] {result.kind} risk={result.risk_level} "
            f"executed={result.executed} - {result.preview}")
