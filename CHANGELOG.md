# Changelog

All notable changes to **vibe-council** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Status:** `0.6.3` is prepared. The repo reports `0.6.3`
> (`backend/__init__.py`, `pyproject.toml`). The `v0.6.3` git tag + GitHub Release are cut by a
> maintainer right after the release PR merges — see [`docs/release-checklist.md`](docs/release-checklist.md).

## [Unreleased]

### Added

- **v0.7 PR D — profile pointers in agent guides** — `vibe guide {claude|codex|fable}` output now
  includes a concise **"Project profile & preferences (v0.7 personalization)"** section in every path
  (base topic guides, role-specific guides, and `--write` sections). It **points to**
  `docs/context/project/PROFILE.md` / `PREFERENCES.md` / `AGENT-ROLES.md` (public-safe Markdown
  project-memory files to read directly when present), states that **personalization is tighten-only**
  (advice to read, never commands to execute — it can never loosen a security/safety/no-stage rule;
  the deterministic trust boundary ignores it), that **root `AGENTS.md` is not the canonical
  preference source** (it may be a `vibe guide --write` output target; role preferences live in
  `AGENT-ROLES.md`), and recommends `vibe project doctor` and `vibe context export --for <agent>
  --role <role>`. The guide **inlines no** scaffold content, **parses/applies no** preferences, and
  **reads no** local/private profile (`.council/profile.*`); output stays deterministic and, with
  `--write`, the existing append + marker-skip behavior is unchanged (no duplication on re-run). No
  context-export / project-doctor / Workbench / importer / executor / trust change, no dependency, no
  version bump.

- **v0.7 PR C — profile pointers in `vibe context export`** — the agent context handoff
  (`vibe context export --for {claude|codex|fable}`) now includes a **"Project profile & preferences
  (v0.7 personalization)"** section with **pointers** to `docs/context/project/PROFILE.md` /
  `PREFERENCES.md` / `AGENT-ROLES.md`. It states they are public-safe Markdown project-memory files
  read directly by agents; the export **does not dump their full contents** (pointers only), notes
  that **personalization is tighten-only** (never loosens a security/safety rule), that **root
  `AGENTS.md` is not the canonical preference source** (it may be a `vibe guide --write` output
  target; role preferences live in `AGENT-ROLES.md`), and recommends `vibe project doctor` to check
  scaffold presence. The export reads **no** local/private profile (never `.council/profile.*`),
  inlines no distinctive file content, degrades gracefully if the scaffold is absent, stays
  deterministic (no timestamp), and remains read-only (stdout by default; `--output FILE` still never
  overwrites). No preference application, no guide/project-doctor semantics change, no context-builder
  change, no Workbench/importer/executor/trust change, no dependency, no version bump.

- **v0.7 PR B — project doctor personalization-scaffold checks** — `vibe project doctor` now reports a
  **"Personalization scaffold (advisory)"** section for the v0.7 scaffold files
  (`docs/context/project/PROFILE.md` / `PREFERENCES.md` / `AGENT-ROLES.md`): present → `[ok ]`, missing
  → `[warn]` with the next step `Create the v0.7 project profile scaffold or see
  docs/context/project/README.md`. **Advisory only** — a missing scaffold is **not** a doctor failure
  (READY/NOT-READY still depends solely on the required vault/core docs and the dangerous-staged
  check). Root `AGENTS.md` is **not required**; if present, the doctor emits an advisory `[warn]` that
  vibe-council keeps project agent roles in `docs/context/project/AGENT-ROLES.md` (avoiding a root
  host-file / preference-source collision) — never a failure. The command stays **read-only**: writes
  no files, creates no `.council/`, makes no model/provider/network call; context health remains
  advisory/in-memory. No context-export / guide / Workbench / importer / executor / trust change, no
  dependency, no version bump.

- **v0.7 PR A — project profile/preferences scaffold** — public-safe, Markdown-first committed vault
  files under `docs/context/project/`: `PROFILE.md` (project identity/shape/local-first stance/release
  state), `PREFERENCES.md` (review-preset policy, Fable usage policy, implementation style, no-stage
  policy, tighten-only principle), and `AGENT-ROLES.md` (per-agent role expectations, the `MODEL:`
  header convention, and the council-in-the-loop workflow). Deliberately a vault **`AGENT-ROLES.md`,
  not a root `AGENTS.md`** (the balanced review flagged a write-target/read-source corruption risk).
  Each file carries a safe-to-commit boundary, a never-store list, and the tighten-only principle
  (personalization may tighten but never loosen safety/security rules). The vault README, WORKFLOWS,
  STATUS, PROGRESS, ROADMAP, and the agent-brief point at the new files. **Scaffold/documentation only
  — no command reads or enforces these files yet; no guide/context-export/project-doctor behavior
  change, no Workbench/importer/executor/trust change, no dependency, no version bump.**

- **v0.7 personalization planning brief** — `docs/fable/v0.7-personalization-and-project-profile-plan.md`,
  a **docs-only, council-in-the-loop** source brief for the v0.7 personalization / project-profile
  phase. It defines the purpose, non-goals (no vector DB / database / hosted stack / auto-execution /
  trust-boundary relaxation), the Markdown-first data model (`docs/context/project/PROFILE.md` /
  `PREFERENCES.md` / `AGENTS.md`), tighten-only safety invariants (personalization may tighten but
  never loosen a guardrail), the council-in-the-loop production workflow, a small A–E PR breakdown,
  open questions, and a copy-paste future-Fable architecture prompt. **No implementation, no code or
  behavior change, no version bump, no dependency change.**

