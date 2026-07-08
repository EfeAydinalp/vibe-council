# Roadmap

A concise, near-term roadmap for vibe-council. This is a **curated summary** — the canonical
phase-by-phase plan lives in [`docs/fable/04-roadmap.md`](../../fable/04-roadmap.md), and accepted
direction lives in [`docs/decisions/`](../../decisions/). Keep this file short; link, don't restate.

## Now

- **v0.9.x — "Apply the proven; describe the personas; defer their behavior" (v0.9.0 released; v0.9.1
  prepared as a release).** Council-backed + Fable-architected planning
  ([`v0.9.x-architecture-plan.md`](../../fable/v0.9.x-architecture-plan.md)). **v0.9.0** *applies* the
  four mechanically-proven, add-friction-only v0.8.2 preference keys in **bounded, advisory,
  tighten-only** ways — a review/diff preset floor + `--no-preferences`, a usage-flag warning, and
  doctor staged-path advisories (CLI wins, suggest≠enforce; guard/executor/Workbench/prompt/ranking/
  synthesis stay preference-blind, locked by tests) — and is **released** (tag + GitHub Release live;
  [`docs/releases/v0.9.0.md`](../../releases/v0.9.0.md)). **v0.9.1 — the council review lenses** as
  pure documentation ([`council-review-lenses.md`](../../fable/council-review-lenses.md): Security
  Guardian, Cost Skeptic, Local-first Guardian + future stubs; no schema/validator/behavior) **plus the
  v0.10.x dissent-preservation design sketch**
  ([`v0.10.x-dissent-preservation-sketch.md`](../../fable/v0.10.x-dissent-preservation-sketch.md):
  threat model, structural/content rules, dissent-canary tests, observability, override/rollback,
  acceptance criteria, an honest feasibility verdict — reframing bias is partly a research problem,
  cancellation on the table) — PRs 6–7 done, **PR 8 (release prep) done here**
  ([`docs/releases/v0.9.1.md`](../../releases/v0.9.1.md)); the `v0.9.1` git tag/GitHub Release remain a
  manual step. **Persona *behavior* deferred to v0.10.x** (dissent-suppression is a new risk class);
  guide/context export stay pointer-only;
  `.council/profile.*` store, session/workspace, UI/dashboard, Workbench-UX deferred.
- **v0.10.x product-surface decision gate (docs-only) — verdict: do not open v0.10.x now.** A balanced
  council-style review over
  [`v0.10.x-product-surface-framing.md`](../../fable/v0.10.x-product-surface-framing.md) (five
  candidates: persona/lens behavior, dissent-preservation infrastructure, a scoped v0.9.2 patch, a
  product-surface/commercialization pause, or no-new-surface maintenance) recommended **not** opening a
  v0.10.x line: with no validated demand, an unsolved reframing-bias research residual, and a clean
  release, the safe next step is a short, **human-led product-surface / commercialization planning pass,
  then a time-boxed hold** — not persona behavior. Persona/lens **behavior** stays deferred (and
  cancelable); **Fable is not run next** (no surface chosen).

## Recently completed

- **v0.8.x — "Solidify the core, local-first" (released).**
  Architecture: [`docs/fable/v0.8.x-architecture-plan.md`](../../fable/v0.8.x-architecture-plan.md).
  **v0.8.0** (`vibe init-agent` launcher + localhost-only guard), **v0.8.1** (capped `RELEASES.md` index
  + STATUS-trimming workflow), and **v0.8.2** (tighten-only preference **schema v1** —
  [`docs/fable/preference-schema-v1.md`](../../fable/preference-schema-v1.md) + a bounded block in
  [`PREFERENCES.md`](./PREFERENCES.md) — plus a **read-only, findings-only** doctor validator,
  [`backend/preferences.py`](../../../backend/preferences.py); **no application**) are all **released**.
  **Note:** this v0.8.x line supersedes the older "v0.8 = mobile/LAN/voice" entry in
  [`docs/fable/04-roadmap.md`](../../fable/04-roadmap.md) — that surface-expanding work is now its own
  gated security line.

## Recently shipped

- **v0.9.1 — describe the personas (documentation only)** *(prepared as the `v0.9.1` release).* The
  council **review lenses** as pure documentation
  ([`docs/fable/council-review-lenses.md`](../../fable/council-review-lenses.md): Security Guardian,
  Cost Skeptic, Local-first Guardian + four future stubs; not applied, not schema, not validated) plus
  the **v0.10.x dissent-preservation design sketch**
  ([`docs/fable/v0.10.x-dissent-preservation-sketch.md`](../../fable/v0.10.x-dissent-preservation-sketch.md):
  design only, no implementation — threat model, structural/content rules, dissent-canary tests,
  observability, override/rollback, acceptance criteria, an honest feasibility verdict that treats
  reframing bias as partly a research problem with cancellation on the table). Neither file changes any
  runtime behavior — no prompt/ranking/synthesis, schema, preference reader/validator, guide/export, or
  Workbench/executor/guard/trust change; no dependency change. Source plan:
  [`docs/fable/v0.9.x-architecture-plan.md`](../../fable/v0.9.x-architecture-plan.md).
- **v0.9.0 — apply the proven preferences (tighten-only, advisory)** *(released).* A clamped,
  fail-closed `effective_suggestions()` reader feeds a review/diff preset floor + `--no-preferences`, a
  usage-flag warning, and doctor staged-path advisories — additive, reversible, CLI-wins,
  guard-authoritative; the trust boundary and council prompt/ranking/synthesis stay preference-blind
  (locked by tests). Source plan:
  [`docs/fable/v0.9.x-architecture-plan.md`](../../fable/v0.9.x-architecture-plan.md).
- **v0.8.2 — preference schema v1 + read-only doctor validator** *(prepared as the `v0.8.2` release).*
  The tighten-only preference **schema v1** (normative
  [`docs/fable/preference-schema-v1.md`](../../fable/preference-schema-v1.md) + a bounded fenced `json`
  block in [`PREFERENCES.md`](./PREFERENCES.md): `schema: 1` + `default_review_preset` /
  `extra_sensitive_paths` / `never_stage_extra` / `require_usage_flag`) plus a **read-only validator**
  ([`backend/preferences.py`](../../../backend/preferences.py)) folded into `vibe project doctor` as an
  advisory section (valid → ok, missing → note, invalid → warn/ignored; READY/exit code unchanged).
  Findings-only, fail-closed, stdlib `json` only; the schema is **defined and validated but never
  applied** — council personas are a future v0.9.x preset direction, not v1 fields. Source plan:
  [`docs/fable/v0.8.x-architecture-plan.md`](../../fable/v0.8.x-architecture-plan.md).
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
