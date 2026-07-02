---
id: DEC-20260701-workbench-approval-auditor
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, approval, auditor, safety]
related: [DEC-20260701-workbench-trust-boundary, DEC-20260701-workbench-orchestrator-state-machine, DEC-20260701-v0.5-workbench-roadmap]
published: true
---

# Approval Auditor is advisory — it summarizes the deterministic guard, never overrides it

## Context

PR #66 added the deterministic trust boundary (the real security gate). The Workbench still needs a
human-facing **approval card**: a short risk summary + a readable approval prompt for the future
panel. The council correction was explicit that an LLM must **not** be the security boundary, so this
layer must be advisory.

## Decision

Add `backend/workbench_auditor.py` (stdlib-only) — an **advisory** Approval Auditor.

- **Functions:** `audit_action`, `audit_action_payload`, `audit_approval_request` (with `save`),
  `rewrite_approval_prompt`, `audit_summary`.
- It runs the deterministic trust evaluation and produces a runtime `AuditResult` whose
  `risk_level`, `blocked`, and `findings` are **copied verbatim** from that evaluation — the auditor
  never computes risk on its own. This makes the safety invariant hold **by construction**:
  - trust `blocked` → audit `blocked` (blocked stays blocked);
  - trust `high` risk cannot be lowered;
  - a requires-approval / cloud-egress-missing / secret-path / unknown-kind result is preserved;
  - the human-readable rewrite **adds** a summary and never drops a critical finding.
- **First version is deterministic / rule-based** (`model = "deterministic"`, no LLM). The prompt
  rewrite uses short deterministic templates ("Approve write_file `docs/foo.md`? Medium risk: write
  requires human approval." / "Blocked: … denied file pattern: *.key."). A later PR may add an
  optional model-assisted rewrite behind the provider abstraction — **still advisory, still unable to
  relax the guard.**
- **No side effects beyond `.council/runtime/`:** with `save=True`, `audit_approval_request` persists
  the `AuditResult` and attaches its id to the approval; otherwise nothing is written. No panel, no
  action execution, no provider/model/network, no git/shell.

## Rationale

- Deriving the audit entirely from the deterministic result guarantees the "advisory-only" invariant
  without trusting the auditor's own judgement — exactly the boundary discipline the roadmap requires.
- Shipping a deterministic rewrite first fixes the API and the invariant so the panel (and a later
  model-assisted rewrite) can build on a stable, safe contract.

## Alternatives considered

- **Let the auditor compute/adjust risk** — rejected; it could disagree with the guard and create a
  false sense of safety. Risk/blocked come only from the deterministic evaluation.
- **Use an LLM for the rewrite now** — deferred; not needed for the MVP and adds provider coupling;
  deterministic templates are enough and keep this PR offline.
- **Store a bespoke audit model** — rejected; reuse the existing runtime `AuditResult`.

## Consequences

- The Workbench can produce panel-ready approval cards (risk + findings + readable prompt) that can
  never be more permissive than the deterministic guard.
- No dependency/provider change; no new CLI/MCP surface; runtime files stay gitignored/local.

## Next actions

- Next PR: the **local panel** — render stages + the approval inbox (using these AuditResults) with
  approve/reject/hold; still no action execution until the executor lands behind the guard.
- Later: optional model-assisted rewrite behind the provider abstraction (advisory only).

## Related links

- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
- Orchestrator: [orchestrator / state machine](./2026-07-01-workbench-orchestrator-state-machine.md)
- Plan: [v0.5 Workbench MVP](../plans/v0.5-workbench-mvp.md)
