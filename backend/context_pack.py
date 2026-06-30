"""Deterministic, local-first context-pack builder.

Assembles a compact agent context pack from curated project memory — the committed
decision records (``docs/decisions/*.md``) plus the project ``STATUS.md`` — with a
character budget. **No LLM, no model/API/network, no vector retrieval.** Reuses
:mod:`backend.decisions_docs` for record parsing and :mod:`backend.redaction` for a
safety scan of the generated pack.

Inclusion order (and budget-reduction order): metadata, project identity, current
status, pinned/high-priority decisions, recent full decisions, decision index,
rejected-alternatives index, constraints. When over budget the builder reduces the
recent-full count, then drops the rejected index, then truncates the decision index,
then (last) truncates status — metadata and status are never dropped entirely.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, NamedTuple, Optional

from . import decisions_docs as dd
from . import redaction

PROJECT_IDENTITY = (
    "vibe-council = local-first council workflow + linked project memory + context "
    "pack builder + skill/council packs + later optional hosted commercial layer."
)
PACK_VERSION = "1"
DEFAULT_MAX_CHARS = 12000
DEFAULT_RECENT = 5
_METADATA_RESERVE = 800  # chars kept aside for the metadata header

CONSTRAINTS = (
    "- Raw `.council/` outputs stay local and gitignored; never committed.\n"
    "- The public repo holds only curated/redacted docs.\n"
    "- A redaction guard exists: `vibe lint --redaction` / `vibe decisions lint` "
    "(see `docs/redaction-policy.md`).\n"
    "- License/provenance remains \"Question 0\" before serious commercialization."
)


class BuildResult(NamedTuple):
    text: str
    warnings: List[str]
    redaction_findings: List[redaction.Finding]


def _strip_frontmatter(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:]).strip()
    return text.strip()


def _date(rec: dd.Record) -> str:
    return str(rec.frontmatter.get("date") or "")


def _status(rec: dd.Record) -> str:
    return str(rec.frontmatter.get("status") or "?")


def _is_pinned(rec: dd.Record) -> bool:
    fm = rec.frontmatter
    return (str(fm.get("pinned", "")).lower() == "true"
            or str(fm.get("priority", "")).lower() == "high")


def _record_full(rec: dd.Record) -> str:
    body = _strip_frontmatter(rec.path.read_text(encoding="utf-8", errors="replace"))
    # drop the leading "# Title" line (we render our own ### header)
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    body = "\n".join(lines).strip()
    return f"### {rec.title} ({_status(rec)}, {_date(rec)})\n\n{body}"


def _index_line(rec: dd.Record) -> str:
    tags = ", ".join(rec.frontmatter.get("tags") or [])
    base = f"- {_date(rec)} · {_status(rec)} · {rec.stem} — {rec.title}"
    return base + (f"  [{tags}]" if tags else "")


def _rejected_index(records: List[dd.Record], cap: int = 12) -> List[str]:
    out: List[str] = []
    for rec in records:
        text = rec.path.read_text(encoding="utf-8", errors="replace")
        for item in dd._extract_section_items(text, ["alternatives considered"], 3):
            out.append(f"- {rec.stem}: {dd._cap(item, 160)}")
            if len(out) >= cap:
                return out
    return out


def _assemble(status_text: str, pinned: List[dd.Record], recent: List[dd.Record],
              index: List[dd.Record], include_rejected: bool) -> str:
    parts: List[str] = []
    parts.append("## Project identity\n\n" + PROJECT_IDENTITY)
    parts.append("## Current status\n\n" + (status_text or "_No STATUS.md found._"))
    if pinned:
        parts.append("## Pinned / high-priority decisions\n\n"
                     + "\n\n".join(_record_full(r) for r in pinned))
    if recent:
        parts.append("## Recent decisions (full)\n\n"
                     + "\n\n".join(_record_full(r) for r in recent))
    if index:
        parts.append("## Decision index (older)\n\n"
                     + "\n".join(_index_line(r) for r in index))
    if include_rejected:
        rej = _rejected_index(pinned + recent + index)
        if rej:
            parts.append("## Rejected alternatives index\n\n" + "\n".join(rej))
    parts.append("## Constraints / safety notes\n\n" + CONSTRAINTS)
    return "\n\n".join(parts)


def build_pack(decisions_dir: Path, status_path: Optional[Path],
               max_chars: int = DEFAULT_MAX_CHARS, recent: int = DEFAULT_RECENT,
               on: Optional[str] = None) -> BuildResult:
    warnings: List[str] = []

    records = dd.list_records(decisions_dir)
    records.sort(key=lambda r: (_date(r), r.stem), reverse=True)
    if not records:
        warnings.append("no curated decision records found")

    status_text = ""
    if status_path and Path(status_path).is_file():
        status_text = Path(status_path).read_text(encoding="utf-8-sig").strip()
    else:
        warnings.append("STATUS file missing; status section shows a placeholder")

    pinned = [r for r in records if _is_pinned(r)]
    pinned_ids = {id(r) for r in pinned}
    rest = [r for r in records if id(r) not in pinned_ids]

    body_budget = max(1000, max_chars - _METADATA_RESERVE)
    recent_n = recent
    index_cap: Optional[int] = None
    include_rejected = True
    status_use = status_text

    while True:
        recent_recs = rest[:recent_n]
        index_recs = rest[recent_n:]
        if index_cap is not None:
            index_recs = index_recs[:index_cap]
        body = _assemble(status_use, pinned, recent_recs, index_recs, include_rejected)
        if len(body) <= body_budget:
            break
        if recent_n > 1:
            recent_n -= 1
            warnings.append("reduced recent full decisions to fit budget")
            continue
        if include_rejected:
            include_rejected = False
            warnings.append("dropped rejected-alternatives index to fit budget")
            continue
        if index_cap is None or index_cap > 0:
            index_cap = 10 if index_cap is None else max(0, index_cap - 10)
            warnings.append("truncated decision index to fit budget")
            continue
        if len(status_use) > 600:
            status_use = status_use[:600].rstrip() + "\n\n_…(status truncated to fit budget)_"
            warnings.append("truncated status to fit budget")
            continue
        warnings.append("pack still exceeds budget after trimming")
        break

    findings = redaction.scan_text(body, "<context-pack>")
    crit = sum(1 for f in findings if f.severity == redaction.CRITICAL)
    warn = sum(1 for f in findings if f.severity == redaction.WARNING)

    generated_at = on or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    src = f"STATUS={status_path if status_path else 'none'}, decisions={decisions_dir} ({len(records)} records)"
    metadata = (
        "## Metadata\n\n"
        f"- generated_at: {generated_at}\n"
        f"- pack_version: {PACK_VERSION}\n"
        f"- sources: {src}\n"
        f"- redaction: critical={crit}, warning={warn}\n"
        f"- size: {len(body)} body chars (budget {max_chars})"
    )

    pack = metadata + "\n\n" + body + "\n"
    # de-dup warnings preserving order
    seen, uniq = set(), []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return BuildResult(pack, uniq, findings)
