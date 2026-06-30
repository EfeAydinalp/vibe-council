"""Read-only MCP server skeleton — pure read layer (v0.4, PR #57).

Implements the **backend** of the read-only MCP surface declared in
:mod:`backend.mcp_contract`: the small set of read-only handlers wired to existing
curated readers. **This PR exposes only project status + curated decisions**
(`get_project_status`, `list_decisions`, `show_decision` ↔ `vibe://status`,
`vibe://decisions`, `vibe://decisions/{id}`). The context-pack, rejected-alternatives,
release-notes, and constraints surfaces are intentionally **deferred** to later PRs.

There is **no transport here yet**: no socket, no daemon, no MCP dependency, no
model/provider/network call, and nothing is written. A spec-compliant MCP stdio
server would require the `mcp` SDK; rather than add that dependency now, this module
is the dependency-free read layer + dispatch that a future transport will wrap, and
is exercised directly by `vibe mcp inspect` and the tests. Importing this module
starts nothing.

Safety: every handler is read-only and reads ONLY curated public docs
(`docs/decisions/*.md`, `docs/context/project/STATUS.md`). It never reads `.council/`,
decision drafts, private/untracked plans, `.env`, `data/`, or arbitrary paths;
`show_decision` is path-traversal guarded to `docs/decisions/` (via
`decisions_docs.find_record`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List

from . import decisions_docs as dd
from . import mcp_contract
from . import context_pack

# The read-only surface implemented so far (a subset of the full contract).
# PR #57: status + curated decisions. PR #58: context pack + health.
ENABLED_TOOLS = (
    "get_project_status", "list_decisions", "show_decision",
    "get_context_pack", "check_context_health",
)
ENABLED_RESOURCES = (
    "vibe://status", "vibe://decisions", "vibe://decisions/{id}",
    "vibe://context/latest",
)

# Surfaces declared in the contract but deliberately not implemented yet.
DEFERRED_TOOLS = ("list_rejected_alternatives",)
DEFERRED_RESOURCES = (
    "vibe://rejected-alternatives", "vibe://release-notes", "vibe://constraints",
)


class ReadError(Exception):
    """A safe read-layer error (unknown id, traversal attempt, missing file).

    Carries a short, public-safe message and never embeds a filesystem path."""


# --------------------------------------------------------------------------- #
# Path resolution (curated public docs only)
# --------------------------------------------------------------------------- #

def _decisions_dir(root: Path) -> Path:
    return Path(root) / "docs" / "decisions"


def _status_path(root: Path) -> Path:
    return Path(root) / "docs" / "context" / "project" / "STATUS.md"


def _crit_warn(findings) -> Dict[str, int]:
    from . import redaction
    return {
        "critical": sum(1 for f in findings if f.severity == redaction.CRITICAL),
        "warning": sum(1 for f in findings if f.severity == redaction.WARNING),
    }


# --------------------------------------------------------------------------- #
# Read-only handlers
# --------------------------------------------------------------------------- #

def get_project_status(root: Path) -> str:
    """Return the curated project status snapshot (``STATUS.md``). Read-only."""
    p = _status_path(root)
    if not p.is_file():
        raise ReadError("project status not found")
    return p.read_text(encoding="utf-8-sig").strip()


def list_decisions(root: Path) -> List[Dict[str, object]]:
    """List curated decision records (``docs/decisions/*.md``). Read-only; never
    reads ``.council/`` drafts."""
    out: List[Dict[str, object]] = []
    for rec in dd.list_records(_decisions_dir(root)):
        fm = rec.frontmatter
        out.append({
            "id": str(fm.get("id") or rec.stem),
            "stem": rec.stem,
            "title": rec.title,
            "date": str(fm.get("date") or ""),
            "status": str(fm.get("status") or ""),
            "tags": list(fm.get("tags") or []),
        })
    return out


def show_decision(root: Path, identifier: str) -> Dict[str, object]:
    """Return a single curated decision by id/stem. Path-traversal guarded to
    ``docs/decisions/`` (via ``decisions_docs.find_record``); raises ``ReadError``
    for unknown ids or anything resolving outside the decisions directory."""
    path = dd.find_record(_decisions_dir(root), identifier or "")
    if path is None:
        raise ReadError("decision not found")
    rec = dd.load_record(path)
    return {
        "id": str(rec.frontmatter.get("id") or rec.stem),
        "stem": rec.stem,
        "title": rec.title,
        "text": path.read_text(encoding="utf-8", errors="replace"),
    }


def get_context_pack(root: Path) -> Dict[str, object]:
    """Build the context pack **in memory** from curated docs and return it.

    Read-only: reuses ``context_pack.build_pack`` (which returns text and does not
    write); this handler writes **nothing** — no ``.council/context/pack-latest.md``,
    no export. The pack reflects the current curated decisions + ``STATUS.md``."""
    res = context_pack.build_pack(_decisions_dir(root), _status_path(root))
    return {
        "text": res.text,
        "chars": len(res.text),
        "warnings": list(res.warnings),
        "redaction": _crit_warn(res.redaction_findings),
    }


def check_context_health(root: Path) -> Dict[str, object]:
    """Build the pack in memory and run the deterministic context check on it.

    Read-only: no file is written. Returns the score and any failed checks so an
    agent can judge whether the curated context is complete."""
    res = context_pack.build_pack(_decisions_dir(root), _status_path(root))
    chk = context_pack.check_pack(res.text)
    return {
        "ok": chk.ok,
        "passed": chk.passed,
        "total": chk.total,
        "score": round(chk.score, 3),
        "reasons": list(chk.reasons),
        "failed_checks": [c.name for c in chk.checks if not c.ok],
        "redaction": _crit_warn(chk.redaction_findings),
    }


# --------------------------------------------------------------------------- #
# Dispatch + contract validation (pure, no transport)
# --------------------------------------------------------------------------- #

_HANDLERS: Dict[str, Callable[..., object]] = {
    "get_project_status": lambda root, **kw: get_project_status(root),
    "list_decisions": lambda root, **kw: list_decisions(root),
    "show_decision": lambda root, id="", **kw: show_decision(root, id),
    "get_context_pack": lambda root, **kw: get_context_pack(root),
    "check_context_health": lambda root, **kw: check_context_health(root),
}


def is_enabled_tool(name: str) -> bool:
    return name in ENABLED_TOOLS


def dispatch(tool: str, root: Path, **kwargs) -> object:
    """Invoke a read-only handler by name. Refuses any tool not enabled in this
    PR (so deferred/forbidden tools are unreachable through the server)."""
    if tool not in ENABLED_TOOLS:
        raise ReadError(f"tool not available: {tool}")
    return _HANDLERS[tool](root, **kwargs)


def validate_server_contract() -> List[str]:
    """Return server-contract violations; empty == valid. Pure/deterministic.

    Asserts that what this server enables is a safe subset of the read-only
    contract: every enabled tool is read-only (and not forbidden), every enabled
    resource is declared, no deferred tool is enabled, and handlers match exactly
    the enabled tools."""
    errors: List[str] = []
    contract_resource_uris = {r.uri for r in mcp_contract.READ_ONLY_RESOURCES}

    for t in ENABLED_TOOLS:
        if not mcp_contract.is_read_only_tool(t):
            errors.append(f"enabled tool not in read-only contract: {t}")
        if mcp_contract.is_forbidden_tool(t):
            errors.append(f"enabled tool is forbidden: {t}")
    for r in ENABLED_RESOURCES:
        if r not in contract_resource_uris:
            errors.append(f"enabled resource not in contract: {r}")
    for t in DEFERRED_TOOLS:
        if t in ENABLED_TOOLS:
            errors.append(f"deferred tool enabled too early: {t}")
    for r in DEFERRED_RESOURCES:
        if r in ENABLED_RESOURCES:
            errors.append(f"deferred resource enabled too early: {r}")
    if set(_HANDLERS) != set(ENABLED_TOOLS):
        errors.append("handler/enabled-tool mismatch")
    return errors
