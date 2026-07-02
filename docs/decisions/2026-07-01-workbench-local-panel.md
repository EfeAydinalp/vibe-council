---
id: DEC-20260701-workbench-local-panel
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, panel, ui, approval, safety]
related: [DEC-20260701-workbench-approval-auditor, DEC-20260701-workbench-trust-boundary, DEC-20260701-workbench-orchestrator-state-machine]
published: true
---

# First Workbench panel is localhost-only and records decisions (no execution)

## Context

The v0.5 slice needed a first **user-visible** surface: PR #64–#69 built the runtime store,
orchestrator, deterministic trust boundary, and advisory Approval Auditor, but nothing rendered them.
This PR adds a minimal panel so a human can *see* task progress + approval cards and act on them.

## Decision

Add `backend/workbench_panel.py` + a minimal `vibe workbench serve` (stdlib `http.server`).

- **Localhost-only:** binds `127.0.0.1`; `make_server` refuses non-local hosts (no `0.0.0.0`, no
  LAN/mobile/remote). The URL is printed on start.
- **Endpoints:** `GET /` (inline HTML panel), `GET /api/state` (tasks + pending approvals + advisory
  audit summaries + progress), `POST /api/approvals/<id>/{approve,reject,hold}`, and an optional
  local `POST /api/tasks/demo` for dogfooding. Unknown routes/ids/decisions → 404/400.
- **Decisions only — never executes.** Approve/reject/hold calls the orchestrator's
  `decide_approval` (records an `ApprovalDecision`, advances lifecycle). It **does not** run a
  command, edit a file, touch git, promote a decision, call a provider/model, or `mark_executing`.
  The UI states "no action execution" plainly, and responses carry `executed: false`.
- **State is read via the advisory audit** (`audit_approval_request(save=False)`) — so `GET`
  requests do not mutate runtime state.
- **Minimal auth:** a random startup token is required for POSTs (`X-Workbench-Token` header or
  `?token=`); GET is open on localhost. No CORS wildcard. Inline HTML/CSS/JS only — **no npm,
  React/Vite, external CDN, or network egress.**

**Deliberately out of scope:** action execution / executor, LAN/mobile access, voice, WebSockets,
richer UI, provider/model calls, new MCP surface. Future mobile/voice/executor must build on the
deterministic guard + advisory auditor, not bypass them.

## Rationale

- A tiny localhost, non-executing panel proves the end-to-end loop (see → decide) with the least
  risk, and reuses the tested runtime/orchestrator/trust/auditor layers rather than reimplementing.
- Keeping execution out of the panel preserves the boundary discipline: a decision is recorded
  intent; running it is a separate, guarded step in a later PR.

## Alternatives considered

- **Execute on approve** — rejected; execution requires the executor + deterministic-guard
  enforcement first. The panel records decisions only.
- **A frontend framework / CDN assets** — rejected; stdlib + inline HTML keeps it dependency-free
  and offline.
- **Bind for LAN/mobile now** — rejected; deferred until token/QR/auth and a security design land.

## Consequences

- The Workbench has its first user-visible slice: progress + approval inbox with approve/reject/hold,
  localhost-only, non-executing. `vibe workbench serve` launches it.
- No dependency/provider change; no new MCP surface; runtime files stay gitignored/local.

## Next actions

- Next: a guarded **executor** (runs an approved action only if the deterministic trust boundary
  allows it), then LAN/mobile access behind token/QR auth, then voice.

## Related links

- Auditor: [approval auditor](./2026-07-01-workbench-approval-auditor.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
- Plan: [v0.5 Workbench MVP](../plans/v0.5-workbench-mvp.md)
