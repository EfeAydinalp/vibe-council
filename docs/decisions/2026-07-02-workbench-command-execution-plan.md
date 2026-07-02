---
id: DEC-20260702-workbench-command-execution-plan
status: accepted
date: 2026-07-02
tags: [v0.5, workbench, executor, run_command, security, safety, plan]
related: [DEC-20260701-workbench-bounded-file-executor, DEC-20260701-workbench-guarded-executor-plan, DEC-20260701-workbench-trust-boundary, DEC-20260702-workbench-panel-execute]
published: true
---

# Plan real command execution as exact allowlisted verification commands only, before building it

## Context

`run_command` real execution has been fail-closed since the guarded executor began (PR #73–#77): the
trust boundary already evaluates `run_command` proposals (allowlist + no shell metacharacters), but
the executor rejects any real run with `ExecutorError`. This PR designs the narrow next step — real
execution of a small allowlist of read-only verification commands — before any code
([plan](../plans/v0.5-command-execution.md)).

## Decision

Accept a design/safety plan for allowlisted command execution; **implement no execution in this PR.**

- **Narrow purpose only.** Real `run_command` support exists only for project-verification commands
  (tests, lints, decision/context/MCP-health checks) — never a general shell. Non-allowlisted commands
  stay blocked, unchanged.
- **No shell, ever.** Execution uses `subprocess.run(argv, shell=False)`. Each allowlisted label
  (reusing `workbench_trust`'s existing exact-match allowlist) resolves to a **fixed, pre-built argv
  list** via a lookup table — never by splitting/parsing the label string at execution time. This
  removes string→argv ambiguity by construction, not by validation.
- **Execution invariant extends, not replaces, the existing one.** All of PR #73–#77's checks
  (approved approval, pending linked action, matching scope, fresh non-blocked trust re-check) still
  apply, plus: exact allowlist match, a fixed pre-built argv, a timeout, project-root cwd, a sanitized
  environment, bounded/redacted output capture, and a logged attempt.
- **Conservative defaults:** 60s timeout (kill + mark `failed` on expiry, never silently retried);
  64 KB combined stdout/stderr cap with a truncation marker; captured output runs through the existing
  redaction guard before being stored/shown, and a critical finding blocks rather than exposes it.
- **Sanitized environment and fixed cwd.** No secret/API-key passthrough, no `.env` loading by the
  executor, minimal explicit env (`PATH` + what's needed for stable output); cwd is always the project
  root, never derived from the action/approval.
- **Windows/Linux compatibility is addressed concretely:** allowlist entries resolve via
  `sys.executable` for Python invocations (not a bare `"python"` string) and bypass the OS-specific
  `vibe.ps1`/`.cmd`/`.sh` launchers in favor of `[sys.executable, "-m", "backend.cli", ...]` — the
  same canonical invocation CLAUDE.md already documents.
- **Panel/CLI wiring stays deferred**, matching the approve/execute separation established in
  PR #73–#77; a concrete test list and a stop-condition list are defined for the eventual
  implementation PR.

## Rationale

- Removing shell entirely (fixed argv, no string parsing) closes an entire class of injection risk by
  construction rather than by trying to validate a shell string safely.
- Extending the existing invariant (not duplicating it) keeps the deterministic guard the single
  source of truth, consistent with every prior executor PR in this track.
- Addressing Windows/Linux resolution now (before any code) avoids a class of "works on my OS" bug
  that would otherwise surface as a platform-specific security gap later.

## Alternatives considered

- **Accept a shell string and validate it (regex/metachar rejection)** — rejected; a blocklist
  approach to shell metacharacters is inherently incomplete compared to never invoking a shell.
- **Let allowlist entries accept dynamic/extra arguments** — rejected; any dynamic argument reopens
  the injection surface the fixed-argv design is meant to close.
- **Inherit the caller's full environment** — rejected; risks leaking API keys/credentials into a
  command's environment or output.
- **Implement execution directly in this PR** — rejected; command execution is a new risk boundary and
  gets a design/safety plan first, matching how file execution was planned (PR #72) before being built
  (PR #73–#74).

## Consequences

- The command-execution track has a concrete, testable safety contract before any code; PR #79–#81
  build to it.
- No execution/executor/panel/CLI change in this PR; `run_command` stays rejected exactly as before.
- License/provenance remains the unrelated "Question 0" gate.

## Next actions

- PR #79: command allowlist → argv resolution model + dry-run/preview only (no real execution).
- PR #80: real execution for allowlisted commands, behind the full invariant, in a temp/test-safe
  scope first.
- PR #81: panel display for command results, after PR #80 is proven.

## Related links

- Plan: [command execution](../plans/v0.5-command-execution.md)
- Plan: [guarded executor plan](../plans/v0.5-guarded-executor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
- Executor: [bounded file executor](./2026-07-01-workbench-bounded-file-executor.md)
- Panel: [panel execute](./2026-07-02-workbench-panel-execute.md)
