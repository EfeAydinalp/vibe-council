"""Decision Memory (v1).

Extracts structured decision records from messy input (notes, chat logs, model
outputs, brainstorming/planning sessions) using a single model, and exports them
to JSON and Markdown.

The DecisionRecord shape is deliberately flat and serializable so a SQLite-backed
store can be added later without changing callers or the export format.
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from .openrouter import query_model_detailed
from .config import DECISIONS_DIR


def _utc_now_iso() -> str:
    """Timezone-aware UTC timestamp (ISO-8601). Never use datetime.utcnow()."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DecisionRecord:
    """A single structured decision extracted from discussion."""
    decision: str = ""
    rationale: str = ""
    risks: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        def bullets(items: List[str]) -> str:
            return "\n".join(f"- {i}" for i in items) if items else "- _None_"

        tags = " ".join(f"`{t}`" for t in self.tags) if self.tags else "_None_"
        return f"""# Decision Record

**Decision:** {self.decision or "_Not specified_"}

**Timestamp:** {self.timestamp}

**Tags:** {tags}

## Rationale
{self.rationale or "_Not specified_"}

## Risks
{bullets(self.risks)}

## Open Questions
{bullets(self.open_questions)}

## Next Actions
{bullets(self.next_actions)}
"""


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #

_EXTRACTION_PROMPT = """You extract a single structured decision record from messy input such as notes, a chat log, model outputs, a brainstorming session, or planning notes.

Input:
{text}

Return ONLY a JSON object (no prose, no code fences) with exactly these keys:
- "decision": string — the core decision that was made (or the most important one). If no clear decision exists, summarize the leading direction.
- "rationale": string — why this decision / direction was chosen.
- "risks": array of strings — risks or downsides.
- "open_questions": array of strings — unresolved questions.
- "next_actions": array of strings — concrete next steps.
- "tags": array of short lowercase strings — topical tags.

Use empty arrays where nothing applies. Do not invent details that are not supported by the input. Output only the JSON object."""


def _coerce_str_list(value: Any) -> List[str]:
    """Normalize a value into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value)]


def _parse_record(raw_text: str) -> DecisionRecord:
    """Tolerantly parse a DecisionRecord from a model's raw text output.

    Falls back to stuffing the raw text into `rationale` if no JSON is found,
    so extraction never hard-fails.
    """
    data: Optional[Dict[str, Any]] = None

    # Strip ```json fences if present, then grab the first {...} block.
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            data = None

    if not isinstance(data, dict):
        return DecisionRecord(
            decision="(Could not parse a structured decision)",
            rationale=raw_text.strip(),
        )

    return DecisionRecord(
        decision=str(data.get("decision", "")).strip(),
        rationale=str(data.get("rationale", "")).strip(),
        risks=_coerce_str_list(data.get("risks")),
        open_questions=_coerce_str_list(data.get("open_questions")),
        next_actions=_coerce_str_list(data.get("next_actions")),
        tags=_coerce_str_list(data.get("tags")),
    )


def save_record(record: DecisionRecord) -> Dict[str, str]:
    """Persist a record to JSON and Markdown files. Returns the written paths."""
    Path(DECISIONS_DIR).mkdir(parents=True, exist_ok=True)
    # Filesystem-safe timestamp slug
    slug = record.timestamp.replace(":", "-").replace("+", "_")
    json_path = os.path.join(DECISIONS_DIR, f"{slug}.json")
    md_path = os.path.join(DECISIONS_DIR, f"{slug}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(record.to_json())
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(record.to_markdown())

    return {"json": json_path, "markdown": md_path}


async def extract_decision_record(
    text: str,
    model: str,
) -> Tuple[Dict[str, Any], str]:
    """Single-model extraction. Returns (record_dict, markdown_string).

    Also persists JSON + Markdown exports to DECISIONS_DIR. No council, no peer
    review, no chairman.
    """
    prompt = _EXTRACTION_PROMPT.format(text=text)
    response, error = await query_model_detailed(model, [{"role": "user", "content": prompt}])

    if response is None:
        # Surface the real, safe reason (e.g. "OpenRouter 401 unauthorized")
        # instead of a generic "model did not respond". Includes the model id
        # for "model not found" cases. Never includes the API key.
        reason = error["reason"] if error else "model did not respond"
        if error and error.get("status") == 404:
            reason = f"{reason}: {model}"
        record = DecisionRecord(
            decision=f"(Extraction failed: {reason})",
        )
    else:
        record = _parse_record(response.get("content", "") or "")

    try:
        save_record(record)
    except OSError:
        # Export-to-disk is best-effort; the record is still returned/streamed.
        pass

    return record.to_dict(), record.to_markdown()
