# vibe-council — agent brief (curated dogfood seed)

A concise, **curated and redacted** project brief for Claude Code and future agents. This is a
hand-written **dogfood seed**, not generated output — it distills the committed decision records
under [`docs/decisions/`](../decisions/). Future *generated* agent briefs should default to a
local, gitignored location and be committed only by explicit, redacted opt-in.

_Last curated: 2026-07-02 (vibe-council 0.4.0)._

## Project identity

**vibe-council** is a local-first AI "council" CLI: multiple LLMs collaboratively review or
answer, with anonymized peer ranking, decision memory, and cost/safety guardrails. The product
is the command-line interface; everything runs on the user's machine with their own API key.
Forked from and crediting [`karpathy/llm-council`](https://github.com/karpathy/llm-council) —
**preserve that attribution**.

## Current released state

- **v0.2.0** (tagged) — the multi-provider milestone (provider abstraction + local Ollama +
  `vibe doctor`). See [v0.2.0 release decision](../decisions/2026-06-29-v0.2-release.md).
- **v0.3.0** (released) — **local-first decision memory + curated project context**. The v0.3 loop
  exists **end-to-end**: extract (`decisions new --from-run`) → review/redact → `decisions promote`
  → `decisions lint` → `context build` → `context check` → `context export claude-code`, plus
  `vibe lint --redaction` and `operator status`. All deterministic and local-first; **generated
  context packs/exports stay local/gitignored**. See [v0.3.0 release notes](../releases/v0.3.0.md).
- **v0.3.1** (released) — **dogfood hardening** of that loop, **no new command surface**:
  `decisions promote` rejects placeholder-only drafts and writes curated `YYYY-MM-DD-slug.md`
  records; `decisions new --from-run` maps review sections into the draft; `context check` passes
  **21/21** on the real repo (explicit human-review signal in packs; default char budget 14000);
  plus a CLI UX pass. See [v0.3.1 release notes](../releases/v0.3.1.md). No commercial-clearance
  claim — license/provenance remains "Question 0".
- **v0.4.0** (released) — the **read-only MCP / Claude Code workflow** release:
  `vibe mcp contract` / `inspect` / `serve --stdio` expose curated decisions, status, and the context
  pack + health to Claude Code / local agents **with no write/action authority** (no promotion,
  file, git, shell, provider/model, or remote-approval tools). A minimal **stdlib** JSON-RPC stdio
  transport — **no `mcp` SDK dependency**; context reads are **in-memory / no `.council/` writes**.
  Curated docs stay source-of-truth; generated/local/private artifacts excluded by default. See
  [v0.4.0 release notes](../releases/v0.4.0.md). No commercial-clearance claim — license/provenance
  remains "Question 0".
- **v0.5** (next; roadmap corrected) — the **AI Council Workbench MVP**: a user-visible **vertical
  slice** (task → visible stages → **audited approval** → safe execution → logged) for "safe repo
  changes with approval", reusing the v0.2–v0.4 infra (MCP = read-only knowledge source;
  decisions/context = memory; operator status = the panel's status surface; `.council/` = local
  runtime). **Deterministic guards are the security boundary; the Approval Auditor is advisory.**
  Landed so far: the **runtime store** (`backend/workbench_runtime.py` — `Task`/`Stage`/
  `ApprovalRequest`/`ApprovalDecision`/`Action`/`AuditResult` + a gitignored `.council/runtime/` JSON
  store) and the **deterministic orchestrator** (`backend/workbench_orchestrator.py` — task lifecycle:
  start → plan → request approval → decide (approve/reject/hold) → mark executing → complete/fail/hold,
  + `get_task_progress` / `list_pending_approvals`). **No action execution** (approve records a
  `pending` Action), no model/git/shell; runtime state is live/local, curated `docs/decisions/` stays
  long-term memory. The **deterministic trust boundary** (`backend/workbench_trust.py`) is the **real
  security gate**: it classifies proposed actions (allowed/blocked/requires-approval + risk +
  cloud-egress consent) — unknown kinds + non-allowlisted/metachar commands blocked, writes require
  approval, secrets/`.git`/`.council`/private plans / out-of-project paths blocked, cloud needs
  consent — and **executes nothing**. The **advisory** Approval Auditor
  (`backend/workbench_auditor.py`) wraps that guard into a panel-ready `AuditResult` (risk + findings
  + a short readable approval prompt); it copies risk/blocked/findings verbatim from the guard, so it
  **can never relax** a blocked/high-risk decision (`model="deterministic"`, no LLM yet). A first
  **localhost-only panel** (`backend/workbench_panel.py` + `vibe workbench serve`) renders task
  progress + approval cards and records approve/reject/hold — **decisions only, no action execution,
  no provider calls, no LAN/mobile** (binds 127.0.0.1, POSTs token-gated). The panel starts empty and
  has a **"Create demo task"** button (`POST /api/tasks/demo`) that seeds a safe local approval
  (runtime-only, executes nothing) for first-time dogfood. The **guarded executor** is **planned in
  docs only** ([plan](../plans/v0.5-guarded-executor.md)): execution stays **separate from approval**,
  the deterministic guard is **re-run at execution time** (the advisory Auditor never authorizes), and
  the first executor is **tiny + dry-run-first**. The **dry-run executor**
  (`backend/workbench_executor.py`) now exists: it re-runs the deterministic guard, validates the
  full execution invariant, and previews what *would* happen — `execute_action(dry_run=False)` **fails
  closed** and it writes/runs nothing (a stale advisory audit cannot authorize). Real execution now
  exists for **bounded `write_file`/`edit_file` only** (`execute_action(dry_run=False, payload=...)`):
  atomic, ≤100 KB / ≤200-line-delta, fs-level path/symlink guard, existing-file needs explicit
  overwrite, edit needs an exact match, logs carry no content. **`run_command` real execution is
  still rejected** (fail-closed). The **execution payload bridge is now implemented**
  (`backend/workbench_payloads.py`, PR #76): a local, gitignored, write-once, hashed
  `.council/runtime/payloads/<action_id>.json` artifact carries `write_file`/`edit_file` content, and
  the executor verifies its hash + kind/target/approval/task agreement before real execution —
  **additional to**, never instead of, the fresh trust re-check. See
  [payload store decision](../decisions/2026-07-02-workbench-payload-store.md). The **panel can now
  execute** an approved bounded file action (`backend/workbench_panel.py`, PR #77): the browser sends
  only an action id to `POST /api/actions/<action_id>/execute` (token-gated) — never file content or
  patch text — and the executor loads/verifies the local payload artifact itself. Approving still
  never executes; a browser `confirm()` adds friction only, not a security boundary. `run_command` is
  not offered by the panel and stays rejected. See
  [panel execute decision](../decisions/2026-07-02-workbench-panel-execute.md). **Allowlisted command
  execution is now planned in docs only** (PR #78): a no-shell, fixed-argv allowlist (label → pre-
  built argv, never string-parsed), extending the existing invariant with a timeout, bounded/redacted
  output, sanitized environment, fixed project-root cwd, and explicit Windows/Linux-safe resolution.
  **No execution/executor/panel/CLI change yet — `run_command` still fails closed.** See
  [command execution plan](../plans/v0.5-command-execution.md). Next: an allowlist/argv model
  (dry-run only), then real allowlisted execution, then panel display; LAN/mobile + voice remain
  deferred.
  **Near-term product name: "AI Council Workbench"; "local-first AI project OS" stays long-term /
  internal — not near-term external messaging.** Mobile/voice/personalization deferred. See
  [v0.5 Workbench plan](../plans/v0.5-workbench-mvp.md),
  [v0.5 roadmap decision](../decisions/2026-07-01-v0.5-workbench-roadmap.md), and
  [runtime store decision](../decisions/2026-07-01-workbench-runtime-store.md).

## Provider architecture

- A minimal `Provider` seam (`ChatRequest` / `ChatResult`) sits under the council.
- **OpenRouter** is the default (`VIBE_PROVIDER=openrouter`).
- **Local Ollama** (`VIBE_PROVIDER=ollama`): no API key, loopback-only host, never fabricates a
  cost; set `VIBE_OLLAMA_MODEL` to a model you've pulled.
- **`vibe doctor`** runs provider diagnostics with no inference (`--offline` supported).
- Details: [provider-abstraction decision](../decisions/2026-06-29-provider-abstraction.md).

## Local-first / privacy rules

- Nothing is sent anywhere except the model calls the user explicitly triggers.
- **The API key is never printed.** Only `.env.example` is tracked.
- Keep stdout machine-readable; diagnostics/usage go to stderr.
- **Never commit** raw council outputs, secrets, `.env`, or local runtime state. Raw `.council/`
  runtime workspace stays **gitignored**.
- For using vibe-council from another project or an AI coding agent, the short
  [agent quickstart](agent-quickstart.md) is the front-door recipe (council is advice, not authority;
  don't send secrets; `review` before coding, `diff` after; `extract`/promote only for durable
  decisions). `vibe guide claude` is the Claude-Code-specific instruction block.

## Decision-memory boundary

- **Committed:** curated, redacted Markdown records in [`docs/decisions/`](../decisions/) and
  this brief (`docs/context/agent-brief.md`).
- **Local / gitignored:** auto-extracted records and raw council output stay on the machine.
- **No committed generated index** yet; **no vector DB**; portable Markdown links are canonical
  (Obsidian-openable, but **Obsidian is not a dependency**; never commit `.obsidian/`).
- Rationale: [linked decision-memory decision](../decisions/2026-06-29-linked-decision-memory.md).

## Current known limitations

- Ollama users must set `VIBE_OLLAMA_MODEL` (presets carry OpenRouter-style model IDs).
- Local Ollama reports no billing cost, so `--max-cost` cannot be enforced for it.
- `full` mode had a None-content ranking fragility (fixed in v0.2.0); prefer `review` for
  plan/diff critique.
- License/provenance cleanup is **ongoing** — no `LICENSE` added yet.
- The context-pack budget is a **naive char budget** (default 14000). **Core sections** (decision
  index, rejected-alternatives index, human-review/source-of-truth constraints, status) **compact —
  never drop** — under budget pressure; full decision bodies trim first (a **token-aware budget** is
  deferred). See [critical-section budget decision](../decisions/2026-07-01-context-pack-critical-section-budget.md).
- MCP is **read-only for v0.4**: a tested contract (`backend/mcp_contract.py` + `vibe mcp contract`)
  and a dependency-free read layer (`backend/mcp_server.py` + `vibe mcp inspect`) for **status,
  curated decisions, and the context pack + health** (`get_project_status` / `list_decisions` /
  `show_decision` / `get_context_pack` / `check_context_health`). Context reads are **in-memory — no
  `.council/` files written**. A minimal **stdlib stdio transport** (`backend/mcp_stdio.py` + `vibe
  mcp serve --stdio`, newline-delimited JSON-RPC) exposes exactly that surface — **no `mcp` SDK
  dependency**. Local setup + dogfood: [Claude Code / MCP setup](mcp/claude-code-setup.md) (generic
  stdio pattern). Standalone rejected/release/constraints resources are deferred. Write/action MCP,
  personas/advisors, app/TUI, and community features are **future work**. See
  [minimal MCP stdio transport](../decisions/2026-07-01-minimal-mcp-stdio-transport.md).

## Accepted decisions (curated set)

- [Provider abstraction (OpenRouter + Ollama)](../decisions/2026-06-29-provider-abstraction.md)
- [Repo cleanup & provenance stance](../decisions/2026-06-29-repo-cleanup-and-provenance.md)
- [Publish v0.2.0](../decisions/2026-06-29-v0.2-release.md)
- [Dogfood linked decision memory](../decisions/2026-06-29-linked-decision-memory.md)
- [External tools & Obsidian research (borrow concepts, not code)](../decisions/2026-06-29-external-tools-and-obsidian-research.md)

## Proposed commercial hypothesis (not decided)

- [Open-core commercial hypothesis](../decisions/2026-06-29-open-core-commercial-hypothesis.md)
  — **proposed**, pending the commercial feasibility review: keep a public local-first core;
  consider a *separate private* hosted/team/sync layer only if demand is validated; prefer
  BYOK + subscription/support/team-sync over a prepaid wallet; self-hosted inference is later.
- **Commercial direction:** public-core/local-first first; detailed hosted/billing strategy remains
  private until validated. See [open-core commercial direction](../decisions/2026-06-29-open-core-commercial-direction.md).

## What not to touch without explicit scope

- Do not start provider-abstraction-2, app/TUI/web, persona/advisor, or community work. MCP is
  scoped **read-only for v0.4** (per its plan/decision); do not add write/action MCP, an MCP server
  beyond the scoped sequence, or an MCP dependency without explicit scope.
- Do not add or change a `LICENSE`, or weaken upstream attribution/provenance.
- Do not commit `.council/`, `data/`, `.env`, `.venv/`, raw outputs, or `.obsidian/`.
- Do not use `premium`/`full` for real runs unless asked; default preset is `balanced`.
- No history rewrite, force-push, or merge unless explicitly requested.

## Next recommended work

1. **Dogfood** this decision-memory batch for ~1 month; check whether this brief measurably
   improves agent answers about the repo (the kill/keep signal).
2. Run the **commercial feasibility review** using the research audit + the open-core hypothesis.
3. Only if dogfooding proves value: scope a **minimal** v0.3 tooling PR with a CI secrets/redaction
   guard — not before. Keep vector/hybrid retrieval and MCP deferred.
4. **Roadmap:** direction is organized as parallel tracks (core/release, decision-memory + context
   pack, project memory, MCP/Remote-Control, operator inbox, packs, orchestration, commercial,
   retrieval, security) with prerequisite-driven version sections. See
   [track-based roadmap](../plans/track-based-roadmap.md).
5. **Project memory (dogfood):** public-safe project-memory seed at
   [`docs/context/project/README.md`](project/README.md) and [`STATUS.md`](project/STATUS.md).
6. **Operator loop:** an approval/status inbox is planned as a minimal local-first layer — not a
   dashboard or custom mobile transport. See
   [operator control loop spec](../plans/operator-control-loop-and-approval-inbox.md).
7. **Redaction guard:** `vibe lint --redaction` scans public docs for leaks (secrets, local paths,
   raw `.council/` artifacts) before promote/commit/export. See [redaction policy](../redaction-policy.md).
8. **License/provenance** remains **Question 0** before serious commercialization; public/local-first
   development continues while the review is clarified. See
   [license & provenance resolution](../plans/license-and-provenance-resolution.md).
9. **Decision CLI:** `vibe decisions list/show/new/lint/promote` operate on curated `docs/decisions/`
   (source of truth); `search/context` stay on the local `.council/` index. `new` is template-only;
   `new --from-run <review>` extracts a **local** draft (gitignored `.council/decisions/drafts/`, no
   LLM, never under `docs/decisions/`); `promote <draft>` validates (frontmatter/headings/redaction) +
   writes into `docs/decisions/` with no auto-stage/commit; `lint` reuses the redaction guard.
10. **Context pack:** `vibe context build` deterministically assembles a compact pack from
    `docs/decisions/` + STATUS (metadata, identity, status, pinned/recent decisions, indexes,
    constraints). No LLM/vector/MCP; runs redaction (blocks on critical); writes gitignored
    `.council/context/pack-latest.md` by default (refuses `docs/` unless `--allow-docs`).
    `vibe context check` is a deterministic quality harness (not an LLM eval): required sections/
    constraints + advisory facts/signals + redaction, scored `passed/total` (`--strict`/`--json`/`--min-score`).
11. **Operator status:** `vibe operator status` (+ `set`/`clear`) is a tiny local-first status surface
    — one gitignored `.council/operator/status.json` (state/message/next_action/severity). Not an
    event log, dashboard, notifications, or remote transport; Remote-Control-friendly, no model calls.
12. **Claude Code export:** `vibe context export claude-code` wraps the pack (usage note + paste-able
    operator instruction + pack body + next commands) into gitignored
    `.council/context/claude-code-context.md`. Gates on check + redaction; refuses `docs/` unless
    `--allow-docs`; never modifies `CLAUDE.md`; no MCP/Remote-Control integration yet.
