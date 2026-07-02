"""AI Council Workbench — command allowlist -> fixed argv resolver (v0.5, dry-run/
preview only, stdlib-only).

Designed in [docs/plans/v0.5-command-execution.md](../docs/plans/v0.5-command-execution.md)
and [its decision](../docs/decisions/2026-07-02-workbench-command-execution-plan.md): real
`run_command` execution stays fail-closed everywhere. This module is the **resolution
layer** a future real-execution PR would use — it maps an exact, allowlisted command
*label* (the same normalized string the deterministic trust boundary
(`backend/workbench_trust.py`) already evaluates) to a **fixed, pre-built argv list**.

**No shell, ever, and no execution here.** A label is never split/parsed into argv —
each allowlist entry hardcodes its own argv at module load time. This module never
imports `subprocess` and never runs anything; it only resolves and previews. Python
invocations use `sys.executable` (not a bare `"python"`/`"python3"` string) and `vibe`
commands resolve to `[sys.executable, "-m", "backend.cli", ...]` rather than the
OS-specific `vibe.ps1`/`.cmd`/`.sh` launcher scripts, so resolution is identical on
Windows, macOS, and Linux.

**Two independent gates, both required.** This resolver is *stricter than*, never a
substitute for, the deterministic trust boundary: a label must be on *both* this
resolver's allowlist *and* `workbench_trust`'s allowlist before the executor will
report `would_execute=True` for a dry-run preview (see `workbench_executor.py`). This
module does not consult trust itself — it only answers "do I know a safe, fixed argv
for this exact label", nothing about the target's broader safety.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RESOLVER_VERSION = 1

DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_OUTPUT_LIMIT_BYTES = 64_000

# Defense-in-depth only: argv tokens below are hardcoded, never derived from user/
# approval-controlled text, so this should never actually trip. Mirrors the class of
# character workbench_trust._SHELL_META_RE rejects in command strings.
_SHELL_META_RE = re.compile(r"(;|&&|\|\||\||>|<|`|\$\()")


class CommandResolutionError(Exception):
    """Raised by `resolve_command_label` for a label not on the resolver allowlist."""


@dataclass(frozen=True)
class CommandSpec:
    label: str
    argv: Tuple[str, ...]
    cwd_policy: str = "project_root"
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES
    description: str = ""


@dataclass
class CommandPreview:
    label: str
    argv: List[str] = field(default_factory=list)
    allowed: bool = False
    blocked: bool = True
    reason: str = ""
    timeout_seconds: int = 0
    output_limit_bytes: int = 0
    cwd: str = ""
    shell: bool = False
    would_execute: bool = False
    executed: bool = False
    resolver_version: int = RESOLVER_VERSION


def _py(*args: str) -> Tuple[str, ...]:
    """Build a fixed argv for a Python module invocation via `sys.executable` — never
    a bare `"python"`/`"python3"` string, which resolves differently per OS/venv."""
    return (sys.executable,) + tuple(args)


# Exact, fixed allowlist. Every label here MUST also be allowlisted by
# `workbench_trust.TrustPolicy.allowed_commands` — the resolver is a stricter,
# additional gate, never a looser one (see module docstring).
_ALLOWLIST: Tuple[CommandSpec, ...] = (
    CommandSpec(
        label="python -m unittest discover -s tests -t .",
        argv=_py("-m", "unittest", "discover", "-s", "tests", "-t", "."),
        description="run the stdlib unittest suite",
    ),
    CommandSpec(
        label="vibe lint --redaction",
        argv=_py("-m", "backend.cli", "lint", "--redaction"),
        description="redaction guard over tracked public docs",
    ),
    CommandSpec(
        label="vibe decisions lint",
        argv=_py("-m", "backend.cli", "decisions", "lint"),
        description="lint curated decision records",
    ),
    CommandSpec(
        label="vibe context build",
        argv=_py("-m", "backend.cli", "context", "build"),
        description="build the local context pack",
    ),
    CommandSpec(
        label="vibe context check",
        argv=_py("-m", "backend.cli", "context", "check"),
        description="deterministic context-pack quality check",
    ),
    CommandSpec(
        label="vibe mcp inspect --context --health",
        argv=_py("-m", "backend.cli", "mcp", "inspect", "--context", "--health"),
        description="read-only MCP context+health inspect",
    ),
    CommandSpec(
        label="git status --short",
        argv=("git", "status", "--short"),
        description="short git status (read-only; already trust-allowlisted)",
    ),
)

_BY_LABEL: Dict[str, CommandSpec] = {spec.label: spec for spec in _ALLOWLIST}


def _normalize_label(label: Optional[str]) -> str:
    """Whitespace-collapse only (mirrors `workbench_trust.is_command_allowed`) — no
    case-folding. A label differing only in case is treated as unknown, not matched;
    only exact, whitespace-normalized labels resolve."""
    return " ".join((label or "").split())


def list_command_allowlist() -> List[CommandSpec]:
    """The full, fixed resolver allowlist (a copy; callers can't mutate the module
    table)."""
    return list(_ALLOWLIST)


def is_command_label_allowed(label: str) -> bool:
    """True only for an exact (whitespace-normalized) match against the resolver
    allowlist — never a prefix/substring/case-insensitive match."""
    return _normalize_label(label) in _BY_LABEL


def resolve_command_label(label: str) -> CommandSpec:
    """Resolve an exact allowlisted label to its fixed `CommandSpec`. Raises
    `CommandResolutionError` for any label not on the resolver allowlist — never
    guesses, never falls back to parsing the label into argv."""
    spec = _BY_LABEL.get(_normalize_label(label))
    if spec is None:
        raise CommandResolutionError(
            f"command label not on the resolver allowlist: {label!r}")
    return spec


def preview_command(label: str, project_root: Optional[Path] = None) -> CommandPreview:
    """Pure, read-only preview of what *would* run for `label` — resolves to a fixed
    argv and describes timeout/output cap/cwd. Never imports or calls `subprocess`;
    never executes anything, regardless of whether `label` resolves."""
    root = str(Path(project_root) if project_root is not None else Path.cwd())
    if not is_command_label_allowed(label):
        return CommandPreview(
            label=label or "", allowed=False, blocked=True,
            reason="command label not on the resolver allowlist", cwd=root, shell=False,
            would_execute=False, executed=False)
    spec = resolve_command_label(label)
    for token in spec.argv:
        if _SHELL_META_RE.search(token):
            # Should never happen (argv is hardcoded) — fail closed if it ever does.
            return CommandPreview(
                label=spec.label, argv=list(spec.argv), allowed=False, blocked=True,
                reason="resolved argv contains a shell metacharacter (internal error)",
                cwd=root, shell=False, would_execute=False, executed=False)
    return CommandPreview(
        label=spec.label, argv=list(spec.argv), allowed=True, blocked=False,
        reason="resolved to a fixed, allowlisted argv (preview only — not executed)",
        timeout_seconds=spec.timeout_seconds, output_limit_bytes=spec.output_limit_bytes,
        cwd=root, shell=False, would_execute=True, executed=False)


def summarize_command_preview(preview: CommandPreview) -> str:
    """One-line, safe summary — argv tokens are fixed/non-secret by construction, so
    this is safe to log/display (unlike file payload content)."""
    verdict = ("WOULD-EXECUTE" if preview.would_execute
               else ("BLOCKED" if preview.blocked else "NO-OP"))
    return (f"[{verdict}] {preview.label} argv={preview.argv} "
            f"timeout={preview.timeout_seconds}s cap={preview.output_limit_bytes}B "
            f"shell={preview.shell} - {preview.reason}")
