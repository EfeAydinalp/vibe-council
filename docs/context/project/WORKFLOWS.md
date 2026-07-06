# Workflows

Common, repeatable workflows for working on vibe-council. Concise and practical; the authoritative
rules live in [`docs/fable/01-operating-rules.md`](../../fable/01-operating-rules.md) and
[`docs/agent-quickstart.md`](../../agent-quickstart.md).

## Normal coding PR

1. Run `vibe project doctor` (read-only) to confirm the repo is onboarding-ready — vault/core docs
   present, no dangerous staged files (`.env`/`.council/`/private plans), context health, guides.
   Then read the vault ([`README.md`](./README.md), [`STATUS.md`](./STATUS.md),
   [`ROADMAP.md`](./ROADMAP.md), [`RISKS.md`](./RISKS.md)) and any `plan.md` before coding. Also skim
   [`PROFILE.md`](./PROFILE.md) (what the project is), [`PREFERENCES.md`](./PREFERENCES.md) (review-preset
   / Fable-usage / implementation-style policy), and [`AGENT-ROLES.md`](./AGENT-ROLES.md) (who does what
   + the `MODEL:` header convention) so you match this project's working preferences. These are
   **read-as-documentation** — tighten-only, and no command enforces them yet (v0.7 scaffold).
2. `vibe status`; for non-trivial work write a short `plan.md` and review it
   (`vibe review --preset cheap|balanced --file plan.md --usage`).
3. Implement a **small, scoped** change; match surrounding style.
4. Run the project tests; then `vibe diff --preset cheap --usage` (`balanced` for security-relevant
   or non-trivial diffs). Apply only useful feedback.
5. Run the gates: `vibe lint --redaction` (0 critical), `vibe decisions lint`, `vibe context build`,
   `vibe context check` (21/21), `vibe mcp inspect --context --health` (21/21).
6. Stage only intended files; run the **no-stage checklist** below; commit; push; open a PR.

## Guide generation & agent onboarding

- `vibe init-agent [--agent claude|codex|fable] [--role <role>]` prints a **read-only onboarding
  report** (dry run): repo readiness (via the project-doctor checks) + per agent what
  `vibe guide … --write` *would* do to the fixed `CLAUDE.md`/`AGENTS.md`/`FABLE.md` files
  (create/append/skip) + the recommended next commands. Writes nothing; no path argument.
- `vibe init-agent --write --agent <agent>... [--role <role>] --yes` **appends** the selected agents'
  guide sections to those fixed files — **append-only, never overwrites, skips an already-present
  section** (idempotent). `--write` requires an explicit `--agent` and `--yes`; there is **no path
  argument** (fixed targets only). It creates no `.council/` and runs no commands.
- `vibe guide {claude|codex|fable} [--role <role>]` prints a role/topic-tailored onboarding pack. It
  now includes a "Project profile & preferences" section with **pointers** to
  [`PROFILE.md`](./PROFILE.md) / [`PREFERENCES.md`](./PREFERENCES.md) / [`AGENT-ROLES.md`](./AGENT-ROLES.md)
  (pointers only, never inlined; tighten-only; reads no `.council/profile.*`).
- Add `--write [FILE]` to append it to a file (per-topic defaults `CLAUDE.md`/`AGENTS.md`/`FABLE.md`);
  it never overwrites — re-runs are skipped and topics/roles coexist.
- `vibe context export --for {claude|codex|fable} [--role <role>] [--output FILE]` prints a read-only
  onboarding context handoff (operating rules + **vault pointers** + **project profile/preferences
  pointers** to [`PROFILE.md`](./PROFILE.md) / [`PREFERENCES.md`](./PREFERENCES.md) /
  [`AGENT-ROLES.md`](./AGENT-ROLES.md) + context-health summary + Workbench flow + a `vibe project
  doctor` reminder). Stdout by default; `--output` never overwrites. The profile section holds to
  four **invariants** (locked by tests): **pointers-only** (never inlines scaffold content),
  **never-reads-`.council/profile.*`** (the local/private profile), **deterministic** (no timestamp),
  and **graceful** (byte-identical whether the scaffold is present or absent). Writes no `.council/`;
  makes no model call. The `vibe guide` profile section holds to the same invariants.
- `vibe project doctor` also reports an **advisory** "Personalization scaffold" section for
  [`PROFILE.md`](./PROFILE.md) / [`PREFERENCES.md`](./PREFERENCES.md) / [`AGENT-ROLES.md`](./AGENT-ROLES.md)
  with a state-differentiated summary (all-present ok / none-present "missing" warn / partial
  "incomplete" warn listing the missing files). It is advisory — a missing/partial scaffold never
  makes the repo "NOT READY"; root `AGENTS.md` is not required (a present-but-`AGENT-ROLES.md`-missing
  state gets a "configuration mismatch" warn, never a removal instruction). The doctor also lists
  `vibe guide` and `vibe context export --for <agent> --role <role>` for onboarding.

## Workbench proposal flow

- To make a bounded change under approval, **propose** it: `vibe workbench propose <file | ->`
  records a *pending* approval and executes nothing.
- A human runs `vibe workbench serve`, reviews the proposed-by-agent card, and approves/rejects/holds;
  execution is a separate, explicit step through the guarded executor. No auto-execution; no arbitrary
  shell; commands are exact allowlisted labels only. See
  [`docs/workbench-agent-bridge.md`](../../workbench-agent-bridge.md).

## Release prep (never ship without explicit approval)

- Bump `backend/__init__.py` + `pyproject.toml`; `uv sync` (self-version line only, no dependency
  churn); dated `CHANGELOG.md` section; `docs/releases/<version>.md`; update README release status.
- Verify all gates green and `vibe --version`. **No git tag or GitHub Release unless explicitly
  allowed** — those are separate, manual steps (see [`docs/release-checklist.md`](../../release-checklist.md)).

## No-stage checklist (before every commit)

Never stage: `.council/`, `.council/runtime/`, `.council/runtime/payloads/`, raw outputs, generated
packs/exports, generated decision drafts, the private local plan files
(`docs/plans/commercialization-and-hosted-platform-feasibility.md`,
`docs/plans/v0.3.1-hardening-and-dogfood.md`), `.env`, `.venv/`, `data/`, `.obsidian/`, cloned repos,
API keys, secrets, and unrelated `uv.lock` churn. Confirm with `git status --short` and
`git diff --cached --name-only`.
