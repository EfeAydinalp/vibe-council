---
id: DEC-20260629-track-based-roadmap
status: accepted
date: 2026-06-29
tags: [roadmap, direction, planning, project-memory, local-first]
related: [DEC-20260629-open-core-commercial-direction, DEC-20260629-linked-decision-memory, DEC-20260629-external-tools-and-obsidian-research]
published: true
---

# Track-based roadmap

## Context

vibe-council's direction spans more than a linear version list: provider/release stability, decision
memory + context packs, project-memory docs, agent/MCP access, an operator approval loop, skill/council
packs, optional orchestration, commercial direction, retrieval, and security/provenance. Flattening
these into "vX does Y" loses the parallelism and the prerequisites between them.

## Decision

Adopt a **track-based roadmap** ([`docs/plans/track-based-roadmap.md`](../plans/track-based-roadmap.md)):
organize work into ten parallel **tracks** and have each **version section** state which tracks advance,
which are deferred, the prerequisite, expected shape, risk, and later milestone. Framing: vibe-council
is an **AI-first Markdown project-memory + decision-graph + context-pack engine**, **not an Obsidian
clone** — canonical data stays plain Markdown (editor-agnostic: GitHub / VS Code / Obsidian), Obsidian
is an optional viewer, and agents access memory via context packs / MCP read-only, not via the Obsidian app.

## Rationale

- Parallel tracks make dependencies explicit (e.g. MCP export needs a context pack; a dashboard needs a
  working memory layer) and prevent premature work.
- "Not now → prerequisite → expected shape → risk → later milestone" keeps deferred items (MCP, remote
  approval, dashboard, vector, hosted) **on** the roadmap without committing to them prematurely or
  declaring them out of scope.
- Plain-Markdown, editor-agnostic memory avoids tool lock-in and keeps the core local-first.

## Alternatives considered

- **A flat version list** — rejected; hides parallelism and prerequisites.
- **Tracks without version anchors** — rejected; gives no sense of sequencing.
- **An Obsidian-centric design** — rejected; Obsidian stays an optional viewer, never a dependency.

## Consequences

- Future PRs implement individual tracks/versions; the roadmap is the shared map, not a delivery contract.
- Detailed commercial strategy stays private/local; only the public-safe commercial **direction** is
  committed.
- Deferred tracks (MCP, operator inbox, dashboard, vector, hosted) are documented with prerequisites,
  not dropped.

## Next actions

- Keep the roadmap public-safe and prerequisite-driven; update it as tracks advance.
- Sequence near-term work per v0.2.x / v0.3.0 (conventions → decision-memory tooling + context-pack MVP).

## Related links

- Roadmap: [track-based roadmap](../plans/track-based-roadmap.md)
- Related: [open-core commercial direction](./2026-06-29-open-core-commercial-direction.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md),
  [external tools & Obsidian research](./2026-06-29-external-tools-and-obsidian-research.md)
- Research: [project-memory / multi-agent addendum](../research/skilltree-project-memory-and-multi-agent-addendum.md)
