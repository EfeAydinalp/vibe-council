"""Read-only validator for the tighten-only preference schema v1 (v0.8.2 PR 8).

This module *validates and reports* — it never applies anything. Per
`docs/fable/v0.8.x-architecture-plan.md` §3 Q3/Q4 and `docs/fable/preference-schema-v1.md`,
the machine-readable preferences live in a single optional fenced ```json block inside
`docs/context/project/PREFERENCES.md`. The block is **untrusted input**: it is size-bounded,
parsed with stdlib `json` only, key-allowlisted, strictly type/value-checked, and any anomaly
**fails closed to "invalid, ignored"** (a warning + no parsed result).

Design contract (enforced by tests):
- The **public API returns findings only** — never the parsed values / settings. Parsing
  helpers are private by naming convention (`_extract_json_blocks`, `_validate_object`).
- It is **read-only**: it reads exactly one file (`PREFERENCES.md`) inside the project root,
  writes nothing, creates no `.council/`, and never reads a `.council/profile.*` store.
- It is **advisory**: nothing here changes `vibe project doctor`'s READY/NOT-READY result,
  and no parsed value influences any command's behavior (that is deferred to v0.9.x).

Stdlib-only (`json`, `re`, `pathlib`). No `jsonschema`/`pydantic`/YAML/TOML dependency.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, NamedTuple

# The one file this validator ever reads (relative to the project root).
PREFERENCES_REL = "docs/context/project/PREFERENCES.md"

# Schema v1 surface (mirrors docs/fable/preference-schema-v1.md).
SCHEMA_VERSION = 1
ALLOWED_KEYS = ("schema", "default_review_preset", "extra_sensitive_paths",
                "never_stage_extra", "require_usage_flag")
# The review-preset floor. "premium" is deliberately absent: the schema is tighten-only and
# must not be able to name a paid/weaker review floor (naming premium is a loosening attempt).
PRESET_ENUM = ("cheap", "balanced", "full")
PATH_ARRAY_KEYS = ("extra_sensitive_paths", "never_stage_extra")
MAX_BLOCK_BYTES = 4096

# Extract a fenced ```json block. Exact language tag `json`; DOTALL for multi-line bodies.
_JSON_FENCE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
_DRIVE_LETTER = re.compile(r"^[A-Za-z]:")


class Finding(NamedTuple):
    """A single advisory finding. ``level`` is one of ``"ok"`` / ``"warn"`` / ``"info"``.

    Findings carry human-readable messages only — never a parsed preference value — so a
    caller cannot route "the parsed preset" into behavior through this API.
    """
    level: str
    message: str


# --------------------------------------------------------------------------- #
# Private parsing/validation helpers (never exported as "settings").
# --------------------------------------------------------------------------- #

def _extract_json_blocks(text: str) -> List[str]:
    """Return the raw bodies of every fenced ```json block, in order."""
    return _JSON_FENCE.findall(text)


def _bad_relative_path(item) -> str:
    """Return an error string if ``item`` is not a safe relative path, else ""."""
    if not isinstance(item, str):
        return f"path entries must be strings (got {type(item).__name__})"
    if item != item.strip() or not item.strip():
        return "path entries must be non-empty and not whitespace-padded"
    if "\\" in item:
        return f"path entries must use '/', not backslashes: {item!r}"
    if item.startswith("/"):
        return f"absolute paths are not allowed: {item!r}"
    if _DRIVE_LETTER.match(item):
        return f"drive-letter paths are not allowed: {item!r}"
    # Detect a `..` segment independently of the backslash check above (defense-in-depth:
    # split on BOTH separators so traversal is caught even for a `foo\..` form regardless of
    # check ordering).
    if ".." in re.split(r"[/\\]", item):
        return f"'..' path traversal is not allowed: {item!r}"
    return ""


def _validate_object(obj) -> tuple[List[str], List[str]]:
    """Validate a parsed JSON value against schema v1.

    Returns ``(errors, warns)``. A non-empty ``errors`` means the block is **invalid and
    ignored** (fail-closed). ``warns`` are soft notes (e.g. empty arrays) on an otherwise
    valid block. Returns findings-shaped strings only — never the parsed values.
    """
    errors: List[str] = []
    warns: List[str] = []

    if not isinstance(obj, dict):
        return ["top level must be a JSON object"], warns

    # schema version gate (missing / unknown -> whole block ignored). Note: a JSON boolean
    # must be rejected even though Python treats ``True == 1`` (bool is a subclass of int).
    if "schema" not in obj:
        errors.append('missing required "schema": 1')
    elif (isinstance(obj["schema"], bool) or not isinstance(obj["schema"], int)
          or obj["schema"] != SCHEMA_VERSION):
        errors.append("unknown schema version (only integer schema 1 is recognized)")

    # key allowlist (unknown keys -> invalid).
    unknown = [k for k in obj if k not in ALLOWED_KEYS]
    if unknown:
        errors.append("unknown key(s) not allowed in schema v1: "
                      + ", ".join(sorted(map(str, unknown))))

    # per-key strict checks (only for known keys that are present).
    if "default_review_preset" in obj:
        val = obj["default_review_preset"]
        if val == "premium":
            errors.append('default_review_preset "premium" is not allowed — the schema is '
                          "tighten-only and cannot request a paid/weaker review floor")
        elif val not in PRESET_ENUM:
            errors.append("default_review_preset must be one of "
                          + "|".join(PRESET_ENUM) + f" (got {val!r})")

    for key in PATH_ARRAY_KEYS:
        if key in obj:
            val = obj[key]
            if not isinstance(val, list):
                errors.append(f"{key} must be an array of relative paths")
                continue
            if not val:
                warns.append(f"{key} is an empty array (stated-but-inert — probably a mistake)")
            seen = set()
            for item in val:
                bad = _bad_relative_path(item)
                if bad:
                    errors.append(f"{key}: {bad}")
                elif item in seen:
                    warns.append(f"{key}: duplicate entry {item!r}")
                else:
                    seen.add(item)

    if "require_usage_flag" in obj:
        if not isinstance(obj["require_usage_flag"], bool):
            errors.append("require_usage_flag must be a boolean")

    return errors, warns


# --------------------------------------------------------------------------- #
# Public API — FINDINGS ONLY.
# --------------------------------------------------------------------------- #

def validate_preferences(project_root) -> List[Finding]:
    """Validate the optional schema v1 block in ``PREFERENCES.md`` under ``project_root``.

    Returns a list of :class:`Finding` (findings only — never parsed settings). Read-only,
    fail-closed, and advisory: any anomaly yields a ``warn`` finding and no parsed result; a
    missing file or missing block yields an informational ``info`` finding (prose-only
    PREFERENCES.md is fine). Never raises on bad input; never applies anything.
    """
    root = Path(project_root)
    prefs = root / PREFERENCES_REL

    # Missing file -> advisory info (the scaffold check covers presence separately).
    if not prefs.exists():
        return [Finding("info", "no PREFERENCES.md — skipping preference-schema check "
                                "(prose-only is fine).")]

    # File-level hardening: resolve to the real path and require it inside the project root.
    # A symlink/out-of-root file -> one generic warn that leaks no content or target path.
    try:
        real = prefs.resolve()
        root_real = root.resolve()
        if not real.is_relative_to(root_real):
            return [Finding("warn", "PREFERENCES.md resolves outside the project root — "
                                    "ignored (untrusted location).")]
    except OSError:
        return [Finding("warn", "PREFERENCES.md could not be resolved — ignored.")]

    # UTF-8 only; an undecodable/unreadable file -> a clean warn, never a traceback.
    try:
        text = prefs.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [Finding("warn", "PREFERENCES.md is not valid UTF-8 — ignored.")]
    except OSError:
        return [Finding("warn", "PREFERENCES.md could not be read — ignored.")]

    blocks = _extract_json_blocks(text)
    if not blocks:
        return [Finding("info", "no machine-readable preferences block — prose-only "
                                "PREFERENCES.md is fine.")]
    if len(blocks) > 1:
        return [Finding("warn", "multiple ```json blocks found; schema v1 allows at most one "
                                "— ignored.")]

    block = blocks[0]
    if len(block.encode("utf-8")) > MAX_BLOCK_BYTES:
        return [Finding("warn", f"preference block exceeds the {MAX_BLOCK_BYTES}-byte cap — "
                                "ignored.")]

    try:
        obj = json.loads(block)
    except (json.JSONDecodeError, ValueError):
        return [Finding("warn", "preference block is not valid JSON — ignored.")]

    errors, warns = _validate_object(obj)
    if errors:
        findings = [Finding("warn", "preference schema block is invalid — ignored "
                                    "(not applied to anything):")]
        findings += [Finding("warn", e) for e in errors]
        return findings

    n = len([k for k in ALLOWED_KEYS if isinstance(obj, dict) and k in obj])
    findings = [Finding("ok", f"preference schema v1 is valid ({n} field(s)); advisory only "
                              "— not applied to any behavior.")]
    findings += [Finding("warn", w) for w in warns]
    return findings
