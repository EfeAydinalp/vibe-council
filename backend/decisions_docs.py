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
    """Return (frontmatter_dict, fm_line_count). Empty dict if no frontmatter.
    Tolerant of a leading UTF-8 BOM (drafts saved by some editors carry one)."""
    if text.startswith("\ufeff"):
        text = text[1:]
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


# --------------------------------------------------------------------------- #
# promote (draft Markdown -> curated docs/decisions/)
# --------------------------------------------------------------------------- #

class PromoteResult(NamedTuple):
    ok: bool
    out_path: Optional[Path]
    written: bool
    errors: List[str]


def _sanitize_filename_stem(s: str) -> str:
    """Reduce an id/title/stem to a safe filename stem (no path separators,
    no traversal). Allowed: ``A-Za-z0-9._-``; everything else -> ``-``."""
    s = (s or "").strip().replace("\\", "/")
    s = s.split("/")[-1]                 # basename only -> kills traversal
    if s.lower().endswith(".md"):
        s = s[:-3]
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s)
    s = s.strip(".-")
    return s or "untitled"


def validate_draft(text: str, label: str = "<draft>") -> List[LintIssue]:
    """Lint a single draft's content: frontmatter completeness, stable headings,
    and redaction (reused). Used by promote and easy to unit-test."""
    issues: List[LintIssue] = []
    fm, _ = _split_frontmatter(text)
    if not fm:
        issues.append(LintIssue(label, 1, "frontmatter-missing",
                                "no YAML frontmatter found", "error"))
    else:
        for field in REQUIRED_FRONTMATTER:
            if field not in fm:
                issues.append(LintIssue(label, 1, "frontmatter-field",
                                        f"missing required field: {field}", "error"))
    headings = _headings(text)
    for req in REQUIRED_HEADINGS:
        if not _has_heading(headings, req):
            issues.append(LintIssue(label, 1, "heading-missing",
                                    f"missing stable heading: {req}", "error"))
    for f in redaction.scan_text(text, label):
        sev = "error" if f.severity == redaction.CRITICAL else "warning"
        issues.append(LintIssue(label, f.line, f"redaction:{f.rule_id}",
                                f"{f.message} (match: {f.match})", sev))
    return issues


def derive_filename(text: str, fm: Dict[str, object], draft_path: Path,
                    on: Optional[str] = None) -> str:
    """Output filename for a promoted draft. Prefer ``<id>.md`` (sanitized);
    else ``<date>-<title-slug>.md``; else the draft stem."""
    rid = str(fm.get("id") or "").strip()
    if rid:
        return _sanitize_filename_stem(rid) + ".md"
    title = _title_of(text, fm, draft_path.stem)
    if title and title != draft_path.stem:
        date = _sanitize_filename_stem(str(fm.get("date") or (on or _date.today().isoformat())))
        return f"{date}-{_slug(title)}.md"
    return _sanitize_filename_stem(draft_path.stem) + ".md"


def promote(draft_path: Path, decisions_dir: Path, force: bool = False,
            dry_run: bool = False, on: Optional[str] = None) -> PromoteResult:
    """Promote a human-reviewed Markdown draft into ``decisions_dir``.

    Blocks on: unreadable draft, missing frontmatter/headings, critical redaction
    findings, an output path that escapes ``decisions_dir``, or an existing target
    without ``force``. Never stages/commits; only reads the given draft path and
    writes one curated record. Reading a draft under ``.council/`` is allowed only
    because the caller passed that explicit path.
    """
    try:
        # utf-8-sig drops a leading BOM so the promoted record is BOM-free.
        text = draft_path.read_text(encoding="utf-8-sig")
    except OSError as e:
        return PromoteResult(False, None, False, [f"cannot read draft: {e}"])

    blocking = [i for i in validate_draft(text, str(draft_path)) if i.severity == "error"]
    if blocking:
        return PromoteResult(False, None, False,
                             [f"{i.rule}: {i.message}" for i in blocking])

    fm, _ = _split_frontmatter(text)
    fname = derive_filename(text, fm, draft_path, on=on)
    decisions_dir = decisions_dir.resolve()
    out_path = decisions_dir / fname
    try:
        rp = out_path.resolve()
    except (OSError, RuntimeError):
        return PromoteResult(False, None, False, ["could not resolve output path"])

    # containment: must land directly inside decisions_dir, and not README
    if rp.parent != decisions_dir or rp.name == README_NAME:
        return PromoteResult(False, None, False, [f"unsafe output path: {fname}"])
    if rp.exists() and not force:
        return PromoteResult(False, rp, False, [f"output exists (use --force): {rp.name}"])
    if dry_run:
        return PromoteResult(True, rp, False, [])

    decisions_dir.mkdir(parents=True, exist_ok=True)
    rp.write_text(text, encoding="utf-8")
    return PromoteResult(True, rp, True, [])


# --------------------------------------------------------------------------- #
# extract (local raw council/review output -> a LOCAL draft decision)
# --------------------------------------------------------------------------- #

class ExtractResult(NamedTuple):
    ok: bool
    out_path: Optional[Path]
    written: bool
    redaction_findings: List[str]   # masked, advisory
    errors: List[str]


_VERDICT_HEAD_RE = re.compile(r"^#{1,6}\s+.*\b(?:verdict|recommendation)\b", re.I)
_VERDICT_INLINE_RE = re.compile(r"^\s*(?:verdict|recommendation)\s*[:\-]\s*(?P<v>.+\S)\s*$", re.I)
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(?P<v>.*\S)\s*$")
_ANY_HEAD_RE = re.compile(r"^#{1,6}\s+(?P<v>.*\S)\s*$")


