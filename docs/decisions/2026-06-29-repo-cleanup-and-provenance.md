---
id: DEC-20260629-repo-cleanup-and-provenance
status: accepted
date: 2026-06-29
tags: [repo, provenance, licensing, cleanup]
related: [DEC-20260629-provider-abstraction, DEC-20260629-v0.2-release]
published: true
---

# Repo cleanup and provenance stance

## Context

vibe-council is a fork of [`karpathy/llm-council`](https://github.com/karpathy/llm-council)
that has diverged substantially. Several files still descend from the unlicensed upstream,
and the repo carried unused subsystems (the old web UI) and stale identity references. There
was a temptation to do a clean-room rewrite or rehome the repo to "launder" the messy history.

## Decision

Keep the **current repo as canonical for now** and clean **progressively**:

- Remove unused subsystems and dependencies (the upstream web UI + FastAPI/Uvicorn).
- Normalize project identity and stale references as cosmetic cleanup.
- **Preserve attribution/provenance** to the upstream project — do not weaken credit.
- **Do not add a `LICENSE`** while licensing/provenance is unresolved.

## Rationale

- **Avoid premature history laundering** — a clean-room rewrite/rehome is expensive and does
  not fix the actual blocker.
- The **real blocker is license/provenance, not messy history** — solving the wrong problem
  first wastes effort and risks weakening attribution.
- Incremental cleanup keeps the tool shippable (v0.2.0) while the licensing question matures.

## Alternatives considered

- **Clean-room rewrite now** — deferred; high cost, doesn't resolve licensing, risks losing
  provenance.
- **Rehome to a fresh repo identity now** — deferred; same reasoning.
- **Add a permissive `LICENSE` immediately** — rejected; licensing is unresolved and an
  upstream-derived tree must not be relicensed casually.

## Consequences

- **License/provenance remains an ongoing, tracked concern** — no `LICENSE` yet.
- Clean-room rewrite and repo rehome are **explicitly deferred**, not abandoned.
- Cleanup continues in small, reviewable PRs (e.g. post-release cosmetic cleanup).

## Next actions

- Continue incremental cleanup; keep attribution intact in every change.
- Revisit licensing/provenance as its own focused effort, not bundled into feature work.

## Related links

- Post-release cosmetic cleanup PR: <https://github.com/EfeAydinalp/vibe-council/pull/32>
- Release prep PR: <https://github.com/EfeAydinalp/vibe-council/pull/31>
- Related: [provider abstraction](./2026-06-29-provider-abstraction.md),
  [v0.2.0 release](./2026-06-29-v0.2-release.md)
