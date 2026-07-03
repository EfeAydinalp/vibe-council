# Status

_Snapshot date: **2026-07-03**._

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
- **PR #83 — v0.5.0 release notes prepared (not tagged).** `docs/releases/v0.5.0.md` written ahead of
  tagging, following the same pattern as prior releases. **No version bump, no `CHANGELOG.md` dated
  section, no git tag, no GitHub Release yet** — the repo still reports `0.4.0`; those steps follow
  `docs/release-checklist.md` once the readiness checklist (PR #82) is clean on a real repo.
- **PR #84 — v0.5.0 version bump + CHANGELOG.** `backend/__init__.py`/`pyproject.toml` now report
  `0.5.0`; `CHANGELOG.md` gained a dated `[0.5.0]` section.
- **`v0.5.0` is tagged** (annotated git tag `v0.5.0`, pushed to `origin`). The GitHub Release itself
  remains a separate manual step (using `docs/releases/v0.5.0.md` as the body).
- **v0.5.1 dogfood/hardening planned (PR #85, docs-only).** A checklist-driven pass — fresh-install
  (clean clone), Workbench panel smoke, Windows-specific verification, UX polish, and a security-
  regression re-check — before any v0.6 feature work. Named known issues: `uv.lock`'s stale self-
  version entry (pre-existing, not a blocker), context-pack budget running close to its limit, the
  demo intentionally seeding no executable action, and Windows/Linux parity still needing real-world
  verification. **No executor/panel/CLI change, no allowlist growth, no v0.6 start in this PR.** See
  [`v0.5.1 dogfood & hardening`](../../plans/v0.5.1-dogfood-hardening.md) and
  [`decision`](../../decisions/2026-07-02-v0.5.1-dogfood-hardening.md).
- **PR #86 — first clean-clone dogfood pass completed.** Ran the PR #85 checklist for real: clean
  clone → `uv sync` → version/doctor/status/presets → test suite → lint/decisions/context/MCP checks,
  plus an HTTP-level Workbench panel smoke (binding, page content, token gating). Everything matched
  the dev checkout (0 critical redaction, 21/21 context/MCP, 570 tests). Found and fixed three small
  docs bugs: README's post-`uv sync` example used a bare `python` command that fails without `uv run`
  (reproduced directly — same class of failure as running the test suite with the wrong interpreter);
  `vibe workbench serve --help`'s text was stale (predated PR #77/#80/#81's real execution); and the
  PR #85 checklist itself didn't name the venv interpreter for the test step. No executor/panel/CLI
  behavior changed (only a help string). See
  [`clean-clone dogfood report`](../../plans/v0.5.1-clean-clone-dogfood-report.md).
- **PR #87 — Workbench interactive smoke/shutdown follow-up.** Investigated PR #86's leftover-process
  finding: a `uv run`-wrapped launch can leave a child process running if only the outer `uv` process
  is killed — confirmed as a **`uv run` process-tree artifact** (a direct venv-python launch released
  the port cleanly every time), not a Workbench bug. Separately, a simulated Windows `CTRL_C_EVENT`
  didn't trigger shutdown within 8s in automated testing (with or without `uv run`); no human-attended
  real interactive terminal was available to confirm or rule out a real bug, so this stays
  **inconclusive** rather than a confirmed issue — the existing `serve_forever()`/`KeyboardInterrupt`
  code already follows the standard, correct pattern. A clean scratch-directory first-run pass (empty
  state, demo, approve, token-gating) all matched expectations. **No code changed.** See
  [`interactive smoke report`](../../plans/v0.5.1-workbench-interactive-smoke-report.md).
- **PR #88 — Windows shutdown/bind hardening, and a correction.** A maintainer's real manual Ctrl+C
  test (`uv run python -m backend.cli workbench serve`, Ctrl+C, prompt returned) was clean; a `netstat`
  listener seen afterward on the default port was fingerprinted as an unrelated local service
  (`PhoneScriptRunner`), not vibe-council — **corrects PR #87's "inconclusive" Ctrl+C finding: no
  confirmed shutdown or 0.0.0.0-bind bug.** Added defense-in-depth anyway: `make_server()` re-checks
  the actual bound address after `bind()` (not just the requested host string); `effective_bind_host()`
  and a pure, testable `_startup_lines()` helper so the printed URL can never drift from what's really
  bound; a regression test simulating Ctrl+C (`KeyboardInterrupt` from `serve_forever()`) that asserts
  `server_close()` really closes the socket. No change to the blocking serve loop, no new CLI flag —
  neither was warranted. See
  [`interactive smoke report`](../../plans/v0.5.1-workbench-interactive-smoke-report.md) §7.
- **PR #89 — manual execution dogfood: the real execute path verified end-to-end.** Manually seeded a
  `write_file` action and a `run_command` action (temp/safe project, `curl` against the panel's real
  HTTP API — no browser automation, matching PR #87's documented fallback) and confirmed both execute
  successfully, both fail closed for non-allowlisted commands / missing payloads, and a crafted
  request body (different target/content/command/argv/env/cwd/timeout) has **zero effect** — only the
  server-resolved action ever runs. Found and fixed two small display/metadata bugs (not security-
  relevant): `ExecutionResult.dry_run` stayed `true` on every real execution response, and a completed/
  blocked `run_command` action's card falsely claimed "does not resolve to an allowlisted argv". See
  [`manual execution dogfood report`](../../plans/v0.5.1-manual-execution-dogfood-report.md).
- **PR #90 — `uv.lock` self-version drift fixed.** Root cause: `uv.lock`'s local `vibe-council`
  package entry had read a stale `version = "0.2.0"` since the pre-v0.3.0 `1d6a3b9` project-rename
  sync — `pyproject.toml`/`backend/__init__.py` stayed correctly at `0.5.0` the whole time, only the
  lockfile's self-entry lagged. `uv sync` deterministically rewrites exactly that one line; no
  dependency package versions changed; a second `uv sync` afterward is a no-op (confirmed idempotent).
  Committed the one-line fix (precedent: `1d6a3b9` did the same kind of self-metadata sync). Stops the
  recurring accidental `uv.lock` diff several v0.5.1 dogfood passes had to explicitly avoid staging.
  No version bump, no dependency change, no executor/panel behavior change. See
  [`v0.5.1 dogfood & hardening`](../../plans/v0.5.1-dogfood-hardening.md) §8.
- **PR #91 — v0.5.1 release prep.** `backend/__init__.py`/`pyproject.toml` now report `0.5.1`;
  `uv.lock`'s self-version entry synced to match (one line, no dependency change — following
  `docs/release-checklist.md`'s documented-but-previously-unfollowed "run `uv lock` after every
  version bump" step, so this doesn't recur). `CHANGELOG.md` gained a dated `[0.5.1]` section and
  [`docs/releases/v0.5.1.md`](../../releases/v0.5.1.md) documents the patch: clean-clone/Windows
  dogfood (PR #86), interactive Workbench smoke (PR #87), localhost bind/shutdown hardening (PR
  #88), manual execution dogfood (PR #89), and `uv.lock` hygiene (PR #90). Security posture is
  explicitly unchanged (approval separate from execution, localhost-only + token-gated panel,
  local/gitignored write-once payload artifacts, fixed-argv `shell=False` commands, no allowlist
  growth). **No version bump beyond `0.5.1`, no tag, no GitHub Release** — those are manual
  follow-up steps once this PR merges.
- **PR #92 — Workbench Host-header validation + `/api/state` token gate (v0.5.2 hardening).** A Fable
  architecture review flagged a DNS-rebinding class gap before the v0.6 agent-proposal bridge: the
  panel binds `127.0.0.1` (good), but localhost binding alone doesn't stop a page whose domain
  re-resolves to `127.0.0.1` — the browser still sends that page's original `Host`. `GET /api/state`
  was also unauthenticated. Fix: every request's `Host` header must name a literal loopback host
  (`127.0.0.1`/`localhost`/`::1`, any port; a missing/malformed/multiple `Host` fails closed) via a
  new pure `host_header_is_local()` helper, checked before routing on `GET /`, `GET /api/state`, and
  all POSTs; and `GET /api/state` is now gated on the **same** startup token as the POST endpoints
  (accepted via `X-Workbench-Token` header or the `?token=` the panel URL already carries; the token
  is never echoed in JSON). `GET /` stays tokenless so the panel URL loads normally — its guard is
  Host validation. **No executor/panel execution behavior changed, no new endpoint, no CORS, no
  allowlist change, no dependency change, no version bump.** 585 tests (+9). Blast radius today is
  small; fixed before v0.6 fills the runtime store with approved-pending actions.
- **PR #92 merged** — Host-header validation + `/api/state` token gate are on `master` (v0.5.2
  hardening; not yet bundled into a tagged release).
- **Fable implementation pack (docs-only)** — `docs/fable/` now holds the full phase-by-phase plan
  for future work: current-state baseline, operating rules, product vision, the non-negotiable
  security invariants, the v0.5.2→v0.9+ roadmap, the **v0.6 agent-to-Workbench bridge** design +
  concrete proposal schema, the onboarding/session-launcher plan, the Obsidian-like project vault
  plan (extend `docs/context/`, not a new `.vibe/`), cross-project onboarding, the tighten-only
  personalization layer, website positioning, the open-core commercial path, an implementation
  playbook, and copy-paste Fable prompt templates. No code/tests/behavior change — it's the map for
  the next phases, with security invariants and roadmap as the source of truth. See
  [`docs/fable/README.md`](../../fable/README.md).
- **PR #94 — v0.5.2 release prep.** `backend/__init__.py`/`pyproject.toml` now report `0.5.2`;
  `uv.lock`'s self-version entry synced to match (one line, no dependency-graph change, per the
  release checklist's `uv lock` step). `CHANGELOG.md` gained a dated `[0.5.2]` section and
  [`docs/releases/v0.5.2.md`](../../releases/v0.5.2.md) documents the patch: Workbench Host-header
  validation + `/api/state` token gate (PR #92) and the `docs/fable/` implementation pack (PR #93).
  Security posture is explicitly unchanged/strengthened (no executor/trust/payload/allowlist
  behavior change, no new endpoint, no dependency change). **No version bump beyond `0.5.2`, no tag,
  no GitHub Release** — those are manual follow-up steps once this PR merges.
- **v0.5.2 is tagged.** Release prep (PR #94) merged and the `v0.5.2` annotated tag is pushed; the
  GitHub Release from [`docs/releases/v0.5.2.md`](../../releases/v0.5.2.md) is the remaining manual
  step.
- **v0.6 phase 1 — proposal schema + validation (`backend/workbench_proposals.py`).** The first
  agent-bridge slice per [`docs/fable/05`](../../fable/05-v0.6-agent-bridge.md)'s PR breakdown:
  proposal envelope **schema v1** (strict — unknown keys rejected at every level) and pure,
  fail-closed validation. Allowed kinds: `write_file`/`edit_file` (relative trust-checked targets,
  exact payload shapes, NUL/size caps mirroring executor bounds — executor stays the final
  authority) and `run_command` by **exact allowlist label only** (resolver ∧ trust, the executor's
  two-gate rule; freeform commands/argv/env/cwd/timeout/shell hard-rejected). Server-minted fields
  (ids, `payload_hash`, statuses, verdicts) reject on sight; `proposal_id` (future dedup key) is
  strictly charset-validated, never sanitized. **Validation only** — no importer, no store writes,
  no id minting, no execution, no `subprocess` import, no panel/CLI/network change. 48 new tests
  (635 total) including the five `docs/fable/06` examples verbatim and writes-nothing /
  never-imports-subprocess / errors-never-echo-content guarantees.
- **v0.6 phase 2 — proposal importer + `vibe workbench propose`
  (`backend/workbench_proposal_importer.py`).** A validated schema-v1 proposal becomes a runtime
  Task + pending ApprovalRequest + pending Action through the **existing, unchanged**
  trust/auditor/panel/executor path. All ids and the payload hash are **server-minted**; the
  internal `kind:target` convention is constructed server-side (agents never author it); file
  payloads live only in the write-once payload artifact — never in task/approval/action JSON or the
  dedup record (fingerprint hash only). **Dedup by `proposal_id`, globally** (deliberately not
  agent-scoped, so dedup never depends on spoofable identity): identical re-import returns the
  original ids; same id + materially different content = **conflict, fail closed**. CLI:
  `vibe workbench propose <file | ->` (stdin supported; JSON result on stdout, human summary on
  stderr, never raw payload; non-zero exit on failure; failed imports create no runtime files).
  Advisory audit saved on import. Tests prove an imported `write_file` executes through the
  **existing** executor after approval in a temp project, and blocks without approval. 26 new tests
  (663 total). No execution on import, no network endpoint, no panel change, no allowlist growth.
- **Model budget policy (binding):** **Fable = technical lead/architect only** from here — routine
  PRs are implemented by Opus/Sonnet. The remaining v0.6.0 sequence (panel agent badge → bridge docs
  → v0.6.0 release prep) with copy-paste implementer prompts and stop conditions lives in
  [`docs/fable/v0.6-followup-implementation-plan.md`](../../fable/v0.6-followup-implementation-plan.md).
- **Current focus:** **v0.6.0 agent bridge — phases 1–2 done (schema PR #95, importer PR #96).**
  Next per the follow-up plan: panel "proposed by agent" badge (display-only), agent bridge docs,
  then v0.6.0 release prep. No new network endpoint anywhere in v0.6.0. Deferred as before:
  personalization (v0.7), mobile/LAN/voice (v0.8), hosted/team (v0.9+).

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
