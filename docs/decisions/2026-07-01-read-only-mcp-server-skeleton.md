---
id: DEC-20260701-read-only-mcp-server-skeleton
status: accepted
date: 2026-07-01
tags: [mcp, v0.4, server, claude-code, safety]
related: [DEC-20260701-read-only-mcp-contract-skeleton, DEC-20260701-v0.4-read-only-mcp-scope, DEC-20260630-decision-cli-skeleton]
published: true
---

# First MCP server skeleton: status + curated decisions only (no transport yet)

## Context

PR #56 added the read-only MCP **contract** (`backend/mcp_contract.py` + `vibe mcp contract`). The
next step is the first **server skeleton** against that contract. A spec-compliant MCP stdio server
would require the `mcp` SDK; per the v0.4 scope we avoid casual dependencies and keep v0.4 read-only.

## Decision

Add a dependency-free **read layer** (`backend/mcp_server.py`) implementing the smallest useful
read-only surface, plus a read-only smoke command:

- **Implemented now:** `get_project_status`, `list_decisions`, `show_decision`
  (↔ `vibe://status`, `vibe://decisions`, `vibe://decisions/{id}`), reusing the existing curated
  readers (`decisions_docs.list_records` / `find_record` / `load_record`, and the `STATUS.md` reader).
- **Deferred:** `get_context_pack`, `check_context_health`, `list_rejected_alternatives` and the
  `vibe://context/latest` / `vibe://rejected-alternatives` / `vibe://release-notes` /
  `vibe://constraints` resources — later PRs.
- **No transport / no dependency yet.** A spec-compliant MCP stdio server needs the `mcp` SDK; rather
  than add it now, this PR ships the read layer + dispatch (the part a transport wraps) and a
  no-dependency `vibe mcp inspect` smoke. The MCP stdio transport (and that dependency decision) are
  the next increment.
- **Safety, enforced by tests:** every handler is read-only and reads only curated public docs;
  `show_decision` is path-traversal guarded to `docs/decisions/`; `.council/` drafts and
  private/untracked plans are never read; forbidden tools (incl. `git_status`) and the deferred tools
  are unreachable through `dispatch`; the command writes nothing and makes no model/provider/network
  call.

## Rationale

- Shipping the read layer first keeps the PR small, dependency-free, and fully testable while the
  transport/dependency decision is made deliberately.
- Reusing the curated readers means the MCP surface inherits the same path/redaction guarantees as
  the CLI, not a parallel (riskier) reader.
- A `validate_server_contract()` check ties the enabled surface back to the PR-#56 contract, so the
  server can't drift past read-only.

## Alternatives considered

- **Hand-roll an MCP-spec stdio server in stdlib now** — rejected for this PR; a half-compliant
  server is risky and larger than a "skeleton." Do the transport deliberately next.
- **Add the `mcp` SDK now** — rejected; defer the dependency to the transport PR with its own
  justification.
- **Expose context pack / rejected-alternatives already** — rejected; out of scope for this minimal
  skeleton (next PR).

## Consequences

- A tested, dependency-free read layer for status + decisions; `vibe mcp inspect` exercises it.
- Context-pack/health/rejected/release/constraints surfaces and the MCP stdio transport remain
  deferred. No version/dependency/provider change; no raw `.council/` or private-plan exposure.

## Next actions

- PR #58: add the context-pack resource + `check_context_health` (reuse `context build`/`check`).
- Then: MCP stdio transport (evaluate the `mcp` SDK) + Claude Code setup docs.

## Related links

- Contract: [read-only MCP contract skeleton](./2026-07-01-read-only-mcp-contract-skeleton.md)
- Scope: [v0.4 read-only MCP scope](./2026-07-01-v0.4-read-only-mcp-scope.md)
- Plan: [v0.4 read-only MCP workflow](../plans/v0.4-read-only-mcp-workflow.md)
