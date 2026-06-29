---
id: DEC-20260629-linked-decision-memory
status: accepted
date: 2026-06-29
tags: [decision-memory, strategy, dogfood, agent-brief]
related: [DEC-20260629-external-tools-and-obsidian-research, DEC-20260629-open-core-commercial-hypothesis]
published: true
---

# Dogfood linked decision memory before building tooling

## Context

vibe-council already has a flat decision-memory primitive (`vibe extract --save`,
`vibe decisions ...`) writing to a gitignored local store. A strategy review asked whether
to grow this into a local-first, Markdown-first **linked decision notebook** — and if so, in
what order and where the commit boundary sits. The full analysis is in
[the linked decision-memory strategy plan](../plans/linked-decision-memory-strategy.md).

## Decision

**Dogfood first; do not build tooling yet.** Specifically:

- Adopt **curated, committed Markdown decision records** under `docs/decisions/` (this set is
  the first batch), using a **minimal frontmatter schema** (`id`, `status`, `date`, `tags`,
  `related`, `published`).
- Keep **raw `.council/` outputs local/gitignored** — only human-curated, redacted records are
  committed.
- **No committed generated index** (no `docs/decisions/index.json`) in this phase.
- **Defer vector/hybrid retrieval** — frontmatter + standard Markdown links + grep first.
- Treat a **manual agent brief / context pack** as the likely killer feature (the moat) and
  seed a redacted one ([`docs/context/agent-brief.md`](../context/agent-brief.md)) to test it.

## Rationale

- The strategy review's verdict was **"validate value before building infrastructure, and
  invert the phases."** Hand-author real records + a manual brief and check it measurably helps
  Claude Code before writing any CLI tooling.
- Markdown + links + tags meet most "find related decisions" needs long before embeddings earn
  their complexity.
- Committing only curated records keeps the repo a clean, shareable design record while
  sensitive material stays local.

## Alternatives considered

- **Build `vibe decisions show/new/promote/lint` tooling now** — deferred to v0.3, *only if*
  dogfooding proves the value (building before the curation hypothesis is proven is the flagged
  risk).
- **Dual store with a promotion path** — collapsed to a single authoring model + `published`
  flag rendered to committed `docs/decisions/`.
- **Commit a generated index for fast search** — rejected for now; it guarantees sync drift.
- **Add vector search early** — deferred; a time-boxed local-embeddings prototype is the cheap
  later test.

## Consequences

- **Curation risk is the existential one:** *no one will curate* unless the value is obvious.
  Mitigation: prove the agent brief measurably helps, and **dogfood in this repo** as the
  forcing function. If our own team won't sustain records for ~1 month, that is the kill signal.
- A documentation **convention** now; CLI tooling is a separate, later decision.
- The agent brief is a **concentration risk** — local-by-default, size-capped, redacted, and
  committed only by explicit opt-in.

## Next actions

- Land this docs-only dogfood batch (records + manual brief); use it for ~1 month.
- Measure whether the brief improves Claude Code's answers about this repo.
- If it helps, scope a **minimal** v0.3 tooling PR with a CI secrets/redaction guard; if not,
  stop before MCP/vectors.

## Related links

- Strategy plan: [linked decision-memory strategy](../plans/linked-decision-memory-strategy.md)
- External-tools research: [agent-skills / knowledge-graph repo audit](../research/agent-skills-knowledge-graph-repo-audit.md)
- Manual agent brief (dogfood seed): [`docs/context/agent-brief.md`](../context/agent-brief.md)
- Related: [external tools & Obsidian research](./2026-06-29-external-tools-and-obsidian-research.md)
