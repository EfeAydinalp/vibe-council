# vibe-council examples

Short, realistic examples you can **read without spending any API credits**. They
show the inputs you'd feed to the council, the commands you'd run, the artifacts
you'd get back, and — importantly — **what not to commit**.

> These examples are **illustrative**. Command output and exact costs vary by model
> and provider. **Last verified: 2026-06-27** against `vibe-council 0.1.0-dev`. If a
> command here doesn't match the CLI, trust `vibe help` and please open an issue.

## What's here

| File | Shows |
|------|-------|
| [`plans/small-doc-fix.md`](plans/small-doc-fix.md) | A tiny change — the "`cheap` is enough / maybe skip the council" case. |
| [`plans/feature-plan.md`](plans/feature-plan.md) | A meatier change — the "`balanced` quality gate" case. |
| [`workflows/review-diff-extract.md`](workflows/review-diff-extract.md) | A copy-pasteable terminal walkthrough with expected artifacts. |
| [`workflows/claude-code-loop.md`](workflows/claude-code-loop.md) | The plan → review → implement → diff → extract loop for AI coding agents. |

## How to run them

From any project (the wrappers write artifacts into **that** project's `.council/`):

```sh
vibe review  --preset balanced --file examples/plans/feature-plan.md --usage
vibe extract --preset cheap   --file examples/plans/small-doc-fix.md --save --usage
```

`extract` is single-model (no council), so it's the cheapest way to see the tool
work. `review` runs the multi-model council.

> These example files are **safe to read without running any real model calls** — the
> plans are just markdown and the walkthroughs show representative (illustrative)
> output. You only spend credits if you actually run the `vibe` commands. To turn this
> loop into a recorded terminal demo safely, see [`../docs/demo.md`](../docs/demo.md).

## What NOT to commit

Running these creates local artifacts under `.council/` (and a registry under
`data/`). **Never commit them:**

- `.council/` — reviews, diffs, decisions, runs, stages, usage, locks (can contain
  your prompts and the models' outputs)
- `data/` — the workspace registry and any `data/decisions/` / `data/cli_runs/`
- `.env` — your `OPENROUTER_API_KEY`

The repo `.gitignore` already covers all three. The **plan files in this folder are
safe to commit** — they're just markdown. The council's **output is advice, not
authority**: read it, apply what helps, discard the rest.

> **Secrets caveat:** whatever you put in a plan/diff is sent to the provider *and*
> written into `.council/` artifacts. If your input contains secrets or PII, those end
> up in those local files too — so avoid reviewing secret-bearing content, and don't
> sync/share `.council/` even though it's gitignored.
