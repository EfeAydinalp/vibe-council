# Risks

Current, active risks and gotchas for vibe-council — the things a human or agent should keep in mind.
Concise and current; retire an entry when it no longer applies. No secrets or private detail here.

## Active risks

- **Fable cost / budget.** Fable is expensive. It is architect / technical lead only; Opus/Sonnet
  implement routine PRs. Do not use Fable for routine release prep or docs-only work, and avoid broad
  Fable repo scans. See [`DECISIONS.md`](./DECISIONS.md).
- **Accidental staging of private/runtime/generated artifacts.** `.council/`, runtime/payload
  artifacts, generated packs/exports, `.env`, `data/`, secrets, and the private local plan files must
  never be staged. Check `git status --short` before every commit (see [`WORKFLOWS.md`](./WORKFLOWS.md)).
- **Overbuilding the launcher / vault.** Keep onboarding a **generator** and the vault **plain
  Markdown**. No interactive launcher, no `vibe council start`, no database, no Obsidian plugin.
- **`AGENT-ROLES.md` vs. a root `AGENTS.md` collision.** Per-agent role **preferences** live in the
  vault [`AGENT-ROLES.md`](./AGENT-ROLES.md) — deliberately **not** a root `AGENTS.md`. Root `AGENTS.md`
  is a `vibe guide … --write` **output target**; if the same file were both a write target and a
  preference **source**, a guide append could corrupt the preference data. Do not make a
  read-and-written file serve both roles (balanced-review guidance from the v0.7 brief).
- **Confusing a future `/council` with the real `vibe` CLI.** `/council` does **not** exist today; it
  is only a possible future host-specific/custom-command idea. The real CLI is `vibe`.
- **Raw payload / output leakage.** Raw file content lives only in the local write-once payload
  artifact and is never rendered in the panel HTML or `/api/state`. Never commit raw model/council
  outputs or paste them into curated docs; run `vibe lint --redaction` before committing public docs.
- **Hosted / network scope creep.** The Workbench is localhost-only; agent intake is file/CLI only
  (no network endpoint). Do not add LAN/mobile/hosted surface outside an explicitly-scoped phase.

## Known-issue pointers

- See [`CLAUDE.md`](../../../CLAUDE.md) "Known issues" (e.g. `full` mode ranking-parser fragility) and
  the context-pack budget note — the pack is near its 14000-char budget; keep new decision records
  concise (~4–5 KB) and do not force large content into the pack.
