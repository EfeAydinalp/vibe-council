---
id: DEC-20260701-workbench-bounded-file-executor
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, executor, file, security, safety]
related: [DEC-20260701-workbench-executor-dry-run, DEC-20260701-workbench-guarded-executor-plan, DEC-20260701-workbench-trust-boundary]
published: true
---

# First real execution is bounded file write/edit only (commands stay deferred)

## Context

The dry-run executor (PR #73) validates the full execution invariant and re-runs the deterministic
trust boundary. This PR adds the **first real execution**, limited to very narrow file actions. It is
the first layer that actually modifies the filesystem, so it stays tightly bounded and fail-closed.

## Decision

Add real execution for **`write_file` and `edit_file` only**, via
`execute_action(action_id, dry_run=False, payload=...)` in `backend/workbench_executor.py`
(stdlib-only). Command execution and all other kinds remain deferred/rejected.

- **Execution is explicit and guarded.** Real execution runs only when the caller passes
  `dry_run=False` **and** the full invariant holds (approval exists and `approved`; action `pending`
  and linked; scope matches the approved scope; kind supported) **and** a **fresh** deterministic
  trust evaluation is re-run and not blocked. `run_command` (and any non-file kind) **fails closed**
  with an `ExecutorError`; a stored advisory audit can never authorize.
- **Payload is explicit.** The `Action` runtime model is unchanged; content/patch is passed in a
  `payload` dict — `write_file`: `content`, `overwrite`; `edit_file`: `old_text`, `new_text`,
  `max_replacements` (default 1). Runtime strings are never overloaded to carry content.
- **Bounded + atomic.** Conservative limits (write/edit ≤ 100 KB, 1 replacement default, ≤ 200-line
  delta); binary/NUL content blocked; writes/edits are **atomic** (temp file in the same dir, then
  `os.replace`). `write_file` to an existing file requires explicit `overwrite`; `edit_file` requires
  an exact `old_text` match and refuses ambiguous multi-match unless explicitly allowed.
- **Path guard (fs-level).** Beyond the lexical trust check, execution resolves the target under the
  project root with containment, **blocks symlinks / symlinked paths**, and blocks denied/private/
  secret/out-of-project paths — all **fail closed** (no mutation).
- **Logging without secrets.** Status transitions (`pending`→`completed`/`blocked`/`failed`),
  `started_at`/`completed_at`, `executor_version`, and a safe `result_summary` (bytes/paths, **never
  file content**) are recorded on the runtime action. Failures leave the action non-`completed` and
  perform no partial write.
- **Dry-run unchanged** and non-mutating; approval and execution remain separate; the panel is **not**
  wired to the executor in this PR.

## Rationale

- File write/edit is the smallest useful execution surface; proving it atomic, bounded, and
  path-guarded (with the invariant + fresh trust re-check) is a safe first real-execution step.
- Re-running the deterministic guard and keeping the payload explicit avoids both stale-audit
  authorization and ambiguous/unsafe string overloading.

## Alternatives considered

- **Add `run_command` execution now** — rejected; commands are a larger risk surface and stay
  deferred (fail-closed) to a later, allowlist-only PR.
- **Store content in the `Action` model** — rejected; pass payload explicitly instead of enlarging
  runtime records with potentially large/sensitive content.
- **Overwrite existing files by default** — rejected; overwrite requires explicit approval.
- **Wire the panel to execute** — deferred to a later PR; approval and execution stay separate.

## Consequences

- The Workbench can now really apply a narrow, approved, guarded file change; everything else
  (commands, cloud, network) remains blocked/deferred.
- No dependency/provider change; no CLI/panel/MCP surface change; runtime files stay gitignored/local.

## Next actions

- PR #75: execution payload bridge design — the `Action` model has no durable payload field, so the
  panel/CLI have nothing to execute against yet. See
  [payload bridge decision](./2026-07-02-workbench-payload-bridge.md).
- PR #76: payload artifact store + executor hash re-check (implements PR #75's design).
- PR #77: panel "Execute approved action" button + result display (dry-run preview first).
- PR #78 (optional): exact allowlisted `run_command` execution (`shell=False`, no metacharacters,
  timeout, captured output), re-checked at run time — only if still needed.

## Related links

- Dry-run: [dry-run executor](./2026-07-01-workbench-executor-dry-run.md)
- Plan: [guarded executor plan](../plans/v0.5-guarded-executor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
