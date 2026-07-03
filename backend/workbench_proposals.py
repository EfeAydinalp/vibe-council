"""AI Council Workbench — agent proposal schema + validation (v0.6, stdlib-only).

The first slice of the v0.6 agent-to-Workbench bridge
([docs/fable/05-v0.6-agent-bridge.md](../docs/fable/05-v0.6-agent-bridge.md)): the
**typed external contract** an agent authors and a (future) importer validates. This
module is **validation only** — it defines proposal schema version 1
([docs/fable/06-proposal-schema.md](../docs/fable/06-proposal-schema.md)) and checks a
candidate proposal against it, deterministically and fail-closed.

**Pure and side-effect-free.** No store writes, no runtime task/approval/action
creation, no payload artifact creation, no id minting, no `subprocess` import, no
network, no panel/CLI integration, no execution. The importer (a later PR) consumes
`validate_proposal`'s result; nothing here authorizes anything — the deterministic
trust boundary (:mod:`backend.workbench_trust`) is still re-run at approval display
and again at execution time regardless of validation outcome.

Schema v1 is **strict**: unknown keys at any level are rejected (not silently
dropped), and every server-minted field (ids, hashes, statuses, verdicts) is a hard
error if present — asserting identity or a verdict from the client side is an
authorship red flag, not a field to ignore. `run_command` proposals carry an **exact
allowlist label only** (validated against *both* the resolver allowlist and the trust
allowlist — the same two-gate rule the executor enforces); freeform command strings,
argv, env, cwd, timeout, and shell never appear in a valid proposal at all.

Dedup contract (for the future importer, stated here so the schema locks it):
``proposal_id`` is the idempotency key — the first import creates records, a repeat
returns the existing ids and creates nothing. This module only validates the id's
shape (strict charset, no sanitization — sanitizing distinct agent ids could collide
dedup keys). **The importer must decide dedup scoping explicitly** (e.g. keying on
``proposal_id`` alone vs. ``agent.name`` + ``proposal_id``) — two different agents
reusing the same id is a collision case this layer detects nothing about.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import workbench_trust as wt
from . import workbench_commands as wc

PROPOSAL_SCHEMA_VERSION = 1

ALLOWED_PROPOSAL_KINDS = ("write_file", "edit_file", "run_command")
_FILE_KINDS = ("write_file", "edit_file")

# Proposal-layer size caps. These mirror the executor's bounds
# (workbench_executor.MAX_WRITE_BYTES / MAX_EDIT_BYTES, both 100 KB) so an agent gets
# a clear early rejection instead of a blocked execution later — but they are
# deliberately defined locally to keep this module free of executor imports, and the
# EXECUTOR REMAINS THE FINAL AUTHORITY at execution time regardless of what passed
# validation here.
MAX_CONTENT_BYTES = 100_000     # write_file 'content'
MAX_EDIT_TEXT_BYTES = 100_000   # edit_file 'old_text' / 'new_text'

MAX_TITLE_CHARS = 2000
MAX_SUMMARY_CHARS = 4000
MAX_AGENT_FIELD_CHARS = 200
MAX_PROPOSAL_ID_CHARS = 120

# Server-minted / execution-parameter fields: presence ANYWHERE in a proposal is a
# hard reject (never silently dropped). Ids/hashes/statuses/verdicts are minted by
# the server; argv/env/cwd/timeout/shell are resolver-owned execution parameters the
# client may never supply; 'command' (freeform) and 'requested_action' (the internal
# kind:target convention) must never be authored externally.
_FORBIDDEN_KEYS = frozenset((
    "payload_hash", "action_id", "approval_id", "task_id", "audit_id", "decision_id",
    "status", "risk", "risk_level", "verdict", "blocked", "findings",
    "argv", "env", "cwd", "timeout", "timeout_seconds", "shell",
    "command", "requested_action",
))

_ALLOWED_TOP_KEYS = frozenset((
    "proposal_schema", "proposal_id", "agent", "title", "summary", "action"))
_ALLOWED_AGENT_KEYS = frozenset(("name", "role", "session"))
_ALLOWED_ACTION_KEYS = frozenset(("kind", "target", "command_label", "payload", "scope"))
_ALLOWED_WRITE_PAYLOAD_KEYS = frozenset(("content", "overwrite"))
_ALLOWED_EDIT_PAYLOAD_KEYS = frozenset(("old_text", "new_text", "max_replacements"))
_ALLOWED_SCOPE_KEYS = frozenset(("files_changed", "lines_changed"))

_PROPOSAL_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_WIN_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class ProposalError(Exception):
    """Programmer misuse of the proposal layer (e.g. summarizing a None validation).
    Ordinary invalid *proposals* never raise — they return ``ok=False`` errors."""


# --------------------------------------------------------------------------- #
# Data models (a *validated* proposal — deliberately no fields for ids, hashes,
# statuses, or verdicts: those are server-minted and cannot exist here)
# --------------------------------------------------------------------------- #

@dataclass
class ProposalAgent:
    name: str
    role: str = ""       # display metadata only; deliberately NOT a hard enum
    session: str = ""    # opaque display/audit label; never a secret


@dataclass
class ProposalAction:
    kind: str
    target: str = ""            # file kinds only
    command_label: str = ""     # run_command only (exact allowlist label)
    payload: Optional[Dict] = None
    scope: Optional[Dict] = None


@dataclass
class Proposal:
    proposal_schema: int
    proposal_id: str
    agent: ProposalAgent
    title: str
    summary: str
    action: ProposalAction


@dataclass
class ProposalValidation:
    ok: bool
    errors: List[str] = field(default_factory=list)
    proposal: Optional[Proposal] = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _clean(s: object, cap: int) -> str:
    """Control-char strip + whitespace collapse + cap (mirrors the runtime store's
    field cleaning). Never raises."""
    if not isinstance(s, str):
        return ""
    out = _CONTROL_RE.sub("", s)
    out = " ".join(out.split())
    return out[:cap]


def _reject_forbidden_and_unknown(obj: Dict, allowed: frozenset, level: str,
                                  errors: List[str]) -> None:
    """Strict schema v1: at every level, a server-minted/forbidden key is a hard
    reject with its own message, and any other unknown key is rejected too (never
    silently dropped)."""
    for key in obj:
        if not isinstance(key, str):
            errors.append(f"{level}: non-string key is not allowed")
            continue
        if key in _FORBIDDEN_KEYS:
            errors.append(
                f"{level}: server-minted or forbidden field '{key}' must not appear "
                "in a proposal")
        elif key not in allowed:
            errors.append(f"{level}: unknown key '{key}' (strict schema v1 rejects "
                          "unrecognized fields)")


def _is_absolute_target(target: str) -> bool:
    """True for POSIX absolute, Windows drive-letter absolute, or UNC targets —
    checked lexically so a Windows-style absolute path is rejected even on POSIX."""
    return (target.startswith("/") or target.startswith("\\")
            or bool(_WIN_DRIVE_RE.match(target)))


def _has_traversal(target: str) -> bool:
    parts = target.replace("\\", "/").split("/")
    return ".." in parts


# --------------------------------------------------------------------------- #
# JSON helper (pure; no file I/O)
# --------------------------------------------------------------------------- #

def parse_proposal_json(text: object) -> Tuple[Optional[Dict], Optional[str]]:
    """Parse a proposal JSON string. Returns ``(dict, None)`` on success or
    ``(None, error)`` on failure. Rejects malformed JSON and any top-level value
    that is not a single JSON object. Pure — no file I/O."""
    if not isinstance(text, str) or not text.strip():
        return None, "proposal JSON must be a non-empty string"
    try:
        data = json.loads(text)
    except ValueError as e:
        return None, f"malformed JSON: {e}"
    if not isinstance(data, dict):
        return None, "proposal JSON must be a single object (not a list/scalar)"
    return data, None


# --------------------------------------------------------------------------- #
# Section validators (each appends to `errors`; validation never stops early)
# --------------------------------------------------------------------------- #

def _validate_envelope(data: Dict, errors: List[str]) -> None:
    _reject_forbidden_and_unknown(data, _ALLOWED_TOP_KEYS, "proposal", errors)

    version = data.get("proposal_schema")
    if not isinstance(version, int) or isinstance(version, bool) \
            or version != PROPOSAL_SCHEMA_VERSION:
        errors.append("proposal_schema is required and must be exactly "
                      f"{PROPOSAL_SCHEMA_VERSION} (integer)")

    pid = data.get("proposal_id")
    if not isinstance(pid, str) or not pid:
        errors.append("proposal_id is required (non-empty string; it is the dedup/"
                      "idempotency key)")
    elif len(pid) > MAX_PROPOSAL_ID_CHARS:
        errors.append(f"proposal_id exceeds {MAX_PROPOSAL_ID_CHARS} characters")
    elif not _PROPOSAL_ID_RE.match(pid):
        errors.append("proposal_id may only contain [A-Za-z0-9._-] (rejected, not "
                      "sanitized — sanitizing could collide dedup keys)")

    for key in ("agent", "action"):
        if key not in data:
            errors.append(f"'{key}' is required")

    for key in ("title", "summary"):
        val = data.get(key)
        if not isinstance(val, str) or not _clean(val, 10_000):
            errors.append(f"'{key}' is required (non-empty string)")


def _validate_agent(data: Dict, errors: List[str]) -> Optional[ProposalAgent]:
    agent = data.get("agent")
    if agent is None:
        return None  # missing-key error already recorded by the envelope check
    if not isinstance(agent, dict):
        errors.append("'agent' must be an object")
        return None
    _reject_forbidden_and_unknown(agent, _ALLOWED_AGENT_KEYS, "agent", errors)
    name = _clean(agent.get("name"), MAX_AGENT_FIELD_CHARS)
    if not name:
        errors.append("agent.name is required (non-empty string)")
        return None
    return ProposalAgent(
        name=name,
        role=_clean(agent.get("role"), MAX_AGENT_FIELD_CHARS),
        session=_clean(agent.get("session"), MAX_AGENT_FIELD_CHARS),
    )


def _validate_scope(scope: object, errors: List[str]) -> Optional[Dict]:
    if scope is None:
        return None
    if not isinstance(scope, dict):
        errors.append("action.scope must be an object when present")
        return None
    _reject_forbidden_and_unknown(scope, _ALLOWED_SCOPE_KEYS, "action.scope", errors)
    out: Dict = {}
    for key in _ALLOWED_SCOPE_KEYS:
        if key in scope:
            val = scope[key]
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                errors.append(f"action.scope.{key} must be a non-negative integer")
            else:
                out[key] = val
    return out or None


def _validate_file_target(target: object, policy: wt.TrustPolicy,
                          errors: List[str]) -> str:
    if not isinstance(target, str) or not target.strip():
        errors.append("action.target is required for file actions (non-empty "
                      "relative path)")
        return ""
    target = target.strip()
    if _is_absolute_target(target):
        errors.append("action.target must be a relative path inside the project "
                      "root (absolute paths are rejected, including Windows-style)")
        return ""
    if _has_traversal(target):
        errors.append("action.target must not contain '..' path traversal")
        return ""
    # Deterministic, lexical trust path check (deny names/globs/relpaths/secrets).
    # This is an EARLY, clearer rejection — the trust boundary still re-runs at
    # approval display and at execution time regardless.
    ok, findings = wt.is_path_allowed(target, policy.project_root, policy)
    if not ok:
        reason = findings[0] if findings else "denied path"
        errors.append(f"action.target is not permitted ({reason})")
        return ""
    return target


def _validate_write_payload(payload: Dict, errors: List[str]) -> Optional[Dict]:
    _reject_forbidden_and_unknown(payload, _ALLOWED_WRITE_PAYLOAD_KEYS,
                                  "write_file payload", errors)
    out: Dict = {}
    content = payload.get("content")
    if not isinstance(content, str):
        errors.append("write_file payload requires string 'content'")
    elif "\x00" in content:
        errors.append("write_file payload 'content' contains NUL bytes (binary "
                      "content is not allowed)")
    elif len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        errors.append(f"write_file payload 'content' exceeds {MAX_CONTENT_BYTES} "
                      "bytes (early cap; the executor enforces the same bound)")
    else:
        out["content"] = content
    overwrite = payload.get("overwrite", False)
    if not isinstance(overwrite, bool):
        errors.append("write_file payload 'overwrite' must be a boolean when present")
    else:
        out["overwrite"] = overwrite
    return out


def _validate_edit_payload(payload: Dict, errors: List[str]) -> Optional[Dict]:
    _reject_forbidden_and_unknown(payload, _ALLOWED_EDIT_PAYLOAD_KEYS,
                                  "edit_file payload", errors)
    out: Dict = {}
    old = payload.get("old_text")
    new = payload.get("new_text")
    if not isinstance(old, str) or old == "":
        errors.append("edit_file payload requires non-empty string 'old_text'")
    elif "\x00" in old:
        errors.append("edit_file payload 'old_text' contains NUL bytes (binary "
                      "content is not allowed)")
    elif len(old.encode("utf-8")) > MAX_EDIT_TEXT_BYTES:
        errors.append(f"edit_file payload 'old_text' exceeds {MAX_EDIT_TEXT_BYTES} "
                      "bytes (early cap; the executor enforces its own bounds)")
    else:
        out["old_text"] = old
    if not isinstance(new, str):
        errors.append("edit_file payload requires string 'new_text'")
    elif "\x00" in new:
        errors.append("edit_file payload 'new_text' contains NUL bytes (binary "
                      "content is not allowed)")
    elif len(new.encode("utf-8")) > MAX_EDIT_TEXT_BYTES:
        errors.append(f"edit_file payload 'new_text' exceeds {MAX_EDIT_TEXT_BYTES} "
                      "bytes (early cap; the executor enforces its own bounds)")
    else:
        out["new_text"] = new
    max_repl = payload.get("max_replacements", 1)
    if isinstance(max_repl, bool) or not isinstance(max_repl, int) or max_repl < 1:
        errors.append("edit_file payload 'max_replacements' must be an integer >= 1 "
                      "when present")
    else:
        out["max_replacements"] = max_repl
    return out


def _validate_command_label(label: object, policy: wt.TrustPolicy,
                            errors: List[str]) -> str:
    if not isinstance(label, str) or not label.strip():
        errors.append("action.command_label is required for run_command (exact "
                      "allowlist label)")
        return ""
    normalized = " ".join(label.split())  # whitespace-collapse only; NO case-folding
    # Two independent gates, both required (the same rule the executor enforces):
    # the resolver must know a fixed argv for the exact label, AND the trust
    # boundary must allowlist it. Neither gate executes anything.
    resolver_ok = wc.is_command_label_allowed(normalized)
    trust_ok, trust_reason = wt.is_command_allowed(normalized, policy)
    if not resolver_ok or not trust_ok:
        shown = normalized[:80]
        reason = trust_reason if not trust_ok else "not on the resolver allowlist"
        errors.append(f"action.command_label {shown!r} is not an exact allowlisted "
                      f"command label ({reason}); freeform commands are never "
                      "accepted")
        return ""
    return normalized


def _validate_action(data: Dict, policy: wt.TrustPolicy,
                     errors: List[str]) -> Optional[ProposalAction]:
    action = data.get("action")
    if action is None:
        return None  # missing-key error already recorded by the envelope check
    if not isinstance(action, dict):
        errors.append("'action' must be an object (exactly one action per proposal)")
        return None
    _reject_forbidden_and_unknown(action, _ALLOWED_ACTION_KEYS, "action", errors)

    kind = action.get("kind")
    kind = kind.strip().lower() if isinstance(kind, str) else ""
    if kind not in ALLOWED_PROPOSAL_KINDS:
        errors.append(
            "action.kind must be one of "
            f"{', '.join(ALLOWED_PROPOSAL_KINDS)} (got {str(action.get('kind'))[:40]!r}; "
            "cloud_call/read_file/unknown kinds are not agent-proposable)")
        return None

    scope = _validate_scope(action.get("scope"), errors)

    if kind == "run_command":
        if "target" in action:
            errors.append("run_command takes 'command_label' only — 'target' is not "
                          "valid for it")
        if "payload" in action:
            errors.append("run_command never carries a payload (the resolver "
                          "provides the fixed argv server-side)")
        label = _validate_command_label(action.get("command_label"), policy, errors)
        return ProposalAction(kind=kind, command_label=label, scope=scope)

    # file kinds
    if "command_label" in action:
        errors.append("'command_label' is only valid for run_command actions")
    target = _validate_file_target(action.get("target"), policy, errors)
    payload = action.get("payload")
    if not isinstance(payload, dict):
        errors.append(f"{kind} requires a 'payload' object")
        return ProposalAction(kind=kind, target=target, scope=scope)
    if kind == "write_file":
        validated = _validate_write_payload(payload, errors)
    else:
        validated = _validate_edit_payload(payload, errors)
    return ProposalAction(kind=kind, target=target, payload=validated, scope=scope)


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #

def validate_proposal(data: object, project_root: Optional[Path] = None,
                      policy: Optional[wt.TrustPolicy] = None) -> ProposalValidation:
    """Validate a candidate proposal dict against schema v1. Pure and fail-closed:
    collects **all** errors (an agent can fix everything in one pass), writes
    nothing, mints nothing, executes nothing. ``ok=True`` only when every check
    passes; the returned :class:`Proposal` then carries the cleaned, typed values
    (with defaults applied) for a future importer to consume."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ProposalValidation(
            ok=False, errors=["proposal must be a JSON object (dict)"])

    pol = policy or wt.default_policy(project_root)
    _validate_envelope(data, errors)
    agent = _validate_agent(data, errors)
    action = _validate_action(data, pol, errors)

    if errors or agent is None or action is None:
        return ProposalValidation(ok=False, errors=errors or
                                  ["proposal failed validation"])

    return ProposalValidation(ok=True, proposal=Proposal(
        proposal_schema=PROPOSAL_SCHEMA_VERSION,
        proposal_id=data["proposal_id"],
        agent=agent,
        title=_clean(data["title"], MAX_TITLE_CHARS),
        summary=_clean(data["summary"], MAX_SUMMARY_CHARS),
        action=action,
    ))


def summarize_validation(validation: Optional[ProposalValidation]) -> str:
    """One-line, log-safe summary — never includes payload content."""
    if validation is None:
        raise ProposalError("summarize_validation requires a ProposalValidation")
    if validation.ok and validation.proposal is not None:
        p = validation.proposal
        what = p.action.command_label if p.action.kind == "run_command" else p.action.target
        return (f"[valid] proposal {p.proposal_id} agent={p.agent.name} "
                f"kind={p.action.kind} -> {what}")
    first = validation.errors[0] if validation.errors else "invalid"
    return f"[invalid] {len(validation.errors)} error(s); first: {first}"
