---
id: DEC-20260630-context-quality-harness
status: accepted
date: 2026-06-30
tags: [cli, context-pack, quality, v0.3, local-first]
related: [DEC-20260630-context-pack-builder-mvp, DEC-20260630-redaction-guard, DEC-20260629-linked-decision-memory]
published: true
---

# Context quality harness MVP (`vibe context check`)

## Context

The [context-pack builder](./2026-06-30-context-pack-builder-mvp.md) assembles a pack, but there was
no way to check whether the pack actually contains what an agent needs. A full LLM-based eval is
premature; a cheap, deterministic checklist comes first.

## Decision

Add `vibe context check` (in `backend/context_pack.py`, stdlib-only, **not an LLM eval**):

- **Reads** a context pack (default gitignored `.council/context/pack-latest.md`, `--file` to override);
  **read-only** — writes nothing. If the pack is missing, it tells the user to run `vibe context build`.
- **Deterministic checks:** required **sections** (Metadata, Project identity, Current status,
  Recent/Pinned decisions, Decision index, Constraints) and **constraints** (raw `.council/` local/
  gitignored, public docs curated/redacted, redaction guard exists, license/provenance "Question 0"),
  plus advisory **current-state facts** (decision CLI / draft extraction / promote / context build /
  pack local), **decision-memory signals** (`docs/decisions/` source-of-truth, `STATUS.md` snapshot,
  human review before promotion, `vibe decisions lint`, `vibe lint --redaction`), and a
  **rejected-alternatives** signal.
- **Redaction:** runs `backend/redaction.py` on the pack — **critical findings fail**; warnings are
  reported and fail only with `--strict`.
- **Scoring:** simple `passed/total`. Fails if any **required** check is missing, a critical redaction
  finding exists, or the score is below `--min-score` (default 0.8). `--strict` also fails on advisory
  misses and warnings. `--json` for a machine-readable report.

This PR also fixes a builder leak the harness surfaced: pack metadata embedded the absolute local
source paths (e.g. `C:\Users\<name>\...`), which the redaction scanner correctly flagged. Metadata now
uses path-safe `parent/name` labels.

## Rationale

- A deterministic checklist is cheap, predictable, and catches the common "pack is missing the current
  blocker / key facts / a constraint" failure — without model cost or nondeterminism.
- Reusing the redaction guard keeps a generated artifact safe even though it is gitignored.
- A scored, machine-readable check is a foundation a later LLM-based eval can build on.

## Alternatives considered

- **LLM-based quality eval now** — deferred; expensive/nondeterministic. Stabilize the deterministic
  check first, then add an LLM eval on top.
- **No harness (eyeball the pack)** — rejected; not repeatable, no CI signal.
- **Make every check hard-required** — rejected; current-state facts depend on which records the budget
  includes, so they are advisory (scored) while sections/constraints/redaction are hard-required.

## Consequences

- Pack quality is checkable locally and in CI (deterministic, stdlib-only).
- The builder no longer leaks absolute local paths into pack metadata.
- New checker + tests; no provider behavior change, no new dependencies.
- An LLM-based quality eval remains follow-up work, after the deterministic check is stable.

## Next actions

- Optionally wire `vibe context check` into CI after `vibe context build`.
- Later: a token-aware budget, rolling summaries, and (eventually) an LLM-based context eval.

## Related links

- Related: [context pack builder MVP](./2026-06-30-context-pack-builder-mvp.md),
  [redaction guard](./2026-06-30-redaction-guard.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md)
- Roadmap: [track-based roadmap](../plans/track-based-roadmap.md)
