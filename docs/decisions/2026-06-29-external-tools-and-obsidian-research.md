---
id: DEC-20260629-external-tools-and-obsidian-research
status: accepted
date: 2026-06-29
tags: [research, licensing, obsidian, knowledge-graph, borrow-not-vendor]
related: [DEC-20260629-linked-decision-memory, DEC-20260629-open-core-commercial-hypothesis]
published: true
---

# External tools & Obsidian research: borrow concepts, not code

## Context

Before building a linked decision-memory / context-pack layer, we audited external tools that
already solve parts of the intended system, to de-risk build-vs-borrow decisions. The full
audit is in
[the external-tools / knowledge-graph repo audit](../research/agent-skills-knowledge-graph-repo-audit.md).
Tools reviewed: ECC, Graphify, Superpowers, UI/UX Pro Max, Planning-with-files, Gstack,
Awesome Claude Code Skills, Claude Remote Control, and Obsidian.

## Decision

**Borrow concepts, not code.** Concretely:

- **No third-party code vendoring or copying** into vibe-council. Do **license review before
  copying** anything, even from permissively-licensed (MIT) repos; the **unlicensed** "awesome"
  list is **discovery only** (all-rights-reserved by default — no content reuse).
- Make decision records **Obsidian-compatible plain Markdown**, but take **no Obsidian
  dependency** and **never commit `.obsidian/`** workspace/config state.
- Use **portable standard Markdown links as canonical**; Wikilinks are optional/user-facing only.
- Treat a **Graphify-like output shape** (human report + machine JSON + optional interactive
  view) as a *later* model for rendering a context pack — not infrastructure to build now.
- Adopt **gstack / planning-with-files context-save patterns** as concepts: append-only,
  branch-scoped Markdown working-state; dedup/prune; supersede + "don't re-litigate"; redaction
  delimiters — re-implemented natively if/when we build tooling.
- Because **Claude Remote Control is an official, well-secured Anthropic feature**, **do not
  build our own mobile-approval / remote-control transport** — design around it instead.

## Rationale

- Concepts are free to learn from; code carries license obligations and attorney-review needs.
- Obsidian-openable plain Markdown gives users backlinks/graph/Canvas for free with zero UI work
  and zero lock-in.
- Reimplementing official, security-heavy platform features (remote control) is undifferentiated
  and a large liability.

## Alternatives considered

- **Vendor Graphify / a graph library for native knowledge-graph output** — rejected now; it is
  exactly the heavy graph/vector infrastructure the strategy review told us to defer.
- **Adopt Obsidian Wikilinks as the primary format** — rejected; a portability trap outside
  Obsidian.
- **Build a mobile approval flow** — rejected; redundant with Claude Remote Control.

## Consequences

- vibe-council stays small and dependency-light; the value taken from these tools is **patterns**.
- Any future code reuse requires an explicit license review first; attribution preserved.
- An optional `vibe context export --format obsidian` (or a Graphify-style render) is a **later**
  possibility, not v0.2.x.

## Next actions

- Feed the monetization findings into the commercial feasibility review (see the
  [open-core commercial hypothesis](./2026-06-29-open-core-commercial-hypothesis.md)).
- Keep records portable Markdown; revisit optional Obsidian/graph export only after dogfooding.

## Related links

- Research audit: [agent-skills / knowledge-graph repo audit](../research/agent-skills-knowledge-graph-repo-audit.md)
- Strategy plan: [linked decision-memory strategy](../plans/linked-decision-memory-strategy.md)
- Related: [linked decision memory](./2026-06-29-linked-decision-memory.md),
  [open-core commercial hypothesis](./2026-06-29-open-core-commercial-hypothesis.md)
