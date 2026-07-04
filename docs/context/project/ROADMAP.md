# Roadmap

A concise, near-term roadmap for vibe-council. This is a **curated summary** — the canonical
phase-by-phase plan lives in [`docs/fable/04-roadmap.md`](../../fable/04-roadmap.md), and accepted
direction lives in [`docs/decisions/`](../../decisions/). Keep this file short; link, don't restate.

## Now

- **v0.7 — personalization** *(in progress; PR A landed the scaffold).* Personal profile / project
  preferences, built on the onboarding surface. The source brief is
  [`docs/fable/v0.7-personalization-and-project-profile-plan.md`](../../fable/v0.7-personalization-and-project-profile-plan.md)
  (Markdown-first data model, A–E PR breakdown, tighten-only invariants); background in
  [`docs/fable/10-personalization-layer.md`](../../fable/10-personalization-layer.md). PR A added the
  public-safe committed scaffold ([`PROFILE.md`](./PROFILE.md) / [`PREFERENCES.md`](./PREFERENCES.md) /
  [`AGENT-ROLES.md`](./AGENT-ROLES.md), documentation only); behavior integration is later PRs.
  Preferences may **tighten but never loosen** a guardrail.

## Recently shipped

- **v0.6.0 — agent-to-Workbench proposal bridge** *(released).* Agents propose bounded actions via
  `vibe workbench propose`; a human approves and executes through the existing guarded executor.
- **v0.6.1–v0.6.3 — cross-project agent onboarding** *(prepared as the `v0.6.3` release).* A role-aware
  `vibe guide {claude|codex|fable} [--role <role>] [--write [FILE]]` layer (read-only generators;
  opt-in append-only write), a local-first Markdown **project vault** (`docs/context/project/`), a
  read-only **`vibe project doctor`** readiness check, and a read-only **`vibe context export --for
  <agent>`** onboarding handoff. All read-only/local; `/council` stays a future idea, not a command.

## Next (near-term, not started)

- **Workbench hardening** — continued dogfood/hardening of the proposal→approval→execute path within
  the existing security model (no new network surface, no allowlist growth by default).

## Later (separate planning, not current implementation)

- **Personalization** (v0.7), **mobile/LAN/voice approval** (v0.8), and **hosted / open-core
  commercial** work (v0.9+) are **deferred and planned separately** — not implemented from this file.
  Commercialization/feasibility detail stays **private/local**, never committed here.

## Guardrails on this roadmap

- The **security invariants** ([`docs/fable/03-security-invariants.md`](../../fable/03-security-invariants.md))
  bound every phase — a later phase must never weaken an earlier one.
- **Fable is architect / technical lead only; Opus/Sonnet implement routine PRs**
  (see [`DECISIONS.md`](./DECISIONS.md)).