## [0.6.3] - 2026-07-04

**Cross-project agent onboarding.** Bundles the v0.6.1–v0.6.3 onboarding arc on top of the v0.6.0
agent-to-Workbench bridge: a role-aware `vibe guide` layer (claude/codex/fable topics, opt-in
append-only `--write`), a local-first Markdown **project vault** under `docs/context/project/`, a
read-only `vibe project doctor` readiness check, and a read-only `vibe context export --for <agent>`
onboarding handoff. All read-only/local: no model/provider/network call, no Workbench trust-boundary
change, no `/council` command (`vibe` remains the real CLI), no new dependency.

### Added

- **`vibe context export --for {claude|codex|fable}`** — a read-only agent onboarding context
  handoff (with optional `--role`). Prints Markdown to stdout by default, or writes an explicit
  `--output FILE` (never overwriting an existing file). It bundles: a header (`vibe` is the real CLI;
  `/council` is a future idea, not a command), the operating rules + agent-specific guidance + the
  never-stage list (reusing the `vibe guide` machinery — Fable gets its budget/technical-lead policy),
  **pointers** to the project vault (deliberately **not** a full vault dump), a context-health
  summary built **in-memory** (no `.council/` written), the Workbench proposal flow, and a
  `vibe project doctor` recommendation. Read-only: no `.council/` creation, no model/provider/network
  call. The existing `vibe context export claude-code` behavior is unchanged. No context-builder
  change, no Workbench/importer/executor/trust change, no dependency, no version bump.

- **`vibe project doctor`** — a read-only onboarding-readiness diagnostic (new `project` subcommand,
  distinct from the provider `vibe doctor`). It reports whether a repo is ready for agent onboarding:
  the project vault files + core onboarding docs are present; no dangerous file is **staged**
  (`.env`, `.council/`, `.council/runtime/`, private plan files → fail; a staged `uv.lock` → advisory
  warning); context health (reusing `context_pack.build_pack`/`check_pack` **in-memory**, e.g. 21/21);
  and the available `vibe guide {claude|codex|fable}` commands (with an explicit note that `/council`
  is a future idea, **not** a real CLI command). Exit 0 when ready; non-zero with next steps when a
  required file is missing or a dangerous file is staged; git-unavailable degrades to a warning, not a
  failure. **Read-only:** writes no files, creates no `.council/`, makes no model/provider/network
  call. No context-builder change, no Workbench/importer/executor/trust change, no dependency, no
  version bump.

- **Project vault scaffold** (`docs/context/project/`) — the first v0.6.2 slice: a local-first,
  Markdown, human- and agent-readable project-memory vault. Alongside the existing `README.md`/
  `STATUS.md`, adds `ROADMAP.md`, `DECISIONS.md` (an **index/pointer** into `docs/decisions/`, never a
  competing canonical store), `PROGRESS.md` (a curated milestone digest), `RISKS.md`, `WORKFLOWS.md`,
  and `NOTES.md`. Each file states what belongs there and what must never go there (secrets, API keys,
  private paths, runtime payloads, raw outputs, private plans). README/agent-brief/agent-quickstart
  now point agents to read the vault before planning/coding. **The context builder is unchanged** —
  the pack remains a budgeted projection (STATUS.md + decision index; 21/21 preserved); the vault is
  read directly and discovered via pointers, not injected into the pack. Not a database, not an
  Obsidian dependency, not a launcher. No Workbench/importer/executor/trust change, no `/council`
  command, no dependency, no version bump.

- **Role-aware agent guide** (`vibe guide claude --role <role>`) — the first v0.6.1 onboarding slice:
  a **read-only stdout generator** that prints a role-tailored Claude instruction block for
  `task-shaper`, `planner`, `coder`, `reviewer`, or `release-manager`. Each role guide pairs its
  role-specific workflow with the common rules — this project's CLI is `vibe` (not `/council`, which
  stays a future idea), council is a reviewer/context/memory layer not an implementer, the
  cheap/balanced/full preset policy, the before/after-coding workflow, the Workbench proposal-bridge
  basics (propose → human approves → separate explicit execute), and the never-stage list.
  `vibe guide claude` with no `--role` is unchanged. No Workbench/importer/executor/trust change, no
  new dependency, no version bump.
- **Opt-in `--write` for role-aware guides** — `vibe guide claude --role <role> --write [FILE]`
  **appends** the role's guide section to a `CLAUDE.md`-style file (default `CLAUDE.md`) and reports
  the path. Follows the existing `--write` convention: it **never overwrites** — a distinct
  per-role marker means a re-run for the same role is skipped (and different roles can coexist in one
  file). Without `--write`, role output stays stdout-only. Only the explicit target file is touched;
  no `.council/` or other project files are created.
