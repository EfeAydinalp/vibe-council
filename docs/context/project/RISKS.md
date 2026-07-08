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
  `vibe init-agent --write` stays **append-only, fixed-target (`CLAUDE.md`/`AGENTS.md`/`FABLE.md`),
  with no path argument** — do not add a path/target option, overwrite/`--force`, or project-init
  behavior (that is a traversal/overwrite surface the v0.8.x plan deliberately excludes).
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
- **Local/private profile leakage.** The machine-local personalization profile (`.council/profile.*`,
  gitignored) must never be committed. Defenses: gitignore, `vibe project doctor` FAILs a staged
  `.council/` file, and `vibe lint --redaction` flags a **concrete** local-profile filename in a
  tracked doc (advisory `local-profile-path` warning). Refer to it by the glob form
  `.council/profile.*` in operational docs. Note: no local profile store exists yet — this is
  forward-looking hardening (v0.7.1).
- **Preference schema / personas becoming hidden behavior or a policy override.** The v1 preference
  schema (a bounded `json` block in [`PREFERENCES.md`](./PREFERENCES.md); normative spec
  [`docs/fable/preference-schema-v1.md`](../../fable/preference-schema-v1.md)) is **defined and
  validated but not applied** — v0.8.2 only **validates** it (PR 8:
  [`backend/preferences.py`](../../../backend/preferences.py), advisory in `vibe project doctor`);
  application is v0.9.x. The subtle failure mode: a helper that "just returns the parsed preset" and
  gets imported somewhere convenient, or a future **council persona** (Cost Skeptic, Security Guardian,
  etc.) wired to silently change council behavior. Guards: the validator is **findings-only** (returns
  `Finding(level, message)`, never parsed settings), **read-only/fail-closed**, and a test asserts **no
  module outside the doctor path imports `backend.preferences`**; the schema is **tighten-only by
  construction** (no vocabulary to loosen a gate, change the executor/trust boundary, add
  shell/auto-exec/network/hosted behavior, override the review policy, or **hide/suppress dissenting
  council opinions**); guide and context-export stay **pointer-only** (never inline the block); personas
  are a future v0.9.x preset of the same tighten-only values, never a policy override. Treat any new
  consumer of `backend.preferences`, or any code path that routes a parsed preference/persona into a
  command's logic, as a review flag. **Dissent suppression is the specific new risk class for any
  future persona/lens *behavior*** — a lens can quietly narrow a seat's attention (reframing bias) so a
  dissenting finding never forms, without touching ranking or synthesis. No persona behavior exists yet
  (deferred to v0.10.x+); before any ships it must satisfy the design-only framework in
  [`docs/fable/v0.10.x-dissent-preservation-sketch.md`](../../fable/v0.10.x-dissent-preservation-sketch.md)
  (threat model, structural/content rules, dissent-canary merge-gate tests, observability, override/
  rollback, acceptance criteria, feasibility verdict). Treat any persona text reaching the ranking/
  synthesis stage, any on-by-default persona, or any lens that could downrank/hide a minority opinion
  as a stop condition requiring full council review. If dissent-preservation proves infeasible in
  prototyping, persona/lens **behavior may be canceled — not merely deferred**; passing the sketch's
  doc tests is not proof the reframing-bias problem is solved.
- **Hosted / network scope creep.** The Workbench is localhost-only; agent intake is file/CLI only
  (no network endpoint). Do not add LAN/mobile/hosted surface outside an explicitly-scoped phase.
  `tests/test_localhost_guard.py` **locks** this: the panel binds loopback only, and **no module
  outside `backend/workbench_panel.py`** may construct a listener — a new listener fails the suite (a
  security finding to surface, not to silence by editing the allowlist without review).

## Known-issue pointers

- See [`CLAUDE.md`](../../../CLAUDE.md) "Known issues" (e.g. `full` mode ranking-parser fragility) and
  the context-pack budget note — the pack is near its 14000-char budget; keep new decision records
  concise (~4–5 KB) and do not force large content into the pack.
