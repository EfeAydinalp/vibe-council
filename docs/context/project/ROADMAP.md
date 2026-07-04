# Roadmap

A concise, near-term roadmap for vibe-council. This is a **curated summary** — the canonical
phase-by-phase plan lives in [`docs/fable/04-roadmap.md`](../../fable/04-roadmap.md), and accepted
direction lives in [`docs/decisions/`](../../decisions/). Keep this file short; link, don't restate.

## Now

- **v0.6.2 — Obsidian-like project vault** *(in progress).* A local-first, Markdown, human- and
  agent-readable project-memory scaffold under `docs/context/project/` (this folder). Not a database,
  not an Obsidian plugin, not a launcher — just curated committed Markdown that agents read before
  planning/coding. See [`docs/fable/08-obsidian-project-vault.md`](../../fable/08-obsidian-project-vault.md).

## Recently shipped

- **v0.6.0 — agent-to-Workbench proposal bridge** *(released).* Agents propose bounded actions via
  `vibe workbench propose`; a human approves and executes through the existing guarded executor.
- **v0.6.1 — role-aware onboarding guide.** `vibe guide {claude|codex|fable} [--role <role>]
  [--write [FILE]]` — read-only stdout generators (opt-in append-only file write) to reduce
  per-session re-onboarding.

## Next (near-term, not started)

- **Onboarding / session-launcher improvements** — build on the guide layer (e.g. `vibe project
  doctor`, cross-project export). Still a **generator**, not an interactive launcher; `/council`
  stays a future host-specific idea, **not** a real `vibe` command.
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
