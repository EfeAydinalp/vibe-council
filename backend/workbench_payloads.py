"""AI Council Workbench — execution payload artifact store (v0.5, stdlib-only).

Bridges the gap left by the bounded file executor (PR #74): the runtime ``Action``
model has no durable place to carry ``write_file``/``edit_file`` content, so a caller
had to pass ``payload=`` explicitly, every time, from outside the runtime store. This
module stores that payload as its own **local, gitignored** runtime artifact —
``.council/runtime/payloads/<action_id>.json`` — keyed by ``action_id``, never on the
``Action`` record itself, so ordinary ``Action`` reads (panel list, index, status
summary) stay small and payload-free. See ``docs/plans/v0.5-payload-bridge.md``.

**Store + verification only.** No execution, no panel, no CLI, no provider/model/
network. The executor (``backend/workbench_executor.py``) consults this module to load
and verify a payload artifact before real execution; the deterministic trust boundary
(``backend/workbench_trust.py``) is still re-run at execution time — a verified payload
hash is an *additional* check, never a replacement for that guard.

Security model:

- The artifact is **write-once**: ``save_payload_artifact`` refuses to overwrite an
  existing artifact unless the caller explicitly opts in (``overwrite=True``).
- ``payload_hash`` is a deterministic sha256 over ``{kind, target, payload}`` only —
  never timestamps or other mutable metadata — computed when the artifact is built and
  re-verified before every real execution. A mismatch means the artifact was rewritten
  after it was created (or corrupted) and must fail closed.
- Raw file content is never included in log-safe summaries (``redacted_summary``,
  ``summarize_payload_artifact``) — only byte/line counts, flags, and a short hash
  prefix.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict, fields as dc_fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import workbench_runtime as wr

SCHEMA_VERSION = 1

PAYLOAD_KINDS = ("write_file", "edit_file")

_PAYLOADS_SUBDIR = "payloads"
_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")


class PayloadError(Exception):
    """Raised on payload store misuse (e.g. overwrite without explicit opt-in)."""


@dataclass
class PayloadArtifact:
    action_id: str
    task_id: str = ""
    approval_id: Optional[str] = None
    kind: str = ""
    target: str = ""
    payload: Dict = field(default_factory=dict)
    payload_hash: str = ""
    approved_scope_hash: Optional[str] = None
    created_at: str = ""
    content_bytes: int = 0
    redacted_summary: Dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    locked: bool = False


@dataclass
class PayloadVerification:
    ok: bool
    action_id: str = ""
    reason: str = ""
    findings: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _now(on: Optional[str] = None) -> str:
    return on or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_id(s: object) -> str:
    """Reduce an id to a safe filename stem: only ``[A-Za-z0-9._-]``, no path
    separators or traversal. Never raises."""
    out = _ID_RE.sub("-", str(s or "")).strip("-.")
    return out[:120] or "id"


def _canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def canonical_payload_hash(kind: str, target: str, payload: Optional[Dict]) -> str:
    """Deterministic sha256 over ``{kind, target, payload}`` only — no timestamps,
    no other metadata. Stable across key order (canonical JSON: sorted keys, compact
    separators, UTF-8)."""
    body = {"kind": (kind or "").strip().lower(), "target": target or "",
            "payload": payload or {}}
    return "sha256:" + hashlib.sha256(_canonical_json(body)).hexdigest()


def _scope_hash(scope: Optional[Dict]) -> Optional[str]:
    if not scope:
        return None
    return "sha256:" + hashlib.sha256(_canonical_json(scope)).hexdigest()


def _redacted_summary(kind: str, payload: Optional[Dict]) -> Dict:
    """Safe, content-free summary of a payload — never raw content."""
    payload = payload or {}
    out: Dict = {"kind": kind}
    if kind == "write_file":
        content = payload.get("content")
        out["content_bytes"] = len(content.encode("utf-8")) if isinstance(content, str) else 0
        out["overwrite"] = bool(payload.get("overwrite", False))
    elif kind == "edit_file":
        old = payload.get("old_text")
        new = payload.get("new_text")
        out["old_bytes"] = len(old.encode("utf-8")) if isinstance(old, str) else 0
        out["new_bytes"] = len(new.encode("utf-8")) if isinstance(new, str) else 0
        out["max_replacements"] = int(payload.get("max_replacements", 1) or 1)
    return out


# --------------------------------------------------------------------------- #
# Store paths + containment
# --------------------------------------------------------------------------- #

def payloads_root(project_root: Optional[Path] = None) -> Path:
    return wr.runtime_root(project_root) / _PAYLOADS_SUBDIR


def ensure_payloads_root(project_root: Optional[Path] = None) -> Path:
    root = payloads_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _entry_path(project_root: Optional[Path], action_id: str) -> Path:
    """Resolve ``<runtime>/payloads/<safe-id>.json`` and hard-guard containment — the
    result must live directly inside ``payloads/`` (never escaping the runtime root)."""
    root = ensure_payloads_root(project_root).resolve()
    p = root / (_safe_id(action_id) + ".json")
    rp = p.resolve()
    if rp.parent != root:
        raise PayloadError("unsafe payload path (containment violation)")
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
# Build / save / load
# --------------------------------------------------------------------------- #

def build_payload_artifact(action, payload: Optional[Dict], task=None, approval=None,
                           on: Optional[str] = None) -> PayloadArtifact:
    """Pure — build (never save) a :class:`PayloadArtifact` for a runtime ``Action`` +
    an explicit payload dict. The hash locks ``kind``/``target``/``payload`` as of this
    call; ``created_at`` and the redacted summary are metadata only and are excluded
    from the hash."""
    if action is None:
        raise PayloadError("action is required to build a payload artifact")
    kind = (getattr(action, "kind", "") or "").strip().lower()
    target = getattr(action, "command_or_path", "") or ""
    payload = payload or {}
    phash = canonical_payload_hash(kind, target, payload)
    summary = _redacted_summary(kind, payload)
    content_bytes = summary.get("content_bytes", summary.get("new_bytes", 0))
    scope = getattr(approval, "scope", None) if approval is not None else None
    task_id = getattr(action, "task_id", "") or (getattr(task, "id", "") if task else "")
    approval_id = (getattr(action, "approval_id", None)
                   or (getattr(approval, "id", None) if approval else None))
    return PayloadArtifact(
        action_id=action.id, task_id=task_id, approval_id=approval_id, kind=kind,
        target=target, payload=payload, payload_hash=phash,
        approved_scope_hash=_scope_hash(scope), created_at=_now(on),
        content_bytes=content_bytes, redacted_summary=summary,
        schema_version=SCHEMA_VERSION, locked=False,
    )


def save_payload_artifact(artifact: PayloadArtifact, project_root: Optional[Path] = None,
                          *, overwrite: bool = False) -> PayloadArtifact:
    """Write-once by default: refuses to replace an existing artifact for the same
    ``action_id`` unless ``overwrite=True`` is passed explicitly. Atomic write."""
    if artifact is None or not getattr(artifact, "action_id", None):
        raise PayloadError("artifact with an action_id is required")
    path = _entry_path(project_root, artifact.action_id)
    if path.is_file() and not overwrite:
        raise PayloadError(
            f"payload artifact already exists for action '{artifact.action_id}' "
            "(write-once; pass overwrite=True to replace)")
    _dump(path, asdict(artifact))
    return artifact


def load_payload_artifact(action_id: str,
                          project_root: Optional[Path] = None) -> Optional[PayloadArtifact]:
    try:
        path = _entry_path(project_root, action_id)
    except PayloadError:
        return None
    data = _load_json(path)
    if not data:
        return None
    known = {f.name for f in dc_fields(PayloadArtifact)}
    kwargs = {k: v for k, v in data.items() if k in known}
    try:
        return PayloadArtifact(**kwargs)
    except TypeError:
        return None


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #

def verify_payload_artifact(artifact: Optional[PayloadArtifact]) -> PayloadVerification:
    """Self-consistency check only: does the artifact's own ``payload_hash`` match a
    fresh hash of its current ``{kind, target, payload}``? Detects a payload artifact
    that was rewritten on disk after it was created."""
    if artifact is None:
        return PayloadVerification(ok=False, reason="payload artifact not found")
    expected = canonical_payload_hash(artifact.kind, artifact.target, artifact.payload)
    if expected != artifact.payload_hash:
        return PayloadVerification(
            ok=False, action_id=artifact.action_id,
            reason="payload hash mismatch (content modified after creation)",
            findings=["payload_hash mismatch"])
    return PayloadVerification(ok=True, action_id=artifact.action_id,
                               reason="payload hash verified")


def verify_payload_against_action(artifact: Optional[PayloadArtifact], action,
                                  approval=None, task=None) -> PayloadVerification:
    """Full cross-check used by the executor before real execution: hash
    self-consistency (``verify_payload_artifact``) **and** agreement with the live
    ``Action``/``ApprovalRequest``/``Task`` records — kind, target, and linked ids.
    This is additional to (never a replacement for) the deterministic trust re-check."""
    if artifact is None:
        return PayloadVerification(ok=False, reason="payload artifact not found")
    if action is None:
        return PayloadVerification(ok=False, action_id=artifact.action_id,
                                   reason="action not found")

    hv = verify_payload_artifact(artifact)
    if not hv.ok:
        return hv

    findings: List[str] = []
    akind = (getattr(action, "kind", "") or "").strip().lower()
    if artifact.kind != akind:
        findings.append(f"kind mismatch (artifact={artifact.kind!r} action={akind!r})")
    atarget = getattr(action, "command_or_path", "") or ""
    if artifact.target != atarget:
        findings.append(f"target mismatch (artifact={artifact.target!r} action={atarget!r})")
    if artifact.action_id != getattr(action, "id", None):
        findings.append("action_id mismatch")

    a_task_id = getattr(action, "task_id", "") or ""
    if artifact.task_id and a_task_id and artifact.task_id != a_task_id:
        findings.append("task_id mismatch (action)")
    if task is not None and artifact.task_id and artifact.task_id != getattr(task, "id", ""):
        findings.append("task_id mismatch (task record)")

    a_approval_id = getattr(action, "approval_id", None)
    if artifact.approval_id and a_approval_id and artifact.approval_id != a_approval_id:
        findings.append("approval_id mismatch (action)")
    if approval is not None and artifact.approval_id and \
            artifact.approval_id != getattr(approval, "id", None):
        findings.append("approval_id mismatch (approval record)")

    if findings:
        return PayloadVerification(
            ok=False, action_id=artifact.action_id,
            reason="payload does not match the linked action/approval/task",
            findings=findings)
    return PayloadVerification(ok=True, action_id=artifact.action_id,
                               reason="payload verified against action/approval/task")


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #

def summarize_payload_artifact(artifact: Optional[PayloadArtifact]) -> str:
    """One-line, content-free summary — safe for logs/panel display. Never includes
    raw ``content``/``old_text``/``new_text``."""
    if artifact is None:
        return "[payload] none"
    base = os.path.basename(artifact.target) if artifact.target else "?"
    bits = [f"kind={artifact.kind}", f"target={base}"]
    summary = artifact.redacted_summary or {}
    if artifact.kind == "write_file":
        bits.append(f"bytes={summary.get('content_bytes', artifact.content_bytes)}")
        bits.append(f"overwrite={summary.get('overwrite', False)}")
    elif artifact.kind == "edit_file":
        bits.append(f"new_bytes={summary.get('new_bytes', artifact.content_bytes)}")
        bits.append(f"max_replacements={summary.get('max_replacements', 1)}")
    hp = (artifact.payload_hash or "")[:15]
    bits.append(f"hash={hp}...")
    return "[payload] " + " ".join(bits)
