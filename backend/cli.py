"""Command-line bridge for vibe-council.

Run council modes from the terminal, with optional
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
    guide claude [--role ROLE] [--write FILE]   Claude Code instruction block (optionally role-aware)

Output goes to stdout; diagnostics (verbose logs, saved paths, model errors,
workspace notices) go to stderr so stdout stays clean for piping. The API key
is never printed.
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Importing config (transitively via council) runs load_dotenv(), consistent
# with the rest of the backend.
from . import __version__
from .config import (
    PRESETS, DEFAULT_PRESET, preset_models, MODEL_ENV_VARS, env_overridden_vars,
)
from .council import run_mode_stream
from .decision_memory import DecisionRecord, save_record
from . import project_workspace as pw
from . import guards
from . import providers
from . import doctor as doctor_mod
from . import redaction
from . import decisions_docs
from . import context_pack
from . import operator as operator_mod
from . import mcp_contract
from . import mcp_server
from . import workbench_panel
from . import workbench_proposal_importer as wb_importer

# Fallback dir for --save when no project workspace is active. Under data/
# (gitignored), so these are never committed.
CLI_RUNS_DIR = "data/cli_runs"

_FINAL_TITLES = {
    "mini": "Final Council Answer",
    "full": "Final Council Answer",
    "review": "Consolidated Review",
}

# Exit codes (stable contract for scripts/agents):
#   0 EXIT_OK       success
#   1 EXIT_RUNTIME  runtime error (e.g. all model calls failed)
#   2 EXIT_USAGE    input/usage error (e.g. missing --prompt/--file)
#   3 EXIT_PREMIUM  premium requested without --allow-premium (checked first)
#   4 EXIT_TOKEN    estimated input exceeds --max-tokens (before any model call)
#   5 EXIT_LOOP     loop guard (duplicate/concurrent/rate-limited run)
#   6 EXIT_COST     provider-reported cost exceeded --max-cost (stdout preserved)
#   7 EXIT_NOKEY    OPENROUTER_API_KEY missing/empty for a model command
EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2
EXIT_PREMIUM = 3
EXIT_TOKEN = 4
EXIT_LOOP = 5
EXIT_COST = 6
EXIT_NOKEY = 7


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


# The exact placeholder value shipped in .env.example. If a user copies the file
# but forgets to replace it, treat the key as not configured.
_ENV_PLACEHOLDER_KEY = "sk-or-v1-..."


def _require_api_key() -> Optional[int]:
    """First-run guard for model commands. Returns EXIT_NOKEY (with a friendly,
    traceback-free message) when OPENROUTER_API_KEY is missing, empty, or still the
    .env.example placeholder; else None. Never prints the key value.

    Note: by the time this runs, config has already called load_dotenv() (which
    populates os.environ from .env). This reads the resolved value.

    Provider-aware: only providers that need an API key are guarded here (the
    selected provider has already been validated by _require_supported_provider).
    Ollama, for example, requires no key."""
    try:
        if not providers.get_provider().requires_api_key():
            return None
    except providers.UnsupportedProviderError:
        return None  # already handled by _require_supported_provider
    key = (os.environ.get("OPENROUTER_API_KEY", "") or "").strip()
    if key and key != _ENV_PLACEHOLDER_KEY:
        return None
    if key == _ENV_PLACEHOLDER_KEY:
        _err("Error: OPENROUTER_API_KEY is still the .env.example placeholder value.")
    else:
        _err("Error: OPENROUTER_API_KEY is not set, so vibe-council cannot call any model.")
    _err("To fix (one-time setup):")
    _err("  1) Copy the example env file:")
    _err("       Windows (PowerShell):  Copy-Item .env.example .env")
    _err("       macOS / Linux:         cp .env.example .env")
    _err("  2) In .env, set:           OPENROUTER_API_KEY=sk-or-v1-<your key>")
    _err("  3) Add credits at:         https://openrouter.ai/")
    _err("Never commit .env — it is gitignored. No-model commands (status, presets,")
    _err("models, decisions, help) work without a key.")
    return EXIT_NOKEY


def _require_supported_provider() -> Optional[int]:
    """Validate the selected provider (VIBE_PROVIDER) before any model call.

    Returns EXIT_USAGE with a clear message when the provider is unsupported,
    else None. For the default (OpenRouter) this is a no-op, so behavior is
    unchanged. Runs before the API-key guard so unsupported providers fail fast
    without requiring any key.
    """
    try:
        providers.get_provider()
    except providers.UnsupportedProviderError as e:
        _err(f"Error: {e}")
        return EXIT_USAGE
    return None


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
        "stage1": None, "stage2": None, "stage3": None,
        "record": None, "markdown": None, "extract_usage": None, "error": None,
    }

    def _usage_tokens(items) -> str:
        u = guards.aggregate_usage([it.get("usage") for it in items])
        t = u["totals"]
        return f"tokens prompt={t['prompt_tokens']} completion={t['completion_tokens']} total={t['total_tokens']}" if u["has_tokens"] else "tokens n/a"

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
            captured["stage1"] = payload["data"]
            log(f"[stage1_complete] {len(payload['data'])} response(s) | {_usage_tokens(payload['data'])}")
        elif event == "stage2_complete":
            captured["stage2"] = payload["data"]
            log(f"[stage2_complete] {len(payload['data'])} ranking(s) | {_usage_tokens(payload['data'])}")
        elif event == "stage3_complete":
            captured["stage3"] = payload["data"]
            log(f"[stage3_complete] | {_usage_tokens([payload['data']])}")
        elif event == "extract_complete":
            captured["record"] = payload["data"]
            captured["markdown"] = payload["markdown"]
            captured["extract_usage"] = payload.get("usage")
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
                # Append to the project-local append-only decision index.
                ws.append_decision_index({
                    "id": paths.get("slug"),
                    "timestamp": rec.get("timestamp"),
                    "title": (rec.get("decision") or "")[:120],
                    "project_name": ws.config.get("project_name"),
                    "source_file": getattr(args, "file", None),
                    "tags": rec.get("tags", []),
                    "json_path": paths["json"],
                    "markdown_path": paths["markdown"],
                })
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
# Usage / stages / guards helpers
# --------------------------------------------------------------------------- #

def _usage_items(captured: Dict[str, Any]) -> List[Optional[Dict[str, Any]]]:
    items = []
    for it in (captured.get("stage1") or []):
        items.append(it.get("usage"))
    for it in (captured.get("stage2") or []):
        items.append(it.get("usage"))
    if captured.get("stage3"):
        items.append(captured["stage3"].get("usage"))
    if captured.get("extract_usage"):
        items.append(captured["extract_usage"])
    return items


def _selected_provider_name() -> str:
    """The active provider name for user-facing usage/cost messages. Defaults to
    'openrouter' if selection can't be resolved (it has already been validated by
    _require_supported_provider before any run)."""
    try:
        return providers.resolve_provider_name()
    except Exception:
        return "openrouter"


def _print_usage(captured: Dict[str, Any], est_input: int) -> None:
    """Print a usage summary to stderr (keeps stdout clean). Honest and provider-
    aware: estimates are labeled; provider cost only shown if actually reported."""
    summary = guards.aggregate_usage(_usage_items(captured))
    provider_name = _selected_provider_name()
    _err(f"[usage] Estimated input tokens: ~{est_input} (rough estimate)")
    if summary["has_tokens"]:
        t = summary["totals"]
        _err(f"[usage] Reported tokens: prompt={t['prompt_tokens']} "
             f"completion={t['completion_tokens']} total={t['total_tokens']}")
    else:
        _err(f"[usage] Reported tokens: not provided by provider '{provider_name}' for this run")
    note = guards.cost_note(summary, provider_name)
    if note:
        _err(f"[usage] {note}")


def _finish_cost(args, captured: Dict[str, Any]) -> int:
    """Post-run cost-cap enforcement. Best-effort: only hard-fails (EXIT_COST)
    when the provider reports a cost above --max-cost. stdout is already printed
    and is preserved. Returns the process exit code."""
    max_cost = getattr(args, "max_cost", None)
    if max_cost is None:
        return EXIT_OK
    summary = guards.aggregate_usage(_usage_items(captured))
    exceeded, _reported, msg = guards.enforce_cost_cap(
        summary, max_cost, _selected_provider_name())
    if msg:
        _err(f"[cost] {msg}")
    if exceeded:
        _err("[cost] Cost cap exceeded (stdout preserved); exiting non-zero.")
        return EXIT_COST
    return EXIT_OK


def _save_stages(args, mode: str, captured: Dict[str, Any], ws, est_input: int) -> None:
    """Persist stage outputs + usage metadata under .council/stages|usage."""
    if ws is None:
        _err("[stages] --save-stages skipped: no active project workspace")
        return
    summary = guards.aggregate_usage(_usage_items(captured))
    slug = pw.timestamp_slug()
    stages_doc = {
        "mode": mode, "preset": captured.get("preset"),
        "estimated_input_tokens": est_input,
        "usage_summary": summary,
        "stages": {
            "stage1": captured.get("stage1"),
            "stage2": captured.get("stage2"),
            "stage3": captured.get("stage3"),
        },
    }
    try:
        sp = ws.save_artifact("stages", f"{slug}_{mode}.json",
                              json.dumps(stages_doc, ensure_ascii=False, indent=2))
        up = ws.save_artifact("usage", f"{slug}_{mode}.json",
                              json.dumps({"mode": mode, "estimated_input_tokens": est_input,
                                          "usage_summary": summary}, ensure_ascii=False, indent=2))
        _err(f"[saved] {sp}")
        _err(f"[saved] {up}")
    except Exception as e:
        _err(f"[stages-error] {type(e).__name__}: {e}")


def _input_hash(command: str, mode: str, preset: str, text: str) -> str:
    return hashlib.sha256(f"{command}|{mode}|{preset}|{text}".encode("utf-8")).hexdigest()[:16]


def _council_size(preset: str) -> int:
    try:
        return len(preset_models(preset)["council"])
    except Exception:
        return 1


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #

def _run_guarded(args, mode: str, text: str, ws, command: str):
    """Apply token + loop guards, run the mode, release the lock.

    Returns (captured, exit_code). On a guard block, captured is None and the
    exit code is non-zero. On success exit_code is None.
    """
    # Token guard (pre-run, estimate) — independent of cost.
    ok, est_input, msg = guards.token_guard(
        text, mode, _council_size(args.preset), getattr(args, "max_tokens", None))
    if not ok:
        _err(f"Error: {msg}")
        return None, est_input, EXIT_TOKEN

    # Loop guard (default on; needs a workspace for its lock files).
    lock = None
    if ws is not None:
        decision = guards.check_and_lock(
            ws.subdir("locks"), command, _input_hash(command, mode, args.preset, text),
            no_loop_guard=getattr(args, "no_loop_guard", False),
            allow_repeat=getattr(args, "allow_repeat", False))
        if not decision.ok:
            _err(f"Error: {decision.message}")
            return None, est_input, EXIT_LOOP
        lock = decision.lock_file

    try:
        captured = asyncio.run(_run(mode, args.preset, text, args.verbose))
    finally:
        guards.release(lock)
    return captured, est_input, None


def cmd_mode(args, mode: str) -> int:
    guard = _premium_blocked(args)
    if guard:
        _err(f"Error: {guard}")
        return EXIT_PREMIUM

    bad_provider = _require_supported_provider()
    if bad_provider is not None:
        return bad_provider

    nokey = _require_api_key()
    if nokey is not None:
        return nokey

    try:
        text = _build_input(args.prompt, args.file)
    except (ValueError, OSError) as e:
        _err(f"Error: {e}")
        return EXIT_USAGE

    ws = _resolve_workspace(args)
    captured, est_input, code = _run_guarded(args, mode, text, ws, command=mode)
    if code is not None:
        return code

    if not _has_result(captured):
        reason = captured["error"] or (
            captured["record"].get("decision") if captured.get("record") else None
        ) or "no output produced (all model calls may have failed)."
        _err(f"Error: {reason}")
        return EXIT_RUNTIME

    print(_render(captured, args.output))
    _save_outputs(args, mode, captured, ws)
    if getattr(args, "save_stages", False):
        _save_stages(args, mode, captured, ws, est_input)
    if getattr(args, "usage", False):
        _print_usage(captured, est_input)
    return _finish_cost(args, captured)


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

    bad_provider = _require_supported_provider()
    if bad_provider is not None:
        return bad_provider

    project_path = pw.caller_cwd()
    diff = _git_diff(project_path)
    if not diff.strip():
        print("No changes to review (git diff is empty).")
        return EXIT_OK

    nokey = _require_api_key()
    if nokey is not None:
        return nokey

    ws = _resolve_workspace(args)
    slug = pw.timestamp_slug()
    if ws:
        raw_path = ws.save_artifact("diffs", f"{slug}.diff", diff)
        _err(f"[saved] {raw_path}")

    text = ("Review the following git diff. Focus on risks, weak assumptions, "
            "security, cost, complexity, missing constraints, and better "
            f"alternatives.\n\n```diff\n{diff}\n```")

    captured, est_input, code = _run_guarded(args, "review", text, ws, command="diff")
    if code is not None:
        return code

    if not _has_result(captured):
        _err(f"Error: {captured['error'] or 'review failed (all model calls may have failed).'}")
        return EXIT_RUNTIME

    review_md = _render(captured, "markdown")
    print(review_md)
    if ws:
        _err(f"[saved] {ws.save_artifact('reviews', f'{slug}_diff.md', review_md)}")
    if getattr(args, "save_stages", False):
        _save_stages(args, "review", captured, ws, est_input)
    if getattr(args, "usage", False):
        _print_usage(captured, est_input)
    return _finish_cost(args, captured)


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


_PRESET_GUIDANCE = {
    "cheap": "smoke tests, quick drafts, low-cost experiments",
    "balanced": "normal real work (default)",
    "premium": "expensive/critical only — requires --allow-premium",
}


def cmd_models(args) -> int:
    """Print configured model IDs per preset + active env overrides. No model call."""
    overridden = env_overridden_vars()
    print("Configured models (defaults from backend/config.py; override via env):\n")
    for name in PRESETS:
        cfg = PRESETS[name]
        print(f"[{name}]")
        print(f"  council:  {', '.join(cfg['council'])}")
        print(f"  chairman: {cfg['chairman']}")
        print(f"  extract:  {cfg['extract']}")
        print("")
    if overridden:
        print("Environment overrides active:")
        for var in sorted(overridden):
            # Print the var name and resolved ID (an OpenRouter model id, not a secret).
            print(f"  {var} = {MODEL_ENV_VARS[var]}")
    else:
        print("Environment overrides active: none (all defaults).")
    print("\nNote: model IDs are not validated against OpenRouter here.")
    return EXIT_OK


_DOCTOR_MARKS = {
    doctor_mod.STATUS_OK: "[ok]  ",
    doctor_mod.STATUS_WARN: "[warn]",
    doctor_mod.STATUS_FAIL: "[fail]",
}


def cmd_doctor(args) -> int:
    """Diagnose provider configuration/reachability. Runs NO inference and never
    prints the API key. Exit: 0 all-pass, 1 a check failed, 2 unsupported provider."""
    online = not getattr(args, "offline", False)
    try:
        checks, provider_name = doctor_mod.run_doctor(online=online)
    except providers.UnsupportedProviderError as e:
        _err(f"Error: {e}")
        return EXIT_USAGE

    print(f"vibe-council {__version__}")
    print(f"Selected provider:   {provider_name}")
    print(f"Supported providers: {', '.join(providers.SUPPORTED_PROVIDERS)}")
    print("Env vars:            VIBE_PROVIDER, OPENROUTER_API_KEY (openrouter), "
          "OLLAMA_HOST (ollama) — values not shown")
    if not online:
        print("Mode:                offline (network reachability checks skipped)")
    print("")
    for c in checks:
        print(f"{_DOCTOR_MARKS.get(c.status, '[?]   ')} {c.name}: {c.detail}")

    code = doctor_mod.doctor_exit_code(checks)
    if code != 0:
        print("\nOne or more checks failed.")
    elif any(c.status == doctor_mod.STATUS_WARN for c in checks):
        print("\nNo failures (some warnings).")
    else:
        print("\nAll checks passed.")
    return code


def cmd_lint(args) -> int:
    """Redaction guard for public docs. No model call, no API key.

    Scans the given paths (or, by default, the tracked public docs) for risky
    content. Prints `path:line:col [SEVERITY] rule-id: message — match: <masked>`
    to stdout. Exit 0 when clean; non-zero when a blocking finding exists
    (criticals always; warnings only with --strict). Secret/path matches are
    masked; full secret values are never printed. See docs/redaction-policy.md.
    """
    root = pw.caller_cwd()
    paths = getattr(args, "paths", None) or []
    findings = redaction.scan_paths(paths, root)

    criticals = sum(1 for f in findings if f.severity == redaction.CRITICAL)
    warnings = sum(1 for f in findings if f.severity == redaction.WARNING)

    for f in findings:
        sev = f.severity.upper()
        print(f"{f.path}:{f.line}:{f.col} [{sev}] {f.rule_id}: {f.message} — "
              f"match: {f.match}")

    target_desc = "given paths" if paths else "tracked public docs"
    blocking = redaction.has_blocking(findings, strict=getattr(args, "strict", False))
    verdict = "FAILED" if blocking else "passed"
    _err(f"[lint] redaction lint {verdict}: {criticals} critical, "
         f"{warnings} warning(s) ({target_desc})")
    if warnings and not getattr(args, "strict", False):
        _err("[lint] warnings are advisory (use --strict to fail on them)")

    return EXIT_RUNTIME if blocking else EXIT_OK


def _under_docs(p: Path) -> bool:
    return "docs" in [x.lower() for x in p.resolve().parts]


def cmd_context(args) -> int:
    """Build or check a deterministic, local-first context pack. No model, API key,
    or network."""
    if args.action == "check":
        return _cmd_context_check(args)
    if args.action == "export":
        return _cmd_context_export(args)
    if args.action != "build":
        _err("Usage: vibe context build | check | export claude-code")
        return EXIT_USAGE

    root = pw.caller_cwd()
    ddir = Path(getattr(args, "decisions_dir", None) or (root / "docs" / "decisions"))
    status = Path(getattr(args, "status", None)
                  or (root / "docs" / "context" / "project" / "STATUS.md"))
    out = Path(getattr(args, "output", None)
               or (root / ".council" / "context" / "pack-latest.md"))
    max_chars = getattr(args, "max_chars", None) or context_pack.DEFAULT_MAX_CHARS

    if _under_docs(out) and not getattr(args, "allow_docs", False):
        _err("[context] refusing to write a generated pack under docs/ "
             "(use --allow-docs to override)")
        return EXIT_USAGE

    res = context_pack.build_pack(ddir, status, max_chars=max_chars)

    for w in res.warnings:
        _err(f"[context] warning: {w}")
    if any("budget" in w for w in res.warnings):
        _err(f"[context] note: content exceeded the {max_chars}-char budget and was "
             f"trimmed (see warnings above); pass --max-chars to allow more room.")

    crit = [f for f in res.redaction_findings if f.severity == redaction.CRITICAL]
    warns = [f for f in res.redaction_findings if f.severity == redaction.WARNING]
    if crit:
        _err(f"[context] BLOCKED: {len(crit)} critical redaction finding(s); not writing")
        for f in crit:
            _err(f"  - line {f.line} {f.rule_id}: {f.message} (match {f.match})")
        return EXIT_RUNTIME

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(res.text, encoding="utf-8")
    print(str(out))
    _err(f"[context] wrote pack ({len(res.text)} chars); "
         f"redaction critical=0 warning={len(warns)}")
    _err("[context] LOCAL/gitignored by default; NOT staged/committed")
    return EXIT_OK


def _cmd_context_check(args) -> int:
    """Deterministic context-quality harness (read-only; no model/API/network)."""
    root = pw.caller_cwd()
    pack_path = Path(getattr(args, "file", None)
                     or (root / ".council" / "context" / "pack-latest.md"))
    if not pack_path.is_file():
        _err(f"[context] pack not found: {pack_path}")
        _err("[context] run `vibe context build` first.")
        return EXIT_USAGE

    text = pack_path.read_text(encoding="utf-8", errors="replace")
    min_score = getattr(args, "min_score", None)
    res = context_pack.check_pack(
        text, strict=getattr(args, "strict", False),
        min_score=(min_score if min_score is not None else context_pack.DEFAULT_MIN_SCORE))

    if getattr(args, "json", False):
        crit = sum(1 for f in res.redaction_findings if f.severity == redaction.CRITICAL)
        warn = sum(1 for f in res.redaction_findings if f.severity == redaction.WARNING)
        print(json.dumps({
            "ok": res.ok,
            "score": round(res.score, 3),
            "passed": res.passed,
            "total": res.total,
            "redaction": {"critical": crit, "warning": warn},
            "reasons": res.reasons,
            "checks": [{"name": c.name, "ok": c.ok, "required": c.required,
                        "category": c.category} for c in res.checks],
        }, ensure_ascii=False, indent=2))
    else:
        for c in res.checks:
            mark = "ok  " if c.ok else "MISS"
            req = "required" if c.required else "advisory"
            print(f"  [{mark}] {c.name} ({req})")
        crit = sum(1 for f in res.redaction_findings if f.severity == redaction.CRITICAL)
        warn = sum(1 for f in res.redaction_findings if f.severity == redaction.WARNING)
        adv_miss = sum(1 for c in res.checks if not c.required and not c.ok)
        score_line = (f"score: {res.passed}/{res.total} ({res.score:.0%}); "
                      f"redaction critical={crit} warning={warn}")
        if adv_miss:
            score_line += f"; {adv_miss} advisory miss(es)"
        print(score_line)
        for r in res.reasons:
            _err(f"[context-check] {r}")

    if res.ok:
        _err("[context-check] PASS")
        return EXIT_OK
    _err("[context-check] FAIL")
    return EXIT_RUNTIME


def _cmd_context_export(args) -> int:
    """`context export claude-code`: wrap the local pack as a Claude Code-friendly
    context file. Read-only on inputs; writes one gitignored local file. No model/
    API/network. Blocks on a failing quality check or a critical redaction finding;
    never modifies CLAUDE.md or writes under docs/ (unless --allow-docs)."""
    target = getattr(args, "target", None)
    if target != "claude-code":
        _err("Usage: vibe context export claude-code")
        return EXIT_USAGE

    root = pw.caller_cwd()
    inp = Path(getattr(args, "input", None)
               or (root / ".council" / "context" / "pack-latest.md"))
    if not inp.is_file():
        _err(f"[context-export] pack not found: {inp}")
        _err("[context-export] run `vibe context build` first.")
        return EXIT_USAGE

    pack_text = inp.read_text(encoding="utf-8", errors="replace")

    # quality gate (includes redaction): a failing check blocks export.
    res = context_pack.check_pack(pack_text)
    if not res.ok:
        _err("[context-export] context check failed; not exporting:")
        for r in res.reasons:
            _err(f"  - {r}")
        _err("[context-export] fix the pack (see `vibe context check`) and retry.")
        return EXIT_RUNTIME

    export_text = context_pack.wrap_for_claude_code(pack_text)

    # belt-and-suspenders: scan the final wrapped export too.
    crit = [f for f in redaction.scan_text(export_text, "<claude-code-export>")
            if f.severity == redaction.CRITICAL]
    if crit:
        _err(f"[context-export] BLOCKED: {len(crit)} critical redaction finding(s); not writing")
        for f in crit:
            _err(f"  - line {f.line} {f.rule_id}: {f.message} (match {f.match})")
        return EXIT_RUNTIME

    out = Path(getattr(args, "output", None)
               or (root / ".council" / "context" / "claude-code-context.md"))
    if _under_docs(out) and not getattr(args, "allow_docs", False):
        _err("[context-export] refusing to write under docs/ (use --allow-docs to override)")
        return EXIT_USAGE

    if getattr(args, "dry_run", False):
        print(f"[dry-run] would write: {out}")
        return EXIT_OK

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(export_text, encoding="utf-8")
    print(str(out))
    _err(f"[context-export] wrote Claude Code context ({len(export_text)} chars)")
    _err("[context-export] LOCAL/gitignored; NOT staged/committed; CLAUDE.md not modified")
    return EXIT_OK


def cmd_operator(args) -> int:
    """Minimal local-first operator status. No model, API key, or network.
    Reads/writes a single gitignored .council/operator/status.json; never an event
    log, dashboard, notification, or remote transport."""
    root = pw.caller_cwd()
    path = operator_mod.status_path(root)
    action = args.action

    if action == "status":
        data, err = operator_mod.read_status(path)
        if err:
            _err(f"[operator] {err}: {path}")
            return EXIT_RUNTIME
        if data is None:
            print("No operator status yet.")
            return EXIT_OK
        if getattr(args, "json", False):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(operator_mod.render(data))
        return EXIT_OK

    if action == "clear":
        if path.is_file():
            try:
                path.unlink()
            except OSError as e:
                _err(f"[operator] could not clear status ({type(e).__name__})")
                return EXIT_RUNTIME
            _err(f"[operator] cleared {path}")
        else:
            _err("[operator] no status to clear")
        return EXIT_OK

    # action == "set"
    state = getattr(args, "state", None)
    if not state:
        _err("Usage: vibe operator set --state <"
             + "|".join(operator_mod.STATES) + "> [--message ...] [--next-action ...]")
        return EXIT_USAGE
    doc, err = operator_mod.write_status(
        path, state=state,
        message=getattr(args, "message", "") or "",
        next_action=getattr(args, "next_action", "") or "",
        source=getattr(args, "source", "") or "",
        severity=getattr(args, "severity", None) or "info",
    )
    if err:
        _err(f"[operator] {err}")
        return EXIT_USAGE
    print(str(path))
    _err("[operator] wrote LOCAL status (gitignored; NOT staged/committed)")
    return EXIT_OK


def cmd_presets(args) -> int:
    """Print available presets and their intended use. No model call."""
    print("Available presets (combine with any mode):\n")
    for name in PRESETS:
        guarded = " [guarded: needs --allow-premium]" if name == "premium" else ""
        print(f"  {name:<9} {_PRESET_GUIDANCE.get(name, '')}{guarded}")
    print(f"\nDefault preset: {DEFAULT_PRESET}")
    print("premium (and full + premium) is blocked unless you pass --allow-premium.")
    print("Use 'vibe models' to see the model IDs behind each preset.")
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

    # Decision memory + guards
    print(f"Decisions indexed: {len(ws.read_decision_index())}")
    print("Loop guard:     enabled (default)")
    print(f"Runs (last 10m): {guards.recent_run_count(ws.subdir('locks'))}")
    last_usage = ws.latest("usage", [".json"])
    if last_usage:
        try:
            u = json.loads(last_usage.read_text(encoding="utf-8"))
            tot = (u.get("usage_summary", {}).get("totals") or {})
            if u.get("usage_summary", {}).get("has_tokens"):
                print(f"Latest usage:   total_tokens={tot.get('total_tokens')} "
                      f"({last_usage.name})")
            else:
                print(f"Latest usage:   {last_usage.name} (tokens not reported)")
        except (OSError, json.JSONDecodeError):
            print(f"Latest usage:   {last_usage}")
    else:
        print("Latest usage:   (none)")
    return EXIT_OK


def _prefer_markdown(path):
    """For decisions saved as both .json and .md, prefer the human-readable .md
    when displaying. JSON remains a valid stored artifact."""
    if path is not None and path.suffix == ".json":
        md = path.with_suffix(".md")
        if md.exists():
            return md
    return path


# --------------------------------------------------------------------------- #
# Decision memory: list / search / context (no model, no API key)
# --------------------------------------------------------------------------- #

def _load_decision(entry: Dict[str, Any]):
    """Return (record_dict, markdown_text) for an index entry; tolerant of
    missing files."""
    record, md = {}, ""
    jp = entry.get("json_path")
    if jp and Path(jp).exists():
        try:
            record = json.loads(Path(jp).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            record = {}
    mp = entry.get("markdown_path")
    if mp and Path(mp).exists():
        try:
            md = Path(mp).read_text(encoding="utf-8")
        except OSError:
            md = ""
    return record, md


def _decision_blob(entry: Dict[str, Any], record: Dict[str, Any], md: str) -> str:
    """Lowercased searchable text across index metadata, structured fields, md."""
    parts = [
        json.dumps(entry, ensure_ascii=False),
        record.get("decision", ""), record.get("rationale", ""),
        " ".join(record.get("risks", []) or []),
        " ".join(record.get("open_questions", []) or []),
        " ".join(record.get("next_actions", []) or []),
        " ".join(record.get("tags", []) or []),
        md,
    ]
    return "\n".join(str(p) for p in parts).lower()


def _matches(query: str, blob: str) -> bool:
    terms = [t for t in query.lower().split() if t]
    return all(t in blob for t in terms) if terms else False


_DECISIONS_DOCS_ACTIONS = {"list", "show", "new", "lint", "promote"}


def cmd_decisions(args) -> int:
    """Dispatch: curated ``docs/decisions/`` (list/show/new/lint) vs the local
    auto-extract index (search/context)."""
    if args.action in _DECISIONS_DOCS_ACTIONS:
        return cmd_decisions_docs(args)
    return cmd_decisions_local(args)


def cmd_decisions_docs(args) -> int:
    """list / show / new / lint over the curated, committed ``docs/decisions/``
    records (the source of truth). No model, no API key, no network."""
    ddir = pw.caller_cwd() / "docs" / "decisions"
    action = args.action

    if action == "list":
        records = decisions_docs.list_records(ddir)
        ftags = getattr(args, "tag", None) or []
        fstatus = getattr(args, "status", None)
        if ftags:
            records = [r for r in records
                       if any(t in (r.frontmatter.get("tags") or []) for t in ftags)]
        if fstatus:
            records = [r for r in records
                       if str(r.frontmatter.get("status", "")) == fstatus]
        if not records:
            print("No curated decision records found (docs/decisions/).")
            return EXIT_OK
        print(f"Curated decisions ({len(records)}):")
        for r in records:
            fm = r.frontmatter
            tags = ", ".join(fm.get("tags") or []) or "-"
            print(f"  {fm.get('date', '?')}  {str(fm.get('status', '?')):<10} {r.stem}")
            print(f"      {r.title}")
            print(f"      tags: {tags}")
        return EXIT_OK

    if action == "show":
        ident = getattr(args, "query", None)
        if not ident:
            _err("Usage: vibe decisions show <id-or-file>")
            return EXIT_USAGE
        path = decisions_docs.find_record(ddir, ident)
        if path is None:
            _err(f"Error: decision not found under docs/decisions/: {ident}")
            return EXIT_USAGE
        print(path.read_text(encoding="utf-8"))
        return EXIT_OK

    if action == "new":
        from_run = getattr(args, "from_run", None)
        if from_run:
            return _cmd_decisions_extract(args, from_run)
        content = decisions_docs.template(
            title=getattr(args, "title", None),
            status=getattr(args, "status", None) or "proposed",
            tags=getattr(args, "tag", None),
            related=getattr(args, "related", None),
        )
        out = getattr(args, "out", None)
        if out:
            p = Path(out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            _err(f"[written] decision draft template -> {p}")
        else:
            print(content)
        return EXIT_OK

    if action == "promote":
        draft = getattr(args, "query", None)
        if not draft:
            _err("Usage: vibe decisions promote <draft-path> [--dry-run] [--force]")
            return EXIT_USAGE
        out_dir = Path(getattr(args, "out_dir", None) or ddir)
        res = decisions_docs.promote(
            Path(draft), out_dir,
            force=getattr(args, "force", False),
            dry_run=getattr(args, "dry_run", False),
        )
        if not res.ok:
            for e in res.errors:
                _err(f"[promote] blocked: {e}")
            _err("[promote] refused (nothing written)")
            return EXIT_RUNTIME
        if res.written:
            print(str(res.out_path))
            _err("[promote] wrote curated decision (NOT staged/committed)")
            _err(f"[promote] next: git diff -- {res.out_path}")
            _err("[promote] next: vibe decisions lint")
        else:
            print(f"[dry-run] would write: {res.out_path}")
        return EXIT_OK

    # action == "lint"
    issues = decisions_docs.lint(ddir)
    for i in issues:
        print(f"{i.path}:{i.line} [{i.severity.upper()}] {i.rule}: {i.message}")
    errors = sum(1 for i in issues if i.severity == "error")
    warns = sum(1 for i in issues if i.severity == "warning")
    _err(f"[decisions lint] {errors} error(s), {warns} warning(s)")
    if decisions_docs.has_errors(issues):
        _err("[decisions lint] FAILED")
        return EXIT_RUNTIME
    _err("[decisions lint] passed")
    return EXIT_OK


def _cmd_decisions_extract(args, from_run: str) -> int:
    """`decisions new --from-run <path>`: extract a LOCAL draft decision from a raw
    council/review output. Writes to gitignored `.council/decisions/drafts/` (or
    `--out`); never to docs/decisions/, never staged/committed."""
    drafts_dir = pw.caller_cwd() / ".council" / "decisions" / "drafts"
    out = getattr(args, "out", None)
    res = decisions_docs.extract_draft(
        Path(from_run), drafts_dir,
        out_path=(Path(out) if out else None),
        title=getattr(args, "title", None),
        tags=getattr(args, "tag", None),
        force=getattr(args, "force", False),
        dry_run=getattr(args, "dry_run", False),
    )
    if not res.ok:
        for e in res.errors:
            _err(f"[extract] blocked: {e}")
        _err("[extract] refused (nothing written)")
        return EXIT_RUNTIME
    if res.redaction_findings:
        _err(f"[extract] redaction findings ({len(res.redaction_findings)}):")
        for r in res.redaction_findings:
            _err(f"  - {r}")
        _err("[extract] This draft has redaction findings; fix before promote.")
    if res.written:
        print(str(res.out_path))
        _err("[extract] wrote LOCAL draft (gitignored, NOT staged/committed)")
        _err(f"[extract] next: review/redact {res.out_path}, then: "
             f"vibe decisions promote {res.out_path}")
    else:
        print(f"[dry-run] would write: {res.out_path}")
    return EXIT_OK


def cmd_decisions_local(args) -> int:
    """search / context over the gitignored local auto-extract index."""
    ws = _resolve_workspace(args, create=False)
    if ws is None:
        print("No active council workspace in this directory.")
        return EXIT_OK

    entries = ws.read_decision_index()
    newest_first = list(reversed(entries))
    action = args.action

    # search / context need a query
    query = getattr(args, "query", None)
    if not query:
        _err(f"Usage: vibe decisions {action} <query>")
        return EXIT_USAGE

    matches = []
    for e in newest_first:
        record, md = _load_decision(e)
        if _matches(query, _decision_blob(e, record, md)):
            matches.append((e, record))

    if not matches:
        print(f"No decisions matched: {query}")
        return EXIT_OK

    if action == "search":
        print(f"Matches for '{query}' ({len(matches)}):")
        for e, record in matches:
            tags = ", ".join(record.get("tags", []) or []) or "-"
            print(f"  - {e.get('timestamp', '?')}  {record.get('decision', e.get('title', ''))}")
            print(f"      tags: {tags}")
            print(f"      md:   {e.get('markdown_path', '?')}")
        return EXIT_OK

    # context: compact block of the most relevant (newest) matches
    top = matches[:3]
    print(f"# Decision context for: {query}\n")
    for e, record in top:
        def lst(items):
            return "; ".join(items) if items else "(none)"
        print(f"## {record.get('decision', e.get('title', 'Decision'))}")
        print(f"- Rationale: {record.get('rationale') or '(none)'}")
        print(f"- Risks: {lst(record.get('risks', []))}")
        print(f"- Next actions: {lst(record.get('next_actions', []))}")
        print(f"- File: {e.get('markdown_path', '?')}")
        print("")
    return EXIT_OK


def cmd_workbench(args) -> int:
    """`workbench serve` | `workbench propose`: the local Workbench (v0.5/v0.6).

    serve: start the localhost-only progress/approval panel. Renders task progress +
    pending approval cards from `.council/runtime/` and lets a human
    approve/reject/hold. **Records decisions only — no action execution, no
    provider/model calls, no LAN/mobile.** Binds 127.0.0.1; POSTs require a token.

    propose: import an agent proposal (schema v1 JSON, from a file or stdin via
    `-`) into the runtime store as a pending approval + pending action. **Local
    intake only — validates, mints ids/hash server-side, never executes, never
    calls a provider/model, adds no network surface.** Approval/execution stay
    separate, explicit panel steps."""
    action = getattr(args, "action", None)
    if action == "serve":
        root = pw.caller_cwd()
        port = getattr(args, "port", None)
        return workbench_panel.serve(root, port=(port if port is not None else 8765),
                                     use_token=not getattr(args, "no_token", False))
    if action == "propose":
        src = getattr(args, "file", None)
        if not src:
            _err("Usage: vibe workbench propose <proposal.json | ->")
            return EXIT_USAGE
        if src == "-":
            text = sys.stdin.read()
        else:
            try:
                text = Path(src).read_text(encoding="utf-8")
            except OSError as e:
                _err(f"[workbench] cannot read proposal file: {type(e).__name__}")
                return EXIT_RUNTIME
        root = pw.caller_cwd()
        result = wb_importer.import_proposal_text(text, project_root=root)
        # stdout stays machine-readable (JSON result; never raw payload content);
        # the human-facing summary/next-step goes to stderr.
        print(json.dumps(wb_importer.result_to_dict(result), ensure_ascii=False,
                         indent=2, sort_keys=True))
        _err(f"[workbench] {wb_importer.summarize_import(result)}")
        if result.ok:
            _err(f"[workbench] next: {result.next_step}")
            return EXIT_OK
        return EXIT_RUNTIME
    _err("Usage: vibe workbench serve [--port N] [--no-token] | "
         "vibe workbench propose <proposal.json | ->")
    return EXIT_USAGE


def cmd_mcp(args) -> int:
    """`mcp contract` | `mcp inspect`: the read-only MCP surface (v0.4).

    All actions are read-only, stdlib-only: no write/git/shell/provider/model calls.
    `contract` prints the planned surface; `inspect` runs a bounded read-only smoke;
    `serve --stdio` starts the minimal read-only MCP stdio transport (no socket/HTTP,
    no daemon, no `.council/` writes)."""
    if getattr(args, "action", None) == "inspect":
        return _cmd_mcp_inspect(args)
    if getattr(args, "action", None) == "serve":
        return _cmd_mcp_serve(args)

    if getattr(args, "json", False):
        print(json.dumps(mcp_contract.contract_dict(), ensure_ascii=False, indent=2))
    else:
        print(mcp_contract.render_contract())
    violations = mcp_contract.validate_mcp_contract()
    if violations:
        for v in violations:
            _err(f"[mcp] contract violation: {v}")
        return EXIT_RUNTIME
    _err("[mcp] read-only contract (design skeleton); no server started, nothing written.")
    return EXIT_OK


def _cmd_mcp_inspect(args) -> int:
    """Bounded read-only smoke over the implemented MCP read layer (status +
    curated decisions). No server, no transport, no writes, no model/network."""
    root = pw.caller_cwd()

    violations = mcp_server.validate_server_contract()
    if violations:
        for v in violations:
            _err(f"[mcp] server contract violation: {v}")
        return EXIT_RUNTIME

    decisions = mcp_server.list_decisions(root)
    try:
        status = mcp_server.get_project_status(root)
        status_note = f"{len(status)} chars"
    except mcp_server.ReadError:
        status_note = "not found"

    one_id = getattr(args, "id", None)
    want_context = getattr(args, "context", False)
    want_health = getattr(args, "health", False)

    # context pack + health are built IN MEMORY (no .council/ file is written).
    pack = mcp_server.get_context_pack(root) if want_context else None
    health = mcp_server.check_context_health(root) if want_health else None

    if getattr(args, "json", False):
        out = {
            "read_only": True,
            "server_implemented": False,  # transport deferred; read layer only
            "enabled_resources": list(mcp_server.ENABLED_RESOURCES),
            "enabled_tools": list(mcp_server.ENABLED_TOOLS),
            "deferred_tools": list(mcp_server.DEFERRED_TOOLS),
            "status_chars": (len(status) if status_note != "not found" else 0),
            "decision_count": len(decisions),
        }
        if one_id:
            try:
                rec = mcp_server.show_decision(root, one_id)
                out["decision"] = {"id": rec["id"], "title": rec["title"],
                                   "chars": len(rec["text"])}
            except mcp_server.ReadError as e:
                out["decision_error"] = str(e)
        if pack is not None:
            out["context_pack"] = {"chars": pack["chars"], "warnings": pack["warnings"],
                                   "redaction": pack["redaction"]}
        if health is not None:
            out["context_health"] = {k: health[k] for k in
                                     ("ok", "passed", "total", "score",
                                      "failed_checks", "redaction")}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("MCP read-only inspect (status + decisions + context; no server/transport)")
        print("  enabled resources: " + ", ".join(mcp_server.ENABLED_RESOURCES))
        print("  enabled tools:     " + ", ".join(mcp_server.ENABLED_TOOLS))
        print("  deferred tools:    " + ", ".join(mcp_server.DEFERRED_TOOLS))
        print(f"  get_project_status: {status_note}")
        print(f"  list_decisions: {len(decisions)} curated record(s)")
        if one_id:
            try:
                rec = mcp_server.show_decision(root, one_id)
                print(f"  show_decision({one_id}): {rec['title']} ({len(rec['text'])} chars)")
            except mcp_server.ReadError as e:
                print(f"  show_decision({one_id}): {e}")
        if pack is not None:
            print(f"  get_context_pack: {pack['chars']} chars (in-memory, not written); "
                  f"redaction critical={pack['redaction']['critical']}")
        if health is not None:
            fails = ", ".join(health["failed_checks"]) or "none"
            print(f"  check_context_health: {health['passed']}/{health['total']} "
                  f"({health['score']:.0%}); failed: {fails}")

    _err("[mcp] read-only inspect; no server started, no .council/ file written.")
    return EXIT_OK


def _cmd_mcp_serve(args) -> int:
    """`mcp serve --stdio`: start the minimal read-only MCP stdio transport.

    Speaks newline-delimited JSON-RPC over stdin/stdout for the existing read-only
    surface (status, decisions, context pack, health). No socket/HTTP port, no
    daemon, no write/git/shell/provider/model calls, no `.council/` writes. Runs
    until stdin EOF. `--stdio` is required (the only transport)."""
    from . import mcp_stdio
    if not getattr(args, "stdio", False):
        _err("Usage: vibe mcp serve --stdio   (stdio is the only supported transport)")
        return EXIT_USAGE
    root = pw.caller_cwd()
    _err("[mcp] read-only stdio transport (JSON-RPC); no write tools, no .council/ writes. "
         "Reading stdin until EOF.")
    return mcp_stdio.serve_stdio(root, sys.stdin, sys.stdout)


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
        _err("Usage: vibe guide claude [--role ROLE] [--write FILE]")
        return EXIT_USAGE

    role = getattr(args, "role", None)
    if role:
        target = getattr(args, "write", None)
        if not target:
            # Default: read-only stdout generator (writes nothing).
            print(role_guide(role))
            return EXIT_OK
        # Opt-in write: append a role section to a CLAUDE.md-style file, following the
        # same append + marker-skip convention as the plain `--write` below. Never
        # overwrites/truncates; a re-run for the same role is skipped (so no --force is
        # needed). Only the explicit target file is touched — no .council/ or other
        # project files.
        path = Path(target)
        marker = _role_guide_marker(role)
        existing = ""
        if path.exists():
            # errors="replace" so a non-UTF-8 target can't crash the marker check.
            existing = path.read_text(encoding="utf-8", errors="replace")
        if marker in existing:
            _err(f"'{path}' already contains a role '{role}' guide section; not modifying.")
            return EXIT_OK
        if _interactive(args) and not _confirm(
                f"Append the '{role}' agent guide to '{path}'?"):
            _err("Aborted.")
            return EXIT_OK
        # Only separate from prior content when the file already has some.
        prefix = "\n\n" if existing.strip() else ""
        section = prefix + role_guide_section(role).rstrip() + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(section)
        _err(f"[written] appended the '{role}' agent guide to {path}")
        return EXIT_OK

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
  vibe status                                         # workspace info + guards
  vibe last [review|decision|diff|run]                # print latest artifact
  vibe projects list                                  # list registered projects
  vibe decisions list                                 # list curated docs/decisions records
  vibe decisions show <id>                            # print a curated decision record
  vibe decisions new --title "..."                    # print a new decision-record template
  vibe decisions new --from-run <review.md>           # extract a LOCAL draft (.council/, gitignored)
  vibe decisions promote <draft.md> [--dry-run]       # promote a reviewed draft into docs/decisions/
  vibe decisions lint                                 # lint curated decision records (reuses redaction)
  vibe decisions search "<query>"                     # search local .council decisions (no model)
  vibe decisions context "<query>"                    # compact local context for planning
  vibe models                                         # show model IDs per preset
  vibe presets                                        # show presets + intended use
  vibe lint --redaction                               # scan public docs for leaks (no model)
  vibe context build                                  # build a local context pack (no model)
  vibe context check                                  # check pack quality (deterministic, no model)
  vibe context export claude-code                     # wrap the pack as a local Claude Code context
  vibe operator status                                # show local workflow status (no model)
  vibe --version
  vibe help
  vibe guide claude [--role task-shaper|planner|coder|reviewer|release-manager] [--write FILE]

Examples:
  vibe review --preset balanced --file plan.md --yes
  vibe review --preset balanced --file plan.md --max-tokens 10000
  vibe review --preset balanced --file plan.md --usage --save-stages
  vibe diff --preset cheap --yes
  vibe extract --preset balanced --prompt "We decided X." --save --yes

Premium guard:
  Preset 'premium' (and full + premium) requires --allow-premium. This prevents
  accidental high-cost runs. Use 'balanced' for real review, 'cheap' for smoke
  tests. Do NOT use premium/full unless explicitly requested.

Token guard (--max-tokens N):
  Estimates input tokens (rough, before any model call) and fails the run if the
  estimate exceeds N. Estimates are clearly labeled as estimates.

Cost guard (--max-cost X):
  OPTIONAL and BEST-EFFORT. If omitted there is NO cost cap. It can only
  hard-fail AFTER the run, when OpenRouter reports an exact cost above X (exit
  code 6); stdout is preserved. If the provider does not report a cost, the cap
  cannot be enforced (no dollar amount is fabricated). For a real PRE-RUN block,
  use --max-tokens.

Loop guard (enabled by default):
  Blocks (a) concurrent identical runs, (b) the same input within 60s, and
  (c) more than 5 runs per 10 minutes — per project workspace. Override with
  --allow-repeat (duplicate/cooldown) or --no-loop-guard (disable all).

Usage (--usage, --save-stages):
  --usage prints a token usage summary (to stderr). --save-stages writes stage
  outputs + usage metadata under .council/stages/ and .council/usage/.

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

Recommended workflow:
1. `vibe status`
2. `vibe decisions context "<topic>"`   # read prior decisions before planning
3. write plan.md
4. `vibe review --preset balanced --file plan.md --yes`
5. implement
6. `vibe diff --preset balanced --yes`
7. fix issues
8. `vibe extract --preset balanced --file plan.md --save --yes`

Decision memory:
- `vibe decisions list` / `search "<query>"` / `context "<query>"` (no model calls).

Rules for agents:
- Prefer `--preset balanced` for real review; `--preset cheap` for smoke tests.
- Do NOT use premium or full unless the user explicitly requests it. Premium
  requires `--allow-premium`.
- Always pass `--yes` in agent workflows to avoid interactive prompts.
- `--max-cost` is optional; if omitted there is no cost cap. Use `--max-tokens`
  for a reliable pre-run guard.
- Loop guard is on by default; override with `--allow-repeat` / `--no-loop-guard`.
- Never print or expose the OPENROUTER_API_KEY.
"""

