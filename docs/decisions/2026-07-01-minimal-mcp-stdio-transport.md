---
id: DEC-20260701-minimal-mcp-stdio-transport
status: accepted
date: 2026-07-01
tags: [mcp, v0.4, transport, stdio, dependency, safety]
related: [DEC-20260701-mcp-context-pack-health, DEC-20260701-read-only-mcp-server-skeleton, DEC-20260701-read-only-mcp-contract-skeleton]
published: true
---

# Minimal read-only MCP stdio transport (stdlib JSON-RPC, no SDK dependency)

## Context

PRs #57–#58 built a tested, dependency-free read layer (`backend/mcp_server.py`) for status, curated
decisions, the context pack, and health. To let Claude Code / MCP clients actually use it, v0.4 now
adds a real **stdio transport** — but only after the read layer was proven safe.

The MCP **stdio** transport is newline-delimited **JSON-RPC 2.0** over stdin/stdout. The official
`mcp` Python SDK is one way to implement it, but it is not installed and would add a runtime
dependency (plus transitive deps) for a feature most CLI users never touch.

## Decision

Introduce the stdio transport as a **thin adapter** (`backend/mcp_stdio.py`) over the existing read
layer, and **add no dependency**:

- Implement the transport in **stdlib** as a minimal JSON-RPC 2.0 server speaking the MCP stdio
  methods `initialize`, `notifications/initialized` (no-op), `ping`, `tools/list`, `tools/call`,
  `resources/list`, `resources/read`. **No `mcp` SDK** is added; the normal `vibe` CLI is unaffected
  and importing non-MCP modules requires no MCP runtime.
- **No new resources/tools.** The transport exposes exactly the already-implemented read-only
  surface: tools `get_project_status` / `list_decisions` / `show_decision` / `get_context_pack` /
  `check_context_health`; resources `vibe://status` / `vibe://decisions` / `vibe://decisions/{id}` /
  `vibe://context/latest`. Every handler delegates to `mcp_server.dispatch`/read functions.
- CLI: `vibe mcp serve --stdio` (stdio is the only transport). It opens **no** HTTP port, starts
  **no** daemon, runs **no** shell/git/provider/model calls, and writes **nothing** (context reads
  stay in memory — no `.council/` files). It runs until stdin EOF.
- **Boundaries stay enforced:** forbidden tools (incl. `git_status`) and the deferred tool/resources
  (`list_rejected_alternatives`, `vibe://rejected-alternatives`, `vibe://release-notes`,
  `vibe://constraints`) are unreachable; `show_decision` is path-traversal guarded; private/untracked
  plans and raw `.council/` are never exposed. A bounded in-process JSON-RPC smoke test covers this.

## Rationale

- A stdlib JSON-RPC server keeps the project's minimal-dependency posture (CLAUDE.md) and lets the
  transport ship and be tested in CI without installing an SDK.
- Keeping the transport a thin adapter means it inherits the read layer's safety guarantees rather
  than re-implementing readers.
- Deferring the SDK keeps the option open: if fuller MCP spec compliance is later required, an
  **optional** `mcp` extra can be adopted without affecting normal `vibe` usage.

## Alternatives considered

- **Add the `mcp` SDK as a runtime dependency** — rejected; forces the dependency on all CLI users
  for a niche feature and can't be smoke-tested in CI without installing it.
- **Add the `mcp` SDK as an optional extra now** — deferred; not needed for a minimal read-only
  server, and an uninstalled extra means no CI smoke. Revisit if spec gaps appear.
- **Docs-only (defer transport entirely)** — rejected; the read layer is ready and a minimal stdlib
  transport is low-risk and testable.

## Consequences

- Claude Code / MCP clients can connect to a real read-only stdio server today, with no extra
  install. `.council/` writes remain **CLI-only**, never MCP side effects.
- The transport is a minimal stdlib implementation of the MCP stdio methods, not the official SDK;
  fuller compliance (if needed) is a future optional-extra decision.
- Write/git/shell/provider/model operations and remote/hosted transports remain forbidden/deferred.

## Next actions

- PR #60: Claude Code setup docs (how to register `vibe mcp serve --stdio`) + example queries.
- Then: v0.4 dogfood notes, then v0.4 release prep.

## Related links

- Read layer: [read-only MCP server skeleton](./2026-07-01-read-only-mcp-server-skeleton.md),
  [MCP context pack health](./2026-07-01-mcp-context-pack-health.md)
- Contract: [read-only MCP contract skeleton](./2026-07-01-read-only-mcp-contract-skeleton.md)
- Plan: [v0.4 read-only MCP workflow](../plans/v0.4-read-only-mcp-workflow.md)
