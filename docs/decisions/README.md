# Decision records

Curated, redacted **decision records** for vibe-council — committed Markdown that captures *why*
significant calls were made, with their alternatives and consequences. This set is a **dogfood
seed** for the linked decision-memory direction (see
[the strategy plan](../plans/linked-decision-memory-strategy.md) and the
[dogfood decision](./2026-06-29-linked-decision-memory.md)).

## Conventions

- **Committed records are curated and redacted.** Raw and auto-extracted council output stays
  **local and gitignored** (`.council/`) — never committed.
- **Minimal frontmatter:** `id`, `status`, `date`, `tags`, `related`, `published`. Links to PRs,
  releases, and docs live in the body, not in frontmatter.
- **Stable headings:** Context · Decision · Rationale · Alternatives considered · Consequences ·
  Next actions · Related links.
- **Portable standard Markdown links are canonical** (these files are Obsidian-openable plain
  Markdown, but **Obsidian is not a dependency** and `.obsidian/` is never committed).
- **No generated index** (`index.json`), no vector DB, no embeddings in this phase.

## Records

- [Provider abstraction (OpenRouter + Ollama)](./2026-06-29-provider-abstraction.md) — accepted
- [Repo cleanup & provenance stance](./2026-06-29-repo-cleanup-and-provenance.md) — accepted
- [Publish v0.2.0](./2026-06-29-v0.2-release.md) — accepted
- [Dogfood linked decision memory](./2026-06-29-linked-decision-memory.md) — accepted
- [External tools & Obsidian research](./2026-06-29-external-tools-and-obsidian-research.md) — accepted
- [Open-core commercial hypothesis](./2026-06-29-open-core-commercial-hypothesis.md) — **proposed**
- [Open-core commercial direction](./2026-06-29-open-core-commercial-direction.md) — accepted
- [Track-based roadmap](./2026-06-29-track-based-roadmap.md) — accepted

See also the curated [agent brief](../context/agent-brief.md) that distills these for agent context.
