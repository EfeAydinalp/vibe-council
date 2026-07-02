---
id: DEC-20260702-workbench-payload-store
status: accepted
date: 2026-07-02
tags: [v0.5, workbench, executor, payload, security, safety]
related: [DEC-20260702-workbench-payload-bridge, DEC-20260701-workbench-bounded-file-executor, DEC-20260701-workbench-executor-dry-run, DEC-20260701-workbench-trust-boundary]
published: true
---

# Payload artifacts are local runtime records, verified by hash + scope before real file execution

## Context

PR #75 designed the execution payload bridge ([plan](../plans/v0.5-payload-bridge.md),
[decision](./2026-07-02-workbench-payload-bridge.md)): the `Action` model has no durable place to
carry `write_file`/`edit_file` content, leaving the panel/CLI nothing to execute against. This PR
implements that design.

## Decision

Add `backend/workbench_payloads.py` (stdlib-only) and extend `backend/workbench_executor.py`.

- **Payloads are local runtime artifacts, not `Action` fields** — `.council/runtime/payloads/
  <action_id>.json` (gitignored), never on `Action` itself, so ordinary `Action` reads stay
  payload-free.
- **`canonical_payload_hash(kind, target, payload)`** — deterministic sha256 over canonical JSON
  (sorted keys, compact separators), stable across key order, excludes timestamps/metadata.
- **`PayloadArtifact`** carries `action_id`/`task_id`/`approval_id`/`kind`/`target`/`payload`/
  `payload_hash`/`created_at`/summary metadata. `save_payload_artifact` is **write-once by default**
  (refuses to overwrite without explicit `overwrite=True`); `load_payload_artifact` reads it back.
- **Two verification levels:** `verify_payload_artifact` (hash self-consistency — was the file
  rewritten after creation) and `verify_payload_against_action` (adds a cross-check of `kind`/
  `target`/`action_id`/`task_id`/`approval_id` against the live records, catching an artifact built
  for, or copied onto, the wrong action).
- **Executor integration.** When `execute_action(..., payload=None)` (the new default), the executor
  loads and verifies the artifact **before** real `write_file`/`edit_file` execution — **additional
  to, never a replacement for,** the fresh deterministic trust re-check; a stale/advisory audit still
  cannot authorize. The explicit `payload=...` path from PR #74 is unchanged. Kind gating
  (`run_command` fails closed via `ExecutorError`) runs **before** any payload lookup.
- **Redaction stays content-free** — summaries carry kind/target/byte-counts/flags/hash-prefix only,
  never raw `content`/`old_text`/`new_text`.

## Rationale

- Keeping the artifact off `Action` avoids widening every routine runtime read and avoids reopening
  the overloaded-payload ambiguity PR #74 rejected.
- Hashing only execution-relevant fields makes "modified after approval" a cheap deterministic check.
- Cross-checking against live records (not just the artifact's own hash) catches an internally
  consistent artifact built for, or copied onto, the wrong action.

## Alternatives considered

- **Store payload on `Action`** — rejected in PR #75; unchanged here.
- **Trust the hash alone, skip the action cross-check** — rejected; a hash-valid artifact copied onto
  another action would otherwise pass unnoticed.
- **Drop the explicit `payload=` path** — rejected; PR #74 callers keep working unchanged.
- **Load payload before the kind check** — rejected during implementation; `run_command` should fail
  closed immediately, not attempt a pointless payload lookup first.

## Consequences

- The Workbench can execute an approved file action from a durable, local, hashed payload artifact —
  no caller has to thread content through from outside the runtime store.
- PR #77 (panel execute button) can build directly on `load_payload_artifact` +
  `verify_payload_against_action`.
- No dependency/provider/network change; `.council/runtime/payloads/` stays local and gitignored.

## Next actions

- PR #77: panel "Execute approved action" button, using this module, with a content-free preview.
- PR #78 (optional): exact allowlisted `run_command` execution — unrelated, after another review.

## Related links

- Plan: [payload bridge](../plans/v0.5-payload-bridge.md)
- Decision: [payload bridge design](./2026-07-02-workbench-payload-bridge.md)
- Executor: [bounded file executor](./2026-07-01-workbench-bounded-file-executor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
