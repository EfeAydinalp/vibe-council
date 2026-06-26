# Workflow: review → implement → diff → extract

**TL;DR:** `review plan → implement → diff → extract`. Four council commands, ≈ $0.50
total on `balanced`, a couple of minutes. Artifacts land in `.council/` (gitignored).

A copy-pasteable terminal walkthrough for one real change. Output below is
**illustrative** (yours will differ); the point is the shape of the loop, the
commands, and the artifacts each step leaves behind.

> All commands assume the global `vibe` command is installed. Otherwise use
> `python -m backend.cli ...`, `scripts\vibe.ps1 ...` (Windows), or
> `scripts/vibe.sh ...` (macOS/Linux).

## 0. See where you are

```sh
vibe status
```

```text
No active council workspace in this directory.
  directory: /path/to/your-project
  run 'vibe init' (or any mode command) to create one.
```

`vibe init` (or the first mode command) creates `.council/` here and adds it to your
`.gitignore`.

## 1. Review the plan (quality gate)

Write `plan.md`, then — note: **no `--yes` the first time**, so you see the approval
prompt and that this spends credits:

```sh
vibe review --preset balanced --file plan.md --usage
```

```text
Create local council workspace for project 'your-project'? [Y/n] y
# ... consolidated review prints to stdout ...
[saved] .council/reviews/2026-..._review.md
[usage] Reported tokens: prompt=12832 completion=8657 total=21489
[usage] Provider-reported cost: $0.15 (as reported by OpenRouter)
```

Read the review. **Apply only the useful feedback** — correctness, security, cost,
and missing-constraint findings are worth acting on; style nits and speculative
rewrites usually aren't. The council advises; you decide.

## 2. Implement

Make your changes as usual. Once you have a working diff:

## 3. Review the diff (second gate)

From here on, `--yes` is fine to skip the prompt:

```sh
vibe diff --preset balanced --yes --usage
```

```text
# ... consolidated review of your git diff prints to stdout ...
[saved] .council/diffs/2026-...diff
[saved] .council/reviews/2026-..._diff.md
[usage] Provider-reported cost: $0.23 (as reported by OpenRouter)
```

Apply the useful findings; re-run if you made substantive changes (`--allow-repeat`
bypasses the duplicate-cooldown loop guard).

## 4. Record the decision

```sh
vibe extract --preset balanced --file plan.md --save --yes --usage
```

```text
Decision: ...
[saved] .council/decisions/2026-...json
[saved] .council/decisions/2026-...md
[usage] Provider-reported cost: $0.03 (as reported by OpenRouter)
```

This appends to `.council/decisions/index.jsonl`, so `vibe decisions list/search/
context` can find it later (no API key needed for those).

## Artifacts this leaves behind (all local, all gitignored)

```text
.council/
  reviews/    <- step 1 + step 3 reviews (markdown)
  diffs/      <- step 3 raw git diff
  decisions/  <- step 4 decision (json + md) + index.jsonl
```

## What NOT to commit

`.council/`, `data/`, and `.env` are local-only and already gitignored. When you
stage your change, stage only your real source/docs edits — never `git add` the
council artifacts. If you ever commit `.env` by accident, rotate your OpenRouter key.
