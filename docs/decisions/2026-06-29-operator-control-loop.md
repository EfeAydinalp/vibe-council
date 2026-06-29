---
id: DEC-20260629-operator-control-loop
status: accepted
date: 2026-06-29
tags: [operator-inbox, approval, notifications, local-first, roadmap]
related: [DEC-20260629-track-based-roadmap, DEC-20260629-project-memory-folder-convention, DEC-20260629-external-tools-and-obsidian-research]
published: true
---

# Operator control loop / approval inbox

## Context

When running councils/agents, users can miss when Claude/agents are waiting for approval, a choice,
test results, PR/merge readiness, or a blocked state — the tool waits silently while the user is
elsewhere. A minimal coordination layer is needed, without drifting into a dashboard, a mobile app, or
a custom remote-control transport. Full design is in
[`docs/plans/operator-control-loop-and-approval-inbox.md`](../plans/operator-control-loop-and-approval-inbox.md).

## Decision

- **Adopt an operator control loop / approval inbox as a roadmap concept.**
- **Keep it local-first and minimal.**
- **Start with docs/spec only** (this PR); no implementation.
- **Later implementation may use a gitignored `.council/operator/` event model** (e.g.
  `events.jsonl` / `status.json`) — never committed.
- **Notifications must be redacted and minimal** — terse pointers, no secrets/prompts/diffs/raw output.
- **Phone/remote approval should design around official Claude Remote Control** instead of a custom
  transport.
- **Dashboard/orchestration remains later**, only after the context/memory layer works.

## Rationale

- Reduces missed approvals and idle waiting with a tiny, local surface over work that already happens
  locally.
- Designing around the official Remote Control primitive avoids owning auth/device-trust/relay
  complexity and the associated security liability.
- A spec-first, prerequisite-gated path keeps scope small and preserves the local-first trust model.

## Alternatives considered

- **Build a dashboard now** — rejected; premature, scope creep before the memory/context layer works.
- **Build a mobile approval app now** — rejected; heavy and undifferentiated.
- **Send full prompts/diffs to notifications** — rejected; leakage risk; emit redacted pointers only.
- **Make operator events canonical memory** — rejected; events are ephemeral/local, not source of truth.
- **Write-capable MCP early** — rejected; read-only first, writes behind approval later.
- **Hosted notification service early** — rejected; local-first first, no hosted dependency now.

## Consequences

- Reduces missed approvals and idle waiting.
- Keeps scope small (spec-first, prerequisite-gated).
- Preserves local-first trust (events stay in gitignored `.council/`, never auto-committed).
- Creates a path toward Remote Control-friendly workflows without a custom transport.
- Still requires careful **redaction and UX discipline** (severity gating to avoid approval fatigue).

## Next actions

- Land this docs/spec; defer any implementation to v0.3.x design → v0.4.0 early inbox per the roadmap.
- Keep operator events out of canonical memory; only human-promoted outcomes become decisions/STATUS.

## Related links

- Spec: [operator control loop / approval inbox](../plans/operator-control-loop-and-approval-inbox.md)
- Related: [track-based roadmap](./2026-06-29-track-based-roadmap.md),
  [project-memory folder convention](./2026-06-29-project-memory-folder-convention.md)
- Project memory: [`docs/context/project/STATUS.md`](../context/project/STATUS.md)
