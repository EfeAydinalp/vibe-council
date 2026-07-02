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
- [v0.4 starts as read-only MCP / Claude Code workflow](./2026-07-01-v0.4-read-only-mcp-scope.md) — accepted
- [Context packs keep core signals stable under the default budget](./2026-07-01-context-pack-budget-headroom.md) — accepted
- [v0.4 read-only MCP contract skeleton (no server yet)](./2026-07-01-read-only-mcp-contract-skeleton.md) — accepted
- [Read-only MCP server skeleton: status + decisions only](./2026-07-01-read-only-mcp-server-skeleton.md) — accepted
- [MCP context pack + health are read-only in-memory reads](./2026-07-01-mcp-context-pack-health.md) — accepted
- [Minimal read-only MCP stdio transport (stdlib, no SDK)](./2026-07-01-minimal-mcp-stdio-transport.md) — accepted
- [Context-pack core sections compact instead of disappearing](./2026-07-01-context-pack-critical-section-budget.md) — accepted
- [Document + dogfood the v0.4 read-only MCP workflow](./2026-07-01-claude-code-mcp-setup-dogfood.md) — accepted
- [Prepare v0.4.0 release](./2026-07-01-v0.4.0-release-prep.md) — accepted
- [Accept council correction: v0.5 is the AI Council Workbench MVP](./2026-07-01-v0.5-workbench-roadmap.md) — accepted
- [`.council/runtime/` is the Workbench's live workflow state (JSON store)](./2026-07-01-workbench-runtime-store.md) — accepted
- [Deterministic Workbench task lifecycle / state machine (no execution)](./2026-07-01-workbench-orchestrator-state-machine.md) — accepted
- [Deterministic trust boundary is the Workbench's real security gate](./2026-07-01-workbench-trust-boundary.md) — accepted
- [Approval Auditor is advisory (summarizes the deterministic guard)](./2026-07-01-workbench-approval-auditor.md) — accepted
- [First Workbench panel is localhost-only and records decisions (no execution)](./2026-07-01-workbench-local-panel.md) — accepted
- [Plan the guarded executor before building it (execution is a new risk boundary)](./2026-07-01-workbench-guarded-executor-plan.md) — accepted
- [Guarded executor skeleton: dry-run only, invariant-validated](./2026-07-01-workbench-executor-dry-run.md) — accepted
- [First real execution is bounded file write/edit only (commands deferred)](./2026-07-01-workbench-bounded-file-executor.md) — accepted
- [Execution payload lives in a separate, hashed, gitignored runtime artifact](./2026-07-02-workbench-payload-bridge.md) — accepted
- [Payload artifacts are verified by hash + scope before real file execution](./2026-07-02-workbench-payload-store.md) — accepted
- [The panel can execute an approved bounded file action, but only by action id](./2026-07-02-workbench-panel-execute.md) — accepted
- [Plan real command execution as exact allowlisted verification commands only](./2026-07-02-workbench-command-execution-plan.md) — accepted

See also the curated [agent brief](../context/agent-brief.md) that distills these for agent context.
