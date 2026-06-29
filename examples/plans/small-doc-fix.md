# Plan: fix a stale command flag in the README

## Context

The README's quick-start shows an example `vibe` command using an outdated flag
spelling. New users copy it verbatim and get an "unknown option" error.

## Change

- Update the one example command in `README.md` to use the current flag name.
- Grep for any other copies of the stale flag in `docs/` and fix them too.

## Why this is a "cheap / maybe skip the council" case

This is a one-line, low-risk, easily-verified factual fix. A full multi-model
**`balanced`** review would cost more than the change is worth.

- If you want a sanity check at all, use **`cheap`** for a quick smoke read:
  `vibe review --preset cheap --file examples/plans/small-doc-fix.md --usage`
- For a change this small and obvious, it's also reasonable to **skip the council
  entirely** and just make the edit — the council is a tool, not a required gate.

## Verification

- `grep -rn "<stale-flag>" README.md docs/` returns nothing (or only intentional matches).
- The quick-start command runs without an "unknown option" error.

## Out of scope

- No code changes; docs only.
