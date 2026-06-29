---
id: DEC-20260630-decision-cli-skeleton
status: accepted
date: 2026-06-30
tags: [cli, decision-memory, v0.3, tooling]
related: [DEC-20260629-linked-decision-memory, DEC-20260630-redaction-guard, DEC-20260629-project-memory-folder-convention]
published: true
---

# Decision memory CLI skeleton (`vibe decisions` over curated docs)

## Context

The council roadmap review put **decision-memory tooling** in the v0.3 must-have set, after the
redaction guard. The curated `docs/decisions/*.md` set is the source of truth, but there was no CLI to
list / read / scaffold / lint it (the existing `vibe decisions` operated only on the gitignored local
auto-extract index). This is the first small v0.3 implementation step; extract/promote and the
context-pack builder are deliberately deferred.

## Decision

Add a minimal `vibe decisions` skeleton over the curated, committed `docs/decisions/` records
(`backend/decisions_docs.py`, stdlib-only, no model/API/network):

- `vibe decisions list` (with `--tag` / `--status` filters) — compact list (date, status, id, title,
  tags), ignoring `README.md`.
- `vibe decisions show <id-or-file>` — print a record, resolved by stem or path, **path-traversal
  guarded** to `docs/decisions/` only.
- `vibe decisions new` — print a draft **template** (minimal frontmatter + the stable headings) to
  stdout; `--out PATH` to write it. **No auto-commit, no auto-promote, no raw `.council/` reads.**
- `vibe decisions lint` — check frontmatter completeness, stable headings (prefix-matched, so
  `Decision (hypothesis)` passes), duplicate ids, broken local links, and **redaction (reusing
  `backend/redaction.py`)**; exit non-zero on errors.
- The existing local-index `search` / `context` actions are preserved unchanged.

## Rationale

- Makes the curated decision set browsable, scaffoldable, and checkable from the CLI — the first
  concrete step of the decision-memory product.
- Reusing the redaction guard for `decisions lint` avoids duplicating safety logic.
- Keeping `new` as a stdout template (no writes by default) is the safest minimal shape — no
  promotion, no commits, no raw-output reads.

## Alternatives considered

- **Repurpose the existing local-index `list`** only — rejected; the curated `docs/decisions/` set is
  the source of truth and needs first-class commands; `search`/`context` stay on the local index.
- **Implement `promote` / `--from-run` now** — deferred to a follow-up PR (raw `.council/` extraction
  is higher-risk and out of scope here).
- **A separate top-level command (e.g. `vibe adr`)** — rejected; extends the existing `decisions`
  surface for consistency.

## Consequences

- A usable decision-memory CLI skeleton; curated records are listable / showable / lintable.
- `decisions lint` can gate record quality and leakage (complements `vibe lint --redaction`).
- Extract/promote and the context-pack builder remain follow-up work.
- New module + tests; no provider behavior change, no new dependencies.

## Next actions

- Follow-up PR: `vibe decisions promote` (raw run → curated draft → human approve), then the
  context-pack builder MVP.
- Consider wiring `decisions lint` into CI alongside `vibe lint --redaction`.

## Related links

- Related: [linked decision memory](./2026-06-29-linked-decision-memory.md),
  [redaction guard](./2026-06-30-redaction-guard.md),
  [project-memory folder convention](./2026-06-29-project-memory-folder-convention.md)
- Roadmap: [track-based roadmap](../plans/track-based-roadmap.md)
