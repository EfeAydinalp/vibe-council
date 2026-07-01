---
id: DEC-20260701-claude-code-mcp-setup-dogfood
status: accepted
date: 2026-07-01
tags: [mcp, v0.4, claude-code, docs, dogfood, safety]
related: [DEC-20260701-minimal-mcp-stdio-transport, DEC-20260701-mcp-context-pack-health, DEC-20260701-v0.4-read-only-mcp-scope]
published: true
---

# Document + dogfood the v0.4 read-only MCP workflow (generic stdio config)

## Context

The v0.4 read-only MCP stack is implemented (contract, read layer, in-memory context pack/health,
stdlib stdio transport). Before release prep, users need a setup guide, and the workflow should be
dogfooded end-to-end to confirm the read-only / no-write / privacy boundaries hold with the real
transport.

## Decision

Add docs + a dogfood record; add **no** new MCP surface:

- `docs/mcp/claude-code-setup.md` — purpose, requirements, the three commands (`mcp contract` /
  `inspect --context --health` / `serve --stdio`), a **generic MCP stdio client config pattern**,
  the exposed read-only resources/tools, the explicitly-not-exposed operations, troubleshooting, and
  a safety checklist.
- `docs/dogfood/v0.4-mcp-local-dogfood.md` — a dated dogfood pass: the stdio JSON-RPC smoke
  (initialize / tools/list / tools/call / resources/list / resources/read / a forbidden call that
  errors), a **no-write audit** (MCP calls don't create/modify `.council/context/*`), and a
  **privacy audit** (private/untracked plans, secrets, and local paths are not exposed).
- **Do not assert exact Claude Code config syntax.** The setup doc labels the config a *generic MCP
  stdio client pattern* and points to the client's own docs; exact Claude Code syntax is a follow-up
  once verified.

## Rationale

- A clearly-labeled generic pattern is honest and still actionable; inventing unverified Claude Code
  fields would be misleading.
- Dogfooding with the real stdio transport (not just unit tests) confirms the boundaries hold in a
  client-like flow before release.

## Alternatives considered

- **Claim verified Claude Code config now** — rejected; not verified against the client, so labeled
  generic instead.
- **Add standalone rejected/release/constraints resources as part of docs** — rejected; out of
  scope, and rejected-alternatives is already in the pack.
- **Add the `mcp` SDK for a "more official" setup** — rejected; the stdlib transport works and stays
  dependency-light; an optional extra remains a later option.

## Consequences

- Users have a setup guide and a recorded dogfood pass; the read-only MCP workflow is documented and
  validated. No new MCP features, dependencies, or transport changes.
- Follow-ups: v0.4 release prep; verified Claude Code config; optional standalone resources / `mcp`
  SDK extra only if a real need appears.

## Next actions

- v0.4 release prep (CHANGELOG `[0.4.0]`, `docs/releases/v0.4.0.md`, version bump, decision record).

## Related links

- Setup: [Claude Code / MCP setup](../mcp/claude-code-setup.md)
- Dogfood: [v0.4 MCP local dogfood](../dogfood/v0.4-mcp-local-dogfood.md)
- Transport: [minimal MCP stdio transport](./2026-07-01-minimal-mcp-stdio-transport.md)
- Plan: [v0.4 read-only MCP workflow](../plans/v0.4-read-only-mcp-workflow.md)
