---
id: DEC-20260701-context-pack-critical-section-budget
status: accepted
date: 2026-07-01
tags: [context-pack, context-check, budget, v0.4, stabilization, safety]
related: [DEC-20260701-context-pack-budget-headroom, DEC-20260701-minimal-mcp-stdio-transport, DEC-20260630-context-quality-harness]
published: true
---

# Context-pack core sections compact instead of disappearing under budget

## Context

PR #55 stabilized the rejected-alternatives signal, but the 14000-char budget cliff recurred during
PR #59: as the curated set grew, the trimmer capped the decision index to **zero entries**, which
dropped the entire required `## Decision index (older)` section and knocked `context check` down to
20/21. STATUS.md was hand-compressed to recover — not a durable fix, since every docs/decision PR
keeps growing the set. This stabilizes the pack structurally before more v0.4 (MCP / Claude Code)
docs land.

## Decision

Treat the pack as **core sections** (never dropped; compacted) vs **expandable content** (trimmed
first), in `backend/context_pack.py` (stdlib-only, checker unchanged):

- **Core sections** — project identity, current status, the **decision index**, the
  **rejected-alternatives index**, and the constraints/human-review/source-of-truth notes — are
  kept and **compacted toward small floors**, never dropped:
  - decision index: drop tags, then cap entries toward a floor (`_INDEX_FLOOR = 8`), but **never to
    zero while older records exist**, so the required section persists;
  - rejected-alternatives index: shrink its cap toward a floor (`_REJECTED_FLOOR = 3`) — compacted,
    not dropped;
  - status: truncated once (one-shot), never removed.
- **Expandable content** — the full recent decision bodies — is **trimmed first** (down to a floor
  of one, so the required recent/pinned section survives).
- If compaction still can't fit, the builder **accepts a marginally over-budget pack rather than
  dropping a core section**. The default budget stays **14000** (no bump needed once compaction was
  in place).
- Trim/compaction is reported via clear warnings (reduced recent full decisions · compacted decision
  index · truncated status · capped decision index · compacted rejected-alternatives index).
- `context check` is unchanged and must keep validating core sections — the decision-index and
  rejected-alternatives signals now come from their dedicated sections, not accidentally from a full
  body that happened to survive trimming.

## Rationale

- Required/core sections must not vanish on trim-order luck; compacting a small section is far
  cheaper than the full bodies that actually consume the budget.
- Accepting a marginally over-budget pack (only in pathological tiny-budget cases) is the right
  trade vs. dropping a required section; at the real default budget the pack stays well within.
- Fixing structure beats endlessly bumping the budget or hand-compressing STATUS; a token-aware
  budget remains deferred unless this proves insufficient.

## Alternatives considered

- **Keep dropping the index / bump the budget each time** — rejected; that's the recurring cliff and
  manual-compression treadmill.
- **Hard-require the budget ceiling even if it drops a required section** — rejected; a usable pack
  with all core sections slightly over budget beats a smaller invalid one.
- **Implement a token-aware budget now** — deferred; out of scope and unnecessary after compaction.

## Consequences

- Default and tight-budget builds keep the decision index, rejected-alternatives index, human-review,
  and source-of-truth constraints; `context check` stays 21/21 on the real repo (guarded by tests).
- The decision index may be compacted (no tags / fewer entries) under pressure; warnings explain it.
- No dependency/provider change; checker and JSON report unchanged; MCP context reads stay in-memory
  (no `.council/` writes) and still report 21/21.

## Next actions

- Proceed to v0.4 Claude Code setup docs, then v0.4 dogfood + release prep.
- Revisit a token-aware budget only if the naive char budget proves insufficient despite compaction.

## Related links

- Prior budget work: [context pack budget headroom](./2026-07-01-context-pack-budget-headroom.md)
- Harness: [context quality harness](./2026-06-30-context-quality-harness.md)
- Plan: [v0.4 read-only MCP workflow](../plans/v0.4-read-only-mcp-workflow.md)
