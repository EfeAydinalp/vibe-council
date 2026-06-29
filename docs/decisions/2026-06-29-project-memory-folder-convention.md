---
id: DEC-20260629-project-memory-folder-convention
status: accepted
date: 2026-06-29
tags: [project-memory, convention, docs, local-first, obsidian-compatible]
related: [DEC-20260629-track-based-roadmap, DEC-20260629-linked-decision-memory, DEC-20260629-external-tools-and-obsidian-research]
published: true
---

# Project-memory folder convention

## Context

vibe-council keeps curated decision records in [`docs/decisions/`](./) and a compact
[agent brief](../context/agent-brief.md). The research addendum and the
[track-based roadmap](../plans/track-based-roadmap.md) both call for a lightweight, editor-agnostic
**project-memory** surface (README + a short STATUS) — a stable landing page humans can browse and
agents can later consume via context packs / MCP — without duplicating the decision source-of-truth or
taking an Obsidian dependency.

## Decision

Adopt a **minimal `docs/context/project/` convention**:

- **Commit** a stable [`README.md`](../context/project/README.md) (identity, boundaries, pointers) and
  a short [`STATUS.md`](../context/project/STATUS.md) (current snapshot, next actions, blockers,
  needs-review).
- **Do not commit by default:** raw `PROGRESS.md` logs, raw transcripts, or raw `.council/` outputs.
  `PROGRESS.md` is **local/generated** unless explicitly promoted as a milestone digest.
- **Do not create a competing canonical `DECISIONS.md`.** If a rollup is ever generated it is **only an
  index/summary**; `docs/decisions/*.md` remains the source of truth.
- **Obsidian compatibility = plain Markdown + standard links, not an Obsidian dependency.** No
  `.obsidian/` is committed; no plugin is required or vendored.
- The **future context-pack builder** can consume this folder; a **future GUI** can visualize the
  graph, but **Markdown remains canonical**.

## Rationale

- A short README + STATUS fills the one genuine gap (a current "where are we / what's next") without
  duplicating the agent brief or the decision records.
- Plain, editor-agnostic Markdown avoids tool lock-in and keeps the core local-first; it works in
  GitHub, VS Code, Obsidian, and similar tools.
- Keeping `PROGRESS.md` local-by-default avoids committing volatile noise that git history already
  captures, and lowers leakage risk.

## Alternatives considered

- **A full Obsidian dependency** — rejected; couples the project to one app and breaks editor-agnostic
  portability.
- **Committing `.obsidian/`** — rejected; machine/user state and noise.
- **A single giant `DECISIONS.md` as the canonical store** — rejected; competes with
  `docs/decisions/*.md` and reintroduces the dual-source-of-truth footgun.
- **A hand-maintained public `PROGRESS.md` log by default** — rejected; volatile, duplicates git
  history, and is rarely sustained.
- **A raw council-transcript archive** — rejected; raw outputs stay local/gitignored.

## Consequences

- **Simpler public dogfood** — two small files, easy to keep current.
- **Easier agent context** — a stable, low-token landing page the context-pack builder can consume.
- **Lower leakage risk** — only curated/redacted Markdown is committed; raw outputs stay local.
- **Requires deliberate curation** — the files are only valuable if kept up to date.

## Next actions

- Land the `docs/context/project/` README + STATUS dogfood.
- Keep `docs/decisions/*.md` as the canonical decision store; keep `PROGRESS.md` local/generated.
- Revisit whether more project-memory files are warranted after dogfooding.

## Related links

- Project memory: [`docs/context/project/README.md`](../context/project/README.md),
  [`docs/context/project/STATUS.md`](../context/project/STATUS.md)
- Related: [track-based roadmap](./2026-06-29-track-based-roadmap.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md),
  [external tools & Obsidian research](./2026-06-29-external-tools-and-obsidian-research.md)
- Research: [project-memory / multi-agent addendum](../research/skilltree-project-memory-and-multi-agent-addendum.md)