- **Codex and Fable guide topics** — `vibe guide codex` and `vibe guide fable` (with the same
  `--role` and opt-in `--write` support as `claude`), reusing the role-aware guide machinery. Codex
  emphasizes using vibe as a reviewer/context/guardrail, reading project instructions first, small
  scoped PRs, running tests before the final report, and proposing Workbench actions instead of
  bypassing approval. Fable emphasizes its cost/technical-lead policy: plan-first, use curated
  `docs/context/`/`docs/fable/` packs (not broad repo scans), let Opus/Sonnet implement routine PRs,
  and reserve Fable for major phase planning / critical architecture-security blockers / high-leverage
  reviews. Each topic has a default `--write` file (`claude`=`CLAUDE.md`, `codex`=`AGENTS.md`,
  `fable`=`FABLE.md`) and a distinct per-topic marker so topics and roles coexist in one file without
  overwriting. `claude` behavior is unchanged; `/council` stays a documented future idea, not a
  command. No Workbench/importer/executor/trust change, no new dependency, no version bump.

## [0.6.0] - 2026-07-04

**Agent-to-Workbench proposal bridge.** AI agents (Claude Code, Codex, Fable, or custom workers) can
now **propose** a bounded code action into the local Workbench instead of acting directly — a human
still approves and executes. Local **file/CLI intake only** (no network endpoint): an agent writes a
schema-v1 proposal JSON, `vibe workbench propose` validates it and mints ids + payload hash
server-side, the panel shows a proposed-by-agent card, and nothing runs until a human approves and
explicitly executes it through the **existing, unchanged** guarded executor. Still local-first and
stdlib-only: no new runtime dependency, no new network surface, no command-allowlist growth.

### Added

- **Workbench proposal schema + validation layer** (`backend/workbench_proposals.py`) — the first
  v0.6 agent-bridge slice: proposal envelope **schema v1** (strict — unknown keys rejected at every
  level) and pure, fail-closed validation for agent-authored proposals. Allowed kinds:
  `write_file`/`edit_file` (relative, trust-checked targets; exact payload shapes; NUL/size caps
  mirroring executor bounds) and `run_command` by **exact allowlist label only** (both resolver and
  trust gates; no freeform commands, argv, env, cwd, timeout, or shell — ever). Server-minted fields
  (ids, `payload_hash`, statuses, verdicts) are hard-rejected if present; `proposal_id` (the future
  dedup key) is strictly charset-validated, not sanitized. **Validation only:** no importer, no store
  writes, no id minting, no execution, no `subprocess` import, no panel/CLI/network change — the
  deterministic trust boundary still re-runs at approval display and execution time regardless.
- **Workbench proposal importer + `vibe workbench propose`**
  (`backend/workbench_proposal_importer.py`) — the second v0.6 bridge slice: a validated schema-v1
  proposal becomes a runtime Task + pending ApprovalRequest + pending Action, flowing into the
  **existing, unchanged** trust/auditor/panel/executor path. All ids and the payload hash are
  **server-minted**; file payloads live only in the local write-once payload artifact (never in
  task/approval/action JSON or the dedup record). Dedup by `proposal_id` (global): an identical
  re-import returns the original ids and creates nothing; the same id with materially different
  content is a **conflict** and fails closed. CLI intake is local-only (`vibe workbench propose
  <file | ->`, stdin supported; JSON result on stdout, never raw payload; non-zero exit on failure).
  An advisory audit is saved on import. **No execution, no network endpoint, no panel change, no
  allowlist growth, no new dependency.** Also adds
  `docs/fable/v0.6-followup-implementation-plan.md` — the remaining v0.6.0 PR sequence with
  copy-paste implementer prompts and the Fable-as-architect-only budget policy.
- **Workbench panel: agent-proposal visibility** (`backend/workbench_panel.py`) — imported
  agent-proposed tasks now show a "proposed by agent: `<name>`" badge with the agent role and
  `proposal_id` (all HTML-escaped), so they are visually distinct from demo/manual tasks. Display
  only: derived from the task's existing `agent:<name>` source plus a **read-only** importer lookup
  of the local proposals index (`proposal_meta_for_task`); **no raw payload content** appears in the
  HTML or `/api/state` JSON, no tokens are exposed, and approval/execution semantics, the Host-header
  check, `/api/state` token gating, and CORS behavior are all unchanged.

### Docs

- **Agent proposal bridge guide** (`docs/workbench-agent-bridge.md`) — documents the now-implemented
  v0.6 flow end to end: an agent writes a schema-v1 proposal JSON, submits it locally via
  `vibe workbench propose <file | ->`, the Workbench validates/mints ids+hash server-side and records
  a **pending** approval, the panel shows proposed-by-agent metadata, and a human approves before the
  **existing** guarded executor runs anything. Covers the safety model (no network endpoint, no
  auto-execution, no agent-supplied argv/hash/ids, server-side hashing, raw payload stays local),
  CLI usage/output, safe `write_file`/`edit_file`/`run_command` examples, rejected-example/common-
  mistake cases (freeform command, smuggled fields, denied paths, `cloud_call`, dedup/conflict), and
  the agent + human operator workflows. README and `docs/agent-quickstart.md` gain short pointers.
  Docs only — no code, test, or dependency change.

## [0.5.2] - 2026-07-03

