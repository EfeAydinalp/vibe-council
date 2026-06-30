---
id: DEC-20260630-decision-promote
status: accepted
date: 2026-06-30
tags: [cli, decision-memory, promote, v0.3, safety]
related: [DEC-20260630-decision-cli-skeleton, DEC-20260630-redaction-guard, DEC-20260629-linked-decision-memory]
published: true
---

# Curated decision promotion MVP (`vibe decisions promote`)

## Context

The decision-memory workflow needs a safe step to turn a **human-reviewed draft** into a curated,
committed `docs/decisions/` record. The CLI skeleton ([decision CLI skeleton](./2026-06-30-decision-cli-skeleton.md))
added list/show/new/lint; `new` produces a draft template but there was no guarded way to promote a
finished draft. Raw `.council/` run extraction (`--from-run`) is deliberately **not** part of this step.

## Decision

Add `vibe decisions promote <draft-path>` (in `backend/decisions_docs.py`, stdlib-only, no model/
API/network):

- **Reads** the given draft Markdown (a user file, a `.council/decisions/drafts/` file, or any safe
  path — read-only, by explicit path).
- **Validates before writing:** required frontmatter + stable headings, and **redaction** (reused from
  `backend/redaction.py`); blocks on missing headings/frontmatter or any **critical** redaction finding.
- **Derives a safe output filename** — `<id>.md` if the frontmatter has an id, else `<date>-<title-slug>.md`,
  else the draft stem — **sanitized** (basename only; no path separators or traversal).
- **Containment:** only writes directly inside `docs/decisions/` (or `--out-dir`); refuses any path
  that escapes it, and refuses `README.md`.
- **Refuses overwrite** unless `--force`; supports `--dry-run` (validate + show target, write nothing).
- **Never auto-stages, commits, or pushes**, and **does not read raw `.council/` run logs**. Prints the
  created path and suggests `git diff` / `vibe decisions lint` next.
- BOM-tolerant: a draft saved with a UTF-8 BOM is accepted and the promoted record is written BOM-free.

## Rationale

- Promotion is the curation gate; doing the safety checks (redaction + structure) *before* writing keeps
  leaks and malformed records out of the committed set.
- Sanitized, contained filenames + overwrite protection make the operation safe to run repeatedly.
- Keeping it write-only-to-`docs/decisions/` with no git side effects preserves the local-first,
  no-surprise-commit posture; humans review the diff and commit deliberately.

## Alternatives considered

- **Promote straight from a raw `.council/` run (`--from-run`)** — deferred; raw extraction is
  higher-risk and belongs in a follow-up PR.
- **Auto-stage/commit the promoted record** — rejected; violates the no-auto-commit rule and removes the
  human review step.
- **Overwrite silently** — rejected; require `--force`.
- **Trust the draft without re-validation** — rejected; redaction + structure checks are the whole point.

## Consequences

- A safe draft→curated promotion path; the curated set stays clean and lint-passing.
- Raw-run extraction / `--from-run` remain follow-up work.
- New functions + tests; no provider behavior change, no new dependencies.

## Next actions

- Follow-up PR: optional, clearly-experimental `--from-run` (raw `.council/` run → draft) with its own
  guards; then the context-pack builder MVP.
- Consider running `vibe decisions lint` automatically on a promoted file.

## Related links

- Related: [decision CLI skeleton](./2026-06-30-decision-cli-skeleton.md),
  [redaction guard](./2026-06-30-redaction-guard.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md)
- Policy: [redaction policy](../redaction-policy.md)
