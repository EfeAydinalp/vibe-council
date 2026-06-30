---
id: DEC-20260701-context-pack-budget-headroom
status: accepted
date: 2026-07-01
tags: [context-pack, context-check, budget, v0.4, stabilization, safety]
related: [DEC-20260630-context-human-review-signal, DEC-20260630-context-pack-builder-mvp, DEC-20260701-v0.4-read-only-mcp-scope]
published: true
---

# Context packs keep core signals stable under the default budget

## Context

After the v0.4 planning docs landed, `vibe context check` still scored 21/21 but the build had
started **dropping the dedicated rejected-alternatives index** to fit the 14000-char budget; the
check only stayed green because the `rejected alternative` phrase happened to appear in an included
decision body. That is brittle — more docs/decisions would eventually fail the check on trim-order
luck. This is a stabilization step **before** starting v0.4 MCP work, since MCP will surface the
same pack.

## Decision

Make the context-pack builder keep its **critical signal sections** stable under the default budget,
in `backend/context_pack.py` (stdlib-only, no model/API/network, no behavior change to the checker):

- **Reorder trimming** so the budget trimmer shrinks the largest, least-critical content first
  (recent full decision bodies → the older decision index → status) and drops the
  **rejected-alternatives index only as the last resort**, after everything else has been trimmed.
- **Build the rejected-alternatives index from all curated records**, not just the decision bodies
  that survived trimming, so the signal no longer depends on which full bodies are included.
- **Make status truncation one-shot** so the trim loop always terminates and can reach the
  last-resort step (it could previously re-truncate the same ~600-char status indefinitely).
- **Keep the default char budget at 14000** — no bump was needed once the trim order was fixed.
- The human-review boundary lives in the always-present constraints section and is unaffected.

The checker (`check_pack`) is unchanged; the fix is in pack assembly/trim order.

## Rationale

- The rejected-alternatives index is a small, high-value signal; the recent full bodies are the
  large cost. Trimming the large, low-criticality content first keeps the small signals intact.
- Sourcing the rejected index from all records makes the signal deterministic and robust to budget
  pressure rather than dependent on trim-order luck.
- Fixing trim order beats endlessly raising the budget; the char budget stays naive and a
  token-aware budget remains deferred.

## Alternatives considered

- **Raise the default budget again (16000–18000)** — rejected as the primary fix; it postpones the
  problem instead of fixing the trim order. (Still available later if genuinely needed.)
- **Make the rejected index strictly non-trimmable** — rejected; a last-resort drop is still the
  right behavior under a punishing budget, as long as it is genuinely last.
- **Weaken/remove the `signal:rejected-alternatives` check** — rejected; that hides the signal
  instead of preserving it.
- **Implement a token-aware budget now** — deferred; out of scope for this stabilization step.

## Consequences

- Under the default budget the pack keeps both the rejected-alternatives index and the human-review
  signal; `context check` stays 21/21 on the real repo, guarded by tests (real-repo build + trim-order
  unit tests).
- The rejected index now reflects all curated records (small, bounded section).
- No provider/dependency change; the checker and JSON report are unchanged. Token-aware budget and
  rolling summaries remain deferred.

## Next actions

- Proceed to v0.4 read-only MCP work (design skeleton → read-only server → pack/health resource).
- Revisit a token-aware budget only if the naive char budget proves insufficient again.

## Related links

- Related: [context human-review signal](./2026-06-30-context-human-review-signal.md),
  [context pack builder MVP](./2026-06-30-context-pack-builder-mvp.md),
  [v0.4 read-only MCP scope](./2026-07-01-v0.4-read-only-mcp-scope.md)
