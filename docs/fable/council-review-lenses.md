# Council review lenses (documentation only)

> **v0.9.1 documentation, subject to change — not applied, not schema, not validated; a human
> reviewer's mental lens, not a command.** These lenses are prose a person (or an agent reading this
> repo) can *adopt while reviewing* a plan or diff. **Nothing here runs.** No lens is a preference key,
> a schema field, a flag, or a code path; none influences prompt construction, peer ranking, chairman
> synthesis, model/provider selection, the guide/context-export output, or the Workbench trust/executor
> boundary. Behavior/application is **deferred to v0.10.x or later**, and only behind the
> dissent-preservation framework designed in
> [`v0.10.x-dissent-preservation-sketch.md`](v0.10.x-dissent-preservation-sketch.md) (planned).

## What a "review lens" is

A **review lens** is a named viewpoint — a checklist a reviewer holds in their head — for reading a
change. It is the vocabulary the project uses for "look at this the way a security-minded reviewer
would." vibe-council's real reviewers are the council (`vibe review`/`vibe diff`, an independent
multi-model second opinion) and the human maintainer; a lens does not replace either — it is a *way of
reading*, adopted by a person, that they can also ask the council to emphasize in their own prompt.
This file names three primary lenses and lists four future stubs. It is intentionally short.

## Binding envelope (applies to EVERY lens, now and in future)

Every lens on this page — and any future lens — is bound by the following. A lens that violates any of
these is not a lens; it is a different, separately-reviewed mechanism.

- **Documentation only.** A lens is prose read by a human/agent. It is **not** a preference key, **not**
  a schema field, and does **not** change `PREFERENCES.md` machine-block semantics, the tighten-only
  preference reader/validator, the v0.9.0 review/diff preset floor, `vibe project doctor`, the
  guide/context-export output, prompt construction, peer ranking, chairman synthesis, model/provider
  selection, or the Workbench/importer/executor/guard/trust boundary.
- **Dissent-preservation (non-negotiable).** A lens may only **add** scrutiny, questions, or emphasis.
  It may **never** suppress, hide, downrank, outrank, filter, or override another lens, another
  reviewer, or the council's independent second opinion. Every viewpoint stays visible; a dissenting
  finding is never silenced because a lens was in use.
- **Safety / non-override (tighten-only).** A lens can only ask for *more* care. It can **never** loosen
  a safety/security/no-stage/trust rule, lower a review level, authorize `premium`/`--allow-premium`,
  skip a guard, or override the review policy. The deterministic trust boundary ignores lenses entirely.
- **No store, no UI.** Lenses are committed Markdown. They do **not** create or read a
  `.council/profile.*` store (none exists), and they imply **no** dashboard/UI.
- **Relationship to the preference system (v0.8.2 schema v1 + v0.9.0 application).** Lenses are **not**
  part of the preference schema and change nothing about it. If a lens is ever turned into *behavior*
  (v0.10.x+), it will arrive as a **curated preset of the existing tighten-only schema values plus
  advisory review-emphasis** — an instance of that model, gated behind the dissent-preservation design —
  never a new, broader mechanism, and never able to suppress dissent.

## Primary lenses

Each lens below is bound by the envelope above (adds scrutiny only; never suppresses dissent; never
loosens a rule; documentation only).

### Security Guardian

The reviewer who reads a change for attack surface and trust-boundary erosion first. It assumes the
change is untrusted input until shown otherwise, and it is loudest exactly where the project's
local-first, approval-separate-from-execution guarantees could quietly weaken.

- **Pays attention to:** new network/LAN/hosted surface or non-loopback binds; anything touching the
  Workbench trust/executor/guard, the command allowlist, or approval-vs-execution separation; parsing
  of untrusted input (fail-closed? bounded? no code execution?).
- **May ask:** "does this add a way to execute or reach the network that wasn't there before, and is it
  gated?"; "is this input treated as untrusted (size-bounded, stdlib-parsed, fail-closed)?"; "could this
  let a preference/lens influence a decision that must stay deterministic?"

### Cost Skeptic

The reviewer who watches model/token spend and guards against silent cost creep. It prefers the
cheapest preset that still answers the question and wants spend to be visible and bounded, never a
surprise.

- **Pays attention to:** the review preset chosen (is `full`/`premium` really warranted, or would
  `cheap`/`balanced` do?); whether `--usage` is on so spend is visible; loops or repeated council runs
  that multiply cost.
- **May ask:** "is this the smallest preset that answers the question?"; "is token usage visible and
  bounded (guards, `--usage`)?"; "does this change add repeated or unbounded model calls?"

### Local-first Guardian

The reviewer who defends the product's spine: everything runs on the user's machine with their own key;
nothing is sent anywhere except the model calls the user explicitly triggers. It resists any drift
toward hosted/LAN/mobile surface or committing local/private artifacts.

- **Pays attention to:** any new non-localhost surface, telemetry, or hosted/SaaS dependency; whether
  generated/runtime/private artifacts (`.council/**`, packs/exports, `.council/profile.*`, secrets)
  could be committed; new runtime dependencies vs the stdlib-only default.
- **May ask:** "does this keep everything local and offline-by-default?"; "could this stage or leak a
  private/runtime artifact?"; "is a new dependency truly needed, and is it reviewed/pinned?"

## Future lenses (stubs — not yet elaborated, not applied)

These are named for vocabulary only; they are **future** and carry no elaborated content, no behavior,
and no schema. They are bound by the same envelope above if they are ever elaborated.

- **Product Strategist** — *(future)* reads a change for product direction, scope, and user value.
- **UX / User Advocate** — *(future)* reads for clarity, ergonomics, and the operator's experience.
- **Risk Officer** — *(future)* reads for process/operational risk and failure modes.
- **Commercialization Lens** — *(future)* reads through the licensing/provenance "Question 0" and
  commercial-clearance gate.

## Status & deferral

This page is **documentation for humans and agents in v0.9.1** — a shared vocabulary, subject to change.
**No lens is defined as behavior, parsed, selected, or applied.** Turning any lens into runtime behavior
(prompt emphasis, a `--lens`/`--persona` flag, a preset object) is a **v0.10.x-or-later** decision that
must land behind the dissent-preservation framework (its acceptance criteria, adversarial dissent tests,
and content rules) — see the planned
[`v0.10.x-dissent-preservation-sketch.md`](v0.10.x-dissent-preservation-sketch.md). Until then, a lens is
only a way of reading. Pointers: the vault [`AGENT-ROLES.md`](../context/project/AGENT-ROLES.md) (roles
are advice, not runtime override) and [`PREFERENCES.md`](../context/project/PREFERENCES.md) (the
tighten-only preference model these lenses would one day preset, unchanged here).
