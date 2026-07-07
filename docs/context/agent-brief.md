# vibe-council — agent brief (curated dogfood seed)

A concise, **curated and redacted** project brief for Claude Code and future agents. This is a
hand-written **dogfood seed**, not generated output — it distills the committed decision records
under [`docs/decisions/`](../decisions/). Future *generated* agent briefs should default to a
local, gitignored location and be committed only by explicit, redacted opt-in.

_Last curated: 2026-07-03 (vibe-council 0.5.1)._

## Project identity

**vibe-council** is a local-first AI "council" CLI: multiple LLMs collaboratively review or
answer, with anonymized peer ranking, decision memory, and cost/safety guardrails. The product
is the command-line interface; everything runs on the user's machine with their own API key.
Forked from and crediting [`karpathy/llm-council`](https://github.com/karpathy/llm-council) —
**preserve that attribution**.

## Current released state

> For the full newest-first release index see
> [`docs/context/project/RELEASES.md`](project/RELEASES.md) (capped index) →
> [`docs/releases/`](../releases/) (canonical notes). The list below is a curated seed excerpt.

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
  never executes; a browser `confirm()` adds friction only, not a security boundary. See
  [panel execute decision](../decisions/2026-07-02-workbench-panel-execute.md). The **command
  allowlist → fixed-argv resolver** (`backend/workbench_commands.py`, PR #79): a label (e.g.
  `"vibe lint --redaction"`) resolves only to a hardcoded, `sys.executable`-based argv — never parsed
  from a string, never OS-launcher-dependent. **Real `run_command` execution now exists** (PR #80):
  `run_command` joined `REAL_EXEC_KINDS`; `subprocess.run(argv, shell=False, cwd=project_root,
  env=sanitized_env, timeout=..., capture_output=True, text=True)` runs the resolver's exact fixed
  argv, gated by the same approval/linkage/scope/fresh-trust-re-check/resolver invariant as every
  other kind. Timeout fails closed with no retry; output is captured, byte-bounded, and
  redaction-scanned before any storage (a critical finding blocks the result instead of storing it);
  environment is allowlist-built (`PATH`/`PYTHONIOENCODING`, plus `SystemRoot`/`SystemDrive` on
  Windows only) — no inherited API keys/credentials, no `.env`. See
  [command executor decision](../decisions/2026-07-02-workbench-command-executor.md). **The panel now
  shows and can execute allowlisted commands** (PR #81): an approved, pending, resolver-allowlisted
  `run_command` action gets a content-free command preview (label, fixed argv with the local
  interpreter path masked, timeout, output cap, `shell=false`) and an "Execute approved command"
  button — no separate payload-artifact requirement (commands don't have one; the resolver + trust
  boundary gate them instead). The browser still sends only the action id; the execute handler never
  reads a request body, so a command/argv/cwd/env/timeout supplied there has zero effect. Results
  (exit code, timed-out/truncated flags, bounded/redacted stdout/stderr) come back in the execute
  response, never a raw/huge dump. This completes the v0.5 guarded-executor track (PR #72–#81). See
  [panel command results decision](../decisions/2026-07-02-workbench-panel-command-results.md).
  **PR #82** adds a docs-only release readiness checklist — what v0.5 contains/excludes, a dogfood
  recipe (the "Create demo task" button seeds **no executable action**; real execution needs a
  manually seeded temp-project fixture), and smoke/security/release-blocker checklists before a
  v0.5.0 tag. It also flags that the context pack is nearing its budget (PR #81 needed one more
  fallback step than earlier PRs to stay 21/21) — keep future decision records concise. See
  [release readiness decision](../decisions/2026-07-02-v0.5-release-readiness.md). **PR #83** prepared
  `docs/releases/v0.5.0.md` ahead of tagging; **PR #84** bumped `backend/__init__.py`/`pyproject.toml`
  to `0.5.0` and added the dated `CHANGELOG.md` `[0.5.0]` section. **`v0.5.0` is now tagged** (annotated
  git tag pushed to `origin`); the GitHub Release itself remains a separate manual step. **PR #85**
  (docs-only) plans **v0.5.1 dogfood/hardening** — fresh-install, Workbench panel, Windows-specific,
  UX, and security-regression checklists on a clean clone and a real small repo, before any v0.6 work.
  Named known issues: `uv.lock`'s stale self-version entry (pre-existing, not a `v0.5.0` blocker), the
  context-pack budget running close to its limit, the demo's intentionally non-executing seed, and
  Windows/Linux parity still needing real-world verification. See
  [v0.5.1 dogfood/hardening decision](../decisions/2026-07-02-v0.5.1-dogfood-hardening.md). **PR #86**
  ran that checklist for real (clean clone, Windows/PowerShell) — everything matched the dev checkout
  (0 critical redaction, 21/21 context/MCP, 570 tests); found and fixed three small docs bugs (a
  README `uv sync`→bare-`python` example that fails without `uv run`, a stale `workbench serve --help`
  text predating real execution, and a missing venv-interpreter note in the PR #85 checklist itself).
  No executor/panel/CLI behavior changed. See
  [clean-clone dogfood report](../plans/v0.5.1-clean-clone-dogfood-report.md). **PR #87** followed up
  on PR #86's leftover-process finding: confirmed it's a **`uv run` process-tree artifact** (killing
  only the outer `uv` process can leave its python child running; a direct venv-python launch always
  released cleanly), not a Workbench bug. A simulated Windows `CTRL_C_EVENT` didn't trigger shutdown
  within 8s either way in automated testing, but no human-attended real interactive terminal was
  available to confirm or rule out a real bug — stays **inconclusive**, not confirmed; the existing
  shutdown code already follows the standard, correct pattern. **No code changed.** See
  [interactive smoke report](../plans/v0.5.1-workbench-interactive-smoke-report.md). **PR #88**
  corrects that finding: a maintainer's real manual Ctrl+C test was clean (prompt returned
  immediately); the `netstat` listener seen afterward on the default port was an unrelated local
  service (`PhoneScriptRunner`), not vibe-council — **no confirmed shutdown or `0.0.0.0`-bind bug**.
  Added defense-in-depth anyway: `make_server()` re-checks the actual bound address after `bind()`,
  `effective_bind_host()`/`_startup_lines()` make the printed URL provably match what's really bound,
  and a new regression test simulates Ctrl+C and asserts `server_close()` actually closes the socket.
  No change to the blocking serve loop or a new CLI flag — neither was warranted. LAN/mobile + voice
  remain deferred to v0.6+. **PR #89** closed the last open v0.5.1 exit-criteria item: manually seeded
  a real `write_file` action and a real `run_command` action in a temp/safe project and drove the
  panel's actual HTTP execute path (`curl`, no browser) — both executed successfully, both negative
  cases (non-allowlisted command, missing payload artifact) failed closed, and a crafted request body
  had **zero effect** on what actually ran (empirically confirmed, not just code-read). Found and fixed
  two small display/metadata bugs (`ExecutionResult.dry_run` stayed `true` on real executions; a
  completed/blocked `run_command` card falsely claimed "does not resolve to an allowlisted argv") —
  neither changes what the executor/trust boundary allows. See
  [manual execution dogfood report](../plans/v0.5.1-manual-execution-dogfood-report.md). **PR #90**
  fixed the recurring `uv.lock` self-version drift (plan §8): the lockfile's local `vibe-council`
  package entry had read a stale `0.2.0` since the pre-v0.3.0 project-rename sync while
  `pyproject.toml`/`backend/__init__.py` stayed correctly at `0.5.0` — `uv sync` deterministically
  rewrites exactly that one line, no dependency versions changed, and a second `uv sync` is a no-op.
  Committed (precedent: an earlier `1d6a3b9` commit did the same kind of self-metadata sync), stopping
  the accidental `uv.lock` diff several v0.5.1 passes had to avoid staging. This closed v0.5.1's exit
  criteria. **PR #91** is v0.5.1 release prep: `backend/__init__.py`/`pyproject.toml` now report
  `0.5.1`, `uv.lock`'s self-version entry is synced to match (one line, no dependency change),
  `CHANGELOG.md` gained a dated `[0.5.1]` section, and
  [`docs/releases/v0.5.1.md`](../releases/v0.5.1.md) documents the patch — clean-clone/Windows
  dogfood, interactive Workbench smoke, localhost bind/shutdown hardening, manual execution
  dogfood, and `uv.lock` hygiene (PR #86–#90), with the security posture explicitly unchanged. **No
  new command surface, no allowlist growth, no tag, no GitHub Release** in this PR — the `v0.5.1`
  git tag and GitHub Release are a separate, manual step once it merges. **v0.5.1 is now tagged.**
  **PR #92** is a small v0.5.2 security hardening from a Fable architecture review, landed **before**
  the v0.6 agent-proposal bridge: it closes a DNS-rebinding class gap on the Workbench panel. Binding
  `127.0.0.1` doesn't stop a page whose domain re-resolves to loopback (the browser still sends that
  page's original `Host`), so every request's `Host` header must now name a literal loopback host
  (`127.0.0.1`/`localhost`/`::1`, any port; missing/malformed/multiple `Host` fails closed) —
  validated by a pure `host_header_is_local()` before routing on `GET /`, `GET /api/state`, and all
  POSTs. `GET /api/state` (previously unauthenticated, and it exposes runtime tasks/approvals/actions)
  is now gated on the **same** startup token as the POSTs, via `X-Workbench-Token` or the `?token=`
  the panel URL already carries; the token is never echoed in JSON. `GET /` stays tokenless (Host
  validation is its guard) so the panel URL still loads. **No executor/panel execution behavior
  changed, no new endpoint, no CORS, no allowlist/dependency change, no version bump.** **PR #92 is
  merged.** A **Fable implementation pack** now lives in [`docs/fable/`](fable/README.md) (docs-only):
  the full phase-by-phase plan an implementer follows for future work — current-state baseline,
  operating rules, product vision, the non-negotiable security invariants, the v0.5.2→v0.9+ roadmap,
  the **v0.6 agent-to-Workbench bridge** design + concrete proposal schema (file/CLI intake, server
  mints ids/hash, no new network endpoint, no `cloud_call`, no allowlist growth), onboarding/session
  launcher, the Obsidian-like vault (extend `docs/context/`, not a new `.vibe/`), cross-project
  onboarding, tighten-only personalization, website positioning, open-core path, an implementation
  playbook, and copy-paste prompt templates. It does not change code or behavior; roadmap + security
  invariants remain the source of truth. Leading next code phase: the **v0.6.0 agent bridge**.
  **PR #94** is v0.5.2 release prep: `backend/__init__.py`/`pyproject.toml` now report `0.5.2`,
  `uv.lock`'s self-version is synced to match (one line, no dependency-graph change), `CHANGELOG.md`
  gained a dated `[0.5.2]` section, and [`docs/releases/v0.5.2.md`](../releases/v0.5.2.md) documents
  the patch (Host-header validation + `/api/state` token gate from PR #92, and the `docs/fable/` pack
  from PR #93). **No new command surface, no allowlist growth, no tag, no GitHub Release** in this PR
  — the `v0.5.2` tag and GitHub Release are a separate, manual step once it merges. **v0.5.2 is now
  tagged.** **v0.6 phase 1** adds `backend/workbench_proposals.py` — proposal **schema v1** + pure,
  fail-closed validation, the typed external contract for the agent bridge (per
  [`docs/fable/06`](fable/06-proposal-schema.md)): strict unknown-key rejection at every level;
  `write_file`/`edit_file` with relative trust-checked targets, exact payload shapes, and NUL/size
  caps (executor stays final authority); `run_command` by **exact allowlist label only** (resolver ∧
  trust two-gate rule); server-minted fields (ids, `payload_hash`, statuses, verdicts) and
  argv/env/cwd/timeout/shell/freeform-`command` hard-rejected; `proposal_id` strictly
  charset-validated (future dedup key). **Validation only — no importer, no store writes, no
  execution, no `subprocess` import, no panel/CLI/network change.** **v0.6 phase 2** adds the
  importer (`backend/workbench_proposal_importer.py`) + `vibe workbench propose <file | ->`: a
  validated proposal becomes a Task + pending ApprovalRequest + pending Action through the
  **existing, unchanged** trust/auditor/panel/executor path; all ids and the payload hash are
  **server-minted**; raw payloads live only in the write-once payload artifact (dedup record stores
  a fingerprint hash only). **Dedup by `proposal_id`, globally** (never agent-scoped — dedup must
  not depend on spoofable identity): identical re-import returns the original ids; same id with
  materially different content is a **conflict, fail closed**. CLI failure creates no runtime files;
  stdout is a JSON result (never raw payload). No execution on import, no network endpoint, no
  allowlist growth. **v0.6 phase 3** adds panel agent-proposal visibility
  (`backend/workbench_panel.py`): imported agent-proposed tasks show a "proposed by agent: `<name>`"
  badge (role + `proposal_id`, all HTML-escaped) so they're distinct from demo/manual tasks —
  display-only, derived from the task `agent:<name>` source + a read-only importer lookup
  (`proposal_meta_for_task`); no raw payload in HTML or `/api/state` JSON, no token exposure,
  approval/execution/Host/token/CORS behavior unchanged. **v0.6 phase 4** documents the bridge in
  [`docs/workbench-agent-bridge.md`](workbench-agent-bridge.md) (overview/flow, safety model, CLI
  usage, safe examples, rejected-example/dedup/conflict cases, agent + operator workflows), with
  README + `docs/agent-quickstart.md` §10 pointers — docs only. **PR #99** is v0.6.0 release prep:
  `backend/__init__.py`/`pyproject.toml` now report `0.6.0`, `uv.lock`'s self-version is synced (one
  line, no dependency-graph change), `CHANGELOG.md` gained a dated `[0.6.0]` section, and
  [`docs/releases/v0.6.0.md`](../releases/v0.6.0.md) documents the agent-to-Workbench proposal bridge
  (PR #95–#98) with the security posture unchanged/extended-upstream-of-approval. **No new command
  surface, no allowlist growth, no tag, no GitHub Release** in this PR — the `v0.6.0` tag and GitHub
  Release are a separate, manual step once it merges. **Budget policy: Fable is technical
  lead/architect only; Opus/Sonnet implement routine PRs** — see
  [`docs/fable/v0.6-followup-implementation-plan.md`](fable/v0.6-followup-implementation-plan.md).
  **v0.6.0 is now tagged/released.** **v0.6.1 phase 1** adds a **role-aware agent guide**
  (`vibe guide claude --role task-shaper|planner|coder|reviewer|release-manager`): a stdout generator
  (no `/council` as a real command) pairing a role-specific workflow with the common rules (`vibe`
  not `/council`; council is reviewer/context/memory not implementer; cheap/balanced/full policy;
  before/after-coding workflow; Workbench propose→approve→execute basics; never-stage list).
  **v0.6.1 phase 2** adds opt-in `--write`: `vibe guide claude --role <role> --write [FILE]` appends
  the role's section to a `CLAUDE.md`-style file (default `CLAUDE.md`) and reports the path — same
  append + marker-skip convention as the plain `--write` (never overwrites; per-role marker lets
  roles coexist and skips re-runs; no `--force` needed). Without `--write`, role output stays
  stdout-only; only the explicit target file is touched. `vibe guide claude` with no role is
  unchanged. **v0.6.1 phase 3** adds **Codex & Fable guide topics** (`vibe guide codex` /
  `vibe guide fable`, same `--role` + `--write` machinery): Codex emphasizes vibe-as-reviewer/
  guardrail, read-first, small PRs, tests-before-report, propose-don't-bypass; Fable emphasizes its
  cost/technical-lead policy (plan-first, curated packs not broad scans, Opus/Sonnet implement
  routine PRs, Fable for major planning/critical blockers/high-leverage reviews). Per-topic default
  write files (`CLAUDE.md`/`AGENTS.md`/`FABLE.md`) with distinct markers so topics/roles coexist.
  `claude` unchanged; `/council` still a documented future idea only. No Workbench/importer/executor/
  trust/dependency change. **v0.6.2 phase 1** scaffolds the **project vault** under
  `docs/context/project/`: alongside `README.md`/`STATUS.md`, adds `ROADMAP.md`, `DECISIONS.md`
  (index/pointer into `docs/decisions/`, not a canonical store), `PROGRESS.md` (curated milestone
  digest), `RISKS.md`, `WORKFLOWS.md`, `NOTES.md` — curated, committed, public-safe Markdown that
  agents read before planning/coding. **The context builder is unchanged** (pack = STATUS.md +
  decision index, still 21/21; the vault is read directly / discovered via pointers, not injected
  into the budgeted pack). Not a database/Obsidian-dep/launcher. No Workbench/importer/executor/trust/
  dependency change. **v0.6.2 phase 2** adds **`vibe project doctor`** — a read-only onboarding-
  readiness diagnostic (new `project` subcommand, distinct from the provider `vibe doctor`): checks
  the vault + core docs are present, no dangerous **staged** file (`.env`/`.council/`/private plans →
  fail, staged `uv.lock` → warn), context health (in-memory `build_pack`/`check_pack`, 21/21), and
  the `vibe guide` commands (`/council` explicitly not-a-real-command). Exit 0 ready / non-zero with
  next steps; git-unavailable → warning. Writes nothing, creates no `.council/`, no model/provider/
  network call. No context-builder change. **v0.6.3** adds **`vibe context export --for
  {claude|codex|fable} [--role <role>]`** — a read-only onboarding context handoff: header
  (`vibe`-real/`/council`-future), operating rules + agent guidance + never-stage list (reused from
  the guide machinery), project-vault **pointers** (not a full dump), an in-memory context-health
  summary, the Workbench proposal flow, and a `vibe project doctor` reminder. Stdout by default;
  `--output FILE` writes it, never overwriting. No `.council/` creation, no model/provider/network
  call; the existing `context export claude-code` path is unchanged. **v0.6.3 release prep** bumps
  `backend/__init__.py`/`pyproject.toml`/`uv.lock` self-version to `0.6.3` (one line, no
  dependency-graph change), adds a dated `CHANGELOG.md` `[0.6.3]` section, and
  [`docs/releases/v0.6.3.md`](../releases/v0.6.3.md) bundling the onboarding arc (guide layer, project
  vault, project doctor, context export) as the "cross-project agent onboarding" release. All
  read-only/local; no Workbench trust change, no `/council`, no dependency change. **No tag / GitHub
  Release** in the PR — those are a separate manual step once it merges. **v0.6.3 is now
  tagged/released.** **v0.7 personalization planning has started (docs-only):**
  [`docs/fable/v0.7-personalization-and-project-profile-plan.md`](../fable/v0.7-personalization-and-project-profile-plan.md)
  is the **source brief** — a council-in-the-loop plan for a Markdown-first personalization /
  project-profile layer (`docs/context/project/PROFILE.md`/`PREFERENCES.md`/`AGENTS.md`), **tighten-only**
  (personalization may tighten but never loosen a guardrail), with explicit non-goals (no vector DB /
  database / hosted stack / auto-execution / trust relaxation), an A–E PR breakdown, and a
  future-Fable architecture prompt. **v0.7 PR A landed the project profile/preferences scaffold**:
  public-safe committed `docs/context/project/PROFILE.md` / `PREFERENCES.md` / `AGENT-ROLES.md` (a
  vault file, **not** a root `AGENTS.md` — balanced-review corruption-risk guidance). Documentation
  only — no command reads/enforces them yet. **v0.7 PR B** made `vibe project doctor` **advisory**ly
  report those scaffold files (present → ok, missing → warn, never a failure; root `AGENTS.md` not
  required, warns if present). **v0.7 PR C** added a "Project profile & preferences" section to
  `vibe context export --for <agent>` — **pointers only** to `PROFILE.md`/`PREFERENCES.md`/
  `AGENT-ROLES.md` (never inlined), a tighten-only note, a root-`AGENTS.md`-not-canonical note, and a
  `vibe project doctor` recommendation; reads no `.council/profile.*`, degrades gracefully if missing.
  **v0.7 PR D** added the same "Project profile & preferences" pointer section to `vibe guide
  {claude|codex|fable}` output (base topic, role-specific, and `--write` sections) — pointers only, no
  preference parsing/application, reads no `.council/profile.*`, `--write` marker-skip unchanged.
  All still read-only, no `.council/`, no model call. **v0.7 PR E (release prep)** bumped
  `backend/__init__.py`/`pyproject.toml`/`uv.lock` self-version to `0.7.0` (one line, no
  dependency-graph change), added a dated `CHANGELOG.md` `[0.7.0]` section, and
  [`docs/releases/v0.7.0.md`](../releases/v0.7.0.md) bundling the v0.7 A–D personalization arc as the
  "safe personalization / project-profile scaffold" release; README release status → v0.7.0.
  **v0.7.0 is now tagged/released.** **v0.7.1 hardening planning has started (docs-only):**
  [`docs/fable/v0.7.1-hardening-architecture-plan.md`](../fable/v0.7.1-hardening-architecture-plan.md)
  is the **source plan** — a Fable architecture pass scoping hardening (not feature expansion): a
  narrow `.council/profile.*` redaction rule + lock-in tests, doctor root-`AGENTS.md` consistency
  polish, export/guide invariant tests, and v0.7.1 release prep, in a 4-PR Opus/Sonnet breakdown with
  copy-paste prompts. Non-goals: no preference parser/application, no local profile store, no vector
  DB/hosted stack, no trust change. **v0.7.1 PR 1 landed the local-profile redaction hardening:** a
  `local-profile-path` WARNING rule flagging concrete `.council/` profile filenames in tracked docs
  (advisory; glob form `.council/profile.*` ignored; public scaffold files not flagged;
  WARNING→CRITICAL promotion path) plus lock-in tests (secret-in-scaffold → CRITICAL; staged
  local-profile → doctor FAIL; enumerated real-repo findings). Warning count 22 → 30; no behavior/
  trust/dependency change. **v0.7.1 PR 2 landed the project-doctor consistency polish:** a
  state-differentiated scaffold summary (all-present / none "missing" / partial "incomplete" listing
  missing files), a state-aware root-`AGENTS.md` advisory (informational vs. "configuration
  mismatch"; never advises removal), and a `vibe context export` line in the guide block — all
  advisory (READY/NOT-READY and dangerous-staged FAIL unchanged), read-only, no `--fix`. **v0.7.1 PR 3
  locked the export/guide profile invariants** (tests + tiny docs only): export & guide profile
  sections are size-bounded, deterministic (no timestamp), and gracefully degrading (byte-identical
  with/without the scaffold); a wording-invariant guards "advice to read, not commands"; a vault
  consistency check + a context-pack no-ingest check (still 21/21). No behavior change. **v0.7.1 PR 4
  (release prep)** bumped `backend/__init__.py`/`pyproject.toml`/`uv.lock` self-version to `0.7.1`
  (one line, no dependency-graph change), added a dated `CHANGELOG.md` `[0.7.1]` section, and
  [`docs/releases/v0.7.1.md`](../releases/v0.7.1.md) bundling the hardening slice as the
  "personalization hardening" release; README release status → v0.7.1. **v0.7.1 is now
  tagged/released.** **v0.8.x planning has started (council-backed, docs-only):** a council-led process
  (two `vibe review --preset balanced` multi-model passes) produced
  [`docs/fable/v0.8.x-council-debate.md`](../fable/v0.8.x-council-debate.md),
  [`v0.8.x-phase-brief.md`](../fable/v0.8.x-phase-brief.md), and
  [`v0.8.x-fable-input.md`](../fable/v0.8.x-fable-input.md). **Council-chosen theme: "Solidify the core,
  local-first"** — headline agent launcher / session workflows, plus vault polish and carefully-reviewed
  Workbench UX; personalization becomes a **read-only preference-control model + validator, not
  behavior** (guide/context-export stay pointer-only; `.council/profile.*` store + preference applier
  deferred to v0.9.x); mobile/LAN/voice deferred to its own gated security line. **The Fable
  architecture pass is done:**
  [`docs/fable/v0.8.x-architecture-plan.md`](../fable/v0.8.x-architecture-plan.md) resolves the open
  questions (four-type tighten-only **JSON** preference schema in a bounded fenced `PREFERENCES.md`
  block — the `>=3.10` floor has no stdlib TOML; a **read-only validator folded into `vibe project
  doctor`** with a findings-only API; **no application in v0.8.x**; named profiles / profile store /
  Workbench UX / notifications deferred; `vibe init-agent` dry-run-first launcher with **no path
  argument**) and defines a 9-PR sequence (v0.8.0 launcher + localhost CI guard; v0.8.1 vault digest
  + `RELEASES.md`; v0.8.2 schema + validator at **full** review). **v0.8.0 PR 1 landed `vibe
  init-agent` report/dry-run mode** (read-only onboarding report; writes nothing, no path argument).
  **v0.8.0 PR 2 landed `vibe init-agent --write`** — appends the selected agents' guide sections to
  the fixed `CLAUDE.md`/`AGENTS.md`/`FABLE.md` via the existing `_guide_append` (append-only,
  marker-skip idempotent, never overwrites; byte-identical to `vibe guide … --write`); **no path
  argument**, requires explicit `--agent` + `--yes`, creates no `.council/`. No guide/export/doctor
  behavior change. **v0.8.0 PR 3 landed the localhost-only guard** (`tests/test_localhost_guard.py`,
  tests only — no production change): locks that the panel binds loopback only (non-local hosts
  rejected), a runtime `socket.bind`-loopback check, `host_header_is_local` loopback-only, and a
  static "no second listener" scan (only `backend/workbench_panel.py` may construct a listener).
  **v0.8.0 PR 4 (release prep)** bumped `backend/__init__.py`/`pyproject.toml`/`uv.lock` self-version to
  `0.8.0` (one line, no dependency-graph change), added a dated `CHANGELOG.md` `[0.8.0]` section, and
  [`docs/releases/v0.8.0.md`](../releases/v0.8.0.md) bundling the launcher slice as the "agent
  onboarding launcher" release; README release status → v0.8.0. **v0.8.0 is now released.**
  **v0.8.1 PR 5 landed the vault release-history index:** a capped, newest-first
  [`docs/context/project/RELEASES.md`](project/RELEASES.md) (one line per release, hard cap 30, oldest
  entries roll up; pointers to `docs/releases/`, never inlined — an index, not a CHANGELOG/notes
  replacement) plus a STATUS-trimming workflow in the vault `WORKFLOWS.md`; `RELEASES.md` is not
  ingested into the context pack (still 21/21); no `summarize-history` command (deferred), docs + tests
  only. **v0.8.1 PR 6 (release prep)** bumped `backend/__init__.py`/`pyproject.toml`/`uv.lock`
  self-version to `0.8.1` (one line, no dependency-graph change), added a dated `CHANGELOG.md`
  `[0.8.1]` section, and [`docs/releases/v0.8.1.md`](../releases/v0.8.1.md) bundling the vault-polish
  slice as the "vault polish" release; README release status → v0.8.1. **No tag / GitHub Release** in
  the PR — a separate manual step once it merges. **v0.8.1 is now released.**
  **v0.8.2 PR 7 defined the tighten-only preference schema v1 (docs + tests):** a normative
  [`docs/fable/preference-schema-v1.md`](../fable/preference-schema-v1.md) + a single bounded (`≤ 4096
  byte`) fenced `json` block in [`PREFERENCES.md`](project/PREFERENCES.md) with a `schema: 1` field and
  exactly four tighten-only keys (a review-preset floor `cheap|balanced|full` — never `premium`;
  additive extra-sensitive-paths / never-stage relative paths; a usage-flag warning bool). It has **no
  vocabulary** to loosen a safety/security/no-stage/trust rule, change the Workbench executor/trust
  boundary, add shell/auto-execution/network/hosted behavior, override the review policy, or
  hide/suppress dissenting council opinions. **Council personas** (Cost Skeptic, Security Guardian,
  Product Strategist, Local-first Guardian, UX/User Advocate, Risk Officer, Commercialization Lens) are
  documented as a **future v0.9.x** direction — curated presets of these tighten-only values, never a
  policy override — **not defined or applied here.** Docs + tests only: no validator/parser (that is PR
  8), no application (v0.9.x), no council/guide/context-export/doctor behavior change (guide/export stay
  pointer-only). **v0.8.2 PR 8 added the read-only preference validator:** a pure
  [`backend/preferences.py`](../../backend/preferences.py) validates the schema v1 `json` block in
  `PREFERENCES.md` and returns **findings only** (read-only, fail-closed, advisory); `vibe project
  doctor` gains a `Preferences (machine-readable, advisory):` section (valid → ok, missing → note,
  invalid → warn "ignored"). **READY/NOT-READY is unchanged** (a missing/invalid block is never a
  failure). Hardening per §3 Q4 (first/only fenced block, 4096-byte cap, `json.loads` only, key
  allowlist, strict types, relative-path checks, realpath-inside-root symlink defense, UTF-8-only,
  fail-closed); findings-only API — a test asserts no module outside the doctor path imports it. **No
  preference is applied to any behavior** (v0.9.x); no council/guide/context-export change, no
  `.council/profile.*` store. **v0.8.2 PR 9 (release prep)** bumped
  `backend/__init__.py`/`pyproject.toml`/`uv.lock` self-version to `0.8.2` (one line, no
  dependency-graph change), added a dated `CHANGELOG.md` `[0.8.2]` section, and
  [`docs/releases/v0.8.2.md`](../releases/v0.8.2.md) bundling the preference-control slice (schema v1 +
  read-only validator) as the "preference schema + validator" release; README release status → v0.8.2.
  **No tag / GitHub Release** in the PR — a separate manual step once it merges. **v0.8.2 is now
  released; this completes the v0.8.x line.**
  **v0.9.x council planning has started (council-backed, docs-only):** two `vibe review --preset
  balanced` passes produced [`v0.9.x-council-debate.md`](../fable/v0.9.x-council-debate.md),
  [`v0.9.x-phase-brief.md`](../fable/v0.9.x-phase-brief.md), and
  [`v0.9.x-fable-input.md`](../fable/v0.9.x-fable-input.md). **Council-chosen theme: "Apply the proven;
  describe the personas; defer their behavior."** v0.9.0 *applies* the four mechanically-proven,
  add-friction-only v0.8.2 preference keys (additive, reversible, override-flagged; **CLI wins,
  suggest≠enforce**, the guard/executor ignore preferences); v0.9.1 *describes* the council personas as
  **pure documentation** (no schema/validator/behavior) + a v0.10.x dissent-preservation design sketch +
  a v0.9.0 dogfood pass; v0.9.2 = release prep. **Persona *behavior* (prompt emphasis) is deferred to
  v0.10.x** — the council found dissent-suppression a new risk class the tighten-only proofs don't cover.
  Guide/context export stay pointer-only; `.council/profile.*` store, session/workspace, UI/dashboard,
  Workbench-UX all deferred. Next version-line moment: the **Fable architecture pass** over the
  fable-input (architecture + PR breakdown; Fable does not implement), then Opus/Sonnet implement v0.9.0.
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
