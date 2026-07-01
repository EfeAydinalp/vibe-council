# Agent Integrations — Global `vibe` Command & Project Workspaces

This guide covers the global `vibe` command, project-local `.council/` workspaces,
and the Claude Code workflow. It is intended for using vibe-council from *any*
repository on your machine and from coding agents.

> It also covers project-local decision memory (`vibe decisions list/search/context`)
> and the token / cost / loop guards and usage tracking.

> **New to using vibe-council from another project or an AI coding agent?** Read the short
> [Agent Quickstart](agent-quickstart.md) first — a copy-paste-safe review → diff → decision recipe
> with the safety rules front-loaded. `vibe guide claude` prints one reusable **Claude Code**
> instruction block; the Agent Quickstart is the short **general-purpose** guide for *any* AI coding
> agent, and this document is the full reference.

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

## Install on macOS / Linux

From the vibe-council repo:

```sh
sh scripts/install-vibe.sh --dry-run        # preview, change nothing
sh scripts/install-vibe.sh --yes            # symlink ~/.local/bin/vibe -> scripts/vibe.sh
sh scripts/install-vibe.sh --yes --bin-dir ~/bin   # install elsewhere
```

- User-local only (`~/.local/bin` by default) — **no sudo**, idempotent, never edits
  your shell rc files.
- If `~/.local/bin` is not on `PATH`, it prints the exact `export PATH=...` line and
  the concrete rc file for your shell.
- A conflicting, non-vibe `vibe` is left alone unless you pass `--force`.

`scripts/vibe.sh` is the POSIX twin of `vibe.ps1`: it resolves the repo from its own
(possibly symlinked) location, runs `python -m backend.cli`, and forwards the exit
code.

## Wrapper environment variables (both platforms)

| Variable | Meaning |
|----------|---------|
| `VIBE_CALLER_CWD`   | The directory you invoked `vibe` from. The wrappers set it (respecting an outer value) so project-local `.council/` artifacts are written in your project, not in the vibe-council repo. |
| `VIBE_COUNCIL_HOME` | Overrides the vibe-council repo root. If set, it **wins** over the script-resolved location — useful when you have multiple clones. |
| `VIBE_PYTHON`       | (Unix) Exact Python interpreter to use. Otherwise the launcher prefers the repo `.venv`, then an active `$VIRTUAL_ENV`, then `python3`/`python` — so a bare `python` pointing at the wrong environment is never silently used. |

> **Security boundary:** `VIBE_PYTHON` and `VIBE_COUNCIL_HOME` select which code runs
> (interpreter and repo). Do **not** run `vibe` in a context where these environment
> variables are attacker-controlled.

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
| `.council/stages/`   | Per-stage JSON snapshots written by `--save-stages` (stage1/2/3 outputs + metadata). |
| `.council/usage/`    | Token/cost usage metadata written by `--save-stages`. |
| `.council/locks/`    | Loop-guard lock files (auto-managed; stale locks from crashed runs self-clean after 10 min). |

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

The standard loop:

1. `vibe status`
2. (optional) `vibe decisions context "<topic>"` — read prior decisions first
3. write `plan.md`
4. `vibe review --preset balanced --file plan.md --yes --usage`
5. revise the plan — **apply only useful feedback** (see "Filtering" below)
6. implement
7. `vibe diff --preset balanced --yes --usage`
8. apply only useful feedback
9. `vibe extract --preset balanced --file plan.md --save --yes --usage`
10. final report: files changed, council commands run, cost/tokens, and `.council/`
    artifact paths — while keeping those artifacts local

Use `--yes` in agent workflows so there are no interactive prompts.
Generate an in-repo guide with `vibe guide claude` (or `vibe guide claude --write CLAUDE.md`).
A copy-pasteable version of this loop lives in
[`examples/workflows/claude-code-loop.md`](../examples/workflows/claude-code-loop.md).

### Filtering: council output is advice, not authority

The council is a second opinion to *filter*, not a gate that decides for you. The
developer/agent owns the decision.

- **Act on:** correctness bugs, security issues, real cost blow-ups, missing
  constraints/edge cases, concrete factual errors.
- **Be skeptical of:** style preferences, speculative rewrites, scope-widening
  "consider also…" suggestions.
- **Never** let an agent apply a diff or land a change **without human review** just
  because the council suggested it.

In the final report, say *which* findings you applied and which you declined (with a
one-line reason). That record beats the raw review.

### Preset/cost notes for agents

- For **tiny changes** (a one-line docs fix), `balanced` over-reviews — use
  `--preset cheap` for a quick smoke read, or skip the council entirely.
- Use `balanced` for real plan/diff gates; reserve `full` for big strategic decisions
  and `premium` (with `--allow-premium`) only when explicitly requested.
- Always pass **`--usage`** so the final report can include provider-reported
  tokens/cost when available.
- **Never commit** `.council/`, `data/`, or `.env`; never print the API key.

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

## Privacy & local-first (summary)

- **Leaves your machine:** prompts/files/diffs you review are sent to the configured
  provider (currently OpenRouter) — see their privacy policy; avoid secrets/PII in
  reviewed content.
- **Stays local:** everything under `.council/` and the `data/` registry.
- **API key:** lives in `.env`, never printed, never committed.
- **BYO key / BYO cost:** you pay the provider directly; `--usage` shows
  provider-reported tokens/cost when available.

See the README's "Privacy & local-first" section for the full version.

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