_GUIDE_CLAUDE = "Claude Code instructions for vibe-council:\n\n" + _GUIDE_CLAUDE_SECTION


# --------------------------------------------------------------------------- #
# Role-aware agent guides (v0.6.1; read-only stdout generators — no repo writes)
# --------------------------------------------------------------------------- #

GUIDE_ROLES = ("task-shaper", "planner", "coder", "reviewer", "release-manager")

_ROLE_BLOCKS = {
    "task-shaper": """### Role: task-shaper

You turn a vague user ask into a scoped, reviewable plan. You do NOT write code by default.

- Restate the goal in one or two sentences; ask clarifying questions ONLY when a real ambiguity
  blocks scoping (don't interrogate for detail you can reasonably assume).
- Run `vibe status` to see the project workspace and any prior context.
- Read prior decisions first: `vibe decisions context "<topic>"` (no model call).
- Produce a short `plan.md`: goal, in-scope, explicit non-goals, and acceptance criteria.
- Recommend a plan review before implementation (`vibe review --preset cheap|balanced --file
  plan.md --usage`), then hand off to a planner/coder. Do not start coding yourself.""",

    "planner": """### Role: planner

You write and refine the implementation plan. You do NOT implement unless explicitly asked.

- Start from the task-shaper's `plan.md` (or write one). Separate **must-have** from
  **nice-to-have**, and list explicit non-goals.
- Get a second opinion when it helps: `vibe review --preset cheap --file plan.md --usage` for
  routine plans, `--preset balanced` for non-trivial or security-relevant ones.
- Apply only the useful feedback (correctness, security, cost, missing constraints); skip style
  nits and speculative rewrites.
- Break the work into small, individually reviewable PRs, and note the review level each needs.""",

    "coder": """### Role: coder

You implement scoped, small PRs. Read the project context BEFORE coding.

- Before coding: read `docs/context/` and any `plan.md`; confirm scope and non-goals; run
  `vibe status`.
- Implement one small, focused change. Match the surrounding code style.
- After coding: run the project tests, then `vibe diff --preset cheap --usage` (use `--preset
  balanced` for security-relevant or non-trivial diffs). Apply only useful feedback.
- **For Workbench actions, PROPOSE — do not bypass approval.** Write a schema-v1 proposal JSON and
  run `vibe workbench propose <file | ->`; this records a *pending* approval and executes nothing.
  A human approves/rejects/holds in `vibe workbench serve`, then executes explicitly. See
  `docs/workbench-agent-bridge.md`. Do not claim a change was applied until an approved action has
  actually executed.
- Never stage `.council/`, runtime/payload artifacts, secrets, `.env`, or private local plans.""",

    "reviewer": """### Role: reviewer

You review a plan or a diff and surface what actually matters.

- Review the working diff with `vibe diff --preset cheap --usage` for routine changes;
  `--preset balanced` for security-relevant or non-trivial diffs; reserve `full` for major
  architecture/security questions only (it is multi-model and more expensive).
- Focus on correctness, security-invariant regressions, cost, and missing constraints. Separate
  must-fix from nice-to-have; apply/recommend only the useful feedback.
- vibe-council output is advice, not authority — a human (or the main coding agent) owns the final
  decision.""",

    "release-manager": """### Role: release-manager

You prepare releases carefully and never ship without explicit approval.

- **No git tag, no GitHub Release, no publish unless the user explicitly allows it.** Release prep
  (version bump + CHANGELOG + release notes) and the tag/Release are separate steps.
- Mirror the established pattern (`docs/release-checklist.md`): bump `backend/__init__.py` +
  `pyproject.toml`, run `uv sync`, and confirm `uv.lock`'s only change is the `vibe-council`
  self-version line (no dependency-graph churn).
- Verify the gates before proposing a tag: tests green, `vibe lint --redaction` 0 critical,
  `vibe decisions lint` passes, `vibe context check` 21/21, `vibe mcp inspect --context --health`
  21/21, and `vibe --version` reports the new version.
- Never stage private/runtime/generated artifacts (`.council/`, payloads, raw outputs, generated
  packs/exports, `.env`, `data/`, secrets).""",
}

