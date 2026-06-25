"""Safety guards for the vibe-council CLI: token estimation, a pre-run token
guard, a best-effort cost note, and a loop guard. Stdlib-only.

Design notes:
- Token estimates are ROUGH (no tokenizer dependency) and always labeled as
  estimates.
- Cost is never fabricated: we only report provider-supplied usage/cost after a
  run. Missing --max-cost never blocks a run.
- The loop guard uses small JSON files under <project>/.council/locks/ and is
  enabled by default.
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Loop-guard defaults
DUP_COOLDOWN_SECONDS = 60
MAX_RUNS_PER_WINDOW = 5
RUN_WINDOW_SECONDS = 600
STALE_LOCK_SECONDS = 600


# --------------------------------------------------------------------------- #
# Token estimation (rough, no external tokenizer)
# --------------------------------------------------------------------------- #

def estimate_tokens(text: str) -> int:
    """Rough token estimate for `text`. Heuristic: ~4 chars/token, with a word
    floor. Deliberately conservative; always treat as an ESTIMATE."""
    if not text:
        return 0
    chars = len(text)
    words = len(text.split())
    return max(chars // 4, words)


# How many times the input prompt is (roughly) sent to a model in each mode.
def _mode_send_multiplier(mode: str, council_size: int) -> int:
    if mode == "extract":
        return 1
    if mode in ("mini", "review"):
        return max(council_size, 1)
    if mode == "full":
        return max(council_size, 1) * 2  # collect + rank
    return max(council_size, 1)


def estimate_run_input_tokens(text: str, mode: str, council_size: int) -> int:
    """Estimated *input* tokens for a whole run (rough)."""
    return estimate_tokens(text) * _mode_send_multiplier(mode, council_size)


def token_guard(text: str, mode: str, council_size: int,
                max_tokens: Optional[int]) -> Tuple[bool, int, Optional[str]]:
    """Pre-run token guard. Returns (ok, estimated_tokens, message).

    Fails (ok=False) only when max_tokens is set and the estimate exceeds it.
    """
    estimate = estimate_run_input_tokens(text, mode, council_size)
    if max_tokens is not None and estimate > max_tokens:
        msg = (f"Token guard blocked this run: estimated input ~{estimate} tokens "
               f"exceeds --max-tokens {max_tokens} (estimate, before model calls). "
               f"Raise --max-tokens or shorten the input.")
        return False, estimate, msg
    return True, estimate, None


# --------------------------------------------------------------------------- #
# Usage aggregation (from provider-reported usage dicts)
# --------------------------------------------------------------------------- #

def aggregate_usage(items: List[Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """Sum token usage across provider usage dicts. Returns totals plus whether
    any provider cost was reported (never fabricated)."""
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    reported_cost = 0.0
    any_tokens = False
    any_cost = False
    for u in items:
        if not u:
            continue
        for k in totals:
            v = u.get(k)
            if isinstance(v, (int, float)):
                totals[k] += int(v)
                any_tokens = True
        c = u.get("cost")
        if isinstance(c, (int, float)):
            reported_cost += float(c)
            any_cost = True
    out = {"totals": totals, "has_tokens": any_tokens}
    if any_cost:
        out["reported_cost"] = round(reported_cost, 6)
    return out


def cost_note(usage_summary: Dict[str, Any]) -> Optional[str]:
    """Informational cost line for --usage. Only states the provider-reported
    cost (never fabricated). Cap enforcement lives in enforce_cost_cap()."""
    reported = usage_summary.get("reported_cost")
    if reported is not None:
        return f"Provider-reported cost: ${reported} (as reported by OpenRouter)."
    return None


def enforce_cost_cap(usage_summary: Dict[str, Any],
                     max_cost: Optional[float]) -> Tuple[bool, Optional[float], Optional[str]]:
    """Post-run, best-effort cost-cap enforcement. Returns (exceeded, reported, message).

    - max_cost is None  -> (False, reported, None): never blocks on cost.
    - cost not reported  -> (False, None, honest "could not enforce" message).
    - reported > max_cost -> (True, reported, exceeded message).
    - reported <= max_cost -> (False, reported, within-cap message).

    Never fabricates a dollar figure. Pre-run blocking is intentionally NOT done
    here (use --max-tokens for a hard pre-run guard).
    """
    if max_cost is None:
        return False, usage_summary.get("reported_cost"), None
    reported = usage_summary.get("reported_cost")
    if reported is None:
        return (False, None,
                f"Cost not reported by the provider; --max-cost ${max_cost} could not be "
                f"enforced exactly (no cost fabricated).")
    if reported > max_cost:
        return (True, reported,
                f"Provider-reported cost ${reported} exceeds --max-cost ${max_cost}.")
    return (False, reported,
            f"Provider-reported cost ${reported} within --max-cost ${max_cost}.")


# --------------------------------------------------------------------------- #
# Loop guard
# --------------------------------------------------------------------------- #

@dataclass
class LoopDecision:
    ok: bool
    reason: Optional[str] = None       # machine-ish: "concurrent" | "cooldown" | "rate"
    message: Optional[str] = None
    lock_file: Optional[Path] = None


def _runs_path(locks_dir: Path) -> Path:
    return locks_dir / "runs.jsonl"


def _read_runs(locks_dir: Path) -> List[Dict[str, Any]]:
    path = _runs_path(locks_dir)
    if not path.exists():
        return []
    runs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return runs


def recent_run_count(locks_dir: Path, window: int = RUN_WINDOW_SECONDS) -> int:
    now = time.time()
    return sum(1 for r in _read_runs(locks_dir) if now - r.get("ts", 0) <= window)


def _clean_stale_locks(locks_dir: Path, now: float) -> None:
    for lk in locks_dir.glob("*.lock"):
        try:
            data = json.loads(lk.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if now - data.get("started_at", 0) > STALE_LOCK_SECONDS:
            try:
                lk.unlink()
            except OSError:
                pass


def check_and_lock(locks_dir: Path, command: str, input_hash: str, *,
                   no_loop_guard: bool, allow_repeat: bool) -> LoopDecision:
    """Apply the loop guard and, if accepted, create a lock + record the run.

    - no_loop_guard: disable all checks (no lock created).
    - allow_repeat: bypass the concurrent-duplicate and cooldown checks (rate
      limit still applies; override the rate limit with --no-loop-guard).
    """
    if no_loop_guard:
        return LoopDecision(ok=True)

    locks_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    _clean_stale_locks(locks_dir, now)

    lock_file = locks_dir / f"{input_hash}.lock"

    # 1) Concurrent duplicate run (fresh lock for the same input).
    if lock_file.exists() and not allow_repeat:
        try:
            d = json.loads(lock_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            d = {}
        if now - d.get("started_at", 0) <= STALE_LOCK_SECONDS:
            return LoopDecision(False, "concurrent",
                "Loop guard blocked this run: an identical run is already in "
                "progress for this workspace. Override with --allow-repeat or "
                "--no-loop-guard.")

    runs = _read_runs(locks_dir)
    recent = [r for r in runs if now - r.get("ts", 0) <= RUN_WINDOW_SECONDS]

    # 2) Rate limit: too many runs in the window (override only via --no-loop-guard).
    if len(recent) >= MAX_RUNS_PER_WINDOW:
        return LoopDecision(False, "rate",
            f"Loop guard blocked this run: too many runs in the last "
            f"{RUN_WINDOW_SECONDS // 60} minutes ({len(recent)} >= "
            f"{MAX_RUNS_PER_WINDOW}). Override with --no-loop-guard.")

    # 3) Same input within the cooldown window (override via --allow-repeat).
    if not allow_repeat:
        same = [r for r in recent if r.get("input_hash") == input_hash]
        if same and (now - max(r.get("ts", 0) for r in same)) < DUP_COOLDOWN_SECONDS:
            return LoopDecision(False, "cooldown",
                "Loop guard blocked this run: the same input was run recently "
                f"(within {DUP_COOLDOWN_SECONDS}s). Override with --allow-repeat "
                "or --no-loop-guard.")

    # Accept: create lock + record the run.
    try:
        lock_file.write_text(json.dumps(
            {"pid": os.getpid(), "started_at": now, "command": command}), encoding="utf-8")
        with open(_runs_path(locks_dir), "a", encoding="utf-8") as f:
            f.write(json.dumps({"command": command, "input_hash": input_hash, "ts": now}) + "\n")
    except OSError:
        pass  # locking is best-effort; never fail the run for IO reasons
    return LoopDecision(ok=True, lock_file=lock_file)


def release(lock_file: Optional[Path]) -> None:
    if lock_file is not None:
        try:
            lock_file.unlink()
        except OSError:
            pass
