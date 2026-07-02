---
id: DEC-20260701-workbench-executor-dry-run
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, executor, dry-run, security, safety]
related: [DEC-20260701-workbench-guarded-executor-plan, DEC-20260701-workbench-trust-boundary, DEC-20260701-workbench-approval-auditor]
published: true
---

# Guarded executor skeleton: dry-run only, invariant-validated, trust re-run at execution time

## Context

The [guarded executor plan](../plans/v0.5-guarded-executor.md) set the safety contract for the first
layer that could modify files / run commands. This PR is the **first implementation step**: an
executor skeleton that is **dry-run only** — it validates the full execution invariant and re-runs
the deterministic trust boundary, but performs no real execution.

## Decision

Add `backend/workbench_executor.py` (stdlib-only) — dry-run only.

- **Functions:** `dry_run_action`, `preview_action`, `validate_execution_invariant`,
  `execute_action`, `summarize_execution_result`; result type `ExecutionResult`.
- **Full execution invariant, validated per attempt** (fail-closed): the action exists and is
  `pending`; a linked approval exists and is `approved`; the action is linked to that approval/task;
  the kind is supported (`write_file`/`edit_file`/`run_command`); the action target/scope **matches
  the approved scope** (blocks "modified after approval"); and a **fresh** deterministic trust
  evaluation is not blocked. Any gap → `blocked`, `would_execute=False`.
- **Trust re-run at execution time.** The executor calls `workbench_trust.evaluate_action` on the
  current action every time; a stored `AuditResult` is **advisory** and **cannot authorize**
  execution (a test proves a stale "looks fine" audit can't let a secret-path write through).
- **Dry-run only / fail-closed.** `execute_action(dry_run=False)` raises "Real execution is not
  implemented yet." Dry-run returns a preview (`executed=false`, `would_execute` per the guard) and
  **performs no side effects** — no file write/edit, no command run, no git/shell/provider/network.
- **No runtime mutation by default.** Optional `record=True` writes only a non-final
  `result_summary` on the action (status stays `pending`); it never marks the action/task completed
  and never executes.
- **Approval and execution remain separate; the panel does not auto-execute** (the panel is not
  wired to the executor in this PR).

## Rationale

- Proving the invariant + trust re-run + no-mutation in a dry-run skeleton makes the highest-risk
  layer safe to grow incrementally; real writes (PR #74) reuse the same, already-tested gate.
- Re-running the deterministic guard (never trusting a stale advisory audit) keeps the boundary
  authoritative even if the proposed action changed after approval.

## Alternatives considered

- **Implement real writes now** — rejected; dry-run-first per the plan; real writes are the next PR.
- **Let the stored audit authorize** — rejected; the audit is advisory; the deterministic guard
  re-runs at execution time.
- **Wire the panel to execute** — rejected; approval and execution stay separate; panel execute is a
  later PR.
- **Add a CLI now** — declined; the executor is a library in this PR (no CLI/panel surface).

## Consequences

- The Workbench has a tested dry-run executor that classifies whether an approved action *would*
  execute, with the full invariant enforced and nothing run.
- No dependency/provider change; no CLI/panel/MCP surface change; runtime files stay gitignored/local.

## Next actions

- PR #74: bounded `write_file`/`edit_file` **real** execution behind this invariant (atomic
  temp-then-replace, size/line/file limits, logging + redaction), still opt-in and re-checked.

## Related links

- Plan: [guarded executor plan](../plans/v0.5-guarded-executor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
- Auditor: [approval auditor](./2026-07-01-workbench-approval-auditor.md)
