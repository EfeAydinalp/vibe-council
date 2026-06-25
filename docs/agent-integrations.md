# Agent Integrations — Global `vibe` Command & Project Workspaces

This guide covers the global `vibe` command, project-local `.council/` workspaces,
and the Claude Code workflow. It is intended for using vibe-council from *any*
repository on your machine and from coding agents.

> PR #4 will add decision search/context, token/cost guards, a loop guard, and
> usage reporting. This PR covers global command usage, workspaces, basic
> artifact saving, and basic Claude Code UX only.

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

`stages/` and `usage/` directories are created but not yet populated (PR #4).

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

## Coming in PR #4

- Decision search / context retrieval
- Token / cost guards (`--max-cost`, `--max-tokens`)
- Loop guard
- Usage reporting (`--usage`, `--save-stages`)
