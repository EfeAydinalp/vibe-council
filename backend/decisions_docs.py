"""Curated public decision records under ``docs/decisions/`` (the source of truth).

Pure, stdlib-only helpers for the ``vibe decisions`` CLI skeleton: list, show,
template (``new``), and lint. No model calls, no API key, no network. This is the
**committed/curated** layer (``docs/decisions/*.md``); the raw auto-extract layer
(gitignored ``.council/decisions/``) is handled separately by the workspace.

Functions take an explicit decisions directory so they are easy to unit-test on a
temp tree. Linting reuses :mod:`backend.redaction` (so secret / local-path /
raw-``.council``-artifact / ``.obsidian`` checks are not duplicated here).
"""

from __future__ import annotations

import re
from datetime import date as _date
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

from . import redaction

README_NAME = "README.md"

# Minimal frontmatter fields every curated record should carry.
REQUIRED_FRONTMATTER = ("id", "status", "date", "tags", "related", "published")

# Stable body headings (matched by prefix, so "Decision (hypothesis)" satisfies
# the "Decision" requirement).
REQUIRED_HEADINGS = (
    "Context", "Decision", "Rationale", "Alternatives considered",
    "Consequences", "Next actions", "Related links",
)

_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<text>.+?)\s*$")
_TITLE_RE = re.compile(r"^#\s+(?P<text>.+?)\s*$")
_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")


class Record(NamedTuple):
    path: Path
    stem: str
    frontmatter: Dict[str, object]
    title: str


