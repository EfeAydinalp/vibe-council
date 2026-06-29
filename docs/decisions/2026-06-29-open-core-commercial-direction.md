---
id: DEC-20260629-open-core-commercial-direction
status: accepted
date: 2026-06-29
tags: [commercial, open-core, direction, local-first, licensing]
related: [DEC-20260629-open-core-commercial-hypothesis, DEC-20260629-linked-decision-memory, DEC-20260629-external-tools-and-obsidian-research]
published: true
---

# Open-core commercial direction

## Context

vibe-council is a local-first AI "council" CLI. As the project matures, the question of *how* (and
whether) to commercialize without compromising its open, local-first character needs a clear,
public-safe directional statement. This record codifies that **direction** — the durable principles —
while leaving specific paid-product choices to be validated. It builds on the
[open-core commercial hypothesis](./2026-06-29-open-core-commercial-hypothesis.md) and the
[external-tools & Obsidian research](./2026-06-29-external-tools-and-obsidian-research.md). Detailed
strategy/feasibility work is kept private/local and is intentionally **not** part of the public repo.

## Decision

- **The core remains public and local-first.** The free CLI must stay fully usable with the user's
  own key and no cloud.
- **Raw `.council/` outputs remain local/gitignored.** Only curated, redacted decision records and
  public-safe docs live in the public repo.
- **BYOK-first** is preferred early (the user brings their own API key).
- **Avoid early token resale.** Do not build a business on reselling unmetered inference early.
- **Avoid early self-hosted GPU inference.** External provider APIs first.
- **If a paid direction is pursued, it should start with support/training and curated Product/Code
  Review council packs** — not a hosted inference product.
- **Individual Pro / sync may come later**, and **team sync may come later**, only as optional layers
  that never gate the core.
- **Hosted/billing/team work should only happen after validation**, and may live **outside the public
  core** (e.g. a separate private repo) rather than in this repository.
- **License/provenance review is Question 0** — it must be resolved before serious commercialization.

## Rationale

- A healthy public, local-first core is the trust and adoption engine; gating basic use would
  undermine the project's identity for little gain.
- BYOK keeps inference cost with the user and avoids the margin/liability risks of reselling tokens.
- Monetizing **convenience and curated content** (support, training, review packs) — not the core —
  is the pattern seen in successful local-first / open-core tools, and is the lowest-infra way to
  test willingness-to-pay.
- Self-hosted GPU is operationally heavy and only makes sense at proven scale and margin.
- Selling anything derived from the codebase before license/provenance is resolved would be
  untenable; see [repo cleanup & provenance stance](./2026-06-29-repo-cleanup-and-provenance.md).

## Alternatives considered

- **Close or hide the core / gate basic use** — rejected; breaks local-first positioning and trust.
- **Resell inference (flat-rate or wallet) as the first model** — disfavored early; low-margin,
  liability-prone, undifferentiated.
- **Self-hosted GPU inference product first** — deferred; heavy and premature.
- **Hosted team product as the first paid offering** — deferred; complex and unvalidated relative to
  support/training and curated packs.

## Consequences

- The public repo stays a clean, shareable design record (curated docs + redacted decision records);
  sensitive/strategy material stays local.
- Any future hosted/billing/team layer is a deliberate, separate, post-validation step — not part of
  this repo by default.
- License/provenance remains a tracked blocker for serious commercialization.
- Specific paid-product decisions (pricing, packaging, hosted layers) are **out of scope here** and
  remain to be validated; this record commits only to the *direction*.

## Next actions

- Keep the core public and local-first; keep raw `.council/` gitignored.
- Treat license/provenance resolution as the gating item before serious commercialization.
- Explore education/service-first validation (support/training, curated review packs) while keeping
  the core open; defer hosted/team/billing work until validated.

## Related links

- Related: [open-core commercial hypothesis](./2026-06-29-open-core-commercial-hypothesis.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md),
  [external tools & Obsidian research](./2026-06-29-external-tools-and-obsidian-research.md),
  [repo cleanup & provenance](./2026-06-29-repo-cleanup-and-provenance.md)
- Public research addendum: [skilltree / project-memory / multi-agent](../research/skilltree-project-memory-and-multi-agent-addendum.md)