_GUIDE_COMMON = """### Common rules (every role)

- **This project's CLI is `vibe`, not `/council`.** `/council` is a possible future host-specific
  custom command / shell alias — it does NOT exist today; never invoke it as if it did.
- **vibe-council is a reviewer, context, and decision-memory layer — not an implementer.** Its
  output is advice a human or the main coding agent must filter and decide on. You own the decision.
- **Preset policy:** `--preset cheap` for routine/smoke, `--preset balanced` for non-trivial or
  security-relevant work, `full` only for major roadmap/product/security questions, `premium` only
  with explicit human approval (`--allow-premium`). Always pass `--usage` on model-spending
  commands, and `--yes` in non-interactive agent workflows.
- **Before coding:** `vibe status` → read `docs/context/` + prior decisions → a short `plan.md` →
  review it. **After coding:** run tests → `vibe diff` → apply only useful feedback.
- **Workbench proposal bridge:** to make a bounded code change under Workbench approval, an agent
  PROPOSES via `vibe workbench propose <file | ->` (a *pending* approval; nothing runs), a human
  approves/rejects/holds, and execution is a separate explicit step through the existing guarded
  executor. No auto-execution; no arbitrary shell; commands are exact allowlisted labels only.
- **Never stage / never send to a model:** `.council/`, `.council/runtime/`,
  `.council/runtime/payloads/`, `.env`, `.venv/`, `data/`, private local plans, raw council
  outputs, generated packs/exports, secrets/API keys, and unrelated `uv.lock` churn. Keep
  `.council/` gitignored; never print the `OPENROUTER_API_KEY`."""