class LintIssue(NamedTuple):
    path: str
    line: int
    rule: str
    message: str
    severity: str  # "error" | "warning"


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def _split_frontmatter(text: str):
    """Return (frontmatter_dict, fm_line_count). Empty dict if no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fm: Dict[str, object] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return fm, i + 1
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", lines[i])
        if m:
            fm[m.group(1)] = _parse_scalar(m.group(2))
    return fm, 0  # unterminated frontmatter -> treat as none


def _parse_scalar(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
    return raw.strip("'\"")


def _title_of(text: str, fm: Dict[str, object], stem: str) -> str:
    for line in text.splitlines():
        m = _TITLE_RE.match(line)
        if m:
            return m.group("text")
    return str(fm.get("id") or stem)


def load_record(path: Path) -> Record:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, _ = _split_frontmatter(text)
    return Record(path=path, stem=path.stem, frontmatter=fm,
                  title=_title_of(text, fm, path.stem))


def list_records(decisions_dir: Path) -> List[Record]:
    """All curated records (``*.md`` except README), sorted by filename stem."""
    if not decisions_dir.is_dir():
        return []
    out: List[Record] = []
    for p in sorted(decisions_dir.glob("*.md")):
        if p.name == README_NAME:
            continue
        out.append(load_record(p))
    return out


# --------------------------------------------------------------------------- #
# show (with path-traversal guard)
# --------------------------------------------------------------------------- #

def find_record(decisions_dir: Path, identifier: str) -> Optional[Path]:
    """Resolve an id/stem/path to a file *inside* ``decisions_dir`` only.

    Accepts a bare stem (``2026-06-30-redaction-guard``), a filename, or a path
    ending in the record. Rejects anything that resolves outside the decisions
    directory (path-traversal guard)."""
    decisions_dir = decisions_dir.resolve()
    ident = (identifier or "").strip()
    if not ident:
        return None

    candidates = []
    raw = Path(ident)
    if raw.name.endswith(".md"):
        candidates.append(decisions_dir / raw.name)        # by filename
        candidates.append((decisions_dir.parent.parent / raw))  # repo-relative path
    else:
        candidates.append(decisions_dir / (raw.name + ".md"))   # by stem

    for cand in candidates:
        try:
            rp = cand.resolve()
        except (OSError, RuntimeError):
            continue
        # containment: must be directly inside decisions_dir
        if rp.parent == decisions_dir and rp.name != README_NAME and rp.is_file():
            return rp
    return None


# --------------------------------------------------------------------------- #
# new (template)
# --------------------------------------------------------------------------- #

def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title or "untitled").lower()).strip("-")
    return s or "untitled"


def template(title: Optional[str] = None, status: str = "proposed",
             tags: Optional[List[str]] = None, related: Optional[List[str]] = None,
             on: Optional[str] = None) -> str:
    """Render a new decision-record draft (frontmatter + stable headings)."""
    today = on or _date.today().isoformat()
    slug = _slug(title or "untitled")
    rec_id = f"DEC-{today.replace('-', '')}-{slug}"
    tag_list = "[" + ", ".join(tags or []) + "]"
    rel_list = "[" + ", ".join(related or []) + "]"
    heading_title = title or "Title"
    body = "\n\n".join(f"## {h}\n\n_TODO_" for h in REQUIRED_HEADINGS)
    return (
        "---\n"
        f"id: {rec_id}\n"
        f"status: {status}\n"
        f"date: {today}\n"
        f"tags: {tag_list}\n"
        f"related: {rel_list}\n"
        "published: false\n"
        "---\n\n"
        f"# {heading_title}\n\n"
        f"{body}\n"
    )


# --------------------------------------------------------------------------- #
# lint
# --------------------------------------------------------------------------- #

def _headings(text: str) -> List[str]:
    return [m.group("text") for line in text.splitlines()
            if (m := _HEADING_RE.match(line))]


def _has_heading(headings: List[str], required: str) -> bool:
    r = required.lower()
    return any(h.lower().startswith(r) for h in headings)


def lint(decisions_dir: Path) -> List[LintIssue]:
    """Lint curated records: frontmatter, stable headings, duplicate ids,
    broken local links, and redaction (reused from backend.redaction)."""
    issues: List[LintIssue] = []
    records = list_records(decisions_dir)
    seen_ids: Dict[str, str] = {}

    for rec in records:
        rel = str(rec.path)
        text = rec.path.read_text(encoding="utf-8", errors="replace")

        # frontmatter completeness
        if not rec.frontmatter:
            issues.append(LintIssue(rel, 1, "frontmatter-missing",
                                    "no YAML frontmatter found", "error"))
        else:
            for field in REQUIRED_FRONTMATTER:
                if field not in rec.frontmatter:
                    issues.append(LintIssue(rel, 1, "frontmatter-field",
                                            f"missing required field: {field}", "error"))

        # duplicate ids
        rid = str(rec.frontmatter.get("id") or "")
        if rid:
            if rid in seen_ids:
                issues.append(LintIssue(rel, 1, "duplicate-id",
                                        f"id '{rid}' also in {seen_ids[rid]}", "error"))
            else:
                seen_ids[rid] = rel

        # stable headings
        headings = _headings(text)
        for req in REQUIRED_HEADINGS:
            if not _has_heading(headings, req):
                issues.append(LintIssue(rel, 1, "heading-missing",
                                        f"missing stable heading: {req}", "error"))

        # broken local links
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in _LINK_RE.finditer(line):
                target = m.group("target").strip()
                if target.startswith(("http://", "https://", "mailto:", "#", "<")):
                    continue
                rel_path = target.split("#")[0]
                if not rel_path:
                    continue
                if not (rec.path.parent / rel_path).exists():
                    issues.append(LintIssue(rel, lineno, "broken-link",
                                            f"local link target not found: {rel_path}",
                                            "error"))

        # redaction (reuse PR #38 scanner): criticals -> error, warnings -> advisory
        for f in redaction.scan_file(rec.path):
            sev = "error" if f.severity == redaction.CRITICAL else "warning"
            issues.append(LintIssue(rel, f.line, f"redaction:{f.rule_id}",
                                    f"{f.message} (match: {f.match})", sev))

    return issues


def has_errors(issues: List[LintIssue]) -> bool:
    return any(i.severity == "error" for i in issues)
