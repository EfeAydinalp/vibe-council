---
id: DEC-20260701-workbench-trust-boundary
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, security, trust-boundary, approval, safety]
related: [DEC-20260701-workbench-orchestrator-state-machine, DEC-20260701-v0.5-workbench-roadmap, DEC-20260630-redaction-guard]
published: true
---

# Deterministic trust boundary is the Workbench's real security gate (Auditor is advisory)

## Context

The Workbench orchestrator (PR #65) can record a `pending` Action on approval but nothing runs. Both
council passes were emphatic: **an LLM is not a security boundary.** Before any executor exists, the
Workbench needs a **deterministic** guard that classifies proposed actions in code. The (later)
Approval Auditor AI is only advisory and must never relax this gate.

## Decision

Add `backend/workbench_trust.py` (stdlib-only) — a pure, deterministic evaluator.

- **`evaluate_action` / `evaluate_action_payload`** return a `TrustEvaluation`
  (`allowed` / `blocked` / `requires_approval`, `risk_level` `low|medium|high|blocked`, `findings`,
  `normalized_kind`/`normalized_target`, `reason`, `cloud_egress_required`/`cloud_egress_approved`,
  `guard_version`). Same input → same result; **no I/O, no execution, no model/network**.
- **Default stance (conservative):** unknown action kind → **blocked**; command execution →
  **blocked** unless the exact command is allowlisted, and **any shell metacharacter**
  (`; && || | > < \` $()`) → blocked; **reads** allowed only inside the project root and outside
  denied/secret paths; **writes/edits** → **require approval** and pass path/secret/size checks;
  **cloud calls** → require explicit **cloud-egress consent** metadata (blocked without it) and are
  **never auto-allowed** (human approval still required).
- **Deterministic path containment** (lexical; no fs/symlink dependency): out-of-project paths and
  `..` traversal are blocked; denied segments (`.env`, `.git`, `.ssh`, `.venv`, `node_modules`,
  `data`, `.council`, `.obsidian`) and secret globs (`.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`,
  `id_rsa`, `id_ed25519`) are blocked; and the two known private/local plan files under
  `docs/plans/` are blocked by exact relative path (kept in the policy denylist).
- **`TrustPolicy`** captures the rules (read/write roots, denied paths/globs/relpaths, command
  allowlist, `max_files_changed`/`max_lines_changed`, `allow_network`, `allow_cloud`, secret
  patterns); `default_policy()` starts conservative.
- **Optional light integration:** `evaluate_pending_actions()` reads `pending` actions from the
  runtime store and evaluates them **read-only** — it executes nothing and mutates nothing; the
  orchestrator/executor are not modified here.

**The Approval Auditor AI (next PR) is advisory only** — it adds a risk label + human-readable
summary on top of this deterministic result and can escalate, but it can never turn a `blocked`
into allowed.

## Rationale

- Anchoring security in deterministic code (not an LLM) makes the approval boundary trustworthy and
  auditable, exactly as the council correction required.
- Evaluating before any executor exists means the guard is proven and testable before anything can
  run; the executor simply refuses to run a non-`allowed` action.
- Cloud-egress consent modeled explicitly keeps the local-first trust boundary honest (nothing
  sensitive leaves the machine without consent, and secrets in egress are blocked outright).

## Alternatives considered

- **Let the Approval Auditor gate actions** — rejected; an LLM is stochastic/manipulable and cannot
  be the boundary.
- **Allow arbitrary commands with a denylist** — rejected; command execution is blocked unless
  explicitly allowlisted (allowlist > denylist for exec).
- **Resolve symlinks / touch the filesystem during evaluation** — rejected; evaluation stays lexical
  and deterministic (the executor resolves for real later).
- **Enforce in the orchestrator now** — deferred; this PR ships pure evaluation + a read-only helper;
  enforcement lands with the executor.

## Consequences

- The Workbench has a tested deterministic guard; unknown/risky actions are blocked, writes require
  approval, secrets/private paths are blocked, and cloud egress needs consent — all without running
  anything.
- Next layers (advisory Approval Auditor → panel → executor) consult this guard; no dependency/
  provider change; no new CLI/MCP surface; runtime files stay gitignored/local.

## Next actions

- Next PR: the **hybrid Approval Auditor** (deterministic checks from this guard + one low-temp AI
  call for a risk label and a short human-readable approval rewrite) — advisory over this boundary.

## Related links

- Orchestrator: [orchestrator / state machine](./2026-07-01-workbench-orchestrator-state-machine.md)
- Redaction: [redaction guard](./2026-06-30-redaction-guard.md)
- Plan: [v0.5 Workbench MVP](../plans/v0.5-workbench-mvp.md)
