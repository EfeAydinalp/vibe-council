"""Command-line bridge for vibe-council.

Run council modes from the terminal without the frontend, with optional
project-local workspaces (.council/). Reuses the existing orchestration
(council.run_mode_stream), presets/modes (config), decision-memory export, and
the project_workspace module — no council/model/preset logic is duplicated.

Commands:
    extract | mini | review | full   run a council mode
    init                              create a .council/ workspace
    diff                             review the caller repo's git diff
    projects list                    list registered projects
    status                           show active workspace info
    last [review|decision|diff|run]  print the latest saved artifact
    help                             usage + workflow help
    guide claude [--write FILE]      Claude Code instruction block

Output goes to stdout; diagnostics (verbose logs, saved paths, model errors,
workspace notices) go to stderr so stdout stays clean for piping. The API key
is never printed.
"""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Importing config (transitively via council) runs load_dotenv(), consistent
# with the rest of the backend.
from .config import PRESETS, DEFAULT_PRESET
from .council import run_mode_stream
from .decision_memory import DecisionRecord, save_record
from . import project_workspace as pw

# Fallback dir for --save when no project workspace is active. Under data/
# (gitignored), so these are never committed.
CLI_RUNS_DIR = "data/cli_runs"

_FINAL_TITLES = {
    "mini": "Final Council Answer",
    "full": "Final Council Answer",
    "review": "Consolidated Review",
}

# Exit codes
EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2
EXIT_PREMIUM = 3


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


# --------------------------------------------------------------------------- #
# Input / run / render (shared by mode commands and diff)
# --------------------------------------------------------------------------- #

def _build_input(prompt: Optional[str], file: Optional[str]) -> str:
    """Combine --file and --prompt. File content first, then prompt as an
    additional instruction. Requires at least one."""
    parts = []
    if file:
        parts.append(Path(file).read_text(encoding="utf-8").strip())
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
            _err(msg)

    # persist_extract=False: the CLI controls file persistence, not the pipeline.
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
    """Render the primary result for the chosen output format."""
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


def _has_result(captured: Dict[str, Any]) -> bool:
    if captured["error"]:
        return False
    if captured["mode"] == "extract":
        rec = captured["record"]
        return bool(rec) and not str(rec.get("decision", "")).startswith("(Extraction failed")
    return bool((captured["stage3"] or {}).get("response"))


# --------------------------------------------------------------------------- #
# Premium guard + workspace resolution
# --------------------------------------------------------------------------- #

def _premium_blocked(args) -> Optional[str]:
    """Return an error message if premium is requested without --allow-premium."""
    if getattr(args, "preset", None) == "premium" and not getattr(args, "allow_premium", False):
        return ("Preset 'premium' (including full + premium) requires explicit "
                "--allow-premium. Use --preset balanced for real review or "
                "--preset cheap for smoke tests.")
    return None


