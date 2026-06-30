---
id: DEC-20260701-read-only-mcp-contract-skeleton
status: accepted
date: 2026-07-01
tags: [mcp, v0.4, contract, claude-code, safety]
related: [DEC-20260701-v0.4-read-only-mcp-scope, DEC-20260701-context-pack-budget-headroom, DEC-20260630-claude-code-context-export]
published: true
---

# v0.4 starts with a testable read-only MCP contract (no server yet)

## Context

v0.4 is scoped as a read-only MCP / Claude Code workflow ([v0.4 scope](./2026-07-01-v0.4-read-only-mcp-scope.md)).
The riskiest part of an MCP surface is **authority** — it can quietly grow write/action power. To
keep that boundary enforceable from the start, the first implementation step defines the contract
**in code** before any server exists.

## Decision

Add a **definition-only** read-only MCP contract in `backend/mcp_contract.py` (stdlib-only; importing
it starts nothing):

- Declare the planned **read-only resources** (`vibe://status`, `vibe://decisions`,
  `vibe://decisions/{id}`, `vibe://context/latest`, `vibe://rejected-alternatives`,
  `vibe://release-notes`, `vibe://constraints`) and **read-only tools** (`list_decisions`,
  `show_decision`, `get_project_status`, `get_context_pack`, `check_context_health`,
  `list_rejected_alternatives`).
- Declare the explicit **forbidden** mutation/action tools (`promote_decision`, `write_file`,
  `edit_file`, `delete_file`, `run_command`, `git_commit`, `git_push`, `git_status`, `send_email`,
  `deploy`). **`git_status` is forbidden here** even though it is read-only elsewhere — vibe-council
  MCP v0.4 exposes no git surface unless explicitly scoped later.
- Add pure validation helpers (`is_read_only_tool`, `is_forbidden_tool`, `validate_mcp_contract`) and
  a `vibe mcp contract` command that prints the contract (text/`--json`). The command starts no
  server, opens no socket, needs no MCP dependency, makes no model/provider/network call, and writes
  nothing.
- **Server implementation is deferred to the next PR** (#57). No MCP SDK/dependency is added here.

## Rationale

- Encoding the read-only/forbidden contract as tested constants makes the no-write-authority boundary
  auditable before any server can drift from it.
- A contract-only step is small, safe, and reversible — the right way to open the v0.4 track.
- Keeping it stdlib-only and server-free avoids a premature dependency decision (the MCP SDK choice
  belongs to the server PR with its own justification).

## Alternatives considered

- **Jump straight to a server** — rejected; the contract/boundary should exist and be tested first.
- **Allow `git_status` as a read-only tool** — rejected for v0.4; no git surface unless explicitly
  scoped later.
- **Add the MCP SDK now** — rejected; defer the dependency decision to the server PR.

## Consequences

- The read-only contract is testable now; forbidden mutation/action tools are explicit and asserted
  by tests. No write/action authority is exposed; no server runs.
- Future server PRs implement against this contract; a forbidden-tool test guards the boundary.
- No dependency/provider change; no version bump; no release/tag change.

## Next actions

- PR #57: minimal read-only MCP server exposing `vibe://status` + `list_decisions`/`show_decision`
  over curated docs, with a forbidden-tool test.

## Related links

- Scope: [v0.4 read-only MCP scope](./2026-07-01-v0.4-read-only-mcp-scope.md)
- Plan: [v0.4 read-only MCP workflow](../plans/v0.4-read-only-mcp-workflow.md)
- Related: [context pack budget headroom](./2026-07-01-context-pack-budget-headroom.md)
