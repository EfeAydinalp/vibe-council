---
id: DEC-20260702-workbench-panel-execute
status: accepted
date: 2026-07-02
tags: [v0.5, workbench, panel, executor, payload, security, safety]
related: [DEC-20260702-workbench-payload-store, DEC-20260701-workbench-bounded-file-executor, DEC-20260701-workbench-local-panel, DEC-20260701-workbench-trust-boundary]
published: true
---

# The panel can execute an approved bounded file action, but only by action id — never by content

## Context

PR #76 made the payload store durable and verifiable (`.council/runtime/payloads/<action_id>.json`,
hash + kind/target/approval/task checks in the executor). Until now the panel
(`backend/workbench_panel.py`) only recorded approve/reject/hold decisions and had no way to trigger
real execution. This PR wires an explicit, guarded execute path into the panel.

## Decision

Add a content-free action view to `build_state()` and a new, token-gated execute endpoint.

- **Approval and execution stay separate.** Approve/reject/hold still only record a decision.
  Execution is a distinct `POST /api/actions/<action_id>/execute`, gated by the same startup token as
  the existing approval/demo endpoints.
- **The browser sends only an action id — never payload content.** The handler never reads the POST
  body for this route; it calls `execute_action(action_id, dry_run=False)` with no payload, so the
  executor loads and verifies the local artifact itself (PR #76). This makes browser-side payload
  tampering structurally impossible, not just policy.
- **Fail-closed reuse, not reimplementation.** `handle_execute` does not re-check approval/action/
  payload state itself — it forwards to the executor and shapes its `ExecutionResult` into JSON
  (`executed`/`dry_run`/`allowed`/`blocked`/`action_id`/`kind`/`risk_level`/`findings`/`preview`/
  `reason`). An unsupported kind (`run_command`) raises `ExecutorError`, caught and returned as a 400.
  All other rejections (unapproved/rejected/held approval, non-pending action, missing/tampered/
  mismatched payload) come back as a `blocked` result with a reason — exactly the invariant chain PR
  #74–#76 already built and tested.
- **`_action_view`** (new, read-only, dry-run only) adds a per-action `executable` flag to state:
  `True` only when the action is `pending`, its kind is `write_file`/`edit_file`, a payload artifact
  exists and verifies against the live action/approval/task, and a fresh trust-boundary preview says
  `would_execute`. Payload display is content-free (`redacted_summary`: byte counts/flags/kind only).
- **UI.** A new "Actions" section renders each action's status, payload-verification state, risk/
  findings, and — only when `executable` — an "Execute approved file action" button behind a browser
  `confirm()` (UX friction only, not a security boundary).
- **Demo stays non-executing.** `create_demo_task` still creates no Action/payload: the panel's
  `project_root` is normally the user's real project, and there is no target that is both a real,
  writable path the trust boundary would allow *and* guaranteed harmless to write to by reflex-
  clicking a demo button. The approve-then-execute path is proven by temp-dir tests instead.

## Rationale

- Keeping the browser payload-free removes an entire class of tampering (a modified request body)
  without adding any new server-side validation — the existing hash/scope checks already cover it.
- Delegating to the executor's existing invariant instead of duplicating checks in the panel avoids
  two implementations drifting apart; the panel is a thin, testable router.
- A demo that could silently write into a real repo on a second click is a bigger risk than a demo
  that can't yet exercise real execution; temp-dir tests give equivalent coverage without that risk.

## Alternatives considered

- **Accept payload content in the execute request body** — rejected; defeats the point of a verified,
  tamper-evident local artifact and reopens browser-side injection.
- **Auto-execute on approve** — rejected; violates the approve/execute separation already established.
- **Give the demo a real executable target in the user's project** — rejected; no path is both
  trust-boundary-writable and safe to write reflexively; kept non-executing instead (see above).
- **Re-validate approval/payload state inside the panel before calling the executor** — rejected;
  duplicates the executor's invariant instead of reusing it, risking drift.

## Consequences

- A user can now complete the full see→decide→execute loop for one bounded file action end-to-end
  from the panel, with every guard from PR #73–#76 still enforced.
- `run_command` remains fully deferred; no new command execution surface exists anywhere.
- No dependency/provider/network change; localhost-only and token-gated behavior unchanged.

## Next actions

- PR #78 (optional): exact allowlisted `run_command` execution — unrelated, only after another review.

## Related links

- Decision: [payload store](./2026-07-02-workbench-payload-store.md)
- Executor: [bounded file executor](./2026-07-01-workbench-bounded-file-executor.md)
- Panel: [local panel](./2026-07-01-workbench-local-panel.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