**Workbench security-hardening patch (+ implementation-pack docs).** A small patch on top of the
v0.5.0/v0.5.1 AI Council Workbench: a DNS-rebinding-class defense on the localhost panel and a token
gate on `/api/state`, plus a docs-only phase book for planning v0.6+. No executor/trust/payload/
allowlist behavior change, no new product surface, no new dependency.

### Security

- **Workbench panel: `Host`-header validation (DNS-rebinding defense) + `/api/state` token gate.**
  The panel already binds `127.0.0.1`, but localhost binding alone doesn't stop a malicious page whose
  domain re-resolves to `127.0.0.1` — the browser still sends that page's original `Host`. Every
  request's `Host` header must now name a literal loopback host (`127.0.0.1`/`localhost`/`::1`, any
  port); a missing, malformed, or multiple `Host` header fails closed. `GET /api/state` (which exposes
  runtime tasks/approvals/actions) is now gated on the **same** startup token as the POST endpoints
  (accepted via `X-Workbench-Token` or the `?token=` the panel URL already carries; never echoed in
  JSON). `GET /` stays tokenless so the panel URL loads normally — Host validation is its guard.
  Landed ahead of the v0.6 agent-proposal bridge (which will populate the runtime store with
  approved-pending actions). No executor/panel **execution** behavior changed, no new endpoint, no
  CORS, no command-allowlist change, no new dependency.

### Docs

- **`docs/fable/` implementation pack.** A structured, phase-by-phase plan for driving future work
  (v0.6 agent-to-Workbench bridge + proposal schema, onboarding/session launcher, Obsidian-like
  project vault, cross-project onboarding, tighten-only personalization, website positioning, and the
  open-core commercial path) with a long-running model, alongside the non-negotiable security
  invariants and operating rules. Docs only — no code, tests, dependencies, or behavior change.

## [0.5.1] - 2026-07-03

**Dogfood & hardening patch — no new product surface.** Mirrors the v0.3→v0.3.1 precedent: a
checklist-driven pass finding and fixing rough edges in the v0.5.0 Workbench MVP, not adding
capability. No executor/panel behavior changes beyond what's listed here, no command allowlist
growth, no v0.6 work.

### Verified

