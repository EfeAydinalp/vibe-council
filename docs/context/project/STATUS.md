# Status

_Snapshot date: **2026-06-30**._

A short, current snapshot of where vibe-council is. See [`README.md`](./README.md) for what this
folder is, and [`docs/decisions/`](../../decisions/) for the canonical decision records.

## Current state

- **v0.2.0 released** (multi-provider milestone; 118 tests).
- **OpenRouter** is the default provider; **Ollama** local provider exists (`VIBE_OLLAMA_MODEL`).
- **`vibe doctor`** exists (no-token provider diagnostics).
- **PR #34 merged** — public research addendum + open-core commercial direction.
- **PR #35 merged** — track-based roadmap.
- **PR #36 merged** — project-memory folder convention (this `docs/context/project/` seed).
- **PR #37 merged** — operator control loop / approval inbox spec.
- **PR #38 merged** — redaction guard (`vibe lint --redaction` + redaction policy).
- **PR #39 merged** — license/provenance "Question 0" checklist (commercial gate).
- **PR #40 merged** — decision-memory CLI skeleton (`vibe decisions list/show/new/lint`).
- **PR #41 merged** — `vibe decisions promote` (safe draft → curated `docs/decisions/`).
- **PR #42 merged** — `vibe decisions new --from-run` (extract a LOCAL draft from raw council output).
- **PR #43 merged** — `vibe context build` (deterministic, local-first context-pack builder MVP).
- **PR #44 merged** — `vibe context check` (deterministic context-quality harness, not an LLM eval).
- **PR #45 merged** — `vibe operator status` (minimal local-first operator status MVP).
- **PR #46 merged** — `vibe context export claude-code` (local Claude Code context export MVP).
- **v0.3 decision-memory / context loop is implemented end-to-end** (extract → promote → lint →
  build → check → export, plus redaction guard and operator status).