def role_guide(role: str) -> str:
    """Build the role-aware Claude guide text (role-specific block + common rules). Pure;
    writes nothing. Raises ``ValueError`` for an unknown role — argparse already
    restricts the CLI to ``GUIDE_ROLES``, but this keeps the public helper safe for
    any direct caller."""
    block = _ROLE_BLOCKS.get(role)
    if block is None:
        raise ValueError(f"unknown guide role '{role}' (roles: {', '.join(GUIDE_ROLES)})")
    return (f"Claude Code instructions for vibe-council — role: {role}\n\n"
            f"{block}\n\n{_GUIDE_COMMON}\n")


def _role_guide_marker(role: str) -> str:
    """The Markdown heading that marks a role's guide section in a written file — used
    for idempotent, non-destructive appends (skip if already present). Deliberately
    distinct from ``_GUIDE_MARKER`` so a role section and the plain workflow section
    never collide."""
    return f"## vibe-council agent guide (role: {role})"


def role_guide_section(role: str) -> str:
    """A Markdown section (heading + role guide) suitable for appending to a
    ``CLAUDE.md``-style file. Pure; writes nothing."""
    return f"{_role_guide_marker(role)}\n\n{role_guide(role)}"


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

    p_guard = argparse.ArgumentParser(add_help=False)
    p_guard.add_argument("--max-tokens", type=int,
                         help="Fail before model calls if estimated input exceeds N (estimate).")
    p_guard.add_argument("--max-cost", type=float,
                         help="Optional cost cap. If omitted, no cost cap (cost never blocks).")
    p_guard.add_argument("--usage", action="store_true",
                         help="Print a token usage summary (to stderr).")
    p_guard.add_argument("--save-stages", action="store_true",
                         help="Save stage outputs + usage under .council/stages and usage.")
    p_guard.add_argument("--no-loop-guard", action="store_true",
                         help="Disable the loop guard for this run.")
    p_guard.add_argument("--allow-repeat", action="store_true",
                         help="Bypass duplicate/cooldown loop-guard checks.")

    parser = argparse.ArgumentParser(
        prog="backend.cli",
        description="vibe-council CLI — modes, project workspaces, and decisions.",
    )
    parser.add_argument("--version", action="version",
                        version=f"vibe-council {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    mode_desc = {
        "extract": "Single model -> structured DecisionRecord (no council).",
        "mini": "Multiple models -> chairman synthesis (no peer review).",
        "review": "Multiple critiques -> consolidated review (no ranking).",
        "full": "Collect -> peer ranking -> chairman synthesis (full council).",
    }
    for mode, desc in mode_desc.items():
        sub.add_parser(mode, parents=[p_model, p_io, p_proj, p_guard], help=desc, description=desc)

    sub.add_parser("diff", parents=[p_model, p_proj, p_guard],
                   help="Review the caller repo's git diff with review mode.")
    sub.add_parser("init", parents=[p_proj],
                   help="Create a .council/ workspace (no model calls).")

    sp_projects = sub.add_parser("projects", help="List registered projects.")
    sp_projects.add_argument("action", choices=["list"])

    sub.add_parser("models", help="Show configured model IDs per preset (no model call).")
    sub.add_parser("presets", help="Show available presets and intended use (no model call).")

    sp_dec = sub.add_parser(
        "decisions", parents=[p_proj],
        help="Curated decision records + local search (no model calls).",
        epilog="Promotion boundary: `new --from-run` writes only a LOCAL gitignored "
               "draft; `promote` requires meaningful reviewed content (not TODO "
               "placeholders) and never auto-stages or commits.")
    sp_dec.add_argument(
        "action",
        choices=["list", "show", "new", "lint", "promote", "search", "context"])
    sp_dec.add_argument("query", nargs="?",
                        help="id/file for `show`; draft path for `promote`; "
                             "query for `search`/`context`.")
    sp_dec.add_argument("--title", help="Title for `new`.")
    sp_dec.add_argument("--status",
                        help="Status for `new`; or filter for `list`.")
    sp_dec.add_argument("--tag", action="append",
                        help="Tag for `new`; or filter for `list` (repeatable).")
    sp_dec.add_argument("--related", action="append",
                        help="Related id for `new` (repeatable).")
    sp_dec.add_argument("--out",
                        help="Write the `new` template/draft to this path instead of stdout.")
    sp_dec.add_argument("--from-run",
                        help="`new`: extract a LOCAL (gitignored) draft from a raw "
                             ".council review/run file; promotion is a separate, "
                             "human-reviewed step.")
    sp_dec.add_argument("--out-dir",
                        help="Target dir for `promote` (default: docs/decisions).")
    sp_dec.add_argument("--force", action="store_true",
                        help="Allow `promote` to overwrite an existing record.")
    sp_dec.add_argument("--dry-run", action="store_true",
                        help="`promote`: validate + show target, but do not write.")

    sub.add_parser("status", parents=[p_proj], help="Show active workspace info.")

    sp_doctor = sub.add_parser(
        "doctor", help="Diagnose provider configuration/reachability (no inference).")
    sp_doctor.add_argument("--offline", action="store_true",
                           help="Skip network reachability checks (config checks only).")

    sp_op = sub.add_parser(
        "operator", help="Minimal local operator status (no model call).")
    sp_op.add_argument("action", choices=["status", "set", "clear"])
    sp_op.add_argument("--json", action="store_true",
                       help="`status`: print JSON.")
    sp_op.add_argument("--state", choices=list(operator_mod.STATES),
                       help="`set`: workflow state.")
    sp_op.add_argument("--message", help="`set`: short public-safe message.")
    sp_op.add_argument("--next-action", help="`set`: short next step.")
    sp_op.add_argument("--source", help="`set`: source label.")
    sp_op.add_argument("--severity", choices=list(operator_mod.SEVERITIES),
                       help="`set`: severity (default: info).")

    sp_ctx = sub.add_parser(
        "context", help="Build/check a local context pack from curated memory (no model call).")
    sp_ctx.add_argument("action", choices=["build", "check", "export"])
    sp_ctx.add_argument("target", nargs="?",
                        help="`export`: target (claude-code).")
    sp_ctx.add_argument("--input",
                        help="`export`: pack to read (default: .council/context/pack-latest.md).")
    sp_ctx.add_argument("--dry-run", action="store_true",
                        help="`export`: validate + show target, but write nothing.")
    sp_ctx.add_argument("--output",
                        help="`build`/`export`: output path "
                             "(build default .council/context/pack-latest.md; "
                             "export default .council/context/claude-code-context.md).")
    sp_ctx.add_argument("--max-chars", type=int,
                        help=f"`build`: character budget (default: {context_pack.DEFAULT_MAX_CHARS}).")
    sp_ctx.add_argument("--status",
                        help="`build`: STATUS.md path (default: docs/context/project/STATUS.md).")
    sp_ctx.add_argument("--decisions-dir",
                        help="`build`: decisions dir (default: docs/decisions).")
    sp_ctx.add_argument("--allow-docs", action="store_true",
                        help="`build`: allow writing the pack under docs/ (default: refused).")
    sp_ctx.add_argument("--file",
                        help="`check`: pack to read (default: .council/context/pack-latest.md).")
    sp_ctx.add_argument("--strict", action="store_true",
                        help="`check`: also fail on advisory misses and redaction warnings.")
    sp_ctx.add_argument("--json", action="store_true",
                        help="`check`: print a JSON report.")
    sp_ctx.add_argument("--min-score", type=float,
                        help=f"`check`: pass threshold (default: {context_pack.DEFAULT_MIN_SCORE}).")

    sp_lint = sub.add_parser(
        "lint", help="Redaction guard for public docs (no model call).")
    sp_lint.add_argument("--redaction", action="store_true",
                         help="Run the redaction check (the only check today; default).")
    sp_lint.add_argument("--strict", action="store_true",
                         help="Also fail on warnings (default: warnings are advisory).")
    sp_lint.add_argument("paths", nargs="*",
                         help="Files/dirs to scan (default: tracked public docs).")

    sp_mcp = sub.add_parser(
        "mcp", help="Read-only MCP surface (no server): print the contract or inspect status+decisions.")
    sp_mcp.add_argument("action", choices=["contract", "inspect", "serve"],
                        help="contract: print read-only resources/tools + forbidden tools. "
                             "inspect: read-only smoke over status/decisions/context. "
                             "serve: start the read-only MCP stdio transport (--stdio).")
    sp_mcp.add_argument("--id", help="inspect: also show one curated decision by id/stem.")
    sp_mcp.add_argument("--context", action="store_true",
                        help="inspect: also build the context pack in memory (no file written).")
    sp_mcp.add_argument("--health", action="store_true",
                        help="inspect: also run the deterministic context health check (in memory).")
    sp_mcp.add_argument("--stdio", action="store_true",
                        help="serve: use the stdio transport (newline-delimited JSON-RPC).")
    sp_mcp.add_argument("--json", action="store_true", help="Print output as JSON.")

    sp_wb = sub.add_parser(
        "workbench",
        help="Local Workbench panel + agent proposal intake (localhost-only; "
             "approve/reject/hold never auto-execute).",
        epilog="serve: the panel starts empty; use the 'Create demo task' button in the UI to seed "
               "a safe local approval (runtime-only, executes nothing). Approving stays separate "
               "from execution; a verified bounded write_file/edit_file action or an exact "
               "allowlisted command can be explicitly executed as a distinct step. "
               "propose: import an agent proposal (schema v1 JSON; file path or '-' for stdin) "
               "as a pending approval + pending action — local intake only, ids/hash minted "
               "server-side, never executes anything.")
    sp_wb.add_argument("action", choices=["serve", "propose"],
                       help="serve: start the localhost-only progress/approval panel. "
                            "propose: import an agent proposal JSON (file or '-').")
    sp_wb.add_argument("file", nargs="?", metavar="PROPOSAL",
                       help="propose: path to the proposal JSON, or '-' to read stdin.")
    sp_wb.add_argument("--port", type=int, default=8765,
                       help="serve: localhost port (default 8765).")
    sp_wb.add_argument("--no-token", action="store_true",
                       help="serve: skip the POST token (localhost-only; default requires a token).")

    sp_last = sub.add_parser("last", parents=[p_proj], help="Print the latest saved artifact.")
    sp_last.add_argument("artifact_type", nargs="?", choices=["review", "decision", "diff", "run"])

    sub.add_parser("help", help="Print usage and workflow help.")

    sp_guide = sub.add_parser(
        "guide",
        help="Print an agent guide (e.g. 'guide claude', 'guide claude --role coder').")
    sp_guide.add_argument("topic", choices=["claude"])
    sp_guide.add_argument("--role", choices=list(GUIDE_ROLES),
                          help="Print a role-specific guide (stdout by default; add --write to "
                               "append it to a file). Roles: " + ", ".join(GUIDE_ROLES) + ".")
    sp_guide.add_argument("--write", nargs="?", const="CLAUDE.md", metavar="FILE",
                          help="Append the workflow section to FILE (default CLAUDE.md); with "
                               "--role, appends that role's guide section. Skips if the section "
                               "already exists (never overwrites).")
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
    if cmd == "models":
        return cmd_models(args)
    if cmd == "presets":
        return cmd_presets(args)
    if cmd == "decisions":
        return cmd_decisions(args)
    if cmd == "status":
        return cmd_status(args)
    if cmd == "doctor":
        return cmd_doctor(args)
    if cmd == "lint":
        return cmd_lint(args)
    if cmd == "context":
        return cmd_context(args)
    if cmd == "operator":
        return cmd_operator(args)
    if cmd == "mcp":
        return cmd_mcp(args)
    if cmd == "workbench":
        return cmd_workbench(args)
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
