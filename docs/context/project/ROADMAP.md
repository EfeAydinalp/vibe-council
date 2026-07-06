# Roadmap

A concise, near-term roadmap for vibe-council. This is a **curated summary** — the canonical
phase-by-phase plan lives in [`docs/fable/04-roadmap.md`](../../fable/04-roadmap.md), and accepted
direction lives in [`docs/decisions/`](../../decisions/). Keep this file short; link, don't restate.

## Now

- **v0.8.x — implementation in progress (v0.8.0 released; v0.8.1 prepared).** Theme: **"Solidify the
  core, local-first."** Architecture:
  [`docs/fable/v0.8.x-architecture-plan.md`](../../fable/v0.8.x-architecture-plan.md) (9-PR sequence).
  **v0.8.0** (`vibe init-agent` launcher: read-only report + guarded append; localhost-only guard) is
  **released**. **v0.8.1** (capped `RELEASES.md` release-history index + STATUS-trimming workflow;
  docs + tests only) is **prepared** (repo reports `0.8.1`; tag/GitHub Release from
  [`docs/releases/v0.8.1.md`](../../releases/v0.8.1.md) is the remaining manual step). **v0.8.2 in
  progress:** the tighten-only **JSON** preference **schema v1** is defined (PR 7 — normative
  [`docs/fable/preference-schema-v1.md`](../../fable/preference-schema-v1.md) + a bounded block in
  [`PREFERENCES.md`](./PREFERENCES.md); docs + tests only); **next** the **read-only** doctor validator
  (PR 8, full review; **no application** — that is v0.9.x). Guide/context-export stay pointer-only;
  `.council/profile.*` store, named profiles / **council personas** (a future v0.9.x preset of the
  tighten-only schema values), Workbench UX, and local notifications deferred. **Note:** this v0.8.x
  line supersedes the older
  "v0.8 = mobile/LAN/voice" entry in [`docs/fable/04-roadmap.md`](../../fable/04-roadmap.md) — that
  surface-expanding work is now its own gated security line.

## Recently shipped

- **v0.8.1 — vault polish (capped release-history index)** *(prepared as the `v0.8.1` release).*
  A **docs + tests only** patch: new [`RELEASES.md`](./RELEASES.md) newest-first release-history index
  (one line per release, hard cap 30, oldest entries roll up; pointers to `docs/releases/`, never
  inlined — an index, not a CHANGELOG/notes replacement) plus a documented STATUS-trimming workflow in
  [`WORKFLOWS.md`](./WORKFLOWS.md). `RELEASES.md` is not ingested into the context pack (still 21/21);
  no `summarize-history` command, no behavior change, no dependency change. Source plan:
  [`docs/fable/v0.8.x-architecture-plan.md`](../../fable/v0.8.x-architecture-plan.md).
- **v0.8.0 — agent onboarding launcher (`vibe init-agent`)** *(prepared as the `v0.8.0` release).*
  A single onboarding entry point composing `vibe project doctor` / `vibe guide`: a deterministic
  **read-only report**, and a **guarded append** (`--write --agent <agent> --yes` → the fixed
  `CLAUDE.md`/`AGENTS.md`/`FABLE.md`; append-only, marker-skip idempotent, no path argument, no
  `.council/`), plus a tests-only **localhost-only guard** (panel loopback-only; no second listener).
  Local-first, read-only-by-default, no preference behavior, no new dependency. Source plan:
  [`docs/fable/v0.8.x-architecture-plan.md`](../../fable/v0.8.x-architecture-plan.md).
- **v0.7.1 — personalization hardening** *(prepared as the `v0.7.1` release).* Hardening, not feature
  expansion: a `local-profile-path` redaction WARNING for concrete `.council/profile.<ext>` references
  (glob form unmatched; public scaffold allowed; WARNING→CRITICAL promotion path), state-differentiated
  `vibe project doctor` scaffold advisories (all/none/partial; missing warns, never fails), and
  export/guide invariant tests (size-bounded, no inlining, never reads the local profile, gracefully
  degrading, deterministic; context pack still 21/21). All advisory/read-only/tighten-only; no profile
  store or preference parser yet. Source plan:
  [`docs/fable/v0.7.1-hardening-architecture-plan.md`](../../fable/v0.7.1-hardening-architecture-plan.md).
- **v0.7 — safe personalization / project-profile scaffold** *(prepared as the `v0.7.0` release).* A
  council-in-the-loop planning brief, a public-safe committed scaffold ([`PROFILE.md`](./PROFILE.md) /
  [`PREFERENCES.md`](./PREFERENCES.md) / [`AGENT-ROLES.md`](./AGENT-ROLES.md)), and **advisory pointers**
  to it from `vibe project doctor`, `vibe context export`, and `vibe guide`. All advisory/read-only/
  local and **tighten-only** — preferences may tighten but never loosen a guardrail; no preference
  parser/store yet, no root `AGENTS.md` as the canonical source. Source brief:
  [`docs/fable/v0.7-personalization-and-project-profile-plan.md`](../../fable/v0.7-personalization-and-project-profile-plan.md);
  background in [`docs/fable/10-personalization-layer.md`](../../fable/10-personalization-layer.md).
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
