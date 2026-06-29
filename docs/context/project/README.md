# Project memory

The stable landing page for vibe-council's **curated, public-safe project memory**.

## Project identity

**vibe-council = local-first council workflow + linked project memory + context-pack builder +
skill/council packs + (later) an optional hosted commercial layer.**

## What this folder is

- A **public-safe, curated project-memory seed**.
- **Plain Markdown** — nothing proprietary, no database.
- **Obsidian-compatible but editor-agnostic** — browse it in GitHub, VS Code, Obsidian, or any
  Markdown tool.
- **Not an Obsidian dependency.** Obsidian is an optional viewer/editor; no `.obsidian/` is committed
  and no plugin is required.

## What this folder is not

- **Not raw council output.** Raw `.council/` stays local and gitignored.
- **Not a private strategy dump.** Detailed commercial/feasibility material stays private/local.
- **Not a generated transcript archive.**
- **Not a replacement for `docs/decisions/*.md`** — those remain the source of truth for decisions.

## Canonical sources

- **Decisions (accepted/proposed):** [`docs/decisions/`](../../decisions/) — the source of truth.
- **Compact agent-facing context:** [`docs/context/agent-brief.md`](../agent-brief.md).
- **Roadmap direction:** [`docs/plans/track-based-roadmap.md`](../../plans/track-based-roadmap.md).
- **Latest research addendum:** [`docs/research/skilltree-project-memory-and-multi-agent-addendum.md`](../../research/skilltree-project-memory-and-multi-agent-addendum.md).

## Files here

- [`README.md`](./README.md) — this stable landing page (identity, boundaries, pointers).
- [`STATUS.md`](./STATUS.md) — a short current snapshot: state, next actions, blockers, needs-review.
- **`PROGRESS.md` — not committed by default.** It is **local/generated** (under gitignored
  `.council/`) unless explicitly promoted as a milestone digest; git history already records most
  progress.
- **No `DECISIONS.md` here.** If a single-file decision rollup is ever generated, it should be **only
  an index/summary** — `docs/decisions/*.md` remains the canonical store, never a competing file.

## Public / private boundary

- **Raw `.council/` stays local/gitignored.**
- **Detailed commercial feasibility stays private/local.**
- **The public repo gets curated/redacted docs only** — no API keys, no local absolute paths, no raw
  outputs.

## Future shape

- The **context-pack builder** will consume this folder to assemble low-token, agent-ready context.
- A **future MCP read-only export** may serve this memory to agents (list/show/export; writes behind
  approval) — agents consume the Markdown via packs/MCP, not via direct Obsidian coupling.
- A **future GUI** may visualize links/graphs, but **Markdown remains canonical** — viewers/agents
  consume it, they don't own it.
