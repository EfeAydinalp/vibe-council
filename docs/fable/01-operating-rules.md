# 01 — Operating rules for an implementing model

These bind Fable / Opus / Claude Code when working in this repo. They are not suggestions. If a rule
conflicts with a task, **stop and ask** rather than choosing.

## Before writing any code

1. **Read the relevant phase docs first.** At minimum: this file,
   [03-security-invariants.md](03-security-invariants.md), and the phase doc for the work
   ([04-roadmap.md](04-roadmap.md) points to it). Do not implement from the task text alone.
2. Run `vibe status` to see workspace state.
3. For non-trivial work, write a short `plan.md` and review it (`vibe review --preset cheap --file
   plan.md --usage`; `balanced` when the work is non-trivial or touches safety/architecture).

## Change discipline

- **Small PRs only.** One phase is several PRs. A PR should be reviewable in one sitting.
- **No broad refactors** unless the task explicitly asks. Match surrounding code style, comment
  density, and idioms.
- **Stay in scope.** Do not start provider-abstraction, app/TUI/web, MCP write-authority, persona/
  advisor, personalization, mobile/LAN, or hosted/commercial work unless *that* phase has explicitly
  started.
- **Stdlib-only by default.** Do not add a runtime dependency without a stated reason and approval.

## Security-shaped rules (see [03](03-security-invariants.md) for the full list)

- No hidden auto-execution. Approval never runs anything; execution is a separate explicit step.
- No arbitrary shell; no dynamic command args/env/cwd/timeout from an agent or browser.
- No command-allowlist expansion unless separately scoped and reviewed.
- No CORS widening. No LAN/mobile/remote/hosted surface unless that phase starts.
- No `cloud_call` proposals in the v0.6 bridge.
- No profile/personalization may loosen a guardrail — it may only tighten.

## Never touch / never stage

- `.env`, `.venv/`, `.council/`, `.council/runtime/`, payload artifacts, raw outputs, generated
  packs/exports/drafts, `data/`, `.obsidian/`, secrets/keys, cloned repos.
- Private local plans (`docs/plans/commercialization-and-hosted-platform-feasibility.md`,
  `docs/plans/v0.3.1-hardening-and-dogfood.md`).
- **No repo visibility change. No force-push. No history rewrite. No merge** unless explicitly asked.
- **No version bump, tag, or GitHub Release** unless explicitly instructed.
- Do not remove/weaken `karpathy/llm-council` attribution. Do not add a `LICENSE` (Question 0 open).

## The `vibe` tools you should use

Run the backend as `python -m backend.cli …` from the repo root (or `vibe …` if installed). Keep
stdout machine-clean; diagnostics/usage go to stderr. Always pass `--usage` for model-spending
commands.

- `vibe status` — workspace state (no tokens).
- `vibe doctor` — provider/config diagnostics (no tokens). Use freely.
- `vibe review --preset <p> --file <f> --usage` — review a plan/doc.
- `vibe diff --preset <p> --usage` — review the working diff.
- `vibe lint --redaction` — 0-critical guard over tracked public docs.
- `vibe decisions lint` — lint curated decision records.
- `vibe context build` / `vibe context check` — build/score the local context pack (21/21 target).
- `vibe mcp inspect --context --health` — read-only MCP context+health (21/21 target).

## Review-cost policy

- **cheap** — routine implementation diffs, docs.
- **balanced** — non-trivial plans/diffs, anything security- or architecture-relevant.
- **full** — only major roadmap/product/security-architecture questions, or when cheap/balanced
  surfaces a serious conflict. Not by default. `premium` needs explicit human approval and
  `--allow-premium`.

Do not be performatively stingy (a balanced review on a security diff is worth it), but do not burn
premium/full calls casually.

## Naming reality check

`vibe` is the **real** CLI. `/council` is a **future UX idea** — a possible host-specific custom
command (Claude Code slash-command) or shell alias — **not** a current shell command. Never document
`/council` as if it exists today. See [07-agent-session-launcher.md](07-agent-session-launcher.md).

## When to stop and ask

Stop and surface the issue instead of proceeding if you hit: a security-invariant conflict, an
unexpectedly broad diff, dependency churn you didn't intend, a request that implies a version/tag/
release, or any private artifact getting touched. Report faithfully — if tests fail, say so with the
output; if a step was skipped, say that.
