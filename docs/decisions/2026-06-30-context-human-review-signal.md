---
id: DEC-20260630-context-human-review-signal
status: accepted
date: 2026-06-30
tags: [context-pack, context-check, v0.3.1, dogfood, safety]
related: [DEC-20260630-context-pack-builder-mvp, DEC-20260630-context-quality-harness, DEC-20260630-decision-promote]
published: true
---

# Context packs must carry the human-review promotion boundary

## Context

Dogfooding the v0.3.0 loop ([dogfood notes](../dogfood/v0.3.1-notes.md)) showed `vibe context
check` stuck at 20/21 on the real repo. The miss was `memory:human-review` (not
`signal:rejected-alternatives`, which already passed): the generated context pack carried no
phrase asserting that decision promotion is human-reviewed. Surfacing that signal then exposed a
second issue — the curated decision set had outgrown the 12000-char MVP budget, so the budget
trimmer was dropping the rejected-alternatives index from the real-repo pack.

## Decision

Make `vibe context build` always carry the human-review promotion boundary, and give the pack
enough budget to keep its advisory signal (in `backend/context_pack.py`, stdlib-only, no model/
API/network):

- Add an explicit line to the pack's **Constraints / safety notes**: promotion into
  `docs/decisions/*.md` is **manual and human-reviewed**; automatic extraction from raw
  `.council/` output only creates **local drafts**. This satisfies the existing
  `memory:human-review` check without weakening it.
- Bump the default char budget from 12000 → **14000** (still a naive char budget, not
  token-aware) so the real-repo pack keeps both the human-review constraint and the
  rejected-alternatives index.
- Keep `check_pack` unchanged — the fix is in pack **content**, not the checker.

The real-repo pack now passes **21/21**, redaction-clean.

## Rationale

- The human-review boundary is a core safety property of the workflow; the context pack an agent
  consumes should state it explicitly rather than leave it implicit.
- Fixing pack content (not the check) keeps the quality harness meaningful — a pack that omits
  the boundary still fails the check.
- The budget bump addresses the real cause of the regression (a curated set that outgrew the MVP
  budget) instead of masking it; a token-aware budget remains future work.

## Alternatives considered

- **Delete / weaken the `memory:human-review` check** — rejected; that hides the gap instead of
  preserving the boundary signal.
- **Only add the constraint line, leave the budget at 12000** — rejected; the added text tipped
  the trimmer into dropping the rejected-alternatives index, leaving the pack at 20/21.
- **Token-aware budget / rolling summaries now** — deferred; out of scope for this fix.

## Consequences

- Generated context packs always carry the human-review promotion boundary; `context check` is
  21/21 on the curated repo, guarded by a test that builds from the real docs.
- Slightly larger packs (default budget 14000). No provider/dependency change; the checker is
  unchanged.
- If the curated set keeps growing, the char budget may need another bump (or the deferred
  token-aware budget) — the real-repo test will flag it.

## Next actions

- PR #51: CLI/help and lint-verdict consistency pass.
- PR #52: v0.3.1 release prep.
- Later: token-aware budget / rolling summaries (still deferred).

## Related links

- Related: [context pack builder MVP](./2026-06-30-context-pack-builder-mvp.md),
  [context quality harness](./2026-06-30-context-quality-harness.md),
  [curated decision promotion](./2026-06-30-decision-promote.md)
- Source: [v0.3.1 dogfood notes](../dogfood/v0.3.1-notes.md)
