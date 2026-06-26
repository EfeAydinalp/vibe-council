# Plan: add a `vibe decisions show <id>` command

> **This is a sample plan for demonstration.** It describes a *hypothetical* feature
> so you have realistic input to run the council against — `vibe decisions show` does
> **not** exist yet. You feed this file to `vibe review`; you don't run the command it
> proposes. (Today, read a decision via `vibe last decision` or open the file under
> `.council/decisions/`.)

## Context

`vibe decisions list` shows recorded decisions and `vibe decisions search "<query>"`
finds them, but to read a full decision a user has to open the Markdown file by hand
from `.council/decisions/`. A `show` subcommand would print one decision's full
record (decision, rationale, risks, next actions) to stdout — handy for piping into
a plan or pasting into a PR description.

## Proposed change

- Add `vibe decisions show <id>` where `<id>` is the slug from `decisions list`
  (or the timestamp prefix).
- Resolve `<id>` against the append-only index `.council/decisions/index.jsonl`;
  if it matches exactly one entry, print that decision's Markdown to stdout.
- On no match, print a friendly "no decision matches `<id>`" to stderr and exit `2`
  (usage error), consistent with the existing exit-code table.
- On multiple partial matches, list the candidates (like `search`) and exit `2`.
- No model call, no API key required — this is local, like the other `decisions`
  subcommands.

## Files likely to change

- `backend/cli.py` — add the `show` action to the `decisions` subparser and a small
  `cmd_decisions` branch that loads one record by id.
- `tests/test_cli_smoke.py` — a no-model test: `decisions show` with no workspace
  exits cleanly; `show <unknown>` exits `2`.
- `README.md` / `docs/agent-integrations.md` — one line each under decision memory.

## Risks

- **Id ambiguity:** timestamps are unique but a user might pass a too-short prefix.
  Mitigate by treating an ambiguous prefix as a multi-match (list + exit `2`), not a
  silent "first match wins."
- **Index/file drift:** an index entry could point at a deleted Markdown file. Handle
  the missing-file case gracefully (stderr note, exit `1`), matching how `last`
  tolerates missing artifacts.

## Why this is a "balanced quality gate" case

This touches real CLI behavior (argument parsing, exit codes, error paths) and has
genuine edge cases (ambiguous ids, missing files). That's exactly where a multi-model
**`balanced`** review earns its keep:

```sh
vibe review --preset balanced --file examples/plans/feature-plan.md --usage
```

It is **not** a big strategic/architecture decision, so **`full`** is not warranted.

## Test strategy

- Stdlib `unittest`, no new deps, no real model calls.
- `decisions show` with no workspace → clean message, exit `0`.
- `decisions show <unknown>` in a temp workspace → exit `2`, no traceback.

## Out of scope

- No fuzzy/semantic matching (string/prefix match only — consistent with `search`).
- No JSON output flag in this first cut (Markdown to stdout only).
- No changes to how decisions are *written*; this is read-only.

---

> **Note:** this plan references the local `.council/decisions/` workspace (where the
> `show` command would read from). That folder is **local-only and gitignored** —
> reviewing or running this plan never commits anything under `.council/`.
