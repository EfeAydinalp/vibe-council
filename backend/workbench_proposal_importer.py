"""AI Council Workbench — proposal importer (v0.6 agent bridge, stdlib-only).

The second v0.6 bridge slice
([docs/fable/05-v0.6-agent-bridge.md](../docs/fable/05-v0.6-agent-bridge.md)): turn a
**validated** agent proposal (:mod:`backend.workbench_proposals`, schema v1) into the
runtime records the existing guarded pipeline already knows how to handle — a
``Task`` + pending ``ApprovalRequest`` + pending ``Action`` (and, for file kinds, a
local write-once payload artifact). Everything downstream is **unchanged**: the
deterministic trust boundary still evaluates at approval display and re-runs at
execution time, the advisory auditor still cannot relax a verdict, approval still
never executes, and real execution still happens only through the existing executor
behind an explicit human step.

**Server mints everything.** Task/approval/action ids come from the runtime store's
own id minting; the payload hash is computed server-side by
:mod:`backend.workbench_payloads` from the *submitted content* — a client-supplied
hash/id/status/verdict is already a schema-level hard reject before this module ever
runs. The internal ``requested_action`` ``kind:target`` convention is constructed
here, server-side, from the validated typed fields; agents never author it.

**Local intake only.** No network endpoint, no panel change, no execution, no
``subprocess`` import, no provider/model call. The only side effects are JSON writes
under the gitignored ``.council/runtime/`` tree (via the existing runtime/payload
stores, plus a small ``proposals/`` dedup index).

Dedup / idempotency (the scoping decision delegated by ``workbench_proposals``):
the dedup key is **``proposal_id`` alone, globally** — deliberately not scoped by
agent name, so dedup can never depend on (spoofable) agent identity. A repeat import
of the same ``proposal_id`` with **identical content** returns the original ids and
creates nothing. The same ``proposal_id`` with **materially different content** (any
change to agent/title/summary/action, fingerprinted server-side) is a **conflict**
and fails closed — nothing is created or updated. Raw payload content is never
stored in the dedup record (fingerprint hash only); it lives solely in the payload
artifact, the intended store.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import workbench_proposals as wprop
from . import workbench_runtime as wr
from . import workbench_orchestrator as wo
from . import workbench_payloads as wpay
from . import workbench_auditor as wa
from . import workbench_trust as wt

IMPORTER_VERSION = 1

_PROPOSALS_SUBDIR = "proposals"

# Risk hint on the created ApprovalRequest. Advisory bookkeeping only — the
# deterministic trust boundary and the auditor recompute risk from the requested
# action itself; nothing reads this field as an authorization.
_RISK_BY_KIND = {"write_file": "medium", "edit_file": "medium", "run_command": "low"}


class ImporterError(Exception):
    """Programmer misuse of the importer (not a validation/conflict outcome)."""


@dataclass
class ImportResult:
    ok: bool
    created: bool = False
    duplicate: bool = False
    conflict: bool = False
    errors: List[str] = field(default_factory=list)
    proposal_id: str = ""
    agent_name: str = ""
    kind: str = ""
    target: str = ""              # file target or command label (safe, content-free)
    task_id: str = ""
    approval_id: str = ""
    action_id: str = ""
    payload_artifact: bool = False
    audit_risk: str = ""
    audit_blocked: bool = False
    next_step: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# Dedup index (.council/runtime/proposals/<proposal_id>.json)
# --------------------------------------------------------------------------- #
# Follows the same local-store pattern as workbench_payloads: own containment-
# checked path helper + atomic-ish dump. proposal_id is filename-safe by schema
# construction ([A-Za-z0-9._-]{1,120}) and re-checked here anyway (fail closed).

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def _proposals_root(project_root: Optional[Path]) -> Path:
    return wr.runtime_root(project_root) / _PROPOSALS_SUBDIR


def _record_path(project_root: Optional[Path], proposal_id: str) -> Path:
    if not _SAFE_ID_RE.match(proposal_id or ""):
        raise ImporterError("unsafe proposal_id (validation should have rejected it)")
    root = _proposals_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    p = (root / (proposal_id + ".json")).resolve()
    if p.parent != root.resolve():
        raise ImporterError("unsafe proposal record path (containment violation)")
    return p


def _dump(path: Path, obj: Dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def _load_record(project_root: Optional[Path], proposal_id: str):
    """Returns ``(record_dict, None)``, ``(None, None)`` when no record exists, or
    ``(None, error)`` when a record file exists but cannot be read/parsed — a
    corrupt dedup record must **fail closed** (refuse the import) rather than be
    silently treated as "never imported", which would break idempotency."""
    try:
        path = _record_path(project_root, proposal_id)
    except ImporterError:
        return None, "unsafe proposal_id"
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, (f"dedup record for proposal_id '{proposal_id}' exists but is "
                      "unreadable/corrupt; refusing to re-import (fail closed) — "
                      "inspect .council/runtime/proposals/ before retrying")
    if not isinstance(data, dict):
        return None, (f"dedup record for proposal_id '{proposal_id}' is malformed; "
                      "refusing to re-import (fail closed)")
    return data, None


def _fingerprint(p: wprop.Proposal) -> str:
    """Server-side content fingerprint for conflict detection: covers everything
    material (agent name, title, summary, and the full validated action including
    payload). Canonical JSON so key order can't produce false conflicts. Only this
    hash is persisted — never the raw payload."""
    body = {
        "agent": p.agent.name,
        "title": p.title,
        "summary": p.summary,
        "action": {
            "kind": p.action.kind,
            "target": p.action.target,
            "command_label": p.action.command_label,
            "payload": p.action.payload or {},
            "scope": p.action.scope or {},
        },
    }
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #

_NEXT_STEP = ("run 'vibe workbench serve' and review/approve the pending approval in "
              "the panel; approving records a decision only — execution is a separate "
              "explicit step")


def _result_from_record(rec: Dict, duplicate: bool) -> ImportResult:
    return ImportResult(
        ok=True, created=False, duplicate=duplicate,
        proposal_id=rec.get("proposal_id", ""),
        agent_name=(rec.get("agent") or {}).get("name", ""),
        kind=rec.get("kind", ""), target=rec.get("target", ""),
        task_id=rec.get("task_id", ""), approval_id=rec.get("approval_id", ""),
        action_id=rec.get("action_id", ""),
        payload_artifact=bool(rec.get("payload_artifact")),
        next_step=_NEXT_STEP,
    )


def import_proposal(data: object, project_root: Optional[Path] = None,
                    policy: Optional[wt.TrustPolicy] = None) -> ImportResult:
    """Validate ``data`` (schema v1) and import it into the runtime store as a
    Task + pending ApprovalRequest + pending Action (+ payload artifact for file
    kinds). Fail-closed: an invalid proposal creates **nothing**; a duplicate
    ``proposal_id`` with identical content returns the original ids and creates
    nothing; a duplicate with different content is a **conflict** and creates
    nothing. Never executes, never calls a provider/model, never touches the
    network."""
    validation = wprop.validate_proposal(data, project_root=project_root, policy=policy)
    if not validation.ok or validation.proposal is None:
        return ImportResult(ok=False, errors=list(validation.errors))
    p = validation.proposal

    fingerprint = _fingerprint(p)
    existing, record_err = _load_record(project_root, p.proposal_id)
    if record_err:
        return ImportResult(ok=False, conflict=True, proposal_id=p.proposal_id,
                            errors=[record_err])
    if existing is not None:
        if existing.get("fingerprint") == fingerprint:
            return _result_from_record(existing, duplicate=True)
        return ImportResult(
            ok=False, conflict=True, proposal_id=p.proposal_id,
            errors=[f"proposal_id '{p.proposal_id}' was already imported with "
                    "materially different content; nothing was created or updated — "
                    "submit the new content under a new proposal_id"])

    kind = p.action.kind
    is_file = kind in ("write_file", "edit_file")
    target = p.action.target if is_file else p.action.command_label

    # ---- create runtime records (all ids server-minted by the stores) -------- #
    task = wo.start_task(p.title, summary=p.summary,
                         source=f"agent:{p.agent.name}", project_root=project_root)
    # The internal `kind:target` convention is constructed HERE, server-side, from
    # the validated typed fields — agents never author it (schema rejects
    # 'requested_action' outright).
    approval = wo.request_approval(
        task.id, title=p.title, prompt=p.summary,
        requested_action=f"{kind}:{target}",
        scope=p.action.scope, risk_level=_RISK_BY_KIND[kind],
        project_root=project_root)

    action = wr.new_action(task.id, kind, command_or_path=target, approval_id=approval.id)
    wr.save_action(action, project_root)
    t = wr.load_task(task.id, project_root)
    t.action_ids.append(action.id)
    wr.save_task(t, project_root)

    payload_artifact = False
    if is_file:
        try:
            # Hash computed server-side from the SUBMITTED content; write-once.
            artifact = wpay.build_payload_artifact(action, p.action.payload,
                                                   task=t, approval=approval)
            wpay.save_payload_artifact(artifact, project_root)
            payload_artifact = True
        except (wpay.PayloadError, OSError) as e:
            # Fail closed: don't leave an approvable-looking card behind. Rejecting
            # the approval also marks the task failed (orchestrator semantics), and
            # the action is blocked so the executor invariant can never pass.
            wo.decide_approval(approval.id, "reject",
                               reason=f"proposal import failed: payload artifact "
                                      f"error ({type(e).__name__})",
                               decided_by="proposal-importer",
                               project_root=project_root)
            action.status = "blocked"
            action.result_summary = "import failed: payload artifact could not be saved"
            wr.save_action(action, project_root)
            return ImportResult(
                ok=False, proposal_id=p.proposal_id,
                errors=["payload artifact could not be created; import failed closed "
                        "(task marked failed, action blocked, nothing approvable)"])

    # Advisory audit (deterministic; copies trust verdicts verbatim, can't relax).
    audit = wa.audit_approval_request(approval.id, project_root=project_root, save=True)

    # Dedup record: ids + fingerprint + safe metadata only — never raw payload.
    rec = {
        "importer_version": IMPORTER_VERSION,
        "proposal_id": p.proposal_id,
        "fingerprint": fingerprint,
        "agent": {"name": p.agent.name, "role": p.agent.role, "session": p.agent.session},
        "title": p.title,
        "kind": kind,
        "target": target,
        "task_id": task.id,
        "approval_id": approval.id,
        "action_id": action.id,
        "payload_artifact": payload_artifact,
        "imported_at": _now(),
    }
    _dump(_record_path(project_root, p.proposal_id), rec)

    return ImportResult(
        ok=True, created=True, proposal_id=p.proposal_id, agent_name=p.agent.name,
        kind=kind, target=target, task_id=task.id, approval_id=approval.id,
        action_id=action.id, payload_artifact=payload_artifact,
        audit_risk=audit.risk_level, audit_blocked=audit.blocked,
        next_step=_NEXT_STEP,
    )


def import_proposal_text(text: str, project_root: Optional[Path] = None,
                         policy: Optional[wt.TrustPolicy] = None) -> ImportResult:
    """Parse a proposal JSON string, then import it. Malformed/non-object JSON
    fails closed with nothing created."""
    data, err = wprop.parse_proposal_json(text)
    if err:
        return ImportResult(ok=False, errors=[err])
    return import_proposal(data, project_root=project_root, policy=policy)


def summarize_import(result: ImportResult) -> str:
    """One-line, log-safe summary — never raw payload content."""
    if result.ok and result.duplicate:
        return (f"[duplicate] proposal {result.proposal_id} already imported -> "
                f"task {result.task_id} approval {result.approval_id}")
    if result.ok:
        return (f"[imported] proposal {result.proposal_id} agent={result.agent_name} "
                f"kind={result.kind} -> task {result.task_id} approval "
                f"{result.approval_id} action {result.action_id}")
    if result.conflict:
        return f"[conflict] proposal {result.proposal_id}: {result.errors[0]}"
    first = result.errors[0] if result.errors else "invalid"
    return f"[rejected] {len(result.errors)} error(s); first: {first}"


def result_to_dict(result: ImportResult) -> Dict:
    """JSON-safe dict for CLI output (stdout stays machine-readable)."""
    return asdict(result)
