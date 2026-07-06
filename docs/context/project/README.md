# Project memory (project vault)

The stable landing page for vibe-council's **curated, public-safe project memory** — the local
**project vault**. `docs/context/project/` is the **canonical local project-memory area**: plain,
committed Markdown that both humans and agents read.

> **Agents: read this vault before planning or coding.** Start with [`STATUS.md`](./STATUS.md)
> (current state), then [`ROADMAP.md`](./ROADMAP.md), [`RISKS.md`](./RISKS.md), and
> [`WORKFLOWS.md`](./WORKFLOWS.md). It tells you where the project is and how it works so you don't
> start from zero each session.
>
> **Never store here:** secrets / API keys / tokens, private local paths, runtime payloads, raw
> model/council outputs, generated packs/exports, or private commercial/feasibility detail. Those
> stay local/gitignored. This folder is curated and public-safe.

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

## Files here (project vault)

- [`README.md`](./README.md) — this stable landing page (identity, boundaries, pointers).
- [`STATUS.md`](./STATUS.md) — a short current snapshot: state, next actions, blockers, needs-review.
- [`ROADMAP.md`](./ROADMAP.md) — curated near-term roadmap summary (links to `docs/fable/04-roadmap.md`).
- [`DECISIONS.md`](./DECISIONS.md) — an **index/summary** of high-level decisions. **Not a canonical
  store** — `docs/decisions/*.md` remains the source of truth; this file only points at it.
- [`PROGRESS.md`](./PROGRESS.md) — a **curated milestone digest** (phase checklist). Detailed progress
  stays in git history / `docs/decisions/`; do not paste raw logs here.
- [`RELEASES.md`](./RELEASES.md) — a **capped, newest-first release-history index** (hard cap 30, oldest
  entries roll up). An index/working-memory aid that keeps `STATUS.md` lean — **not** a replacement for
  `docs/releases/*.md` (canonical notes) or `CHANGELOG.md` (chronological changes).
- [`RISKS.md`](./RISKS.md) — current active risks / gotchas.
- [`WORKFLOWS.md`](./WORKFLOWS.md) — common repeatable workflows (coding PR, guide, Workbench proposal,
  release prep, the no-stage checklist).
- [`NOTES.md`](./NOTES.md) — a small scratchpad for **durable, curated** notes only.
- [`PROFILE.md`](./PROFILE.md) — public-safe project identity/profile (what the project is, product
  shape, local-first stance, current release state). *(v0.7 personalization scaffold — documentation
  only; no command reads it yet.)*
- [`PREFERENCES.md`](./PREFERENCES.md) — project working preferences (review-preset policy, Fable usage
  policy, implementation style, no-stage policy, tighten-only principle). *(v0.7 scaffold.)*
- [`AGENT-ROLES.md`](./AGENT-ROLES.md) — per-agent role expectations + the `MODEL:` header convention
  and council-in-the-loop workflow. Deliberately a **vault file, not a root `AGENTS.md`**. *(v0.7
  scaffold.)*

These are all **plain, committed, public-safe Markdown**. Curated content only; no raw/generated/
private artifacts (see the boundary note above and below).

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
