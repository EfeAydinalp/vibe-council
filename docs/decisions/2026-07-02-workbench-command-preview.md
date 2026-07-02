---
id: DEC-20260702-workbench-command-preview
status: accepted
date: 2026-07-02
tags: [v0.5, workbench, executor, run_command, security, safety]
related: [DEC-20260702-workbench-command-execution-plan, DEC-20260701-workbench-bounded-file-executor, DEC-20260701-workbench-executor-dry-run, DEC-20260701-workbench-trust-boundary]
published: true
---

# Command labels resolve to fixed argv — dry-run preview only, real execution stays fail-closed

## Context

PR #78 designed real `run_command` execution as a narrow, no-shell, fixed-argv allowlist
([plan](../plans/v0.5-command-execution.md)). This PR implements the resolution layer that design
depends on — mapping an exact allowlisted command label to a fixed argv — for **dry-run preview
only**. Real execution is not added.

## Decision

Add `backend/workbench_commands.py` (stdlib-only) and extend `workbench_executor.py`'s dry-run path.

- **Command labels resolve to fixed argv, never parsed strings.** Each entry in a small, hardcoded
  allowlist (`CommandSpec`) pairs an exact label — the same normalized string
  `workbench_trust.is_command_allowed` already evaluates — with a pre-built argv tuple. No label is
  ever split via `shlex` or otherwise parsed into argv at resolution time.
- **No dynamic args, no shell.** Every allowlist entry is complete and fixed; `is_command_label_allowed`
  requires an exact (whitespace-normalized, case-sensitive) match — an extra argument, a shell
  metacharacter, or a case change all resolve to "unknown", not a fuzzy match.
- **`sys.executable`-based, launcher-independent argv.** Python invocations use `sys.executable`, not
  a bare `"python"` string; `vibe` commands resolve to `[sys.executable, "-m", "backend.cli", ...]`
  rather than the OS-specific `vibe.ps1`/`.cmd`/`.sh` launcher scripts, so resolution is identical on
  Windows, macOS, and Linux.
- **`preview_command` is pure and never touches `subprocess`.** The module never imports `subprocess`;
  `preview_command`/`resolve_command_label`/`is_command_label_allowed` only resolve and describe —
  they cannot execute anything, regardless of input.
- **Two independent gates, both required.** `workbench_executor.validate_execution_invariant` now
  calls the resolver for `run_command` actions **after** the existing deterministic trust re-check
  passes; a `run_command` dry-run reports `would_execute=True` only if **both** trust and the resolver
  agree. Either failing blocks it — the resolver narrows, never widens, what trust already allows.
- **`ExecutionResult` gains command-preview fields** (`command_label`/`command_argv`/
  `command_timeout_seconds`/`command_output_limit_bytes`/`command_cwd`/`command_shell`), populated
  only for a successfully-previewed `run_command`; file-action (`write_file`/`edit_file`) results are
  unaffected.
- **Real execution is unchanged and still absent.** `REAL_EXEC_KINDS` still excludes `run_command`;
  `execute_action(..., dry_run=False)` for a command still raises `ExecutorError` regardless of
  whether it resolves — this PR only adds a *preview*, not a path to running anything.
- **The resolver's allowlist is a subset of trust's.** `workbench_trust._ALLOWED_COMMANDS` gained
  `"vibe context build"` (a documented gap from PR #78) so every resolver label is also
  trust-allowlisted; the resolver never claims to know a command trust hasn't already permitted.

## Rationale

- Resolving to a fixed argv (never parsing a string) closes the injection surface by construction,
  matching PR #78's design rather than approximating it with validation.
- Requiring both gates keeps the deterministic trust boundary the single authority while letting the
  resolver add strictly narrower, additional confidence (a command a human would recognize by its
  exact label) before real execution is ever built.
- Keeping this PR preview-only proves the resolution/argv model is correct under test before any
  subprocess is ever started — the same incremental pattern PR #73→#74 used for file execution.

## Alternatives considered

- **Parse the trust-allowlisted string into argv at resolve time** — rejected; reopens the
  string-to-argv ambiguity PR #78 explicitly closed by design.
- **Let the resolver have its own, independent command list not required to be trust-allowlisted** —
  rejected; would let the resolver widen what's effectively executable beyond what trust permits.
- **Implement real execution in this PR** — rejected; §13 of the PR #78 plan calls for the resolver
  and dry-run to land first and be proven before any subprocess is started.
- **Shell out via `vibe.ps1`/`.cmd`/`.sh`** — rejected; adds OS-specific indirection and a real
  portability/availability risk the `sys.executable` module-invocation approach avoids.

## Consequences

- `run_command` dry-run previews are now meaningfully informative (exact argv, timeout, output cap)
  without any new ability to execute anything.
- PR #80 (real execution) can build directly on `resolve_command_label`/`CommandSpec` instead of
  inventing its own mapping.
- No dependency/provider/network change; `run_command` real execution remains exactly as fail-closed
  as before this PR.

## Next actions

- PR #80: real execution for allowlisted commands, behind the full invariant + timeout/output/env/cwd
  guards, in a temp/test-safe scope first.
- PR #81: panel display for command results, after PR #80 is proven.

## Related links

- Plan: [command execution](../plans/v0.5-command-execution.md)
- Decision: [command execution plan](./2026-07-02-workbench-command-execution-plan.md)
- Executor: [dry-run executor](./2026-07-01-workbench-executor-dry-run.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
