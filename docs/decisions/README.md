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
- [Project-memory folder convention](./2026-06-29-project-memory-folder-convention.md) — accepted
- [Operator control loop / approval inbox](./2026-06-29-operator-control-loop.md) — accepted
- [Redaction guard (`vibe lint --redaction`)](./2026-06-30-redaction-guard.md) — accepted
- [License/provenance is Question 0 (commercial gate)](./2026-06-30-license-provenance-question-zero.md) — accepted
- [Decision memory CLI skeleton](./2026-06-30-decision-cli-skeleton.md) — accepted
- [Curated decision promotion MVP](./2026-06-30-decision-promote.md) — accepted
- [Decision draft extraction](./2026-06-30-decision-draft-extraction.md) — accepted
- [Context pack builder MVP](./2026-06-30-context-pack-builder-mvp.md) — accepted
- [Context quality harness MVP](./2026-06-30-context-quality-harness.md) — accepted
- [Operator status MVP](./2026-06-30-operator-status-mvp.md) — accepted
- [Claude Code context export MVP](./2026-06-30-claude-code-context-export.md) — accepted
- [Prepare v0.3.0 release](./2026-06-30-v0.3-release-prep.md) — accepted
- [Decision CLI dogfood rough-edge fixes (v0.3.1)](./2026-06-30-decision-cli-dogfood-fixes.md) — accepted
- [Context packs carry the human-review boundary (v0.3.1)](./2026-06-30-context-human-review-signal.md) — accepted
- [v0.3.1 CLI UX consistency pass](./2026-06-30-v0.3.1-ux-consistency.md) — accepted
- [Prepare v0.3.1 release](./2026-06-30-v0.3.1-release-prep.md) — accepted

See also the curated [agent brief](../context/agent-brief.md) that distills these for agent context.