- **Clean-clone / Windows dogfood** (PR #86) — fresh `git clone` → `uv sync` → version/doctor/
  status/presets → full test suite → lint/decisions/context/MCP checks, plus an HTTP-level
  Workbench panel smoke, all matching the dev checkout.
- **Workbench interactive smoke** (PR #87) — a clean scratch-directory first run (empty state,
  demo, approve, token-gating) matched expectations end-to-end.
- **Manual execution dogfood** (PR #89) — the real guarded-executor path, previously untested
  through the panel: a manually-seeded `write_file` action and a manually-seeded `run_command`
  action both executed successfully through the panel's real HTTP API in a temp/safe project;
  both a non-allowlisted command and a missing payload artifact failed closed; a crafted request
  body (different target/content/command/argv/env/cwd/timeout) had **zero effect** on what
  actually ran.

### Fixed

- **Workbench localhost bind/shutdown hardening** (PR #88) — `make_server()` now re-checks the
  actual bound address after `bind()` (defense-in-depth; no confirmed `0.0.0.0`-bind bug was ever
  found), and a new regression test locks in that `server_close()` actually closes the socket on
  `Ctrl+C`/`KeyboardInterrupt`.
- **`ExecutionResult.dry_run` metadata bug** (PR #89) — every real (non-preview) execution
  response incorrectly reported `dry_run: true` alongside `executed: true`; now correctly `false`.
  Display/metadata only — did not change what the executor was willing to run.
- **Misleading `run_command` panel message** (PR #89) — a completed or blocked command action's
  card could falsely claim "does not resolve to an allowlisted argv" even when it had already run
  successfully; the card now shows the actual target/status instead.
- **`uv.lock` self-version drift** (PR #90) — the local `vibe-council` package entry in `uv.lock`
  had read a stale `0.2.0` since before `v0.3.0`, causing an accidental lockfile diff on every
  `uv sync`/`uv run`. Synced to match `pyproject.toml`/`backend/__init__.py`; no dependency package
  versions changed.

### Unchanged (security posture)

Nothing here relaxes or expands the v0.5.0 security model:

- Approval is still **separate from execution** — approving never auto-executes.
- The panel is still **localhost-only (`127.0.0.1`)** and **POSTs are still token-gated**.
- Payload artifacts are still **local, gitignored, write-once, and hash-verified**.
- Command execution is still **fixed argv + `shell=False`, always** — no dynamic arguments, no
  arbitrary shell, no new allowlist entries.

### Explicit non-goals (deferred, not started)

No v0.6 agent-to-Workbench bridge · no personalization/profile implementation · no mobile/LAN/
voice access · no hosted/team/cloud work · no command allowlist expansion.

### Verification

- 576 tests pass; redaction lint 0 critical; decisions lint passes; `context check` 21/21; MCP
  health 21/21.

## [0.5.0] - 2026-07-02

**AI Council Workbench MVP (guarded execution).** A task now moves through **visible stages**, an AI
proposes a change, an **audited approval** step gates it (deterministic guards are the boundary; the
Approval Auditor is advisory only), and — as a **separate, explicit** step — an approved,
narrowly-bounded action can actually run: a file write/edit behind a verified local payload artifact,
or an exact allowlisted command behind a fixed-argv resolver. Still local-first and stdlib-only: no
new runtime dependency, no provider/model/network call from the executor, no LAN/mobile/remote
surface.

### Added

- **Runtime store + state machine** (`backend/workbench_runtime.py`, `backend/workbench_orchestrator.py`)
  — a gitignored `.council/runtime/` JSON tree (`Task`/`Stage`/`ApprovalRequest`/`ApprovalDecision`/
  `Action`/`AuditResult`) and a deterministic task lifecycle (plan → request approval →
  approve/reject/hold → executing → complete/fail/hold).
- **Deterministic trust boundary** (`backend/workbench_trust.py`) — path allow/deny, command
  allowlist, secret patterns, change-size limits, cloud-egress consent; re-run at execution time, not
  just at approval time.
- **Advisory Approval Auditor** (`backend/workbench_auditor.py`) — a human-readable approval summary
  that copies risk/blocked/findings verbatim from the trust boundary, so it can never relax a block.
- **Localhost Workbench panel** (`backend/workbench_panel.py`, `vibe workbench serve`) — task/approval
  cards, approve/reject/hold, a "Create demo task" dogfood button, and (new this release) a separate,
  explicit **"Execute"** step for approved actions.
- **Payload artifacts + hash/scope verification** (`backend/workbench_payloads.py`) — bounded file
  actions carry content in a local, gitignored, write-once `.council/runtime/payloads/<action_id>.json`,
  hashed at creation and re-verified before every real execution.
- **Bounded file write/edit execution** (`backend/workbench_executor.py`) — atomic writes, size/
  line-delta limits, path/symlink guard, explicit-overwrite requirement, no content in logs.
- **Command allowlist → fixed argv resolver** (`backend/workbench_commands.py`) — no shell, no string
  parsing, `sys.executable`-based, no OS-specific launcher dependency; plus a dry-run preview.
- **Real exact allowlisted command execution** — `subprocess.run(shell=False)` with a sanitized
  environment, project-root cwd, a timeout, and bounded/redaction-checked output capture.
- **Panel execute + result display** for both bounded file actions and allowlisted commands — the
  browser only ever sends an action id.
- **v0.5 release readiness / dogfood checklist** (`docs/plans/v0.5-release-readiness.md`) and prepared
  release notes (`docs/releases/v0.5.0.md`).

### Changed

- `workbench_trust`'s command allowlist gained `vibe context build` (a gap noted while building the
  command resolver).
- README / project status / agent brief reflect the completed guarded-executor track.

### Safety

- **Approval is separate from execution** — approving only records a decision; it never writes a
  file, edits a file, or runs a command.
- **The deterministic trust boundary re-runs at execution time** — a stored/stale `AuditResult` or a
  cached preview cannot authorize anything; the advisory Auditor is never the gate.
- **The browser sends only an action id** (+ a startup token) — never file content, patch text, a
  command string, argv, cwd, env, or a timeout; the executor resolves everything server-side.
- **Payload artifacts are local/gitignored**, write-once, and hash/scope-verified before use.
- **Command execution is fixed argv + `shell=False`, always** — no dynamic arguments, ever.
- **The subprocess environment is allowlist-built** (no inherited secrets/API keys/`.env`); a timeout
  and output-byte cap are enforced; a critical redaction finding in output blocks the result instead
  of storing it.
- **The panel is localhost-only (`127.0.0.1`) and token-gated** — no CORS wildcard.
- Redaction lint remains **0 critical**; `context check` and MCP health remain **21/21**.
- **License/provenance remains an unresolved commercial "Question 0"** — no clearance claim, no
  `LICENSE`.

### Verification

- 570 tests pass; redaction lint 0 critical; decisions lint passes; `context check` 21/21; MCP health
  21/21.

### Deferred

- Arbitrary command execution · a larger command allowlist · package install/deploy/`git push` ·
  provider/model/API calls from the executor · LAN/mobile/remote access · voice · background/
  autonomous loops · a plugin system · multi-user/team/hosted mode · cloud sync.

## [0.4.0] - 2026-07-01

**Read-only MCP / Claude Code workflow.** Exposes vibe-council's curated project memory — project
status, curated decisions, and the generated context pack + health — to Claude Code / local MCP
clients over a **read-only** stdio server, without granting any write/action authority. Still
deterministic and local-first: no `mcp` SDK dependency (the transport is a minimal stdlib
JSON-RPC-over-stdio server), no write-capable tools, no provider/model calls, no hosted/sync.

### Added

- **`vibe mcp contract`** — prints the read-only MCP contract: read-only resources/tools and the
  explicit forbidden mutation/action tools (`backend/mcp_contract.py`).
- **`vibe mcp inspect`** — a dependency-free read-only smoke over the read layer (status + curated
  decisions; `--context`/`--health` also build the context pack + health **in memory**, writing no
  `.council/` files; `--id`, `--json`).
- **`vibe mcp serve --stdio`** — a read-only MCP **stdio transport** (newline-delimited JSON-RPC
  2.0: `initialize`/`tools/list`/`tools/call`/`resources/list`/`resources/read`/`ping`) wrapping the
  read layer (`backend/mcp_stdio.py`). No `mcp` SDK, no HTTP/socket/daemon.
- **MCP read layer** (`backend/mcp_server.py`): tools `get_project_status`, `list_decisions`,
  `show_decision` (path-guarded to `docs/decisions/`), `get_context_pack`, `check_context_health`;
  resources `vibe://status`, `vibe://decisions`, `vibe://decisions/{id}`, `vibe://context/latest`.
- **Claude Code / MCP setup docs** (`docs/mcp/claude-code-setup.md`, a generic MCP stdio client
  pattern) and **v0.4 MCP dogfood notes** (`docs/dogfood/v0.4-mcp-local-dogfood.md`).
- **Tests** for the MCP contract, read layer, stdio transport, and the no-write/path/forbidden-tool
  boundaries.

### Changed

- **Context-pack budget protects core sections.** Under budget pressure the builder now **compacts**
  core sections instead of dropping them — the decision index and the rejected-alternatives index
  survive (compacted), and full decision bodies are trimmed **first**. This fixes the recurring
  14000-char cliff that previously dropped the required `section:decision-index`.
- **README** documents the read-only MCP workflow and commands.
- **Project status / agent brief** reflect the read-only MCP release.

### Safety

- MCP exposes **read-only** status, decisions, context pack, and context health **only**.
- **No** write/git/shell/provider/model tools; **no** decision promotion through MCP; `git_status` is
  forbidden for v0.4.
- **No raw `.council/` exposure** and **no private/untracked plans** exposed; `show_decision` is
  path-traversal guarded to `docs/decisions/`.
- **MCP context reads do not write `.council/`** (built in memory); the forbidden `write_file` tool
  is tested to return a JSON-RPC error.
- Redaction lint remains **0 critical**; `context check` remains **21/21**.
- **License/provenance remains an unresolved commercial "Question 0"** — no clearance claim, no
  `LICENSE`.

### Verification

- 287 tests pass; redaction lint 0 critical; decisions lint passes; `context check` 21/21; MCP
  contract/inspect/serve-help pass; bounded MCP stdio smoke passes; no-write and privacy audits clean.

### Deferred

- MCP SDK / full protocol compliance · write-capable MCP tools · remote approval transport ·
  hosted/team/sync · dashboard / mobile / custom transport · standalone
  `vibe://rejected-alternatives` / `vibe://release-notes` / `vibe://constraints` resources ·
  token-aware budget · vector/hybrid retrieval · LLM-based context eval · rolling summaries ·
  operator notifications / event log.

## [0.3.1] - 2026-06-30

**Dogfood hardening for the v0.3 decision-memory / context loop.** No new command surface — this
release uses the v0.3 loop on real work and fixes the rough edges that surfaced. Still
deterministic and local-first: no MCP, no rolling summaries, no token-aware tokenizer, no vector
retrieval, no LLM eval, no dashboard/hosted layer. Raw `.council/` outputs and generated packs/
exports/operator status stay gitignored; `docs/decisions/*.md` remain the curated source of truth.

### Added

- **v0.3.1 dogfood notes** (`docs/dogfood/v0.3.1-notes.md`) — public-safe findings from exercising
  the full v0.3 loop on real work.
- **Tests** for the decision-CLI rough edges and the CLI UX output (`tests/test_cli_ux.py`), plus a
  real-repo `context check` guard that builds from the actual `docs/decisions/` + `STATUS.md` and
  asserts a perfect, redaction-clean score.

### Fixed

- **`decisions promote` rejects placeholder-only drafts** — an all-`TODO` scaffold can no longer be
  promoted; core sections (Decision, Rationale, and Consequences/Next actions) must carry meaningful
  content. Scoped to `promote` (not `decisions lint`).
- **`decisions promote` follows the curated `YYYY-MM-DD-slug.md` filename convention** (date from
  frontmatter, slug from title → id → stem; no more `DEC-….md`).
- **`decisions new --from-run` maps obvious review sections** into the draft (verdict → Decision,
  rationale → Rationale, alternatives/rejected → Alternatives considered, risks/consequences →
  Consequences, next actions → Next actions); unmatched sections keep `TODO` markers.
- **Long extracted slugs are capped/sanitized.**
- **Context packs include an explicit human-review promotion boundary**, so `vibe context check`
  passes **21/21** on the real repo (the missed advisory was `memory:human-review`).
- **Context-pack default char budget bumped 12000 → 14000** so the curated set keeps its core
  signals (the trimmer was dropping the rejected-alternatives index).

### Changed

- **Clearer `vibe lint --redaction` verdict** — `redaction lint passed/FAILED: N critical,
  M warning(s) (<scope>)`.
- **Clearer `vibe context build` budget hint** — names the current budget and suggests `--max-chars`
  when trimming.
- **`vibe context check`** score line reports the advisory-miss count.
- **`vibe decisions` help** clarifies the local-draft / human-review / no-auto-stage boundary.
- **README** reflects the current v0.3.1 workflow (promoted filename convention, `--from-run`
  mapping, placeholder-rejecting `promote`).

### Safety

- Generated `.council/` artifacts (reviews, drafts, context packs, Claude Code exports, operator
  status) remain **gitignored** / local by default; none are committed.
- Redaction lint remains **0 critical**; `decisions lint` passes.
- Promotion into `docs/decisions/` remains **human-reviewed**; nothing auto-commits.
- **License/provenance remains an unresolved commercial "Question 0"** — no commercial-clearance
  claim, no `LICENSE` added.

### Deferred

- MCP read-only export · rolling summaries · a token-aware (real tokenizer) budget ·
  vector/hybrid retrieval · LLM-based context eval · operator event log / notifications ·
  dashboard / mobile / custom remote transport · hosted/team/sync layer.

## [0.3.0] - 2026-06-30

**Local-first decision memory + curated project context.** Builds the v0.3 decision-memory /
context-pack loop on top of v0.2's multi-provider core. Everything is **deterministic and
local-first** — no LLM summarization, no vector retrieval, no MCP, no hosted/sync. Raw `.council/`
outputs and generated packs/exports stay gitignored; public `docs/decisions/*.md` remain the curated
source of truth.

### Added

- **`vibe lint --redaction`** — a stdlib-only redaction guard for public docs (API keys, private
  keys, secret assignments, per-user local paths, dated `.council/` artifact paths, `.obsidian/`
  workspace), with `--strict` and masked output.
- **Curated decision CLI** over `docs/decisions/*.md`: `vibe decisions list` (with `--tag`/`--status`),
  `show` (path-traversal guarded), `new` (template), and `lint` (frontmatter, stable headings,
  duplicate ids, broken links, redaction).
- **`vibe decisions new --from-run`** — extract a **local** draft decision from a raw council/review
  output (deterministic heuristics, no LLM) into gitignored `.council/decisions/drafts/`.
- **`vibe decisions promote`** — safely promote a human-reviewed draft into `docs/decisions/`
  (validates frontmatter/headings/redaction; sanitized filename; `--dry-run`/`--force`).
- **`vibe context build`** — deterministic context-pack builder from curated decisions + `STATUS.md`
  with a character budget; writes gitignored `.council/context/pack-latest.md`.
- **`vibe context check`** — deterministic context-quality harness (not an LLM eval): required
  sections/constraints + advisory facts/signals + redaction, scored `passed/total`.
- **`vibe context export claude-code`** — wrap the pack as a Claude Code-friendly local context file
  (gitignored; gated on check + redaction; never modifies `CLAUDE.md`).
- **Operator status** — `vibe operator status` / `set` / `clear` over a gitignored
  `.council/operator/status.json` (state/message/next_action/severity).
- **License/provenance checklist** — an engineer's "Question 0" commercial gate
  (`docs/plans/license-and-provenance-resolution.md`), with no commercial-clearance claim and no
  `LICENSE` added.

### Changed

- **README** now documents the end-to-end decision-memory / context workflow.
- **Project status and agent brief** reflect the v0.3 workflow.
- Added `docs/redaction-policy.md` defining what must/should/may be redacted.

### Safety

- Generated `.council/` artifacts (reviews, decisions, drafts, context packs, Claude Code exports,
  operator status) remain **gitignored** / local by default.
- The redaction guard runs across the decision and context workflows (and blocks unsafe context
  build/export).
- Promotion into `docs/decisions/` remains **human-reviewed**; nothing auto-commits.
- **License/provenance remains an unresolved commercial gate** — no commercial-clearance claim.

### Deferred

- MCP read-only export · rolling summaries · a token-aware (real tokenizer) budget ·
  vector/hybrid retrieval · skill/council packs · hosted/team/sync layer ·
  dashboard / mobile / custom remote transport · LLM-based context eval.

## [0.2.0] - 2026-06-29

The **multi-provider** release: break the single-provider lock-in with a provider
abstraction, add a local **Ollama** provider, and ship `vibe doctor` diagnostics — all
while OpenRouter remains the default and existing behavior is unchanged.

### Added

- **Provider abstraction** — a minimal `Provider` seam with `ChatRequest` / `ChatResult`
  and an **OpenRouter adapter**; legacy helper functions delegate to it with no behavior
  change for OpenRouter users.
- **Provider selection** via `VIBE_PROVIDER`, defaulting to `openrouter`; unsupported
  values fail clearly before any model call.
- **Local Ollama provider** via `VIBE_PROVIDER=ollama` — non-streaming `/api/chat`,
  requires no API key, loopback-only `OLLAMA_HOST` validation (SSRF-safe), and never
  fabricates a dollar cost.
- **`VIBE_OLLAMA_MODEL`** — map the existing preset's OpenRouter-style model IDs to a
  local Ollama model name you've pulled, without redesigning presets.
- **`vibe doctor`** — provider diagnostics (key presence/placeholder, OpenRouter
  model-list reachability, Ollama host validation + `/api/tags` reachability + local model
  list + `VIBE_OLLAMA_MODEL` availability). Runs **no inference** and spends no tokens;
  supports `--offline`.
- **Provider-aware usage/cost messaging** — `--usage` and `--max-cost` now name the active
  provider and state honestly when a provider does not report cost.

### Fixed

- **`full` mode** no longer crashes when a ranking model returns `None` or empty content
  (`parse_ranking_from_text` tolerates missing/empty/whitespace/unparsable output).

### Removed

- **Unused upstream web UI subsystem** — the legacy React + Vite `frontend/`, the
  `backend/main.py` FastAPI server and `backend/storage.py` conversation storage, plus the
  related upstream `start.sh`, root `main.py`, and root `header.jpg` — and the now-unused
  **FastAPI/Uvicorn** dependencies. The product is the local-first CLI; a future app/TUI/web
  surface should be rebuilt intentionally rather than carried over from upstream.

### Changed

- **Project identity** metadata renamed from `llm-council` to `vibe-council`
  (`pyproject.toml`, `uv.lock`, `CLAUDE.md`).
- **Author identity** normalized with a `.mailmap` (display-only; no history rewrite).

### Known limitations

- **Ollama users should set `VIBE_OLLAMA_MODEL`** — presets still carry OpenRouter-style
  model IDs; provider-specific preset config is future work.
- **Local Ollama does not report billing cost**, so `--max-cost` cannot be enforced for
  Ollama runs (cost is never fabricated).
- **MCP, personas/advisors, app/TUI, and community** features are still future work.
- **License/provenance cleanup is ongoing** — parts of the backend still descend from the
  unlicensed upstream `karpathy/llm-council`; no `LICENSE` is added yet.

## [0.1.0] - 2026-06-28

First public release. Because this is the initial cut, the notes below are a
**feature inventory** of what the fork adds on top of upstream
[`karpathy/llm-council`](https://github.com/karpathy/llm-council) (the council concept:
query several models, peer-review/rank, chairman synthesis), not a since-last-tag delta.

### Added

- **Workflow modes** — `extract`, `mini` (default), `review`, and `full`. `full` is the
  only mode that uses anonymized peer ranking; `review` is the everyday plan/diff gate.
- **Presets** — `cheap`, `balanced` (default), and `premium`, each mapping council /
  chairman / extract roles to OpenRouter model IDs (env-overridable).
- **CLI** — run any mode via `python -m backend.cli`, plus a global **`vibe`** command:
  `--version`, `vibe status`, `vibe review`, `vibe diff`, `vibe extract`, `vibe mini`,
  `vibe full`, `vibe models`, `vibe presets`, `vibe last`, `vibe guide`, `vibe init`,
  `vibe projects`. Output goes to stdout; progress/usage/guard messages to stderr; the
  API key is never printed. Dedicated exit codes (`0`–`7`) for scripts and agents.
- **`.council/` workspace** — a project-local folder (`reviews/`, `diffs/`,
  `decisions/`, `runs/`, `stages/`, `usage/`, `locks/`, `config.json`) created when
  `vibe` runs inside a project, and auto-added to that project's `.gitignore`.
- **Decision memory** — `vibe extract --save` writes a structured decision as JSON +
  Markdown and appends to `.council/decisions/index.jsonl`; `vibe decisions list`,
  `search`, and `context` read it back. These commands call **no model** and need
  **no API key**. Search is plain local string matching (no embeddings/SQLite).
- **Guardrails** — premium guard (`--allow-premium`), pre-run token guard
  (`--max-tokens`, hard block before any call), best-effort cost guard (`--max-cost`),
  a loop guard against duplicate/concurrent/too-frequent runs (`--allow-repeat`,
  `--no-loop-guard`), `--usage` (provider-reported tokens/cost), and `--save-stages`.
- **First-run key guard** — a clear message and exit code **7** when
  `OPENROUTER_API_KEY` is missing for a model command, instead of a raw traceback.
- **Tests & CI** — stdlib `unittest` smoke and structural tests, run by GitHub Actions
  on Ubuntu, macOS, and Windows.
- **Cross-platform install** — `scripts/install-vibe.ps1` (Windows) and
  `scripts/install-vibe.sh` (macOS/Linux), with `vibe.ps1` / `vibe.cmd` / `vibe.sh`
  launchers that prefer the repo `.venv` and never print the key.
- **Examples & docs** — `examples/` (sample plans + workflow walkthroughs, readable
  without spending credits), [`docs/agent-integrations.md`](docs/agent-integrations.md),
  and committed plan docs under `docs/plans/`.
- **Demo guide & transcript** — [`docs/demo.md`](docs/demo.md) (safe terminal-recording
  guide) plus a committed, sanitized text walkthrough at
  [`docs/demo-transcript.md`](docs/demo-transcript.md).
- **Privacy / local-first docs** — explicit explanation that artifacts stay local while
  your prompts/files/diffs **are** sent to OpenRouter (not local inference), plus
  bring-your-own-key / cost transparency.
- **Web UI** — the original React + Vite council UI (stage tabs) still runs against the
  FastAPI backend.

### Known limitations

- **OpenRouter-only** — bring-your-own-key; no provider abstraction yet.
- **No Ollama / local inference** — prompts are sent to remote providers.
- **No MCP server** yet.
- **No real demo recording yet** — a sanitized text transcript
  ([`docs/demo-transcript.md`](docs/demo-transcript.md)) ships; an actual asciinema
  cast / GIF remains an approved follow-up.
- **Decision search is plain string matching** — no embeddings or SQLite.

<!-- The [0.1.0] tag link goes live once the maintainer pushes the v0.1.0 tag right
     after this release PR merges (a brief 404 between merge and tag is expected). -->
[Unreleased]: https://github.com/EfeAydinalp/vibe-council/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/EfeAydinalp/vibe-council/releases/tag/v0.1.0