- **v0.3.0 released** (decision-memory + curated project context; 209 tests).
- **v0.3.1 released** (tag `v0.3.1`): dogfood hardening (decision-CLI fixes, `context check` 21/21,
  CLI UX) + release-link hygiene; context-pack budget stabilized (trim order keeps core signals under
  the 14000 char budget; token-aware budget deferred — PR #55).
- **v0.4 read-only MCP (in progress):** contract + dependency-free read layer + a minimal stdlib
  stdio transport — `vibe mcp contract` / `inspect [--context --health]` / `serve --stdio`. Exposes
  status, curated decisions, and the context pack + health (`get_project_status` / `list_decisions` /
  `show_decision` / `get_context_pack` / `check_context_health`); **read-only, no `mcp` SDK, no
  `.council/` writes, no write/git/shell/provider tools**. See
  [`minimal MCP stdio transport`](../../decisions/2026-07-01-minimal-mcp-stdio-transport.md).
- **Context-pack core sections stabilized** (PR #60): core sections (decision index,
  rejected-alternatives index, human-review/source-of-truth constraints, status) are **compacted, not
  dropped** under budget pressure; full decision bodies are trimmed first. The required
  `section:decision-index` no longer falls off the 14000-char cliff. See
  [`critical-section budget`](../../decisions/2026-07-01-context-pack-critical-section-budget.md).
- **v0.4 read-only MCP track implemented + dogfooded:** setup docs
  ([`Claude Code / MCP setup`](../../mcp/claude-code-setup.md)) + dogfood
  ([`v0.4 MCP dogfood`](../../dogfood/v0.4-mcp-local-dogfood.md)) — stdio smoke, no-write + privacy
  audits pass; health 21/21.
- **v0.4.0 released** (tag `v0.4.0`) — read-only MCP / Claude Code workflow.
- **Roadmap corrected → v0.5 = AI Council Workbench MVP** (council pass accepted): build a **vertical
  slice** (task → visible stages → **audited approval** → safe execution → logged) for "safe repo
  changes with approval", reusing the v0.2–v0.4 infra. Deterministic guards are the security
  boundary; the Approval Auditor is advisory. "AI Council Workbench" is the near-term name; "AI
  project OS" stays long-term/internal. See [`v0.5 plan`](../../plans/v0.5-workbench-mvp.md) and
  [`v0.5 roadmap decision`](../../decisions/2026-07-01-v0.5-workbench-roadmap.md).
- **v0.5 runtime store landed** (PR #64): `backend/workbench_runtime.py` — `Task`/`Stage`/
  `ApprovalRequest`/`ApprovalDecision`/`Action`/`AuditResult` dataclasses + a gitignored
  `.council/runtime/{tasks,approvals,audits,actions}/ + index.json` JSON store (stdlib-only,
  atomic-ish, sorted-keys, id-sanitized/containment-guarded; no server/model/CLI). See
  [`runtime store`](../../decisions/2026-07-01-workbench-runtime-store.md).
- **v0.5 orchestrator landed** (PR #65): `backend/workbench_orchestrator.py` — deterministic task
  lifecycle over the runtime store (`start_task`/`request_approval`/`decide_approval`
  (approve/reject/hold)/`mark_executing`/`complete`/`fail`/`hold`) + `get_task_progress`
  (panel-friendly) + `list_pending_approvals`. **No action execution** (approve records a `pending`
  Action); no model/git/shell. See
  [`orchestrator`](../../decisions/2026-07-01-workbench-orchestrator-state-machine.md).
- **v0.5 trust boundary landed** (PR #66): `backend/workbench_trust.py` — deterministic action
  evaluation (allowed / blocked / requires-approval + risk + findings + cloud-egress consent).
  Unknown kinds + non-allowlisted/metachar commands blocked; writes require approval;
  secrets/`.git`/`.council`/private plans / out-of-project paths blocked; cloud needs consent, never
  auto-runs. **The real security gate; executes nothing.** See
  [`trust boundary`](../../decisions/2026-07-01-workbench-trust-boundary.md).
- **Agent quickstart added**: [`docs/agent-quickstart.md`](../../agent-quickstart.md) — a short,
  copy-paste-safe review → diff → decision recipe for humans and AI coding agents (council is advice,
  not authority; keep `.council/` gitignored; don't send secrets).
- **v0.5 Approval Auditor landed** (PR #69): `backend/workbench_auditor.py` — **advisory** layer that
  wraps the deterministic guard into an `AuditResult` (risk + findings + blocked + a short readable
  approval prompt). Risk/blocked/findings are copied verbatim from the trust evaluation, so it can
  **never relax** the guard; `model="deterministic"` (no LLM). No execution/provider calls. See
  [`approval auditor`](../../decisions/2026-07-01-workbench-approval-auditor.md).
- **Current focus:** **v0.5 Workbench MVP** — next: the **local panel** (render stages + the approval
  inbox using these AuditResults; approve/reject/hold). Execution stays behind the guard; mobile/voice
  deferred.

## Next actions

1. Next v0.4 PRs: MCP design skeleton → read-only server (status + decisions) → pack/health resource
   → Claude Code docs → dogfood → release prep.
2. Keep v0.4 **read-only**: no write-capable MCP, no remote approval transport, no hosted/sync.
3. Later: token-aware budget / rolling summaries; vector retrieval only if plain retrieval proves
   insufficient.
4. License/provenance "Question 0" remains the gate before any commercial step.

## Blockers / open risks

- **License/provenance remains Question 0** before serious commercialization.
- **Curation risk:** this memory is only valuable if it is actually curated.
- Avoid committing raw `.council/`, secrets, local paths, or private commercial details.
- Avoid overbuilding dashboard / vector / hosted layers before their prerequisites are met.

## Needs review

- Whether `README.md` + `STATUS.md` is enough for public project memory (vs adding more files).
- Whether `PROGRESS.md` should remain local/generated by default.
- How the extract/promote workflow should feed curated decisions / status later.
- How the operator approval inbox should be scoped (minimal, local-first first).
