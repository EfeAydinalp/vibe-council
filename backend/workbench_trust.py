"""AI Council Workbench — deterministic trust boundary (v0.5, stdlib-only).

**This is the real security boundary.** Given a proposed action (an
:class:`backend.workbench_runtime.Action` or a raw payload), it returns a
deterministic :class:`TrustEvaluation`: allowed / blocked / requires-approval, a
risk level, findings, a normalized target, and cloud-egress consent status. A future
executor MUST consult this guard before running anything; the (later) Approval
Auditor AI is **advisory only** and can never relax this deterministic gate.

**Evaluation only — nothing is executed.** No shell/git, no file I/O beyond a
read-only scan of the runtime store in the optional ``evaluate_pending_actions``
helper, no provider/model/network. Pure and deterministic: the same input always
yields the same result.

Default stance (conservative):
- unknown action kind → **blocked**
- shell/command execution → **blocked** unless the exact command is allowlisted;
  any shell metacharacter → blocked
- writes/edits → **require approval** and must pass path/secret checks
- reads → allowed only inside the project root and outside denied/secret paths
- cloud calls → **require explicit cloud-egress consent** metadata (blocked without
  it); never auto-allowed (human approval still required)
- secret / private-plan / `.council` / `.git` / `.env` / key files → **blocked**
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

GUARD_VERSION = 1

ACTION_KINDS = ("read_file", "write_file", "edit_file", "run_command", "cloud_call", "unknown")
RISK = ("low", "medium", "high", "blocked")

# Shell metacharacters that make a command unsafe to treat as a fixed argv.
_SHELL_META_RE = re.compile(r"(;|&&|\|\||\||>|<|`|\$\()")

# Denied single-segment names (matched against any path component).
_DENY_NAMES = (".env", ".git", ".ssh", ".venv", "node_modules", "data", ".council",
               ".obsidian", "id_rsa", "id_ed25519")

# Denied filename globs (matched against the basename).
_DENY_GLOBS = (".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519", "*.crt")

# Secret-content filename globs (a subset of deny globs, kept explicit for findings).
_SECRET_GLOBS = (".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519")

# Exact relative paths that must never be written/read via the executor.
_DENY_RELPATHS = (
    "docs/plans/commercialization-and-hosted-platform-feasibility.md",
    "docs/plans/v0.3.1-hardening-and-dogfood.md",
)

# Very narrow read-only/status command allowlist (exact, whitespace-normalized).
_ALLOWED_COMMANDS = (
    "git status --short",
    "git diff --stat",
    "git diff --cached --stat",
    "python -m unittest discover -s tests -t .",
    "vibe lint --redaction",
    "vibe decisions lint",
    "vibe context build",
    "vibe context check",
    "vibe mcp inspect --context --health",
)


# --------------------------------------------------------------------------- #
# Policy + result models
# --------------------------------------------------------------------------- #

@dataclass
class TrustPolicy:
    project_root: str
    allowed_read_roots: List[str] = field(default_factory=list)
    allowed_write_roots: List[str] = field(default_factory=list)
    denied_paths: Tuple[str, ...] = _DENY_NAMES
    denied_globs: Tuple[str, ...] = _DENY_GLOBS
    denied_relpaths: Tuple[str, ...] = _DENY_RELPATHS
    allowed_commands: Tuple[str, ...] = _ALLOWED_COMMANDS
    secret_patterns: Tuple[str, ...] = _SECRET_GLOBS
    max_files_changed: int = 20
    max_lines_changed: int = 400
    allow_network: bool = False
    allow_cloud: bool = False


@dataclass
class TrustEvaluation:
    allowed: bool
    blocked: bool
    requires_approval: bool
    risk_level: str
    findings: List[str]
    normalized_kind: str
    normalized_target: str
    reason: str
    cloud_egress_required: bool = False
    cloud_egress_approved: bool = False
    guard_version: int = GUARD_VERSION


def default_policy(project_root: Optional[Path] = None) -> TrustPolicy:
    root = os.path.normpath(os.path.abspath(str(project_root if project_root is not None
                                               else Path.cwd())))
    return TrustPolicy(project_root=root,
                       allowed_read_roots=[root],
                       allowed_write_roots=[root])


# --------------------------------------------------------------------------- #
# Path + command checks
# --------------------------------------------------------------------------- #

def _norm(root: str, target: str) -> str:
    if os.path.isabs(target):
        return os.path.normpath(target)
    return os.path.normpath(os.path.join(root, target))


def _rel_parts(root: str, cand: str) -> List[str]:
    rel = os.path.relpath(cand, root)
    return rel.replace("\\", "/").split("/")


def is_path_allowed(path: str, project_root: str,
                    policy: TrustPolicy) -> Tuple[bool, List[str]]:
    """Deterministic path check. Returns (allowed, findings). A path is allowed only
    if it stays inside the project root and hits no denied name/glob/relpath/secret.
    Lexical (no filesystem access, no symlink resolution) — deterministic."""
    findings: List[str] = []
    root = os.path.normpath(os.path.abspath(project_root))
    cand = _norm(root, path or "")

    inside = cand == root or cand.startswith(root + os.sep)
    if not inside:
        findings.append("path escapes the project root")
        return False, findings

    parts = _rel_parts(root, cand)
    rel = "/".join(parts)
    base = parts[-1] if parts else ""

    if ".." in parts:
        findings.append("path traversal component")
        return False, findings
    for name in policy.denied_paths:
        if name in parts:
            findings.append(f"denied path segment: {name}")
            return False, findings
    for pat in policy.denied_globs:
        if fnmatch.fnmatch(base, pat):
            findings.append(f"denied file pattern: {pat}")
            return False, findings
    for rp in policy.denied_relpaths:
        if rel == rp:
            findings.append("private/local plan file")
            return False, findings
    for pat in policy.secret_patterns:
        if fnmatch.fnmatch(base, pat):
            findings.append(f"secret file pattern: {pat}")
            return False, findings
    return True, findings


def is_command_allowed(command: str, policy: TrustPolicy) -> Tuple[bool, str]:
    """Deterministic command check. Returns (allowed, reason). Only exact,
    whitespace-normalized allowlist matches pass; any shell metacharacter is
    rejected outright."""
    cmd = " ".join((command or "").split())
    if not cmd:
        return False, "empty command"
    if _SHELL_META_RE.search(command or ""):
        return False, "shell metacharacter in command"
    if cmd in policy.allowed_commands:
        return True, "allowlisted read-only command"
    return False, "command not on the allowlist"


# --------------------------------------------------------------------------- #
# Cloud egress
# --------------------------------------------------------------------------- #

def requires_cloud_egress_consent(payload: Dict) -> bool:
    kind = (payload.get("kind") or "").strip().lower()
    if kind == "cloud_call":
        return True
    md = payload.get("metadata") or {}
    return bool(md.get("sends_to_provider") or md.get("data_shared")
                or (md.get("cloud_egress") or {}).get("data_shared"))


def _cloud_meta(metadata: Optional[Dict]) -> Dict:
    md = metadata or {}
    ce = md.get("cloud_egress") if isinstance(md.get("cloud_egress"), dict) else {}
    consent = bool(ce.get("consent") or md.get("consent"))
    data_shared = ce.get("data_shared") or md.get("data_shared") or []
    if not isinstance(data_shared, list):
        data_shared = [str(data_shared)]
    return {"consent": consent, "data_shared": data_shared}


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #

def _result(kind, target, *, allowed=False, blocked=False, requires_approval=False,
            risk="blocked", findings=None, reason="",
            cloud_required=False, cloud_approved=False) -> TrustEvaluation:
    return TrustEvaluation(
        allowed=allowed, blocked=blocked, requires_approval=requires_approval,
        risk_level=risk, findings=list(findings or []), normalized_kind=kind,
        normalized_target=target or "", reason=reason,
        cloud_egress_required=cloud_required, cloud_egress_approved=cloud_approved,
    )


def evaluate_action_payload(kind: str, target: Optional[str] = None,
                            command: Optional[str] = None, scope: Optional[Dict] = None,
                            metadata: Optional[Dict] = None,
                            project_root: Optional[Path] = None,
                            policy: Optional[TrustPolicy] = None) -> TrustEvaluation:
    """Deterministically evaluate a proposed action. Pure — no I/O, no execution."""
    policy = policy or default_policy(project_root)
    root = policy.project_root
    nk = (kind or "").strip().lower()
    if nk not in ACTION_KINDS:
        nk = "unknown"

    if nk == "unknown":
        return _result("unknown", target or command or "", blocked=True, risk="blocked",
                       findings=["unknown action kind"],
                       reason="unknown action kind is blocked by default")

    if nk == "read_file":
        ok, findings = is_path_allowed(target or "", root, policy)
        if not ok:
            return _result(nk, target, blocked=True, risk="blocked", findings=findings,
                           reason="read target not permitted")
        return _result(nk, target, allowed=True, risk="low", findings=findings,
                       reason="read inside project root")

    if nk in ("write_file", "edit_file"):
        ok, findings = is_path_allowed(target or "", root, policy)
        if not ok:
            return _result(nk, target, blocked=True, risk="blocked", findings=findings,
                           reason="write target not permitted")
        risk = "medium"
        scope = scope or {}
        files = int(scope.get("files_changed") or 0)
        lines = int(scope.get("lines_changed") or 0)
        if files > policy.max_files_changed or lines > policy.max_lines_changed:
            risk = "high"
            findings.append(f"change size over limit "
                            f"(files={files}/{policy.max_files_changed}, "
                            f"lines={lines}/{policy.max_lines_changed})")
        return _result(nk, target, requires_approval=True, risk=risk, findings=findings,
                       reason="write requires human approval")

    if nk == "run_command":
        ok, reason = is_command_allowed(command or target or "", policy)
        if not ok:
            return _result(nk, command or target, blocked=True, risk="blocked",
                           findings=[reason], reason=reason)
        return _result(nk, command or target, allowed=True, risk="low",
                       findings=[reason], reason=reason)

    # cloud_call
    meta = _cloud_meta(metadata)
    findings: List[str] = []
    if not meta["consent"]:
        return _result(nk, target, blocked=True, risk="blocked",
                       findings=["cloud-egress consent missing"],
                       reason="cloud call requires explicit egress consent",
                       cloud_required=True, cloud_approved=False)
    for shared in meta["data_shared"]:
        ok, pf = is_path_allowed(str(shared), root, policy)
        if not ok:
            return _result(nk, target, blocked=True, risk="blocked",
                           findings=["cloud egress would leak: " + "; ".join(pf)],
                           reason="cloud egress includes a secret/denied path",
                           cloud_required=True, cloud_approved=True)
    risk = "medium" if policy.allow_cloud else "high"
    if not policy.allow_cloud:
        findings.append("cloud disabled by policy; needs explicit human approval")
    return _result(nk, target, requires_approval=True, risk=risk, findings=findings,
                   reason="cloud egress consented; still requires human approval",
                   cloud_required=True, cloud_approved=True)


def evaluate_action(action, project_root: Optional[Path] = None,
                    policy: Optional[TrustPolicy] = None) -> TrustEvaluation:
    """Evaluate a runtime ``Action``. Maps ``command_or_path`` to a command (for
    ``run_command``) or a target path (otherwise)."""
    kind = getattr(action, "kind", "") or ""
    cop = getattr(action, "command_or_path", "") or ""
    if kind.strip().lower() == "run_command":
        return evaluate_action_payload("run_command", command=cop,
                                       project_root=project_root, policy=policy)
    return evaluate_action_payload(kind, target=cop, project_root=project_root,
                                   policy=policy)


def summarize_evaluation(ev: TrustEvaluation) -> str:
    """One-line human-readable summary of a trust evaluation."""
    verdict = "BLOCKED" if ev.blocked else ("ALLOWED" if ev.allowed else "NEEDS-APPROVAL")
    tail = f" — {ev.reason}" if ev.reason else ""
    return f"[{verdict}] {ev.normalized_kind} {ev.normalized_target} (risk={ev.risk_level}){tail}"


# --------------------------------------------------------------------------- #
# Optional read-only integration (evaluate, never execute)
# --------------------------------------------------------------------------- #

def evaluate_pending_actions(project_root: Optional[Path] = None,
                             policy: Optional[TrustPolicy] = None) -> List[Tuple[object, TrustEvaluation]]:
    """Evaluate all ``pending`` actions in the runtime store (read-only; executes
    nothing, mutates nothing). Returns (action, evaluation) pairs. Lightweight
    integration only — the orchestrator/executor are not modified here."""
    from . import workbench_runtime as wr
    policy = policy or default_policy(project_root)
    out: List[Tuple[object, TrustEvaluation]] = []
    for task in wr.list_tasks(project_root=project_root):
        for aid in task.action_ids:
            act = wr.load_action(aid, project_root)
            if act is not None and act.status == "pending":
                out.append((act, evaluate_action(act, project_root=project_root, policy=policy)))
    return out
