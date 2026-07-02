---
id: DEC-20260701-workbench-guarded-executor-plan
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, executor, security, safety, plan]
related: [DEC-20260701-workbench-local-panel, DEC-20260701-workbench-trust-boundary, DEC-20260701-workbench-approval-auditor]
published: true
---

# Plan the guarded executor before building it (execution is a new risk boundary)

## Context

The Workbench see→decide loop is visible and **non-executing** (runtime store → orchestrator →
deterministic trust boundary → advisory Approval Auditor → localhost panel). The next step is
**guarded execution** — the first layer that could modify files or run commands. Because that crosses
a real risk boundary, it gets a design/safety plan first ([guarded executor plan](../plans/v0.5-guarded-executor.md)).

## Decision

Accept a design/safety plan for the guarded executor; **implement no execution in this PR.**

- **The guarded executor is a new risk boundary** and is treated as such: tiny first scope, explicit
  invariant, and stop conditions.
- **Execution is separate from approval.** Approving records intent (today's behavior); executing is
  a distinct, explicit step. The panel must **never auto-execute on approve**.
- **The deterministic trust boundary is re-run at execution time.** A stored `AuditResult` is
  advisory only and **cannot authorize execution**; the Approval Auditor never gates.
- **The first executor is tiny and dry-run-first:** bounded `write_file`/`edit_file` (and, later,
  only exact allowlisted `run_command`), previewing side effects with **no mutation** until a
  subsequent opt-in PR. It refuses unless the full execution invariant holds (approved approval,
  pending linked action, fresh non-blocked trust check, supported kind, matching scope, logged).
- **Every attempt is logged** (status/timestamps/summary/trust verdict/version/error) with **no raw
  secrets** (redaction reused); no partial side effects.
- **Stop conditions** (halt + review): scope beyond bounded file write/edit, arbitrary command
  execution, any cloud/network execution, blocked actions appearing executable, approval bypass,
  path/symlink uncertainty, concurrency/race risk, or pressure to let the advisory Auditor authorize.
- **Recommended sequence:** PR #73 executor skeleton (dry-run only) → PR #74 bounded file write/edit →
  PR #75 exact allowlisted commands (if still needed) → PR #76 panel execute button.

## Rationale

- Execution is the highest-risk surface in the Workbench; a written invariant + dry-run-first + stop
  conditions make it safe to build incrementally and reviewably.
- Re-checking the deterministic guard at execution time (not trusting a stale advisory audit) keeps
  the boundary authoritative even if the proposed action changed after approval.
- Separating approve from execute is the primary guard against accidental side effects.

## Alternatives considered

- **Auto-execute on approve** — rejected; conflates intent with action and invites accidents.
- **Trust the stored audit to authorize** — rejected; the audit is advisory; the deterministic guard
  must re-run at execution time.
- **Start with arbitrary command execution** — rejected; bounded file write/edit is a smaller surface;
  commands come later (or not at all) behind the allowlist.
- **Skip a plan and implement directly** — rejected; execution warrants an explicit safety design.

## Consequences

- The executor track has a clear, testable safety contract before any code; PRs #73–#76 build to it.
- No execution/executor/CLI/panel change in this PR; the loop stays non-executing.
- License/provenance remains the commercial "Question 0".

## Next actions

- PR #73: executor **skeleton, dry-run only** — full invariant + security-case tests; mutates nothing.

## Related links

- Plan: [v0.5 guarded executor](../plans/v0.5-guarded-executor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
- Auditor: [approval auditor](./2026-07-01-workbench-approval-auditor.md)
- Panel: [local panel](./2026-07-01-workbench-local-panel.md)
