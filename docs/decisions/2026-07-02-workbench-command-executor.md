---
id: DEC-20260702-workbench-command-executor
status: accepted
date: 2026-07-02
tags: [v0.5, workbench, executor, run_command, security, safety]
related: [DEC-20260702-workbench-command-preview, DEC-20260702-workbench-command-execution-plan, DEC-20260701-workbench-bounded-file-executor, DEC-20260701-workbench-trust-boundary]
published: true
---

# Real command execution is limited to exact resolver labels, sandboxed argv/env/cwd, and stays fail-closed on any gap

## Context

PR #78 designed allowlisted command execution; PR #79 built the label→argv resolver and a dry-run
preview only. `run_command` real execution has been fail-closed since PR #73. This PR adds the real
execution itself, strictly for commands the PR #79 resolver already resolves.

## Decision

`run_command` joins `REAL_EXEC_KINDS`; `backend/workbench_executor.py` gains `_do_run_command`.

- **Real execution is limited to exact resolver labels.** Every real run goes through
  `validate_execution_invariant` first (approval approved, action pending and linked, scope matches,
  fresh trust boundary not blocked, **and** the PR #79 resolver resolves the label) — the same gate
  the dry-run preview already used. Nothing here relaxes it; any gap still blocks with no subprocess
  started.
- **Fixed argv, `shell=False`, always.** `subprocess.run(argv, shell=False, cwd=project_root,
  env=sanitized_env, timeout=..., capture_output=True, text=True)` uses the resolver's exact,
  pre-built argv — never a re-derived or `shlex`-parsed string, never dynamic arguments.
- **cwd is always the project root.** A belt-and-suspenders check (`_cwd_is_safe`) also refuses if the
  resolved root itself lands in a denied directory (`.council`, `.venv`, `.git`, `data`,
  `node_modules`) — defense in depth, since cwd is never derived from the action/approval/payload.
- **Environment is allowlist-built, not inherited.** Only `PATH` and `PYTHONIOENCODING=utf-8` are set
  by default; on Windows, `SystemRoot`/`SystemDrive` are also included (required for Windows
  subprocess/socket initialization — not secrets). No API keys, provider credentials, or `.env` values
  are ever passed through; there is no shell, so no shell startup files run either.
- **Timeout fails closed, no retry.** A `TimeoutExpired` marks the action `failed`, records the
  timeout reason, and returns — the executor never retries or leaves a process running.
- **Output is bounded and redaction-checked before storage.** Combined stdout+stderr is capped to the
  resolver's byte limit (stdout gets priority); the (already-capped) output is scanned with the
  existing redaction guard, and a **critical** finding blocks the result (`blocked`, output not
  stored) rather than persisting it. The runtime `result_summary` stays short (label + exit code,
  ≤2000 chars) — never a raw output blob, matching the file executor's existing log style.
- **Exit code determines outcome.** Exit `0` → action `completed`, `executed=True`. Nonzero exit →
  action `failed`, `executed=True` (the process *ran*, it just reported failure) — distinct from
  `blocked`/timeout, where `executed=False` because nothing valid completed.
- **No panel/CLI wiring.** The panel's `executable` flag still requires a verified payload artifact,
  and `run_command` actions never have one (payloads are file-only) — so the panel gains **no new
  UI/button** for commands even though the executor can now run allowlisted ones directly.

## Rationale

- Reusing `validate_execution_invariant` unchanged (rather than writing a parallel check) keeps the
  deterministic guard the single authority for every action kind, file or command.
- An allowlist-built environment (rather than a blocklist over the inherited one) makes "no secrets
  leak" true by construction, not by enumeration of what to strip.
- Distinguishing `executed=True/nonzero-exit` from `executed=False/blocked-or-timeout` gives callers
  an honest signal: did the sandboxed process run to completion at all, separate from whether the
  command itself succeeded.
- Redacting output before storage (not after) means a secret accidentally printed by an allowlisted
  command never reaches disk in the first place.

## Alternatives considered

- **Inherit the caller's environment and strip known secret names** — rejected; a blocklist is
  incomplete by construction (a new secret env var name is a new hole); the allowlist has no such gap.
- **Retry on timeout** — rejected; a hung/misbehaving process should surface as a clear failure, not
  be retried automatically.
- **Store full captured output** — rejected; violates the "bounded, no large/raw output" design and
  risks storing secrets a command printed.
- **Wire a panel button in this PR** — rejected; scoped out, matching the recommended sequence (PR #81
  after this one is proven).

## Consequences

- The Workbench can now really run a narrow set of read-only verification commands end-to-end
  (approve → execute → completed/failed), with the same safety chain as file actions.
- The panel is unaffected — no new capability is user-reachable without direct API/test use, since
  there's still no execute affordance for `run_command`.
- No dependency/provider/network change; `subprocess` is stdlib-only, already used elsewhere in the
  codebase (`backend/redaction.py`).

## Next actions

- PR #81: panel display for command results, only after this PR is proven in production use.

## Related links

- Plan: [command execution](../plans/v0.5-command-execution.md)
- Decision: [command preview](./2026-07-02-workbench-command-preview.md)
- Executor: [bounded file executor](./2026-07-01-workbench-bounded-file-executor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
