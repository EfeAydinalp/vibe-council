"""Read-only MCP contract for vibe-council (v0.4 design skeleton).

**DEFINITION ONLY — there is no MCP server here.** No socket, no process, no MCP
dependency, no model/provider/network call, no file mutation. This module declares
the *planned* read-only surface (resources + tools) and the explicitly **forbidden**
mutation/action tools, plus pure validation helpers, so the contract is testable
**before** any server exists (server implementation is deferred to a later PR).

Safety contract (v0.4): **read-only first.** The MCP surface must never promote
decisions, write/edit/delete files, run shell commands, mutate git, use a remote
approval transport, or call providers/models. It must not expose raw ``.council/``
reviews/drafts, private/untracked plans, secrets, ``.env``/``.venv``/``data/``, raw
outputs, local absolute paths, cloned repos, or ``.obsidian/``.

Stdlib-only; importing this module starts nothing.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple

MCP_SCHEME = "vibe://"
CONTRACT_VERSION = "v0.4-skeleton"


class Resource(NamedTuple):
    uri: str
    description: str
    source: str  # where the data comes from / trust note


class Tool(NamedTuple):
    name: str
    description: str


# --------------------------------------------------------------------------- #
# Planned read-only surface (definition only)
# --------------------------------------------------------------------------- #

READ_ONLY_RESOURCES: List[Resource] = [
    Resource("vibe://status", "Project status snapshot",
             "docs/context/project/STATUS.md (curated)"),
    Resource("vibe://decisions", "Curated decision index",
             "docs/decisions/*.md (curated)"),
    Resource("vibe://decisions/{id}", "A single curated decision record",
             "docs/decisions/<id>.md (curated; path-guarded)"),
    Resource("vibe://context/latest", "Latest generated context pack",
             ".council/context/pack-latest.md (generated, local-only)"),
    Resource("vibe://rejected-alternatives", "Aggregated rejected alternatives",
             "curated decisions"),
    Resource("vibe://release-notes", "Release metadata + tag-pinned note pointers",
             "docs/releases/*.md, CHANGELOG.md (curated)"),
    Resource("vibe://constraints", "Current constraints / safety boundaries",
             "context-pack constraints (curated)"),
]

READ_ONLY_TOOLS: List[Tool] = [
    Tool("list_decisions", "List curated decisions (optional tag/status filters)."),
    Tool("show_decision",
         "Return one curated decision by id (docs/decisions/ only, path-guarded)."),
    Tool("get_project_status", "Return the STATUS.md snapshot."),
    Tool("get_context_pack", "Return the latest generated context pack (local)."),
    Tool("check_context_health",
         "Return the deterministic context-check result (not an LLM eval)."),
    Tool("list_rejected_alternatives", "Return aggregated rejected alternatives."),
]

# Tools that must NEVER exist in the v0.4 read-only surface. NOTE: ``git_status``
# is intentionally forbidden here even though it is read-only elsewhere — vibe-council
# MCP v0.4 exposes no git surface at all unless explicitly scoped in a later release.
FORBIDDEN_TOOLS: List[str] = [
    "promote_decision",
    "write_file",
    "edit_file",
    "delete_file",
    "run_command",
    "git_commit",
    "git_push",
    "git_status",
    "send_email",
    "deploy",
]

READ_ONLY_TOOL_NAMES = frozenset(t.name for t in READ_ONLY_TOOLS)
FORBIDDEN_TOOL_NAMES = frozenset(FORBIDDEN_TOOLS)

# Defense-in-depth: substrings that signal a mutating/action tool. Used to catch a
# future read-only tool that is accidentally named like a write/action tool.
_MUTATION_HINTS = (
    "write", "edit", "delete", "remove", "create", "update", "promote", "commit",
    "push", "merge", "run_", "exec", "shell", "deploy", "send_", "mutate", "apply",
)


# --------------------------------------------------------------------------- #
# Validation helpers (pure, deterministic)
# --------------------------------------------------------------------------- #

def is_read_only_tool(name: str) -> bool:
    """True iff ``name`` is a declared read-only tool."""
    return name in READ_ONLY_TOOL_NAMES


def is_forbidden_tool(name: str) -> bool:
    """True iff ``name`` is on the explicit forbidden (mutation/action) list."""
    return name in FORBIDDEN_TOOL_NAMES


def _looks_mutating(name: str) -> bool:
    low = (name or "").lower()
    return any(h in low for h in _MUTATION_HINTS)


def validate_mcp_contract() -> List[str]:
    """Return a list of contract violations; an empty list means the contract is
    valid. Pure and deterministic — no I/O, no network."""
    errors: List[str] = []

    # every resource must use the vibe:// scheme
    for r in READ_ONLY_RESOURCES:
        if not r.uri.startswith(MCP_SCHEME):
            errors.append(f"resource not under {MCP_SCHEME}: {r.uri}")

    # read-only and forbidden sets must be disjoint
    overlap = READ_ONLY_TOOL_NAMES & FORBIDDEN_TOOL_NAMES
    if overlap:
        errors.append("read-only/forbidden overlap: " + ", ".join(sorted(overlap)))

    # no declared read-only tool may look like a mutation/action tool
    for t in READ_ONLY_TOOLS:
        if _looks_mutating(t.name):
            errors.append(f"read-only tool looks mutating: {t.name}")

    # the forbidden list must cover the core mutation/action + git tools
    required_forbidden = {
        "promote_decision", "write_file", "edit_file", "delete_file",
        "run_command", "git_commit", "git_push", "git_status",
    }
    missing = required_forbidden - FORBIDDEN_TOOL_NAMES
    if missing:
        errors.append("forbidden list missing: " + ", ".join(sorted(missing)))

    return errors


def contract_dict() -> Dict[str, object]:
    """Machine-readable contract (for `--json` and tests). Deterministic."""
    return {
        "version": CONTRACT_VERSION,
        "read_only": True,
        "server_implemented": False,
        "scheme": MCP_SCHEME,
        "resources": [{"uri": r.uri, "description": r.description, "source": r.source}
                      for r in READ_ONLY_RESOURCES],
        "tools": [{"name": t.name, "description": t.description}
                  for t in READ_ONLY_TOOLS],
        "forbidden_tools": list(FORBIDDEN_TOOLS),
    }


def render_contract() -> str:
    """Human-readable, deterministic rendering of the read-only contract."""
    lines = [
        f"vibe-council MCP contract ({CONTRACT_VERSION}, read-only)",
        "DESIGN SKELETON — definition only; no server is started by this command.",
        "",
        "Read-only resources:",
    ]
    for r in READ_ONLY_RESOURCES:
        lines.append(f"  {r.uri}  — {r.description}  [{r.source}]")
    lines.append("")
    lines.append("Read-only tools:")
    for t in READ_ONLY_TOOLS:
        lines.append(f"  {t.name}  — {t.description}")
    lines.append("")
    lines.append("Forbidden (never exposed) tools:")
    for n in FORBIDDEN_TOOLS:
        lines.append(f"  {n}")
    lines.append("")
    lines.append(
        "Safety: read-only first — no promote/write/edit/delete/shell/git/"
        "remote-approval/provider calls; no raw `.council/`, private/untracked plans, "
        "secrets, `.env`/`.venv`/`data/`, raw outputs, or local absolute paths exposed."
    )
    return "\n".join(lines)
