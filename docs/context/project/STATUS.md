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
- **v0.5 local panel landed** (PR #70): `backend/workbench_panel.py` + `vibe workbench serve` — a
  **localhost-only** stdlib panel rendering task progress + approval cards (advisory audit summaries)
  with approve/reject/hold. Binds `127.0.0.1`, POSTs token-gated, inline HTML (no external assets).
  **Decisions only — no action execution, no provider/model calls.** See
  [`local panel`](../../decisions/2026-07-01-workbench-local-panel.md).
- **Panel dogfood polish** (PR #71): self-explanatory empty state + a **"Create demo task"** button
  (`POST /api/tasks/demo`, token-gated) that seeds a task + pending approval + saved advisory audit
  (local runtime only, executes nothing); clearer approval cards ("No action will run from this
  panel"). Still localhost-only and non-executing.
- **Guarded executor plan** (PR #72, docs-only): a design/safety plan gates the first execution layer
  — execution **separate from approval**, deterministic guard **re-run at execution time** (advisory
  Auditor never gates), first executor **tiny + dry-run-first**, with a stop-condition list. No
  execution added. See [`guarded executor plan`](../../plans/v0.5-guarded-executor.md) and
  [`decision`](../../decisions/2026-07-01-workbench-guarded-executor-plan.md).
- **v0.5 dry-run executor landed** (PR #73): `backend/workbench_executor.py` — a **dry-run-only**
  guarded executor that re-runs the deterministic trust guard, validates the full execution invariant
  (approved approval + pending linked action + matching scope + supported kind + fresh non-blocked
  trust), and previews what *would* happen. `execute_action(dry_run=False)` **fails closed**; writes/
  runs nothing; a stale advisory audit can't authorize. See
  [`dry-run executor`](../../decisions/2026-07-01-workbench-executor-dry-run.md).
- **v0.5 bounded file executor landed** (PR #74): `execute_action(dry_run=False, payload=...)` really
  runs **`write_file`/`edit_file`** behind the full invariant + fresh trust re-check — atomic writes,
  ≤100 KB / ≤200-line-delta limits, fs-level path/symlink guard, existing-file needs explicit
  overwrite, edit needs exact match, logs carry no content. **`run_command` real execution still
  rejected**; dry-run unchanged. See [`bounded file executor`](../../decisions/2026-07-01-workbench-bounded-file-executor.md).
- **PR #75 (docs-only) — payload bridge design landed.** The `Action` model has no durable payload
  field, so the panel/CLI have nothing to execute against yet. Designed a separate, local, gitignored
  `.council/runtime/payloads/<action_id>.json` artifact (hashed at/before approval, write-once after
  approval, hash + scope re-checked at execution time), plus panel-display and redaction-at-write-time
  requirements. **No code/schema/helper/executor/panel/`run_command` changes.** See
  [`payload bridge plan`](../../plans/v0.5-payload-bridge.md) and
  [`decision`](../../decisions/2026-07-02-workbench-payload-bridge.md).
- **PR #76 — payload store + executor hash verification landed.** `backend/workbench_payloads.py`
  implements the PR #75 design (write-once hashed artifacts over `.council/runtime/payloads/`); the
  executor now loads and verifies one (hash + kind/target/approval/task) when called without an
  explicit `payload`, **additional to** the fresh trust re-check. No panel/`run_command` change. See
  [`payload store`](../../decisions/2026-07-02-workbench-payload-store.md).
- **PR #77 — panel execute button landed.** `backend/workbench_panel.py`: `build_state()` gains a
  content-free per-action payload/risk/`executable` view; `POST /api/actions/<action_id>/execute`
  (token-gated, action id only — never content/patch) calls the executor, which loads/verifies the
  local payload artifact itself. Approve/reject/hold still never execute; `run_command` not offered.
  See [`panel execute`](../../decisions/2026-07-02-workbench-panel-execute.md).
- **PR #78 (docs-only) — allowlisted command execution planned.** No-shell, fixed-argv allowlist
  model for narrow verification commands only; extends the existing invariant (not a duplicate);
  conservative timeout/output/env/cwd defaults; explicit Windows/Linux-safe resolution.
  **No execution/executor/panel/CLI change — `run_command` still fails closed.** See
  [`command execution plan`](../../plans/v0.5-command-execution.md) and
  [`decision`](../../decisions/2026-07-02-workbench-command-execution-plan.md).
- **PR #79 — command allowlist/argv resolver + dry-run preview landed.**
  `backend/workbench_commands.py`: fixed label → argv allowlist (`sys.executable`-based, no
  OS-specific `vibe` launcher), pure `preview_command`. `run_command` dry-run now requires **both**
  the trust boundary and this resolver to pass before `would_execute=True`. Real execution still
  absent — `run_command` still fails closed. See
  [`command preview`](../../decisions/2026-07-02-workbench-command-preview.md).
- **PR #80 — real allowlisted command execution landed.** `run_command` joined
  `REAL_EXEC_KINDS`: `subprocess.run(shell=False)` with the PR #79 resolver's exact fixed argv,
  allowlist-built sanitized environment (no inherited API keys/credentials), project-root cwd, a
  timeout (fail-closed, no retry), and bounded/redaction-checked output capture. Every existing gate
  (approval/linkage/scope/fresh trust re-check/resolver) still applies unchanged. No panel/CLI change.
  See [`command executor`](../../decisions/2026-07-02-workbench-command-executor.md).
- **PR #81 — panel command display landed.** An approved, pending, resolver-allowlisted
  `run_command` action now shows a content-free command preview (label/argv/timeout/output cap/
  `shell=false`) and an "Execute approved command" button in the panel, gated by the same invariant as
  file actions. The browser sends only the action id; the execute handler never reads a request body.
  Results (exit code, timed-out/truncated flags, bounded/redacted output) come back in the response.
  This completes the v0.5 guarded-executor track. See
  [`panel command results`](../../decisions/2026-07-02-workbench-panel-command-results.md).
- **PR #82 — v0.5 release readiness checklist.** Docs-only: what v0.5 contains/excludes, a manual
  dogfood recipe (the demo seeds **no executable action** — real execution needs a manually seeded
  temp-project fixture), and smoke/security/release-blocker checklists before a v0.5.0 tag. Flags
  rising context-pack budget pressure — future decision records should stay concise. See
  [`release readiness`](../../decisions/2026-07-02-v0.5-release-readiness.md).
- **Current focus:** **v0.5 Workbench MVP** — the guarded executor track (PR #72–#81) is complete and
  readiness-checked (PR #82); not yet tagged. Next: dogfood on a real small repo, fix rough edges,
  then release notes. Execution stays separate from approval; mobile/voice deferred.

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
