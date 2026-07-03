# 00 — Current state (read this first)

Where vibe-council actually is as of the v0.5.2 Workbench hardening (PR #92 merged). This is the
factual baseline an implementer builds on. Do not assume anything beyond what's here is built.

## Product identity

**vibe-council** is a **local-first AI "council" workflow tool** evolving into an **AI Council
Workbench**: multiple LLMs review/answer with anonymized peer ranking, plus a local Workbench where
AI-proposed actions are inspected, approved, and only then executed behind deterministic guards.
Everything runs on the user's machine with their own API key. Forked from and crediting
[`karpathy/llm-council`](https://github.com/karpathy/llm-council) — **preserve that provenance**.

The product is the **CLI + local Workbench**, not a hosted service.

## Shipped layers

### v0.3 — decision memory + project context
- Curated decision records (`vibe decisions new --from-run`, `promote`, `lint`) under
  `docs/decisions/*.md` (committed, canonical long-term memory).
- Local context pack builder/checker (`vibe context build`, `vibe context check`) and export.
- Redaction guard over tracked public docs (`vibe lint --redaction`).
- Operator status; license/provenance "Question 0" checklist.

### v0.4 — read-only MCP / Claude Code workflow
- `vibe mcp contract` / `inspect` / `serve --stdio` — a **read-only** MCP surface exposing project
  status, curated decisions, and the context pack + health to Claude Code / local agents.
- **No write/action authority.** Minimal stdlib JSON-RPC stdio transport (no `mcp` SDK); context
  reads are in-memory (no `.council/` writes). Forbidden write/git/shell/provider tools are
  unreachable.

### v0.5 — AI Council Workbench MVP (guarded execution)
- **Runtime store + state machine** (`backend/workbench_runtime.py`,
  `backend/workbench_orchestrator.py`): a gitignored `.council/runtime/` JSON tree
  (Task / Stage / ApprovalRequest / ApprovalDecision / Action / AuditResult) and a deterministic
  lifecycle (plan → request approval → approve/reject/hold → executing → complete/fail/hold).
- **Deterministic trust boundary** (`backend/workbench_trust.py`) — the real security gate: path
  allow/deny, exact command allowlist, secret patterns, change-size limits, cloud-egress consent.
  Re-run at execution time, not just at approval time.
- **Advisory Approval Auditor** (`backend/workbench_auditor.py`) — a human-readable approval summary
  that copies risk/blocked/findings **verbatim** from the trust boundary; it can never relax a block.
- **Localhost Workbench panel** (`backend/workbench_panel.py`, `vibe workbench serve`) — task/approval
  cards, approve/reject/hold, "Create demo task" button, and a separate explicit **Execute** step.
- **Payload artifacts + hash/scope verification** (`backend/workbench_payloads.py`) — bounded file
  actions carry content in a local, gitignored, write-once `.council/runtime/payloads/<action_id>.json`,
  hashed at creation and re-verified before every real execution.
- **Bounded file write/edit execution** and **exact allowlisted command execution**
  (`backend/workbench_executor.py`, `backend/workbench_commands.py`) — atomic writes, size/line
  limits, path/symlink guard; a fixed label→argv resolver (`sys.executable`-based, no shell, no
  string parsing) running via `subprocess.run(shell=False)` with a sanitized env, project-root cwd,
  timeout, and bounded/redaction-checked output.

### v0.5.1 — dogfood & hardening (patch)
- Clean-clone/Windows quickstart dogfood (PR #86), interactive Workbench smoke (PR #87), localhost
  bind/shutdown hardening + record correction (PR #88), manual execution dogfood + two small
  display/metadata fixes (PR #89), `uv.lock` self-version hygiene (PR #90), release prep (PR #91).
- **Tagged and pushed** (`v0.5.1`).

### v0.5.2 candidate — Workbench Host-header + `/api/state` hardening (PR #92, merged)
- `Host`-header validation on all panel requests (loopback names only; missing/malformed/multiple
  `Host` fails closed) — a DNS-rebinding defense, since binding `127.0.0.1` alone doesn't stop a page
  whose domain re-resolves to loopback.
- `GET /api/state` (which exposes runtime tasks/approvals/actions) now **token-gated** like the POST
  endpoints; token never echoed in JSON. `GET /` stays tokenless (Host validation guards it).
- No executor/panel **execution** behavior changed; no new endpoint, no CORS, no allowlist growth.
  Merged to `master`; not yet bundled into a tagged `v0.5.2` release.

## Health expectations (must stay green)

- **Tests:** the stdlib `unittest` suite is green on Windows/macOS/Linux CI. Post-#92 count is ~587;
  treat the exact number as "current suite passes," not a fixed target.
- **Redaction lint:** `vibe lint --redaction` → **0 critical** (a stable set of ~17 warnings on
  tracked public docs is expected/acceptable).
- **Decisions lint:** `vibe decisions lint` → passes (0 errors).
- **Context check:** `vibe context check` → **21/21**.
- **MCP health:** `vibe mcp inspect --context --health` → **21/21**.
- The **context pack is near its budget** — it trims to fit ~14000 chars with several fallback steps.
  Keep new decision records concise (~4–5 KB). `docs/fable/` is **not** a context-pack input, so it
  does not affect 21/21; but it **is** scanned by redaction lint, so keep it secret-free.

## Never stage / never send to a model

- `.council/`, `.council/runtime/`, `.council/runtime/payloads/`
- raw council outputs, generated context packs/exports, generated decision drafts
- private local plans: `docs/plans/commercialization-and-hosted-platform-feasibility.md`,
  `docs/plans/v0.3.1-hardening-and-dogfood.md`
- `.env`, `.venv/`, `data/`, `.obsidian/`, cloned repos, local artifacts
- API keys / secrets / tokens
- unrelated `uv.lock` churn (only an intentional self-version sync at release, per the checklist)

## Key files an implementer will touch or read

- CLI entry: `backend/cli.py` · orchestration: `backend/council.py` · model client:
  `backend/openrouter.py` · config/presets/modes: `backend/config.py` · guards: `backend/guards.py`
- Workbench: `backend/workbench_runtime.py`, `_orchestrator.py`, `_trust.py`, `_auditor.py`,
  `_executor.py`, `_panel.py`, `_payloads.py`, `_commands.py`
- Tests: `tests/` (stdlib `unittest`). Canonical memory: `docs/decisions/`. Release notes:
  `docs/releases/`. Agent context: `docs/context/`.
