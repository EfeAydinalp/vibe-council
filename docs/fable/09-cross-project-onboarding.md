# 09 — Cross-project council onboarding (v0.6.3)

## Goal

Make vibe-council usable in **arbitrary** projects without re-explaining it each time. This builds on
the launcher (v0.6.1) and the vault (v0.6.2): the launcher generates instruction packs, the vault
gives them something to read, and this phase makes both portable across repos.

All commands below except `vibe guide claude` are **proposed** (not yet built). Mark them as such in
any generated docs until they land.

## Proposed commands

| Command | Purpose |
|---|---|
| `vibe init-agent` | Bootstrap agent onboarding in the current project (detect state, offer to generate the vault + an agent pack). |
| `vibe guide <agent>` | Print (or, with `--write`, emit) a role-specialized instruction pack. `guide claude` exists. |
| `vibe context export --for <agent>` | Export a **redaction-checked**, budgeted context file shaped for a host (Claude/Codex/Fable). |
| `vibe summarize-history` | Compress old status/history into a short, local digest to keep the context pack lean. |
| `vibe project doctor` | Read-only health check: is memory/context present? is the vault initialized? are gates green? no token spend. |

## Generated files (per host)

- `AGENTS.md` — generic agent rules.
- `CLAUDE.md` — Claude Code project instructions (already emit-able via `guide claude --write`).
- `.codex/instructions.md` — Codex instructions.
- `.vibe/agent-quickstart.md` — **only if** a `.vibe/` convention is later adopted for host-neutral
  quickstarts; prefer `docs/context/` first (see [08](08-obsidian-project-vault.md)). Treat as
  optional/uncertain, not a default.
- `docs/context/project/STATUS.md` — seeded if absent.

## Safety rules for generated files

- **Never overwrite an existing file without explicit confirmation** (`--yes` or an interactive
  confirm). A silent overwrite of a user's `CLAUDE.md` is unacceptable.
- **No raw private artifacts in any exported context.** The exporter runs the redaction guard and
  refuses on a critical finding. Never include `.env`, `.council/runtime/`, payloads, secrets, or the
  private local plan files.
- **Project-specific guardrails** carry over: the generated pack states this project's sensitive
  paths, review policy, and never-stage list.
- **No network fetches** during generation. Everything is derived from local state.
- History summaries stay **local by default**; sending them to a provider is a separate, explicit,
  consented step (it's cloud egress).

## `vibe project doctor` scope

Read-only and free (no tokens): report provider/config sanity, whether the vault/context exists,
whether decisions lint / context check / MCP health pass, and whether any never-stage artifact is
currently staged. It **diagnoses**; it does not fix, spend, or write.

## The safest minimum version

1. `vibe project doctor` (read-only, no writes, no tokens) — pure signal, zero risk.
2. `vibe guide <agent>` for codex/fable (stdout only) — extends the existing `guide claude`.
3. `vibe context export --for <agent>` (redaction-checked, budgeted, local) — reuses existing
   context/export + redaction machinery.
4. `--write`/`init-agent` (file emission) **last**, with mandatory confirmation-before-overwrite.

## Non-goals (v0.6.3)

- No overwriting without confirmation. No raw private artifacts in exports. No network. No hosted/
  remote onboarding. No auto-running anything in the target project — onboarding generates and
  advises; it does not execute.
