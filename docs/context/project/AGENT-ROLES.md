# Agent roles

Per-agent role expectations for working on vibe-council — a curated, committed part of the
[project vault](./README.md). This is the "who does what" page: which model/agent is expected to do
which kind of work, and the conventions every agent follows.

> **Scaffold only (v0.7 PR A).** This file is **documentation agents read**; no command reads or
> enforces it yet. It is deliberately a **vault `AGENT-ROLES.md`, not a root `AGENTS.md`** — the
> balanced review of the [v0.7 brief](../../fable/v0.7-personalization-and-project-profile-plan.md)
> flagged a corruption risk if one file were both a `vibe guide --write` **output target** and a
> preference **source**. Root `AGENTS.md` stays the guide-output target only; this file is the
> preference source.

## Role expectations

- **Claude / Opus / Sonnet (implementers)** — implement scoped, small PRs; read the project context
  before coding; run tests and `vibe diff` before reporting; propose (don't bypass) Workbench actions.
  Opus/Sonnet are the **routine implementers**.
- **Codex** — same implementer discipline: use vibe as a reviewer/guardrail, read instructions first,
  small PRs, tests before report, propose don't bypass.
- **Fable (technical lead / architect)** — expensive; **not** a routine implementer. Use only for phase
  planning, a critical blocker, or a high-leverage architecture/security review. No broad repo scans —
  read the curated brief + the phase's minimal reading set, produce a plan/review, then **stop**. See
  the Fable usage policy in [`PREFERENCES.md`](./PREFERENCES.md).
- **The council (`vibe review` / `vibe diff`)** — an independent multi-model **second opinion** on
  plans and diffs. **Advice to filter, not authority.** Preset per the review policy in
  [`PREFERENCES.md`](./PREFERENCES.md).
- **The user** — the **final authority**. Approves, merges, tags, and releases; no model does those
  autonomously.

## MODEL header convention

Every task prompt states the intended model/budget up front, so routing is unambiguous:

- `MODEL: OPUS/SONNET CODE` — routine implementation, reviews, focused single-PR work.
- `MODEL: FABLE CODE` — a phase-planning / architecture pass by Fable (only when explicitly approved).

## `vibe` is the real CLI

**This project's CLI is `vibe`.** `/council` is a possible **future** host-specific custom command
(e.g. a Claude Code slash-command) or shell alias — it does **not** exist today. Never document or
invoke `/council` as if it were a real command.

## Council-in-the-loop production workflow

1. **User / product direction** — the maintainer sets direction and holds final authority.
2. **Council debates / reviews / criticizes** — `vibe review`/`vibe diff` give an independent second
   opinion on plans and diffs.
3. **Council / Opus / Sonnet creates the phase brief** if one is missing.
4. **Fable reads only the curated brief / minimal context**, as an expensive architect, **if
   approved** — produces an architecture review or PR breakdown, then stops.
5. **Opus / Sonnet implement the PRs**, one small reviewable PR at a time.
6. **Council reviews plans and diffs** (cheap/balanced; full only for major architecture/security).
7. **The user is the final authority.**

## Guide / context-export / project-doctor usage

- `vibe project doctor` (read-only, no tokens) — confirm the repo is onboarding-ready before starting.
- `vibe guide {claude|codex|fable} [--role <role>]` — print a role/topic-tailored onboarding pack;
  `--write [FILE]` appends to a `CLAUDE.md`/`AGENTS.md`/`FABLE.md`-style file (append-only, never
  overwrites). Root `AGENTS.md` is a **guide-output target**, distinct from this vault file.
- `vibe context export --for {claude|codex|fable} [--role <role>]` — a read-only onboarding context
  handoff (operating rules + vault **pointers** + context-health summary + Workbench flow). Read-only;
  no model call.

## Workbench proposal flow

To make a bounded change under approval, **propose** it — do not act directly:

- `vibe workbench propose <file | ->` records a *pending* approval and runs nothing.
- A human runs `vibe workbench serve`, reviews the proposed-by-agent card, and approves/rejects/holds.
- Execution is a **separate, explicit** step through the existing guarded executor — **no
  auto-execution**, no arbitrary shell, commands are exact allowlisted labels only, and raw payload
  content is never rendered. See [`docs/workbench-agent-bridge.md`](../../workbench-agent-bridge.md).

## Tighten-only personalization principle

**Personalization may tighten rules but never loosen safety/security rules.** Role preferences may add
friction (stricter review, closer confirmation) but can never widen the command allowlist, relax the
trust boundary, enable auto-execution, or expand the network surface. See security invariant #17 in
[`docs/fable/03-security-invariants.md`](../../fable/03-security-invariants.md).

## Role docs are source-of-truth advice, not a runtime override

These role expectations (and the preferences in [`PREFERENCES.md`](./PREFERENCES.md)) are
**documentation agents read and follow** — a curated source of truth for *how* to work here. **No
command reads or enforces them, and they never override runtime behavior.** In particular they never
change what the council does, what the guide/context-export emit (those stay **pointer-only** — they
reference these files, never inline their contents), or how the Workbench trust/executor gate decides.

**Council review lenses** — named viewpoints such as **Security Guardian**, **Cost Skeptic**, and
**Local-first Guardian** (plus future stubs: Product Strategist, UX/User Advocate, Risk Officer,
Commercialization Lens) — are **documentation only**: a human/agent reviewer's mental lens, **not** a
command, schema field, or behavior. They are written up in
[`docs/fable/council-review-lenses.md`](../../fable/council-review-lenses.md) (v0.9.1, subject to
change). A lens may only *add* scrutiny — it never suppresses another lens's dissent, loosens a
safety/trust rule, or changes prompts/ranking/synthesis, the preference system, or the Workbench/trust
boundary. If a lens ever becomes *behavior* (v0.10.x+), it arrives as a **curated preset of the
tighten-only preference schema v1** (see [`PREFERENCES.md`](./PREFERENCES.md) → "Machine-readable
preferences" and the normative
[`docs/fable/preference-schema-v1.md`](../../fable/preference-schema-v1.md)) plus advisory
review-emphasis prose, gated behind a dissent-preservation design. **No lens/persona is defined,
selected, or applied today.**

## Safe-to-commit boundary

Content is **safe to commit** here if it holds no secrets, no private user data, no absolute machine
paths/usernames, and the author would be comfortable seeing it in a public GitHub repo. All vault
files are subject to `vibe lint --redaction`; a **critical** finding blocks the commit.

## What must never go here

This file is **committed and world-readable**. Never put:

- Secrets, API keys, credentials, or tokens.
- Raw model / council outputs.
- Runtime payloads or any `.council/runtime/` artifact.
- Private local plans (see the never-stage list in [`WORKFLOWS.md`](./WORKFLOWS.md)).
- `.env` / `.venv/` / `data/` contents or any data dump.
- Precise private local data (absolute machine paths, usernames-in-paths, private hostnames).
- Sensitive personal facts (health/medical/political/etc.) **unless** the user explicitly requests it
  *and* it is safe and appropriate for a committed, public file. Default: omit.
