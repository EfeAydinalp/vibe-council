---
id: DEC-20260701-workbench-runtime-store
status: accepted
date: 2026-07-01
tags: [v0.5, workbench, runtime, data-model, safety]
related: [DEC-20260701-v0.5-workbench-roadmap, DEC-20260629-project-memory-folder-convention, DEC-20260630-operator-status-mvp]
published: true
---

# `.council/runtime/` is the Workbench's live workflow state (JSON, local, stdlib)

## Context

v0.5 is the AI Council Workbench MVP ([v0.5 plan](../plans/v0.5-workbench-mvp.md)); its first
implementation step is the runtime foundation the orchestrator, panel, and Approval Auditor will
build on. The Workbench needs **live workflow state** (tasks moving through stages, approval
requests/decisions, actions, audit results) — distinct from the curated long-term memory in
`docs/decisions/`.

## Decision

Add `backend/workbench_runtime.py` (stdlib-only): small dataclasses + a local JSON store.

- **`.council/runtime/` is the canonical live workflow state** for the Workbench, laid out as
  `tasks/`, `approvals/`, `audits/`, `actions/`, and an `index.json`. It is **local and gitignored**
  (under the already-ignored `.council/`) and is **never committed**.
- **Committed `docs/decisions/*.md` remain curated long-term memory** — the source-of-truth for
  *approved, completed* outcomes — **not** the live runtime DB. Runtime JSON never writes under
  `docs/`.
- **JSON first, stdlib-only** — `json` + `dataclasses`; **no DB dependency**, no server, no
  model/API/network, no git/shell, no action execution. Writes are atomic-ish (temp file then
  replace) and stable (UTF-8, sorted keys, indent 2); timestamps are ISO-like UTC.
- **Models:** `Task`, `Stage`, `ApprovalRequest`, `ApprovalDecision`, `Action`, `AuditResult`, with
  fixed status vocabularies (task/stage/approval/action) and a `low|medium|high|blocked` risk scale.
- **Safety:** ids are sanitized to `[A-Za-z0-9._-]`; every read/write is containment-guarded to stay
  directly inside its `.council/runtime/` subdir (path traversal is impossible); no absolute local
  paths are emitted in summaries.
- **The panel, orchestrator, and Approval Auditor build on this store** in later PRs. **No panel,
  server, orchestrator, auditor model call, mobile, or voice is in this PR.**

## Rationale

- A structured runtime store is the foundation the whole v0.5 slice flows from; keeping it JSON +
  stdlib matches the project's minimal-dependency, local-first posture.
- Separating live runtime JSON from curated Markdown decisions (a projection of approved outcomes)
  prevents coupling UX/runtime evolution to the committed log format — a point both council passes
  stressed.
- Containment + id sanitization keep the store safe by construction before any UI or execution lands.

## Alternatives considered

- **SQLite now** — deferred; JSON is enough for the MVP and adds no dependency. Revisit only if JSON
  proves insufficient.
- **Store runtime state in `docs/`** — rejected; runtime is ephemeral/local and must stay gitignored;
  `docs/decisions/` is curated memory only.
- **Add a CLI surface now** — declined; this PR is library/store only (no new CLI) to keep surface
  growth frozen until the panel exists.

## Consequences

- The Workbench has a tested, local, gitignored runtime store; later PRs add the orchestrator,
  deterministic trust boundary, advisory Approval Auditor, and the panel on top.
- No dependency/provider change; no new CLI/MCP surface; runtime files never staged/committed.

## Next actions

- Next PR: the **task orchestrator / 3-stage state machine** (deterministic, single-model) over this
  store; then the deterministic trust boundary, then the hybrid Approval Auditor, then the panel.

## Related links

- Plan: [v0.5 Workbench MVP](../plans/v0.5-workbench-mvp.md)
- Related: [v0.5 roadmap decision](./2026-07-01-v0.5-workbench-roadmap.md),
  [project-memory folder convention](./2026-06-29-project-memory-folder-convention.md),
  [operator status MVP](./2026-06-30-operator-status-mvp.md)
