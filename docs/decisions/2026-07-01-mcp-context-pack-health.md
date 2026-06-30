---
id: DEC-20260701-mcp-context-pack-health
status: accepted
date: 2026-07-01
tags: [mcp, v0.4, context-pack, read-only, safety]
related: [DEC-20260701-read-only-mcp-server-skeleton, DEC-20260701-context-pack-budget-headroom, DEC-20260630-context-pack-builder-mvp]
published: true
---

# MCP context pack + health are read-only in-memory reads (no `.council/` writes)

## Context

The read-only MCP read layer (PR #57) exposed project status + curated decisions. The next useful
surface is the **context pack** and its **health check**, so an agent can pull the assembled project
memory and judge whether it is complete. The risk: the CLI `context build`/`export` write generated
files under `.council/`, and an MCP **read** must never produce side effects.

## Decision

Extend the dependency-free read layer (`backend/mcp_server.py`) with `get_context_pack` and
`check_context_health` (↔ `vibe://context/latest`), reusing the existing pure functions:

- `context_pack.build_pack(...)` already returns the pack **text in memory** (the CLI does the
  writing separately), and `check_pack(text)` is pure. The MCP handlers call these directly and
  **write nothing** — no `pack-latest.md`, no `claude-code-context.md`, no `.council/` files. Tests
  assert no files are created/modified by the MCP context calls.
- `get_context_pack` returns text + warnings + redaction counts; `check_context_health` returns
  score / passed / total / failed checks / redaction critical. The health reflects the **current
  curated docs** (rebuilt in memory), not a possibly-stale on-disk pack.
- Surfaced read-only via `vibe mcp inspect --context --health` (and `--json`).
- **Deferred:** the standalone `vibe://rejected-alternatives`, `vibe://release-notes`, and
  `vibe://constraints` resources and `list_rejected_alternatives` (the rejected-alternatives content
  is already carried inside the pack). The real MCP **stdio transport** and the `mcp` SDK decision
  remain deferred.

## Rationale

- Reusing the existing pure builders means the MCP surface inherits the same trim/redaction guarantees
  and stays a true read (no side effects), which is the whole point of a read-only server.
- Rebuilding in memory keeps health honest about the current curated docs rather than a stale file.
- Keeping standalone rejected/release/constraints resources deferred keeps the PR focused; their
  signal is already in the pack.

## Alternatives considered

- **Read an existing `.council/context/pack-latest.md` if present** — rejected as the primary path; it
  can be stale and may be absent. (The in-memory build is the source of truth; a future PR could add
  a "use cached if fresh" option if needed.)
- **Let MCP run `vibe context build` (which writes)** — rejected; an MCP read must not write
  generated files.
- **Add the standalone rejected/release/constraints resources now** — deferred; out of scope.

## Consequences

- Agents can query the context pack + health over the read layer with zero side effects; `.council/`
  generated artifacts remain **CLI outputs**, never MCP side effects.
- Real MCP transport and the remaining standalone resources stay deferred. No dependency/provider
  change; no version bump.

## Next actions

- Next: MCP stdio transport (evaluate the `mcp` SDK) + Claude Code setup docs.

## Related links

- Server skeleton: [read-only MCP server skeleton](./2026-07-01-read-only-mcp-server-skeleton.md)
- Budget: [context pack budget headroom](./2026-07-01-context-pack-budget-headroom.md)
- Plan: [v0.4 read-only MCP workflow](../plans/v0.4-read-only-mcp-workflow.md)
