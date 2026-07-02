---
id: DEC-20260702-workbench-payload-bridge
status: accepted
date: 2026-07-02
tags: [v0.5, workbench, executor, payload, security, safety, plan]
related: [DEC-20260701-workbench-bounded-file-executor, DEC-20260701-workbench-executor-dry-run, DEC-20260701-workbench-guarded-executor-plan, DEC-20260701-workbench-trust-boundary]
published: true
---

# Execution payload lives in a separate, hashed, gitignored runtime artifact — not on the `Action` record

## Context

PR #74 added real, bounded execution for `write_file` / `edit_file`
(`execute_action(dry_run=False, payload=...)`), but kept the payload explicit and caller-supplied
rather than adding it to the runtime `Action` model
(see [bounded file executor decision](./2026-07-01-workbench-bounded-file-executor.md)). That is safe,
but it leaves no durable payload source for the panel (or any future CLI `execute` command) to read
between "approve" and "execute". Before adding a panel execute button or any command execution, this PR
designs the payload bridge — see [payload bridge plan](../plans/v0.5-payload-bridge.md).

## Decision

Accept a design/safety plan for the execution payload bridge; **implement no execution, panel, or CLI
change in this PR.**

- **Payload lives in a separate runtime artifact, not on `Action`.** New, local, gitignored
  `.council/runtime/payloads/<action_id>.json`, referenced by `action_id` — the `Action` model gains no
  new content fields, keeping every existing `Action` read (panel list, index, status summary)
  small and payload-free.
- **Two sha256 hashes, computed at/before approval:** `payload_hash` over `{kind, target, payload}`
  (the fields that drive execution) and `approved_scope_hash` over the approval's `scope`. Timestamps
  and redaction metadata are excluded from the hash so re-reads never look like tampering.
- **Write-once after approval.** No code path updates an existing payload artifact once its action has
  an approved approval linked to it; the executor recomputes `payload_hash` immediately before real
  execution and refuses (`blocked`) on any mismatch — this extends, not replaces, the existing
  approved-scope/target match check.
- **Executor re-check order extended:** load artifact → verify `kind`/`target` agree with the live
  `Action` → verify `payload_hash` → re-run the deterministic trust boundary against the artifact's
  actual target → only then execute. A stored `AuditResult` remains advisory-only, unchanged.
- **Redaction runs at payload-write time, not just execution time** — a payload that trips a critical
  secret finding is refused before it is ever written to disk, not discovered later.
- **Logging/panel display stay content-free by default:** logs and the future panel preview show
  kind/target/byte-or-line counts/hash/verdict, never raw `content`/`old_text`/`new_text` (an opt-in
  expansion can show a diff later; that's a future panel PR's concern, not this one's).
- **Chain of custody:** approval → payload artifact (hashed at/before approval) → live `Action` →
  executor (re-derives everything from the artifact's own recorded values, never from whatever a caller
  passes in) — preserving "approved scope == executed scope" end-to-end.

## Rationale

- Keeping payload off the `Action` record avoids widening every routine runtime read with potentially
  large or sensitive content, and avoids re-opening the "overloaded string" ambiguity PR #74 already
  rejected.
- Hashing the execution-relevant fields (not the whole artifact) and re-checking that hash immediately
  before execution turns "was this payload modified after approval" into a cheap, deterministic check
  instead of a trust assumption.
- Redacting at write time (not just execution time) fails closed earlier and keeps secrets out of the
  local runtime tree in the first place.

## Alternatives considered

- **Add `content`/`old_text`/`new_text` fields directly to the `Action` model** — rejected; enlarges
  every `Action` read with potentially sensitive/large content and reopens the overloaded-payload
  concern PR #74 deliberately avoided.
- **Skip hashing and just re-read the artifact at execution time** — rejected; without a hash recorded
  at approval time there is no way to detect the artifact was silently rewritten after approval.
- **Encrypt the payload artifact at rest** — rejected for now; it is local-only runtime state at the
  same trust level as the rest of `.council/runtime/`, and encryption adds complexity without a network
  or multi-user threat model to justify it yet.
- **Let the panel write and immediately execute a payload in one step** — rejected; violates the
  existing approve/execute separation invariant.

## Consequences

- The payload bridge is fully specified (storage location, shape, hashing, re-check order, display,
  logging, tamper tests) before any panel/CLI code touches it.
- `execute_action`'s existing `payload=` calling convention for direct/test callers is unaffected in
  this PR; a future implementation PR decides whether panel/CLI callers pass `action_id` only and let
  the executor load the artifact itself.
- No dependency/provider/network change; no `run_command` scope change; `.council/runtime/` stays local
  and gitignored.

## Next actions

- PR #76: payload artifact store (create/load/hash helpers) + executor-side hash re-check + tamper
  scenario tests (missing artifact, hash mismatch, kind/target mismatch, cross-action artifact reuse,
  secret-pattern payload refused at write time).
- PR #77: panel "Execute approved action" button, reading the payload artifact and showing the §8
  preview from the plan doc.
- PR #78 (optional): exact allowlisted `run_command` execution — unrelated to this bridge, only after
  another review.

## Related links

- Plan: [payload bridge](../plans/v0.5-payload-bridge.md)
- Executor: [bounded file executor](./2026-07-01-workbench-bounded-file-executor.md)
- Executor: [dry-run executor](./2026-07-01-workbench-executor-dry-run.md)
- Plan: [guarded executor plan](../plans/v0.5-guarded-executor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
