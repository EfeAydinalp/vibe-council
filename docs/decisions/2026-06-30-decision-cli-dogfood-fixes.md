---
id: DEC-20260630-decision-cli-dogfood-fixes
status: accepted
date: 2026-06-30
tags: [cli, decision-memory, promote, extract, v0.3.1, dogfood, safety]
related: [DEC-20260630-decision-promote, DEC-20260630-decision-draft-extraction, DEC-20260630-decision-cli-skeleton]
published: true
---

# Decision CLI dogfood rough-edge fixes (v0.3.1)

## Context

Dogfooding the v0.3.0 decision-memory loop ([dogfood notes](../dogfood/v0.3.1-notes.md)) surfaced
concrete rough edges in `vibe decisions`: `promote` accepted an all-`TODO` skeleton draft;
promoted filenames used a `DEC-….md` form instead of the curated `YYYY-MM-DD-slug.md` convention;
`new --from-run` produced a scaffold that left every substantive section as `_TODO_`; and a long
review H1 produced an unwieldy slug. This is the first hardening PR of the v0.3.1 cycle and is
deliberately scoped to the `decisions` commands only (context-check and general CLI/UX cleanup are
separate follow-ups).

## Decision

Harden `backend/decisions_docs.py` (stdlib-only, no model/API/network, no provider change):

- **Promote content validation.** `promote` now refuses a draft whose core sections are
  placeholder-only (empty / `TODO` / `TBD` / "fill this in"). It requires meaningful content in
  **Decision** and **Rationale** and in at least one of **Consequences / Next actions**, with an
  actionable error. This is **promote-only** — `decisions lint` stays lenient so existing curated
  records are unaffected.
- **Curated filename convention.** `derive_filename` now emits `<date>-<slug>.md`: date from
  frontmatter `date` (else today); slug from the H1 title, else the id (`DEC-`/date prefix
  stripped), else the draft stem. The date is never duplicated, the slug is sanitized and
  length-capped, and path-traversal protections are preserved. `DEC-….md` is no longer emitted.
- **Better deterministic extraction.** `new --from-run` maps obvious review sections —
  Verdict/Recommendation → Decision, Rationale/Why → Rationale, Alternatives/Rejected
  alternatives → Alternatives considered, Risks/Consequences/Tradeoffs → Consequences, Next
  actions → Next actions — using bounded, per-line-capped excerpts. Sections with no source
  content keep their `TODO` markers; no LLM, no large raw pastes.
- **Slug length cap.** `_slug` caps to a reasonable maximum on a word boundary, fixing long
  verbatim-H1 slugs for both draft filenames and ids.

## Rationale

- Refusing placeholder-only drafts protects the curated set from empty scaffolds while staying
  conservative (it does not demand polished prose, only non-placeholder content).
- Matching the established `YYYY-MM-DD-slug.md` naming keeps the curated directory consistent and
  readable; existing records are untouched because the name is derived at promote time.
- Mapping review sections makes `--from-run` meaningfully easier than writing a record by hand,
  while bounded excerpts and retained `TODO`s keep it honest and safe.

## Alternatives considered

- **Add the placeholder check to `decisions lint` too** — rejected; lint must stay lenient for
  already-curated records. Scope the check to `promote` drafts only.
- **Keep `DEC-….md` filenames** — rejected; inconsistent with every existing curated record.
- **LLM-assisted extraction** — rejected; the loop is deliberately deterministic and offline.
- **Strip the draft's source-note automatically on promote** — deferred; the note is a bare
  filename (no path/secret) and the draft reminds the human to remove it before promote.

## Consequences

- `promote` is safer (no empty scaffolds) and consistent with curated naming.
- `--from-run` drafts are closer to human-reviewable; sparse reviews still yield honest `TODO`s.
- New + updated unit tests; the context-pack builder is untouched (its `_extract_section_items`
  helper is preserved). No dependency or provider behavior change.

## Next actions

- PR #50: address the `context check` `memory:human-review` advisory miss (not in this PR).
- PR #51: CLI/help and lint-verdict consistency pass.
- PR #52: v0.3.1 release prep.

## Related links

- Related: [curated decision promotion](./2026-06-30-decision-promote.md),
  [decision draft extraction](./2026-06-30-decision-draft-extraction.md),
  [decision CLI skeleton](./2026-06-30-decision-cli-skeleton.md)
- Source: [v0.3.1 dogfood notes](../dogfood/v0.3.1-notes.md)
