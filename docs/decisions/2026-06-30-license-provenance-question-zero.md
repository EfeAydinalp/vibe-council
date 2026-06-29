---
id: DEC-20260630-license-provenance-question-zero
status: accepted
date: 2026-06-30
tags: [licensing, provenance, commercial, gate, question-zero]
related: [DEC-20260629-repo-cleanup-and-provenance, DEC-20260629-open-core-commercial-direction, DEC-20260630-redaction-guard]
published: true
---

# License/provenance is Question 0 (commercial gate)

> **Not legal advice.** This records an engineer's process decision and gate, not a legal opinion or a
> commercial-clearance claim.

## Context

The commercial direction and the council roadmap review both flagged license/provenance as the
existential **"Question 0"**: vibe-council descends from the unlicensed-upstream
[`karpathy/llm-council`](https://github.com/karpathy/llm-council), has **no `LICENSE` file**, and
`pyproject.toml` declares no license field. Until provenance is understood, paid/commercial steps are
unsafe. The detailed checklist lives in
[`docs/plans/license-and-provenance-resolution.md`](../plans/license-and-provenance-resolution.md).

## Decision

- **Accept license/provenance as Question 0** before serious commercialization, with an explicit
  owner, status, evidence trail, and go/no-go gate (the checklist).
- **Treat the current status as not fully resolved** unless and until evidence proves otherwise.
- **Preserve attribution** to the upstream project on every path.
- **Do not make strong commercial/license claims** (no "commercially cleared", "MIT", or "safe to
  resell") until the review supports them.
- **Do not add a `LICENSE` file yet** — document the open question first; add a license only after
  provenance is understood.
- **Public, local-first development continues**; **paid commercialization and hosted/private-repo work
  remain gated** on this review.

## Rationale

- Selling or hosting anything derived from an unlicensed-upstream tree, before provenance is
  understood, is the kind of risk that can invalidate the commercial premise.
- An explicit checklist with an owner and a gate turns a vague "resolve later" into a tracked,
  auditable blocker.
- Conservative public claims protect trust and avoid asserting rights the project may not have.

## Alternatives considered

- **Ignore license/provenance until paid launch** — rejected; existential risk discovered too late.
- **Add a `LICENSE` without a provenance review** — rejected; can't relicense what isn't understood.
- **Hide the repo to avoid the issue** — rejected; destroys trust and resolves nothing.
- **Assume public GitHub means commercially usable** — rejected; visibility is not a license.
- **Treat dependency licenses as the only license issue** — rejected; the upstream-derivation question
  is the larger risk.

## Consequences

- A safer commercial path with a clear gate and evidence trail.
- Paid work is **delayed** until the review clears (acceptable trade-off).
- Clearer public trust (conservative, honest claims).
- May require cleanup, a clean-room rewrite, or attorney review depending on findings.

## Next actions

- Work the [resolution checklist](../plans/license-and-provenance-resolution.md): upstream evidence →
  derived-file inventory → dependency licenses → proposed license → attorney-review decision.
- Create a **final resolution decision record** when resolved; lift the gate only if the outcome is
  `clear`.

## Related links

- Checklist: [license & provenance resolution](../plans/license-and-provenance-resolution.md)
- Related: [repo cleanup & provenance](./2026-06-29-repo-cleanup-and-provenance.md),
  [open-core commercial direction](./2026-06-29-open-core-commercial-direction.md),
  [redaction guard](./2026-06-30-redaction-guard.md)
