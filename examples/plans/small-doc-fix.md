# Plan: fix the stale port number in the README

## Context

The README's "Web UI" section says the backend runs on **port 8000**, but the code
in `backend/main.py` binds **8001** (8000 was already taken on the author's machine).
New users copy the wrong URL and get a connection error.

## Change

- Update the one URL in `README.md` from `localhost:8000` to `localhost:8001`.
- Grep for any other `8000` references in docs and fix them too.

## Why this is a "cheap / maybe skip the council" case

This is a one-line, low-risk, easily-verified factual fix. A full multi-model
**`balanced`** review would cost more than the change is worth.

- If you want a sanity check at all, use **`cheap`** for a quick smoke read:
  `vibe review --preset cheap --file examples/plans/small-doc-fix.md --usage`
- For a change this small and obvious, it's also reasonable to **skip the council
  entirely** and just make the edit — the council is a tool, not a required gate.

## Verification

- `grep -rn "8000" README.md docs/` returns nothing (or only intentional matches).
- The Web UI section points at `http://localhost:8001`.

## Out of scope

- No code changes; docs only.
