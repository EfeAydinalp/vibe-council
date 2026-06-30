"""Minimal, local-first operator status (stdlib-only).

A tiny status surface so a user can see whether a run/workflow is done, failed, or
needs human input. **Not** an event log, dashboard, notification system, or remote
transport — just a single small JSON file under gitignored ``.council/operator/``.

No model/API/network. The status file is local-only and never committed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

VERSION = 1
STATES = ("needs_input", "failed", "done", "running", "idle")
SEVERITIES = ("info", "warning", "error")
MAX_FIELD = 280  # cap message / next_action / source length

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def operator_dir(root: Path) -> Path:
    return root / ".council" / "operator"


def status_path(root: Path) -> Path:
    return operator_dir(root) / "status.json"


def _clean(s: Optional[str], cap: int = MAX_FIELD) -> str:
    """Strip control chars, collapse whitespace, cap length. Never raises."""
    if not s:
        return ""
    s = _CONTROL_RE.sub("", str(s))
    s = " ".join(s.split())
    return s[:cap]


def read_status(path: Path) -> Tuple[Optional[Dict], Optional[str]]:
    """Return (status_dict, error). Missing file -> (None, None). Invalid JSON ->
    (None, error-message)."""
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"invalid status file ({type(e).__name__})"
    if not isinstance(data, dict):
        return None, "status file is not a JSON object"
    return data, None


def write_status(path: Path, state: str, message: str = "", next_action: str = "",
                 source: str = "", severity: str = "info",
                 on: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
    """Validate + write the status file (under ``.council/operator/`` only).

    Returns (written_dict, error). Rejects unknown state/severity. Sanitizes and
    caps free-text fields. Never writes outside the operator dir."""
    if state not in STATES:
        return None, f"invalid state '{state}' (allowed: {', '.join(STATES)})"
    if severity not in SEVERITIES:
        return None, f"invalid severity '{severity}' (allowed: {', '.join(SEVERITIES)})"

    # containment: only ever the fixed status.json under operator dir
    if path.name != "status.json" or path.parent.name != "operator":
        return None, "refusing to write outside .council/operator/status.json"

    doc = {
        "version": VERSION,
        "updated_at": on or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state": state,
        "source": _clean(source),
        "message": _clean(message),
        "next_action": _clean(next_action),
        "severity": severity,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    except OSError as e:
        return None, f"could not write status file ({type(e).__name__})"
    return doc, None


def render(data: Dict) -> str:
    """Compact human-readable rendering of a status dict."""
    def g(k: str) -> str:
        return str(data.get(k, "") or "-")
    return (
        f"state:       {g('state')}\n"
        f"severity:    {g('severity')}\n"
        f"source:      {g('source')}\n"
        f"message:     {g('message')}\n"
        f"next_action: {g('next_action')}\n"
        f"updated_at:  {g('updated_at')}"
    )
