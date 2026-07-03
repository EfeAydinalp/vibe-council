# 07 — Agent session launcher / council onboarding layer (v0.6.1)

## The problem

Today, every new project or session requires manually re-explaining: what vibe-council is, how to
use `vibe`, when to run review/diff, what not to stage, how to treat the council as a reviewer/memory
(not an implementer), and — soon — how to use Workbench approvals and propose actions instead of
acting blindly. That re-explanation is friction and it blocks adoption.

The fix: a **generator** that emits a role-specialized instruction pack from committed project
knowledge + fixed safety text, so an agent starts a session already knowing the rules.

## Naming: `vibe` is real; `/council` is a future idea

- **Canonical entrypoint:** `vibe guide <agent>` (partially exists — `vibe guide claude` ships today
  with `--write CLAUDE.md`). Everything else is generated *output* of that command.
- `vibe council start`, `vibe init-agent` — reasonable **future aliases/wrappers**; treat as proposed.
- `/council` — a **future UX idea only**: a possible Claude Code custom slash-command or a shell
  alias that wraps `vibe guide claude`. **Not** a current shell command. Never document it as
  existing. If built later, it's a thin wrapper, not a new core primitive.

Recommendation: build the launcher as `vibe guide <agent> [--role <role>] [--write]`. Keep
`vibe council start` as an optional friendly alias later.

## Safest first implementation: read-only stdout generator

Version 1 **prints** a copy-paste instruction pack to stdout and writes nothing to the user's repo.
File emission is opt-in and later:

```sh
vibe guide claude                       # print an instruction pack (exists today)
vibe guide claude --role coder          # role-specialized pack — IMPLEMENTED (v0.6.1 phase 1)
vibe guide claude --role coder --write  # opt-in write (append) — IMPLEMENTED (v0.6.1 phase 2)
vibe guide codex                        # (proposed) print a Codex pack
vibe guide fable                        # (proposed) print a Fable pack
```

> **Status:** the **role-aware `vibe guide claude --role <role>`** slice is **implemented** —
> read-only stdout for `task-shaper`/`planner`/`coder`/`reviewer`/`release-manager`, plus **opt-in
> `--write`** (appends the role's section to a `CLAUDE.md`-style file, default `CLAUDE.md`; never
> overwrites — per-role marker skips re-runs and lets roles coexist). No `vibe council start`/
> `/council`. Codex/Fable topics remain proposed/later.

`--write` must never overwrite an existing file without confirmation (see
[09-cross-project-onboarding.md](09-cross-project-onboarding.md)).

## What the launcher does

1. **Detect the current project** (the caller's cwd / `VIBE_CALLER_CWD`, as `vibe` already does).
2. **Check whether project memory/context exists** (`docs/context/project/`, decisions, a context
   pack) and note if it's missing.
3. **Offer to initialize or refresh** local Markdown project knowledge (the vault —
   [08-obsidian-project-vault.md](08-obsidian-project-vault.md)); read-only until `--write`.
4. **Let the user choose an agent role** (below).
5. **Generate a copy-paste prompt / host-specific instruction pack.**
6. **Teach the agent to use `vibe`** (status/review/diff/context/mcp; cheap/balanced/full policy).
7. **Teach the agent to propose actions into the Workbench** (v0.6 bridge) rather than assuming
   execution, and to point the user at the localhost panel when approval is needed.
8. **Keep raw/private/local artifacts out** of prompts and commits.

## Roles and what each prompt should contain

Every role's generated pack includes the same safety spine (council is advisor not authority; don't
stage `.council/`/secrets/private plans; cheap/balanced/full policy; propose into Workbench, point to
the panel URL for approval). The emphasis differs:

| Role | Emphasis in the generated prompt |
|---|---|
| **task-shaper / prompt engineer** | Turn a vague ask into a crisp `plan.md`. Run `vibe status`. Propose nothing yet. |
| **planner** | Write/refine the plan; `vibe review --preset balanced` for non-trivial plans; enumerate scope + non-goals. |
| **coder worker** | Implement in small diffs, then **propose file/command actions into Workbench**; never assume execution; run tests + `vibe diff`. |
| **reviewer** | `vibe diff --preset cheap|balanced`; apply only useful feedback; check against security invariants. |
| **release manager** | The version/CHANGELOG/tag discipline; verify gates; never tag/release without explicit instruction. |

## How this reduces repeated onboarding

The pack is generated from **committed** project knowledge (the vault) plus fixed safety text. New
project → `vibe guide claude --write` (later) → the agent reads a committed `CLAUDE.md`/`AGENTS.md`
next session with zero re-explanation. The onboarding becomes a repo artifact, not a chat ritual.

## How it works with Claude / Codex / Fable

- **Claude Code:** emit `CLAUDE.md` (already supported by `guide claude --write`) and/or a slash-
  command pack later.
- **Codex:** emit `.codex/instructions.md`.
- **Fable / generic:** emit `AGENTS.md` and/or print to stdout for copy-paste.

Each host gets the same content shaped to its convention. The content is the contract; the file name
is per-host.

## Non-goals (v0.6.1)

- No `/council` shell command. No writing files without `--write` + confirmation. No network. No
  role that grants execution authority — every role still proposes into the guarded loop.
