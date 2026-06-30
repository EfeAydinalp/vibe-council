---
id: DEC-20260630-operator-status-mvp
status: accepted
date: 2026-06-30
tags: [cli, operator, local-first, v0.3]
related: [DEC-20260629-operator-control-loop, DEC-20260630-redaction-guard, DEC-20260629-track-based-roadmap]
published: true
---

# Operator status MVP (`vibe operator status`)

## Context

The [operator control loop spec](../plans/operator-control-loop-and-approval-inbox.md) describes a
minimal, local-first approval/status surface so users don't miss when a run is waiting for them. This
is the first tiny slice: a status command, with no event log, notifications, dashboard, or transport.

## Decision

Add `vibe operator status` (in `backend/operator.py`, stdlib-only, no model/API/network):

- **Reads** a single gitignored `.council/operator/status.json`. If missing, prints
  "No operator status yet." and exits 0. Invalid JSON fails cleanly (clear message, non-zero, no
  traceback). `--json` for machine-readable output.
- **Schema (v1):** `version`, `updated_at` (ISO-8601), `state`
  (`needs_input` / `failed` / `done` / `running` / `idle`), `source`, `message`, `next_action`,
  `severity` (`info` / `warning` / `error`).
- **Writer** (`vibe operator set`): validates `state`/`severity`, sanitizes + caps free-text fields,
  creates the parent dir, and **only ever writes `.council/operator/status.json`** (never outside the
  operator dir). `vibe operator clear` removes the file. Neither stages/commits.
- **MVP is local status only.** It does **not** read raw `.council/` run logs, write event logs, send
  notifications, or open any transport.

## Rationale

- A single small status file is the cheapest useful version of the operator loop — it answers
  "done / failed / needs input" without building infrastructure.
- Keeping it local/gitignored and validation-guarded preserves the local-first, no-surprise-commit
  posture and avoids leaking content.
- A human-readable state supports **Remote Control-friendly** workflows (surface a clear decision
  point inside a Remote-Control'd Claude Code session) **without a custom mobile/remote transport**.

## Alternatives considered

- **An append-only event log + notifications now** — deferred; the spec's "early shape" is a status
  file first; events/notifications are a later milestone.
- **A dashboard / mobile app / custom remote transport** — rejected; out of scope and a security
  liability (design around official Claude Remote Control instead).
- **Read-only status with no writer** — the writer is small and safe, so `set`/`clear` are included,
  constrained to the operator dir.

## Consequences

- A minimal, scriptable status surface exists; status is **not canonical project memory** — it is
  ephemeral and local, never committed.
- Event logs, notifications, dashboard, mobile, MCP, and remote approval remain **deferred**.
- New module + tests; no provider behavior change, no new dependencies.

## Next actions

- Later (per the spec/roadmap): an append-only event log, terminal/desktop notifications, and MCP
  read-only visibility — each prerequisite-gated.
- Keep status files local/gitignored; never promote them into curated docs.

## Related links

- Spec: [operator control loop / approval inbox](../plans/operator-control-loop-and-approval-inbox.md)
- Related: [operator control loop decision](./2026-06-29-operator-control-loop.md),
  [track-based roadmap](./2026-06-29-track-based-roadmap.md)
