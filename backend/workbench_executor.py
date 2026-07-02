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

**Payload source (PR #76):** real execution needs `write_file`/`edit_file` content. A
caller may still pass ``payload=`` explicitly (unchanged from PR #74, kept for tests/
direct callers). If ``payload`` is omitted, the executor loads the matching
:mod:`backend.workbench_payloads` artifact for the action, verifies its hash and its
agreement with the live action/approval/task, and uses its stored payload. A payload
hash check is **additional** to, never a replacement for, the deterministic trust
re-check performed by ``validate_execution_invariant``.

**Command preview (PR #79):** for ``run_command`` dry-run previews, the executor also
consults :mod:`backend.workbench_commands` — a label must resolve to a fixed,
allowlisted argv **and** pass the deterministic trust boundary before a preview reports
``would_execute=True``; either gate failing blocks it. This module still never imports
``subprocess``, and ``REAL_EXEC_KINDS`` still excludes ``run_command`` — real command
execution stays fail-closed (``ExecutorError``) exactly as before.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import workbench_runtime as wr
from . import workbench_trust as wt
from . import workbench_payloads as wp
from . import workbench_commands as wc

EXECUTOR = "workbench-executor"
EXECUTOR_VERSION = 3
SUPPORTED_KINDS = ("write_file", "edit_file", "run_command")  # accepted by the invariant
REAL_EXEC_KINDS = ("write_file", "edit_file")  # kinds that can ACTUALLY run (this PR)

# Conservative bounded-execution limits.
MAX_WRITE_BYTES = 100_000       # ~100 KB max file content written
MAX_EDIT_BYTES = 100_000        # ~100 KB max file size to edit
MAX_REPLACEMENTS_DEFAULT = 1    # edit_file replaces one occurrence by default
MAX_LINES_CHANGED = 200         # max net line delta for an edit


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
    # PR #79: populated only for a successfully-previewed run_command dry-run.
    command_label: str = ""
    command_argv: List[str] = field(default_factory=list)
    command_timeout_seconds: int = 0
    command_output_limit_bytes: int = 0
    command_cwd: str = ""
    command_shell: bool = False


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

    if kind == "run_command":
        # Two independent gates, both required (PR #79): trust already passed above;
        # the command must ALSO resolve to a fixed, allowlisted argv via the resolver.
        # Neither gate can authorize alone — this only ever narrows would_execute,
        # never widens it. REAL_EXEC_KINDS still excludes run_command, so real
        # execution stays fail-closed regardless of this preview's outcome.
        cp = wc.preview_command(target, project_root=project_root)
        if not cp.would_execute:
            return blocked(cp.reason or "command not resolvable", risk="blocked")
        return ExecutionResult(
            action_id=aid, approval_id=apid, task_id=tid, kind=kind, dry_run=True,
            executed=False, allowed=ev.allowed, blocked=False, would_execute=True,
            risk_level=ev.risk_level, findings=list(ev.findings),
            preview=(f"[dry-run] would RUN allowlisted command `{cp.label}` "
                     f"(argv={cp.argv}, timeout={cp.timeout_seconds}s, "
                     f"cap={cp.output_limit_bytes}B, shell=False; not executed)."),
            reason="invariant + command resolver satisfied; dry-run only (nothing executed)",
            started_at=now, completed_at=now,
            command_label=cp.label, command_argv=list(cp.argv),
            command_timeout_seconds=cp.timeout_seconds,
            command_output_limit_bytes=cp.output_limit_bytes,
            command_cwd=cp.cwd, command_shell=cp.shell)

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


class _GuardError(Exception):
    """A filesystem-level guard failure during real execution (fail-closed)."""


def _resolve_safe_target(root: Path, target: str) -> Path:
    """Resolve ``target`` under the project root with filesystem-level guards
    (belt-and-suspenders beyond the lexical trust boundary): reject symlink final
    components and any path whose real location escapes the project root."""
    root_real = os.path.realpath(str(root))
    cand = target if os.path.isabs(target) else os.path.join(root_real, target)
    cand_norm = os.path.normpath(cand)
    if os.path.islink(cand_norm):
        raise _GuardError("target is a symlink")
    real = os.path.realpath(cand_norm)
    if not (real == root_real or real.startswith(root_real + os.sep)):
        raise _GuardError("path escapes the project root")
    # a resolved path that diverges from the lexical path means a symlink was traversed
    if real != cand_norm and real != os.path.normpath(cand_norm):
        raise _GuardError("symlink in path (blocked)")
    return Path(cand_norm)


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` atomically: temp file in the same dir, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".wbx-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _fail(action, status: str, reason: str, result: ExecutionResult,
          project_root: Optional[Path]) -> ExecutionResult:
    """Fail closed: mark the action (blocked/failed), record a safe reason, mutate no
    file, and return an executed=False result. Never marks completed."""
    action.status = status
    action.result_summary = reason[:2000]
    wr.save_action(action, project_root)
    result.blocked = (status == "blocked")
    result.executed = False
    result.would_execute = False
    result.reason = reason
    result.preview = f"[execute] {status.upper()}: {reason} (no file changed)."
    result.completed_at = _now()
    return result


def _real_execute(action_id: str, payload: Optional[Dict], project_root: Optional[Path],
                  policy: Optional[wt.TrustPolicy]) -> ExecutionResult:
    action = wr.load_action(action_id, project_root)
    approval = (wr.load_approval(action.approval_id, project_root)
                if action and action.approval_id else None)
    task = wr.load_task(action.task_id, project_root) if action else None

    # Re-validate the full invariant + re-run the deterministic trust guard NOW.
    result = validate_execution_invariant(action, approval, task, project_root, policy)
    if action is None:
        return result  # nothing to mutate
    if not result.would_execute:
        # guard/invariant refused: mark blocked (records the refused attempt)
        return _fail(action, "blocked", result.reason or "blocked by guard", result,
                     project_root)

    kind = result.kind
    if kind not in REAL_EXEC_KINDS:
        # e.g. run_command — accepted by the invariant but NOT executable in this PR.
        # Checked before any payload lookup: non-file kinds never need/get a payload.
        raise ExecutorError(f"real execution not implemented for kind '{kind}'")

    effective_payload = payload
    if effective_payload is None:
        # No explicit payload: load + verify the runtime payload artifact (PR #76).
        # Hash + kind/target/approval/task agreement is an ADDITIONAL check on top of
        # (never a replacement for) the trust re-check already run above.
        artifact = wp.load_payload_artifact(action_id, project_root)
        if artifact is None:
            return _fail(action, "blocked", "no payload artifact found for action",
                         result, project_root)
        pv = wp.verify_payload_against_action(artifact, action, approval, task)
        if not pv.ok:
            return _fail(action, "blocked",
                         f"payload verification failed: {pv.reason}", result, project_root)
        effective_payload = artifact.payload

    target = action.command_or_path
    try:
        safe = _resolve_safe_target(Path(project_root) if project_root else Path.cwd(),
                                    target)
    except _GuardError as e:
        return _fail(action, "blocked", f"path guard: {e}", result, project_root)

    result.started_at = _now()
    if kind == "write_file":
        return _do_write(action, safe, effective_payload, result, project_root)
    return _do_edit(action, safe, effective_payload, result, project_root)


def _do_write(action, path: Path, payload: Dict, result: ExecutionResult,
              project_root: Optional[Path]) -> ExecutionResult:
    content = payload.get("content")
    overwrite = bool(payload.get("overwrite", False))
    if not isinstance(content, str):
        return _fail(action, "failed", "write_file requires string 'content'", result,
                     project_root)
    if "\x00" in content:
        return _fail(action, "blocked", "binary content is not allowed", result, project_root)
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        return _fail(action, "blocked", f"content exceeds max {MAX_WRITE_BYTES} bytes",
                     result, project_root)
    if path.exists():
        if path.is_dir():
            return _fail(action, "blocked", "target is a directory", result, project_root)
        if not overwrite:
            return _fail(action, "blocked", "file exists and overwrite not approved",
                         result, project_root)
    try:
        _atomic_write(path, content)
    except OSError as e:
        return _fail(action, "failed", f"write error: {type(e).__name__}", result, project_root)
    action.status = "completed"
    action.completed_at = _now()
    action.result_summary = f"wrote {len(content.encode('utf-8'))} bytes to {os.path.basename(str(path))}"
    wr.save_action(action, project_root)
    result.executed = True
    result.blocked = False
    result.completed_at = action.completed_at
    result.reason = "write_file executed"
    result.preview = f"[execute] wrote file (bytes={len(content.encode('utf-8'))})."
    return result


def _do_edit(action, path: Path, payload: Dict, result: ExecutionResult,
             project_root: Optional[Path]) -> ExecutionResult:
    old = payload.get("old_text")
    new = payload.get("new_text")
    max_repl = int(payload.get("max_replacements", MAX_REPLACEMENTS_DEFAULT))
    if not isinstance(old, str) or not isinstance(new, str) or old == "":
        return _fail(action, "failed", "edit_file requires non-empty 'old_text' and 'new_text'",
                     result, project_root)
    if "\x00" in new:
        return _fail(action, "blocked", "binary content is not allowed", result, project_root)
    if not path.is_file():
        return _fail(action, "failed", "target file does not exist", result, project_root)
    if path.stat().st_size > MAX_EDIT_BYTES:
        return _fail(action, "blocked", f"file exceeds max {MAX_EDIT_BYTES} bytes", result,
                     project_root)
    try:
        original = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _fail(action, "blocked", "cannot read target as UTF-8 text (binary?)", result,
                     project_root)
    count = original.count(old)
    if count == 0:
        return _fail(action, "failed", "old_text not found (no change)", result, project_root)
    if count > max_repl:
        return _fail(action, "blocked",
                     f"old_text matches {count}x but max_replacements={max_repl}", result,
                     project_root)
    edited = original.replace(old, new, max_repl)
    if len(edited.encode("utf-8")) > MAX_EDIT_BYTES:
        return _fail(action, "blocked", f"edited file exceeds max {MAX_EDIT_BYTES} bytes",
                     result, project_root)
    line_delta = abs(edited.count("\n") - original.count("\n"))
    if line_delta > MAX_LINES_CHANGED:
        return _fail(action, "blocked", f"line change {line_delta} exceeds max {MAX_LINES_CHANGED}",
                     result, project_root)
    try:
        _atomic_write(path, edited)
    except OSError as e:
        return _fail(action, "failed", f"edit error: {type(e).__name__}", result, project_root)
    action.status = "completed"
    action.completed_at = _now()
    action.result_summary = f"edited {os.path.basename(str(path))} ({max_repl} replacement(s))"
    wr.save_action(action, project_root)
    result.executed = True
    result.blocked = False
    result.completed_at = action.completed_at
    result.reason = "edit_file executed"
    result.preview = f"[execute] edited file ({max_repl} replacement(s))."
    return result


def execute_action(action_id: str, project_root: Optional[Path] = None,
                   policy: Optional[wt.TrustPolicy] = None, dry_run: bool = True,
                   payload: Optional[Dict] = None, record: bool = False) -> ExecutionResult:
    """Single entry point.

    ``dry_run=True`` (default) returns a preview and executes nothing. ``dry_run=False``
    performs **real, bounded** execution for ``write_file`` / ``edit_file`` only, behind
    the full invariant + a fresh deterministic trust re-check. Any other kind (e.g.
    ``run_command``) **fails closed** with an ExecutorError. ``payload`` carries the
    content/patch explicitly (never overloaded into runtime strings); if omitted, the
    matching :mod:`backend.workbench_payloads` artifact is loaded and verified instead."""
    if dry_run:
        return dry_run_action(action_id, project_root=project_root, policy=policy, record=record)
    return _real_execute(action_id, payload, project_root, policy)


def summarize_execution_result(result: ExecutionResult) -> str:
    verdict = ("WOULD-EXECUTE" if result.would_execute
               else ("BLOCKED" if result.blocked else "NO-OP"))
    return (f"[{verdict}] {result.kind} risk={result.risk_level} "
            f"executed={result.executed} - {result.preview}")
