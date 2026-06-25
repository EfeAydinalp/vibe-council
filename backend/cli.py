"""Command-line bridge for vibe-council.

Run any council mode from the terminal without starting the frontend. Reuses
the existing orchestration (council.run_mode_stream), presets/modes
(config.PRESETS / MODES), and decision-memory export (decision_memory) — no
council/model/preset logic is duplicated here.

Examples:
    python -m backend.cli extract --preset cheap --prompt "We dropped solo mode."
    python -m backend.cli mini    --preset balanced --prompt "SQLite now or later?"
    python -m backend.cli review  --preset balanced --file plan.md
    python -m backend.cli full    --preset cheap --prompt "JSON+MD vs SQLite for v1?"

Output goes to stdout; diagnostics (verbose stage logs, save paths, model
errors) go to stderr so stdout stays clean for piping. The API key is never
printed.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Importing config (transitively via council) runs load_dotenv(), consistent
# with the rest of the backend.
from .config import PRESETS, DEFAULT_PRESET
from .council import run_mode_stream
from .decision_memory import DecisionRecord, save_record

# Runtime output dir for non-extract --save. Lives under data/ which is
# gitignored, so CLI run artifacts are never committed.
CLI_RUNS_DIR = "data/cli_runs"

_FINAL_TITLES = {
    "mini": "Final Council Answer",
    "full": "Final Council Answer",
    "review": "Consolidated Review",
}


def _build_input(prompt: Optional[str], file: Optional[str]) -> str:
    """Combine --file and --prompt. File content first, then prompt as an
    additional instruction. Requires at least one."""
    parts = []
    if file:
        content = Path(file).read_text(encoding="utf-8")
        parts.append(content.strip())
    if prompt:
        parts.append(prompt.strip())
    text = "\n\n".join(p for p in parts if p)
    if not text:
        raise ValueError("Provide --prompt or --file (or both).")
    return text


async def _run(mode: str, preset: str, text: str, verbose: bool) -> Dict[str, Any]:
    """Drive run_mode_stream and capture the outputs we care about."""
    captured: Dict[str, Any] = {
        "mode": mode, "preset": preset,
        "stage3": None, "record": None, "markdown": None, "error": None,
    }

    def log(msg: str) -> None:
        if verbose:
            print(msg, file=sys.stderr)

    # persist_extract=False: the CLI controls file persistence via --save, so
    # the pipeline must not auto-write decision files. (Web keeps the default.)
    async for event, payload in run_mode_stream(text, mode, preset, persist_extract=False):
        if event == "start":
            captured["mode"] = payload["mode"]
            captured["preset"] = payload["preset"]
            log(f"[start] mode={payload['mode']} preset={payload['preset']}")
        elif event.endswith("_start"):
            log(f"[{event}]")
        elif event == "stage1_complete":
            log(f"[stage1_complete] {len(payload['data'])} response(s)")
        elif event == "stage2_complete":
            log(f"[stage2_complete] {len(payload['data'])} ranking(s)")
        elif event == "stage3_complete":
            captured["stage3"] = payload["data"]
            log("[stage3_complete]")
        elif event == "extract_complete":
            captured["record"] = payload["data"]
            captured["markdown"] = payload["markdown"]
            log("[extract_complete]")
        elif event == "error":
            captured["error"] = payload["message"]
            log(f"[error] {payload['message']}")

    return captured


def _record_to_text(rec: Dict[str, Any]) -> str:
    def block(label: str, items) -> str:
        if not items:
            return f"{label}:\n  - (none)"
        return label + ":\n" + "\n".join(f"  - {i}" for i in items)

    return "\n".join([
        f"Decision: {rec.get('decision', '')}",
        f"Rationale: {rec.get('rationale', '') or '(none)'}",
        block("Risks", rec.get("risks", [])),
        block("Open Questions", rec.get("open_questions", [])),
        block("Next Actions", rec.get("next_actions", [])),
        f"Tags: {', '.join(rec.get('tags', [])) or '(none)'}",
        f"Timestamp: {rec.get('timestamp', '')}",
    ])


def _render(captured: Dict[str, Any], output: str) -> str:
    """Render the primary result for the chosen --output format."""
    mode = captured["mode"]

    if mode == "extract":
        rec = captured["record"] or {}
        if output == "json":
            return json.dumps(rec, ensure_ascii=False, indent=2)
        if output == "markdown":
            return captured["markdown"] or ""
        return _record_to_text(rec)

    final = captured["stage3"] or {}
    resp = final.get("response", "") or ""
    model = final.get("model", "")
    if output == "json":
        return json.dumps(
            {"mode": mode, "preset": captured["preset"], "model": model, "output": resp},
            ensure_ascii=False, indent=2,
        )
    if output == "markdown":
        title = _FINAL_TITLES.get(mode, "Output")
        return f"# {title}\n\n_Model: {model} · preset: {captured['preset']}_\n\n{resp}"
    return resp


def _save(captured: Dict[str, Any]) -> None:
    """Persist results. Extract uses the decision-memory export system
    (JSON + Markdown); other modes write a markdown run file under data/."""
    mode = captured["mode"]
    if mode == "extract":
        rec = captured["record"] or {}
        try:
            paths = save_record(DecisionRecord(**rec))
            print(f"[saved] {paths['json']}", file=sys.stderr)
            print(f"[saved] {paths['markdown']}", file=sys.stderr)
        except Exception as e:  # never fatal
            print(f"[save-error] {type(e).__name__}: {e}", file=sys.stderr)
        return

    # Non-extract: small markdown run artifact under a gitignored dir.
    try:
        Path(CLI_RUNS_DIR).mkdir(parents=True, exist_ok=True)
        slug = datetime.now(timezone.utc).isoformat().replace(":", "-").replace("+", "_")
        path = Path(CLI_RUNS_DIR) / f"{mode}_{slug}.md"
        path.write_text(_render(captured, "markdown"), encoding="utf-8")
        print(f"[saved] {path}", file=sys.stderr)
    except Exception as e:
        print(f"[save-error] {type(e).__name__}: {e}", file=sys.stderr)


def _has_result(captured: Dict[str, Any]) -> bool:
    if captured["error"]:
        return False
    if captured["mode"] == "extract":
        rec = captured["record"]
        return bool(rec) and not str(rec.get("decision", "")).startswith("(Extraction failed")
    final = captured["stage3"] or {}
    return bool(final.get("response"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backend.cli",
        description="Run vibe-council modes (extract / mini / review / full) from the terminal.",
    )
    sub = parser.add_subparsers(dest="mode", required=True, metavar="{extract,mini,review,full}")

    descriptions = {
        "extract": "Single model -> structured DecisionRecord (no council).",
        "mini": "Multiple models -> chairman synthesis (no peer review).",
        "review": "Multiple critiques -> consolidated review (no ranking).",
        "full": "Collect -> peer ranking -> chairman synthesis (full council).",
    }
    for mode, desc in descriptions.items():
        sp = sub.add_parser(mode, help=desc, description=desc)
        sp.add_argument("--preset", choices=list(PRESETS.keys()), default=DEFAULT_PRESET,
                        help=f"Model preset (default: {DEFAULT_PRESET}).")
        sp.add_argument("--prompt", help="Inline prompt / instruction.")
        sp.add_argument("--file", help="Path to an input file (UTF-8).")
        sp.add_argument("--output", choices=["text", "json", "markdown"], default="text",
                        help="Output format (default: text).")
        sp.add_argument("--save", action="store_true",
                        help="Persist results (extract: JSON+Markdown; others: markdown run file).")
        sp.add_argument("--verbose", action="store_true",
                        help="Print stage progress to stderr (never prints secrets).")
    return parser


def main(argv=None) -> int:
    # Ensure Unicode (e.g. Turkish) output is emitted reliably on Windows
    # consoles, which default to a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = _build_parser().parse_args(argv)

    try:
        text = _build_input(args.prompt, args.file)
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    captured = asyncio.run(_run(args.mode, args.preset, text, args.verbose))

    if not _has_result(captured):
        reason = captured["error"] or (
            captured["record"].get("decision") if captured.get("record") else None
        ) or "no output produced (all model calls may have failed)."
        print(f"Error: {reason}", file=sys.stderr)
        return 1

    print(_render(captured, args.output))

    if args.save:
        _save(captured)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
