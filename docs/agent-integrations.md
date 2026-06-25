# Agent Integrations — Global `vibe` Command & Project Workspaces

This guide covers the global `vibe` command, project-local `.council/` workspaces,
and the Claude Code workflow. It is intended for using vibe-council from *any*
repository on your machine and from coding agents.

> It also covers project-local decision memory (`vibe decisions list/search/context`)
> and the token / cost / loop guards and usage tracking.

## Install the global `vibe` command (Windows)

From the vibe-council repo:

```powershell
# Preview what will happen (no changes):
scripts\install-vibe.ps1 --dry-run

# Install: creates %USERPROFILE%\bin\vibe.cmd and adds %USERPROFILE%\bin to User PATH
scripts\install-vibe.ps1            # asks before changing PATH
scripts\install-vibe.ps1 --yes      # no prompt (good for automation)
```

- No admin required.
- The shim points at this repo's `scripts\vibe.ps1`.
- If the repo lives elsewhere, set `VIBE_COUNCIL_HOME` to its path before installing.
- Restart your shell after install so the PATH change takes effect.

`vibe.ps1` remembers your current directory (`VIBE_CALLER_CWD`), switches into the
vibe-council repo, runs `python -m backend.cli`, then restores your directory and
forwards the exit code. The API key is never printed.

## Use from any repo

```powershell
vibe status
vibe review  --preset balanced --file plan.md
vibe diff    --preset balanced
vibe extract --preset balanced --file plan.md --save
vibe mini    --preset balanced --prompt "Should we add caching now?"
vibe help
vibe guide claude
vibe last
vibe projects list
```

## How `.council/` works

The first time you run `vibe` (any mode, or `vibe init`) inside a project, a local
workspace is created at `<project>/.council/`:

| Directory            | Contents |
|----------------------|----------|
| `.council/reviews/`  | Saved reviews (markdown). `review` and `diff` write here. |
| `.council/diffs/`    | Raw `git diff` captures (`.diff`). |
| `.council/decisions/`| Decision records (JSON + Markdown) from `extract --save`. |
| `.council/runs/`     | `mini` / `full` outputs saved with `--save`. |
| `.council/stages/`   | Reserved for PR #4 (per-stage metadata). |
| `.council/usage/`    | Reserved for PR #4 (token/cost usage). |
| `.council/locks/`    | Reserved for PR #4 (loop guard / locks). |

`config.json` stores: `project_name`, `project_path`, `created_at`, `last_used_at`,
`default_preset` (balanced), `max_preset` (balanced), `require_allow_premium` (true).
`last_used_at` updates on every run.

`.council/` is **local-only**. vibe adds `.council/` to your project's `.gitignore`
(without touching existing content). Skip workspace use entirely with `--no-project`.

## Global registry — `data/projects.json`

Every workspace is registered in the vibe-council repo at `data/projects.json`
(name, path, created_at, last_used_at). List them with `vibe projects list`. Because
`data/` is gitignored, the registry is never committed.

## Claude Code workflow

1. `vibe status`
2. write `plan.md`
3. `vibe review --preset balanced --file plan.md --yes`
4. implement
5. `vibe diff --preset balanced --yes`
6. fix issues
7. `vibe extract --preset balanced --file plan.md --save --yes`

Use `--yes` in agent workflows so there are no interactive prompts.
Generate an in-repo guide with `vibe guide claude` (or `vibe guide claude --write CLAUDE.md`).

## Exact commands

```text
vibe review  --preset balanced --file plan.md
vibe diff    --preset balanced
vibe extract --preset balanced --file plan.md --save
vibe mini    --preset balanced --prompt "..."
vibe help
vibe guide claude
vibe status
vibe last
```

## Saving behavior (this PR)

| Command | stdout | Saved |
|---------|--------|-------|
| `review`  | yes | always to `.council/reviews/` (when a workspace is active) |
| `diff`    | yes (the review) | raw diff to `.council/diffs/`, review to `.council/reviews/` |
| `extract` | yes | only with `--save`: JSON+Markdown to `.council/decisions/` (or `data/decisions/` if no workspace) |
| `mini`    | yes | only with `--save`: `.council/runs/` |
| `full`    | yes | only with `--save`: `.council/runs/` |

With `--save-stages`, stage outputs + usage metadata are written under
`.council/stages/` and `.council/usage/`.

> **Note:** stage files contain model **input/output content** (responses,
> rankings, synthesis) and may quote your reviewed material. They never contain
> the API key. Keep `.council/` gitignored (vibe does this automatically) so this
> content is never committed.

## Decision memory (list / search / context)

`extract --save` records each decision as JSON + Markdown under
`.council/decisions/` and appends an entry to an append-only index,
`.council/decisions/index.jsonl` (id, timestamp, title, project_name,
source_file, tags, json_path, markdown_path). This project-local folder is the
primary source for the project's decisions.

```text
vibe decisions list                 # newest-first list of recorded decisions
vibe decisions search "topic"       # stdlib substring search over metadata + content
vibe decisions context "topic"      # compact context block for planning (paste into a plan)
```

These commands call no model and need no API key. `search`/`context` match over
index metadata, decision text, rationale, risks, open questions, next actions,
tags, and Markdown content (simple V1 string matching — no embeddings, no SQLite).

## Token, cost, and loop guards

- **`--max-tokens N`** — estimates input tokens (rough, before any model call)
  and fails the run if the estimate exceeds `N`. Estimates are labeled as
  estimates.
- **`--max-cost X`** — **optional and best-effort**. If omitted there is **no
  cost cap**. It can only hard-fail **after** the run, when OpenRouter reports an
  exact cost above `X` (exit code **6**); stdout is preserved. If the provider
  does not report a cost, the cap cannot be enforced (no dollar amount is
  fabricated). Use **`--max-tokens`** for a real pre-run block.
- **Loop guard** — **enabled by default**, independent of cost. It blocks:
  1. concurrent identical runs in the same workspace,
  2. the same input within a 60s cooldown,
  3. more than 5 runs per 10 minutes.
  Override with `--allow-repeat` (duplicate/cooldown) or `--no-loop-guard`
  (disable all). Lock/run metadata lives under `.council/locks/` (local-only).
- **`--usage`** — prints a token usage summary (to stderr): estimated input
  tokens plus provider-reported tokens when available.

Use `cheap` for smoke tests and `balanced` for real review.

## Presets & the premium guard

- **cheap** — fast/low-cost; use for smoke tests.
- **balanced** *(default)* — use for real review.
- **premium** — highest quality; **requires `--allow-premium`**.

`premium` (including `full --preset premium`) is blocked unless you pass
`--allow-premium`, to avoid accidental high-cost runs.

> **Warning:** Do not use `full + premium` (or premium at all) unless explicitly
> requested.

## Local / ignored files

- `.council/` is local and should stay gitignored (vibe adds it automatically).
- `.env` and `data/` are local and ignored.
- Generated runtime files (reviews, diffs, decisions, runs, registry) must never
  be committed.

## Claude Code workflow (with decision memory)

1. `vibe status`
2. `vibe decisions context "<topic>"`
3. write `plan.md`
4. `vibe review --preset balanced --file plan.md --yes`
5. implement
6. `vibe diff --preset balanced --yes`
7. fix issues
8. `vibe extract --preset balanced --file plan.md --save --yes`

## Future work

- Provider-exact cost accounting / pricing tables
- Embedding-based decision search and SQLite-backed memory
