---
id: DEC-20260701-workbench-orchestrator-state-machine
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, orchestrator, state-machine, safety]
related: [DEC-20260701-workbench-runtime-store, DEC-20260701-v0.5-workbench-roadmap, DEC-20260629-operator-control-loop]
published: true
---

# Workbench has a deterministic task lifecycle over `.council/runtime/` (no execution)

## Context

PR #64 added the runtime data models + `.council/runtime/` JSON store. The next v0.5 step is the
**orchestrator** that drives a task through its lifecycle, so later PRs (deterministic trust
boundary, Approval Auditor, panel) have a stable state machine to build on.

## Decision

Add `backend/workbench_orchestrator.py` (stdlib-only) — a deterministic lifecycle over the runtime
store:

- **State machine:** `planning → awaiting_approval → executing → completed`, with `reject → failed`,
  `hold → held`, and `fail_task`/`hold_task` reachable from any state.
- **Functions:** `start_task`, `add_planning_stage`, `request_approval`, `decide_approval`
  (approve/reject/hold), `mark_executing`, `complete_task`, `fail_task`, `hold_task`,
  `get_task_progress`, `list_pending_approvals`.
- **Panel-facing progress:** `get_task_progress` returns a small structured view (task id/title/
  status, current stage, completed stages, pending approvals, next action, active worker/model) —
  the backend state that will power the visible stage/progress indicator later. **No UI in this PR.**
- **No execution.** On approve + `mark_executing` the task moves to `executing` and records a
  **`pending` Action** (a placeholder for a later executor) — **it is never run**. `decide_approval`
  approve/reject/hold only updates runtime state.
- **Clean validation:** invalid transitions fail cleanly (`OrchestratorError`) — cannot approve an
  already-decided approval, cannot complete a task still `awaiting_approval`, cannot mark executing
  without an approved approval, unknown task/approval ids raise. Path traversal stays blocked by the
  runtime store.

**Deliberately NOT in this PR:** the deterministic path/command **trust boundary** (beyond lifecycle
checks), the **Approval Auditor** model call, action **execution**, and the **panel/server** — those
are separate later layers. No model/provider/network, no git/shell, no decision promotion, no MCP
surface change.

## Rationale

- A deterministic lifecycle is the backbone the trust boundary, auditor, and panel all attach to;
  keeping it side-effect-free (runtime state only) makes it safe and fully testable before any
  execution or UI lands.
- Recording a `pending` Action (rather than running it) cleanly separates "approved intent" from
  "execution", which is where the deterministic guard + executor will slot in next.

## Alternatives considered

- **Execute actions on approve** — rejected; execution requires the deterministic trust boundary
  first; this PR is lifecycle only.
- **Fold the Approval Auditor in here** — rejected; the auditor is a separate advisory layer.
- **Reject → held instead of failed** — chose `reject → failed` (a rejected approval ends the task);
  a user can still `hold_task` explicitly for pause/resume.
- **Add a CLI now** — declined; surface growth stays frozen until the panel exists.

## Consequences

- The Workbench has a tested, deterministic task/stage lifecycle with panel-friendly progress and a
  pending-approvals query; no actions execute and no models are called.
- Next layers (trust boundary → auditor → panel) build on this without changing it.
- No dependency/provider change; no new CLI/MCP surface; runtime files stay gitignored/local.

## Next actions

- Next PR: the **deterministic trust boundary** (path allow/deny, command allowlist, secret-file
  patterns, change-size limits, cloud-egress consent) that gates the `pending` Actions — the real
  security boundary — before any executor.

## Related links

- Store: [runtime store decision](./2026-07-01-workbench-runtime-store.md)
- Plan: [v0.5 Workbench MVP](../plans/v0.5-workbench-mvp.md)
- Related: [operator control loop](./2026-06-29-operator-control-loop.md)