def _cap(s: str, n: int = 200) -> str:
    s = s.strip()
    return (s[:n] + "…") if len(s) > n else s


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        m = _TITLE_RE.match(line)
        if m:
            return m.group("text")
    return fallback


def _extract_verdict(text: str) -> Optional[str]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        mi = _VERDICT_INLINE_RE.match(line)
        if mi:
            return mi.group("v")
        if _VERDICT_HEAD_RE.match(line):
            for j in range(i + 1, min(i + 6, len(lines))):
                s = lines[j].strip()
                if s and not s.startswith("#"):
                    li = _LIST_ITEM_RE.match(lines[j])
                    return (li.group("v") if li else s)
    return None


def _extract_section_items(text: str, keywords, max_items: int = 5) -> List[str]:
    out: List[str] = []
    capturing = False
    for line in text.splitlines():
        hm = _ANY_HEAD_RE.match(line)
        if hm:
            head = hm.group("v").lower()
            capturing = any(k in head for k in keywords)
            continue
        if capturing:
            im = _LIST_ITEM_RE.match(line)
            if im:
                out.append(im.group("v"))
                if len(out) >= max_items:
                    break
    return out


def _build_extract_draft(src: str, title: str, today: str,
                         tags: Optional[List[str]], source_name: str) -> str:
    rec_id = f"DEC-{today.replace('-', '')}-{_slug(title)}"
    tag_list = "[" + ", ".join(tags or []) + "]"
    verdict = _extract_verdict(src)
    risks = _extract_section_items(src, ["risk"], 5)
    actions = _extract_section_items(
        src, ["next action", "action item", "recommended next", "final action",
              "next step"], 5)
    decision = _cap(verdict) if verdict else "_TODO: state the decision._"
    cons = ("\n".join(f"- Risk (extracted, review): {_cap(r)}" for r in risks)
            if risks else "_TODO: consequences._")
    nexts = ("\n".join(f"- {_cap(a)}" for a in actions)
             if actions else "_TODO: next actions._")
    src_note = ("_Draft extracted from local council output; review/redact before "
                "promotion._\n"
                f"Source: `{source_name}`")
    return (
        "---\n"
        f"id: {rec_id}\n"
        "status: proposed\n"
        f"date: {today}\n"
        f"tags: {tag_list}\n"
        "related: []\n"
        "published: false\n"
        "---\n\n"
        f"# {title}\n\n"
        f"## Context\n\n{src_note}\n\n_TODO: summarize the context._\n\n"
        f"## Decision\n\n{decision}\n\n"
        "## Rationale\n\n_TODO: rationale._\n\n"
        "## Alternatives considered\n\n_TODO._\n\n"
        f"## Consequences\n\n{cons}\n\n"
        f"## Next actions\n\n{nexts}\n\n"
        "## Related links\n\n_TODO._\n"
    )


def _under_docs_decisions(p: Path) -> bool:
    parts = [x.lower() for x in p.resolve().parts]
    return any(parts[i] == "docs" and parts[i + 1] == "decisions"
               for i in range(len(parts) - 1))


def extract_draft(source_path: Path, drafts_dir: Path, out_path: Optional[Path] = None,
                  title: Optional[str] = None, tags: Optional[List[str]] = None,
                  force: bool = False, dry_run: bool = False,
                  on: Optional[str] = None) -> ExtractResult:
    """Extract a LOCAL draft decision from a raw council/review output file.

    Deterministic (no LLM): pulls a title, a verdict-like line, and the first few
    risk/next-action items if the source is sectioned; otherwise a mostly-blank
    template with a source reference and TODO markers. Writes only under
    ``drafts_dir`` (default ``.council/decisions/drafts/``, gitignored). Refuses to
    write under ``docs/decisions/``. Runs a redaction scan and **reports** findings
    (advisory — drafts are local); ``vibe decisions promote`` blocks unsafe records.
    Never stages/commits. Reading a ``.council/`` source is allowed only because the
    caller passed that explicit path.
    """
    try:
        src = source_path.read_text(encoding="utf-8-sig")
    except OSError as e:
        return ExtractResult(False, None, False, [], [f"cannot read source: {e}"])

    today = on or _date.today().isoformat()
    ttl = (title or _extract_title(src, source_path.stem) or "untitled").strip()
    content = _build_extract_draft(src, ttl, today, tags, source_path.name)

    findings = [f"{f.rule_id} (line {f.line}, match {f.match})"
                for f in redaction.scan_text(content, "<draft>")]

    if out_path is not None:
        parent = Path(out_path).parent
        name = _sanitize_filename_stem(Path(out_path).name) + ".md"
        target = parent / name
    else:
        target = drafts_dir / f"{_sanitize_filename_stem(today)}-{_slug(ttl)}.md"

    if _under_docs_decisions(target):
        return ExtractResult(False, None, False, findings,
                             ["refusing to write under docs/decisions/ "
                              "(use `vibe decisions promote` for that)"])
    try:
        rp = target.resolve()
    except (OSError, RuntimeError):
        return ExtractResult(False, None, False, findings,
                             ["could not resolve output path"])
    if rp.name == README_NAME:
        return ExtractResult(False, None, False, findings, ["unsafe output name"])
    if rp.exists() and not force:
        return ExtractResult(False, rp, False, findings,
                             [f"draft exists (use --force): {rp.name}"])
    if dry_run:
        return ExtractResult(True, rp, False, findings, [])

    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(content, encoding="utf-8")
    return ExtractResult(True, rp, True, findings, [])
