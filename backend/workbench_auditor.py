"""AI Council Workbench — advisory Approval Auditor (v0.5, stdlib-only).

Turns the **deterministic** trust evaluation (:mod:`backend.workbench_trust`) into a
panel-friendly :class:`backend.workbench_runtime.AuditResult`: a risk level, findings,
a blocked flag, and a short human-readable approval-prompt rewrite.

**Advisory only.** The auditor never computes risk independently and never relaxes or
overrides the deterministic trust boundary — its `risk_level`, `blocked`, and
`findings` are taken **directly** from the trust evaluation, so a blocked/high-risk
trust result stays blocked/high-risk after auditing (safety invariant by
construction). The rewrite is text that *adds* a human summary; it never drops a
finding.

This first version is **deterministic / rule-based** (no LLM). A later PR may add an
optional model-assisted rewrite behind the provider abstraction; this PR fixes the
API and the safety invariant. No provider/model/network calls, no action execution,
no panel. The only side effect (when ``save=True``) is writing the AuditResult under
gitignored ``.council/runtime/``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from . import workbench_runtime as wr
from . import workbench_trust as wt

AUDITOR = f"deterministic-trust-guard-v{wt.GUARD_VERSION}"
MODEL = "deterministic"  # rule-based; not an LLM (a later PR may add model-assist)


class AuditorError(Exception):
    """A clean auditor error (e.g. unknown approval id)."""


# --------------------------------------------------------------------------- #
# Prompt rewrite (deterministic templates)
# --------------------------------------------------------------------------- #

def rewrite_approval_prompt(evaluation: wt.TrustEvaluation, approval=None,
                            action=None) -> str:
    """Short, panel-friendly one-line approval prompt derived from the trust
    evaluation. Deterministic; always mentions kind, target, risk, and why."""
    ev = evaluation
    kind = ev.normalized_kind
    target = ev.normalized_target or "(none)"
    risk = ev.risk_level
    first = ev.findings[0] if ev.findings else ev.reason

    if ev.blocked:
        # A blocked result must surface the reason/critical finding.
        return f"Blocked: {kind} `{target}` - {first or ev.reason}."
    if ev.allowed:
        return f"Allowed ({risk} risk): {kind} `{target}` - {ev.reason}."
    if kind == "cloud_call":
        return (f"Approve cloud call ({target})? {risk.capitalize()} risk: "
                f"prompts/files may leave this machine - {ev.reason}.")
    return f"Approve {kind} `{target}`? {risk.capitalize()} risk: {ev.reason}."


# --------------------------------------------------------------------------- #
# Audit (advisory) — always derived from the deterministic evaluation
# --------------------------------------------------------------------------- #

def _audit_from_evaluation(ev: wt.TrustEvaluation, approval_id: str = "",
                           approval=None, action=None,
                           on: Optional[str] = None) -> wr.AuditResult:
    # risk/blocked/findings are copied from the deterministic result verbatim —
    # the auditor cannot lower risk or unblock. The rewrite only adds a summary.
    return wr.new_audit(
        approval_id=approval_id,
        risk_level=ev.risk_level,
        findings=list(ev.findings),
        rewritten_prompt=rewrite_approval_prompt(ev, approval=approval, action=action),
        blocked=bool(ev.blocked),
        auditor=AUDITOR,
        model=MODEL,
        on=on,
    )


def audit_action_payload(kind: str, target: Optional[str] = None,
                         command: Optional[str] = None, scope: Optional[Dict] = None,
                         metadata: Optional[Dict] = None,
                         project_root: Optional[Path] = None,
                         policy: Optional[wt.TrustPolicy] = None,
                         approval_id: str = "", on: Optional[str] = None) -> wr.AuditResult:
    """Advisory audit of a proposed action payload. Runs the deterministic trust
    evaluation, then wraps it in an AuditResult. Pure — no I/O, no execution."""
    ev = wt.evaluate_action_payload(kind, target=target, command=command, scope=scope,
                                    metadata=metadata, project_root=project_root,
                                    policy=policy)
    return _audit_from_evaluation(ev, approval_id=approval_id, on=on)


def audit_action(action, project_root: Optional[Path] = None,
                 policy: Optional[wt.TrustPolicy] = None,
                 on: Optional[str] = None) -> wr.AuditResult:
    """Advisory audit of a runtime ``Action`` (references its approval id)."""
    ev = wt.evaluate_action(action, project_root=project_root, policy=policy)
    approval_id = getattr(action, "approval_id", "") or ""
    return _audit_from_evaluation(ev, approval_id=approval_id, action=action, on=on)


def _payload_from_approval(ap) -> Dict:
    """Derive a trust payload from an ApprovalRequest. ``requested_action`` uses a
    ``kind:target`` convention (e.g. ``write_file:src/foo.py``,
    ``run_command:git status --short``, ``cloud_call:anthropic``); a missing/opaque
    value yields ``unknown`` (which the guard blocks by default). Cloud-egress
    consent is read from the approval's ``cloud_egress`` block."""
    ra = (getattr(ap, "requested_action", None) or "").strip()
    if ":" in ra:
        kind, rest = ra.split(":", 1)
        kind, rest = kind.strip().lower(), rest.strip()
    else:
        kind, rest = (ra.lower() or "unknown"), ""
    metadata: Dict = {}
    ce = getattr(ap, "cloud_egress", None)
    if isinstance(ce, dict):
        metadata["cloud_egress"] = ce
    payload = {"kind": kind, "scope": getattr(ap, "scope", None), "metadata": metadata}
    if kind == "run_command":
        payload["command"] = rest
    else:
        payload["target"] = rest
    return payload


def audit_approval_request(approval_id: str, project_root: Optional[Path] = None,
                           policy: Optional[wt.TrustPolicy] = None, save: bool = True,
                           on: Optional[str] = None) -> wr.AuditResult:
    """Audit an ApprovalRequest by id. Evaluates its proposed action, builds an
    AuditResult referencing the approval, and (when ``save``) persists it under
    ``.council/runtime/`` and attaches its id to the approval. Raises if unknown."""
    ap = wr.load_approval(approval_id, project_root)
    if ap is None:
        raise AuditorError("approval not found")
    p = _payload_from_approval(ap)
    ev = wt.evaluate_action_payload(p["kind"], target=p.get("target"),
                                    command=p.get("command"), scope=p.get("scope"),
                                    metadata=p.get("metadata"), project_root=project_root,
                                    policy=policy)
    audit = _audit_from_evaluation(ev, approval_id=ap.id, approval=ap, on=on)
    if save:
        wr.save_audit_result(audit, project_root)
        # attach the audit id back to the approval (best-effort, same-package store)
        try:
            ap.audit_id = audit.id
            wr._save_entry("approvals", ap, project_root)
        except Exception:
            pass
    return audit


def audit_summary(audit_result: wr.AuditResult) -> str:
    """One-line human-readable summary of an AuditResult (advisory)."""
    tag = "BLOCKED" if audit_result.blocked else audit_result.risk_level
    return f"[{tag}] {audit_result.rewritten_prompt}"