def _confirm(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        ans = input(f"{question} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not ans:
        return default
    return ans in ("y", "yes")


def _interactive(args) -> bool:
    return sys.stdin.isatty() and not getattr(args, "yes", False)


def _init_workspace(args, project_path: Path) -> Optional[pw.Workspace]:
    """Create a workspace, prompting in interactive mode, auto-yes otherwise."""
    name = getattr(args, "project", None) or project_path.name
    if _interactive(args):
        if not _confirm(f"Create local council workspace for project '{name}'?"):
            return None
        add_ignore = _confirm("Add .council/ to .gitignore?")
        register = _confirm("Register this project globally?")
    else:
        add_ignore = register = True

    ws = pw.Workspace.create(project_path, name)
    if add_ignore and pw.add_gitignore_entry(project_path):
        _err("[workspace] added .council/ to .gitignore")
    if register:
        pw.register_project(ws.config["project_name"], project_path)
    _err(f"[workspace] initialized {ws.council_dir}")
    return ws


def _resolve_workspace(args, create: bool = True) -> Optional[pw.Workspace]:
    """Find the active workspace; optionally auto-create unless --no-project."""
    if getattr(args, "no_project", False):
        return None
    project_path = pw.caller_cwd()
    ws = pw.Workspace.load(project_path)
    if ws is None and create:
        ws = _init_workspace(args, project_path)
    if ws is not None:
        ws.touch_used()
    return ws


# --------------------------------------------------------------------------- #
# Saving
# --------------------------------------------------------------------------- #

def _save_fallback(mode: str, content: str) -> str:
    Path(CLI_RUNS_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(CLI_RUNS_DIR) / f"{mode}_{pw.timestamp_slug()}.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


def _save_outputs(args, mode: str, captured: Dict[str, Any], ws: Optional[pw.Workspace]) -> None:
    """Apply this PR's per-mode saving rules and report paths to stderr."""
    saved = []
    try:
        if mode == "extract":
            if not getattr(args, "save", False):
                return
            rec = captured["record"] or {}
            rec_obj = DecisionRecord(**rec)
            if ws:
                paths = ws.save_decision(rec, rec_obj.to_json(), rec_obj.to_markdown())
                saved += [paths["json"], paths["markdown"]]
            else:
                paths = save_record(rec_obj)  # existing data/decisions behavior
                saved += [paths["json"], paths["markdown"]]

        elif mode == "review":
            # review saves by default when a workspace is active.
            content = _render(captured, "markdown")
            if ws:
                saved.append(str(ws.save_artifact("reviews", f"{pw.timestamp_slug()}_review.md", content)))
            elif getattr(args, "save", False):
                saved.append(_save_fallback(mode, content))

        elif mode in ("mini", "full"):
            if getattr(args, "save", False):
                content = _render(captured, "markdown")
                if ws:
                    saved.append(str(ws.save_artifact("runs", f"{pw.timestamp_slug()}_{mode}.md", content)))
                else:
                    saved.append(_save_fallback(mode, content))
    except Exception as e:  # never fatal
        _err(f"[save-error] {type(e).__name__}: {e}")

    for s in saved:
        _err(f"[saved] {s}")


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #

def cmd_mode(args, mode: str) -> int:
    guard = _premium_blocked(args)
    if guard:
        _err(f"Error: {guard}")
        return EXIT_PREMIUM

    try:
        text = _build_input(args.prompt, args.file)
    except (ValueError, OSError) as e:
        _err(f"Error: {e}")
        return EXIT_USAGE

    ws = _resolve_workspace(args)
    captured = asyncio.run(_run(mode, args.preset, text, args.verbose))

    if not _has_result(captured):
        reason = captured["error"] or (
            captured["record"].get("decision") if captured.get("record") else None
        ) or "no output produced (all model calls may have failed)."
        _err(f"Error: {reason}")
        return EXIT_RUNTIME

    print(_render(captured, args.output))
    _save_outputs(args, mode, captured, ws)
    return EXIT_OK


def _git_diff(project_path: Path) -> str:
    """Return the caller repo's diff (staged+unstaged vs HEAD, else worktree)."""
    for cmd in (["git", "-C", str(project_path), "diff", "HEAD"],
                ["git", "-C", str(project_path), "diff"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    return ""


def cmd_diff(args) -> int:
    guard = _premium_blocked(args)
    if guard:
        _err(f"Error: {guard}")
        return EXIT_PREMIUM

    project_path = pw.caller_cwd()
    diff = _git_diff(project_path)
    if not diff.strip():
        print("No changes to review (git diff is empty).")
        return EXIT_OK

    ws = _resolve_workspace(args)
    slug = pw.timestamp_slug()
    if ws:
        raw_path = ws.save_artifact("diffs", f"{slug}.diff", diff)
        _err(f"[saved] {raw_path}")

    text = ("Review the following git diff. Focus on risks, weak assumptions, "
            "security, cost, complexity, missing constraints, and better "
            f"alternatives.\n\n```diff\n{diff}\n```")
    captured = asyncio.run(_run("review", args.preset, text, args.verbose))

    if not _has_result(captured):
        _err(f"Error: {captured['error'] or 'review failed (all model calls may have failed).'}")
        return EXIT_RUNTIME

    review_md = _render(captured, "markdown")
    print(review_md)
    if ws:
        _err(f"[saved] {ws.save_artifact('reviews', f'{slug}_diff.md', review_md)}")
    return EXIT_OK


def cmd_init(args) -> int:
    project_path = pw.caller_cwd()
    name = getattr(args, "project", None) or project_path.name
    ws = pw.Workspace.create(project_path, name)
    if pw.add_gitignore_entry(project_path):
        _err("[workspace] added .council/ to .gitignore")
    pw.register_project(ws.config["project_name"], project_path)
    print(f"Initialized council workspace for '{ws.config['project_name']}'")
    print(f"  workspace: {ws.council_dir}")
    print(f"  subdirs:   {', '.join(pw.SUBDIRS)}")
    print(f"  config:    {ws.config_path}")
    return EXIT_OK


def cmd_projects(args) -> int:
    if args.action != "list":
        _err("Usage: vibe projects list")
        return EXIT_USAGE
    projects = pw.list_projects()
    if not projects:
        print("No projects registered yet.")
        return EXIT_OK
    print(f"Registered projects ({len(projects)}):")
    for p in projects:
        print(f"  - {p.get('project_name', '?')}")
        print(f"      path:      {p.get('project_path', '?')}")
        print(f"      last_used: {p.get('last_used_at', '?')}")
    return EXIT_OK


def cmd_status(args) -> int:
    ws = _resolve_workspace(args, create=False)
    if ws is None:
        print("No active council workspace in this directory.")
        print(f"  directory: {pw.caller_cwd()}")
        print("  run 'vibe init' (or any mode command) to create one.")
        return EXIT_OK

    cfg = ws.config
    require_premium = cfg.get("require_allow_premium", True)
    print(f"Project:        {cfg.get('project_name')}")
    print(f"Project path:   {cfg.get('project_path')}")
    print(f"Workspace:      {ws.council_dir}")
    print(f"Default preset: {cfg.get('default_preset')}")
    print(f"Max preset:     {cfg.get('max_preset')}")
    last_review = ws.latest("reviews", [".md"])
    last_decision = _prefer_markdown(ws.latest("decisions", [".md", ".json"]))
    last_diff = ws.latest("diffs", [".diff"])
    last_run = ws.latest("runs", [".md"])
    print(f"Last review:    {last_review or '(none)'}")
    print(f"Last decision:  {last_decision or '(none)'}")
    print(f"Last diff:      {last_diff or '(none)'}")
    print(f"Last run:       {last_run or '(none)'}")
    print(f"Premium allowed: {'no (requires --allow-premium)' if require_premium else 'yes'}")
    return EXIT_OK


def _prefer_markdown(path):
    """For decisions saved as both .json and .md, prefer the human-readable .md
    when displaying. JSON remains a valid stored artifact."""
    if path is not None and path.suffix == ".json":
        md = path.with_suffix(".md")
        if md.exists():
            return md
    return path


def cmd_last(args) -> int:
    ws = _resolve_workspace(args, create=False)
    if ws is None:
        print("No active council workspace in this directory.")
        return EXIT_OK

    type_map = {
        "review": ("reviews", [".md"]),
        "decision": ("decisions", [".md", ".json"]),
        "diff": ("diffs", [".diff"]),
        "run": ("runs", [".md"]),
    }
    atype = getattr(args, "artifact_type", None)
    if atype:
        subdir, suffixes = type_map[atype]
        latest = ws.latest(subdir, suffixes)
    else:
        candidates = [ws.latest(sd, sx) for sd, sx in type_map.values()]
        candidates = [c for c in candidates if c is not None]
        latest = max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None

    # Default user-facing display prefers Markdown over JSON for decisions.
    latest = _prefer_markdown(latest)

    if latest is None:
        kind = atype or "artifact"
        print(f"No saved {kind}s found in this workspace.")
        return EXIT_OK

    _err(f"== {latest} ==")
    print(latest.read_text(encoding="utf-8"))
    return EXIT_OK


def cmd_help(args) -> int:
    print(_HELP_TEXT)
    return EXIT_OK


def cmd_guide(args) -> int:
    if args.topic != "claude":
        _err("Usage: vibe guide claude [--write FILE]")
        return EXIT_USAGE

    target = getattr(args, "write", None)
    if not target:
        print(_GUIDE_CLAUDE)
        return EXIT_OK

    path = Path(target)
    section = "\n\n" + _GUIDE_CLAUDE_SECTION + "\n"
    if path.exists() and _GUIDE_MARKER in path.read_text(encoding="utf-8"):
        _err(f"'{path}' already contains a Vibe Council Workflow section; not modifying.")
        return EXIT_OK

    if _interactive(args) and not _confirm(f"Append Vibe Council Workflow section to '{path}'?"):
        _err("Aborted.")
        return EXIT_OK

    with open(path, "a", encoding="utf-8") as f:
        f.write(section)
    _err(f"[written] appended Vibe Council Workflow section to {path}")
    return EXIT_OK


# --------------------------------------------------------------------------- #
# Help / guide text
# --------------------------------------------------------------------------- #

_HELP_TEXT = """vibe-council CLI — multi-model review & decision workflow

Common commands:
  vibe review  --preset balanced --file plan.md      # critique a plan/code/draft
  vibe diff    --preset balanced                      # review the repo's git diff
  vibe extract --preset balanced --file plan.md --save  # decision record (JSON+MD)
  vibe mini    --preset balanced --prompt "..."       # quick multi-model answer
  vibe full    --preset balanced --prompt "..."       # full council (ranking)
  vibe init                                           # create .council/ workspace
  vibe status                                         # show workspace info
  vibe last [review|decision|diff|run]                # print latest artifact
  vibe projects list                                  # list registered projects
  vibe help
  vibe guide claude

Examples:
  vibe review --preset balanced --file plan.md --yes
  vibe diff --preset cheap --yes
  vibe extract --preset balanced --prompt "We decided X." --save --yes

Premium guard:
  Preset 'premium' (and full + premium) requires --allow-premium. This prevents
  accidental high-cost runs. Use 'balanced' for real review, 'cheap' for smoke
  tests. Do NOT use premium/full unless explicitly requested.

Project workspace (.council/):
  When run from a project, vibe stores artifacts in <project>/.council/:
    reviews/  diffs/  decisions/  runs/  stages/  usage/  locks/
  .council/ is local-only and is added to your project's .gitignore.

Claude Code quick workflow:
  1) vibe status
  2) write plan.md
  3) vibe review --preset balanced --file plan.md --yes
  4) implement
  5) vibe diff --preset balanced --yes
  6) fix issues
  7) vibe extract --preset balanced --file plan.md --save --yes

Warnings:
  - Do not use premium/full unless explicitly requested (cost).
  - .council/ is local and should stay gitignored.
  - .env and data/ are local and ignored; never commit generated artifacts.
"""

_GUIDE_MARKER = "## Vibe Council Workflow"

_GUIDE_CLAUDE_SECTION = """## Vibe Council Workflow

vibe-council is a multi-model review/decision CLI. Use it to get a consolidated
critique from several models and to record decisions.

When to use:
- Reviewing a plan, design, diff, or draft before/after implementing.
- Capturing a decision (with rationale, risks, next actions) as a record.

How to run:
- Status first:        `vibe status`
- Review a file:       `vibe review --preset balanced --file plan.md --yes`
- Review the git diff: `vibe diff --preset balanced --yes`
- Extract a decision:  `vibe extract --preset balanced --file plan.md --save --yes`

Rules for agents:
- Prefer `--preset balanced` for real review; `--preset cheap` for smoke tests.
- Do NOT use premium or full unless the user explicitly requests it. Premium
  requires `--allow-premium`.
- Always pass `--yes` in agent workflows to avoid interactive prompts.
- Never print or expose the OPENROUTER_API_KEY.
- Run `vibe status` first to confirm the active workspace.
"""

_GUIDE_CLAUDE = "Claude Code instructions for vibe-council:\n\n" + _GUIDE_CLAUDE_SECTION


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    # Shared option groups
    p_model = argparse.ArgumentParser(add_help=False)
    p_model.add_argument("--preset", choices=list(PRESETS.keys()), default=DEFAULT_PRESET,
                         help=f"Model preset (default: {DEFAULT_PRESET}).")
    p_model.add_argument("--allow-premium", action="store_true",
                         help="Allow preset=premium (otherwise blocked).")

    p_io = argparse.ArgumentParser(add_help=False)
    p_io.add_argument("--prompt", help="Inline prompt / instruction.")
    p_io.add_argument("--file", help="Path to an input file (UTF-8).")
    p_io.add_argument("--output", choices=["text", "json", "markdown"], default="text",
                      help="Output format (default: text).")
    p_io.add_argument("--save", action="store_true", help="Persist results.")

    p_proj = argparse.ArgumentParser(add_help=False)
    p_proj.add_argument("--yes", action="store_true", help="Assume yes; no interactive prompts.")
    p_proj.add_argument("--project", help="Project name (default: folder name).")
    p_proj.add_argument("--no-project", action="store_true",
                        help="Do not use/create a .council/ workspace.")
    p_proj.add_argument("--verbose", action="store_true",
                        help="Print stage progress to stderr (never prints secrets).")

    parser = argparse.ArgumentParser(
        prog="backend.cli",
        description="vibe-council CLI — modes, project workspaces, and decisions.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    mode_desc = {
        "extract": "Single model -> structured DecisionRecord (no council).",
        "mini": "Multiple models -> chairman synthesis (no peer review).",
        "review": "Multiple critiques -> consolidated review (no ranking).",
        "full": "Collect -> peer ranking -> chairman synthesis (full council).",
    }
    for mode, desc in mode_desc.items():
        sub.add_parser(mode, parents=[p_model, p_io, p_proj], help=desc, description=desc)

    sub.add_parser("diff", parents=[p_model, p_proj],
                   help="Review the caller repo's git diff with review mode.")
    sub.add_parser("init", parents=[p_proj],
                   help="Create a .council/ workspace (no model calls).")

    sp_projects = sub.add_parser("projects", help="List registered projects.")
    sp_projects.add_argument("action", choices=["list"])

    sub.add_parser("status", parents=[p_proj], help="Show active workspace info.")

    sp_last = sub.add_parser("last", parents=[p_proj], help="Print the latest saved artifact.")
    sp_last.add_argument("artifact_type", nargs="?", choices=["review", "decision", "diff", "run"])

    sub.add_parser("help", help="Print usage and workflow help.")

    sp_guide = sub.add_parser("guide", help="Print an agent guide (e.g. 'guide claude').")
    sp_guide.add_argument("topic", choices=["claude"])
    sp_guide.add_argument("--write", nargs="?", const="CLAUDE.md", metavar="FILE",
                          help="Append the workflow section to FILE (default CLAUDE.md).")
    sp_guide.add_argument("--yes", action="store_true", help="Assume yes for writing.")

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
    cmd = args.command

    if cmd in ("extract", "mini", "review", "full"):
        return cmd_mode(args, cmd)
    if cmd == "diff":
        return cmd_diff(args)
    if cmd == "init":
        return cmd_init(args)
    if cmd == "projects":
        return cmd_projects(args)
    if cmd == "status":
        return cmd_status(args)
    if cmd == "last":
        return cmd_last(args)
    if cmd == "help":
        return cmd_help(args)
    if cmd == "guide":
        return cmd_guide(args)

    _err(f"Unknown command: {cmd}")
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
