# Progress

A **curated milestone digest** — a short phase-progress checklist for humans and agents. The
detailed record is git history and [`docs/decisions/`](../../decisions/); this file is the
high-level "where are we" at a glance. Keep it lean; do not paste raw logs or transcripts here.

## Phase checklist

- [x] **v0.5.x — AI Council Workbench MVP + hardening** (runtime store, orchestrator, deterministic
      trust boundary, advisory auditor, guarded executor, bounded file/command execution, localhost
      panel; Host-header + `/api/state` token hardening).
- [x] **v0.6.0 — agent-to-Workbench proposal bridge** *(released).* Proposal schema + validation,
      importer + `vibe workbench propose`, panel proposed-by-agent visibility, bridge docs.
- [x] **v0.6.1 — role-aware onboarding guide.** `vibe guide {claude|codex|fable}` with `--role` and
      opt-in `--write` (append-only).
- [x] **v0.6.2 — project vault scaffold + project doctor.** This folder (README, STATUS, ROADMAP,
      DECISIONS index, PROGRESS, RISKS, WORKFLOWS, NOTES) plus `vibe project doctor` (read-only
      readiness check).
- [x] **v0.6.3 — cross-project onboarding.** `vibe context export --for {claude|codex|fable}`
      (read-only onboarding handoff). Bundled into the `v0.6.3` release (prepared; tag/Release manual).
- [x] **v0.7 — personalization / project profile** *(prepared as the `v0.7.0` release; tag/Release
      manual).* Source brief:
      [`docs/fable/v0.7-personalization-and-project-profile-plan.md`](../../fable/v0.7-personalization-and-project-profile-plan.md)
      (Markdown-first data model, A–E PR breakdown, tighten-only invariants).
    - [x] **PR A — project profile/preferences scaffold.** Public-safe committed
          [`PROFILE.md`](./PROFILE.md) / [`PREFERENCES.md`](./PREFERENCES.md) /
          [`AGENT-ROLES.md`](./AGENT-ROLES.md) (vault, not root `AGENTS.md`). Documentation only — no
          behavior wired up yet.
    - [x] **PR B — `vibe project doctor` reports profile/preferences presence (advisory).** New
          "Personalization scaffold (advisory)" section: present → `[ok ]`, missing → `[warn]` (never a
          failure); root `AGENTS.md` not required (advisory warn only). Read-only; no behavior enforced.
    - [x] **PR C — `vibe context export` references profile/preferences (pointers-only).** New
          "Project profile & preferences" section: pointers to `PROFILE.md`/`PREFERENCES.md`/
          `AGENT-ROLES.md` (never inlined), tighten-only note, root-`AGENTS.md`-not-canonical note,
          `vibe project doctor` recommendation. Reads no `.council/profile.*`; graceful if missing.
    - [x] **PR D — `vibe guide` reflects preferences (advisory, tighten-only).** All guide paths
          (base topic, role, `--write`) carry a "Project profile & preferences" section: pointers to
          `PROFILE.md`/`PREFERENCES.md`/`AGENT-ROLES.md` (never inlined), tighten-only note,
          root-`AGENTS.md`-not-canonical note, doctor/context-export recommendations. No preference
          parsing/application; reads no `.council/profile.*`; `--write` marker-skip unchanged.
    - [x] **PR E — v0.7.0 release prep.** Version → `0.7.0` (`backend/__init__.py`/`pyproject.toml`/
          `uv.lock` self-version), dated `CHANGELOG.md` `[0.7.0]` section,
          [`docs/releases/v0.7.0.md`](../../releases/v0.7.0.md), README release status. No tag/Release
          (manual follow-up).
- [x] **v0.7.1 — hardening** *(prepared as the `v0.7.1` release; tag/Release manual).* Source plan:
      [`docs/fable/v0.7.1-hardening-architecture-plan.md`](../../fable/v0.7.1-hardening-architecture-plan.md)
      (redaction rule → doctor polish → invariant tests → release prep; all Opus/Sonnet).
    - [x] **PR 1 — local-profile redaction hardening.** `local-profile-path` WARNING rule for concrete
          `.council/` profile filenames in tracked docs (advisory; glob form ignored; public scaffold
          not flagged; WARNING→CRITICAL promotion path) + lock-in tests (secret-in-scaffold → CRITICAL,
          staged local-profile → doctor FAIL, enumerated real-repo findings). Warning count 22 → 30.
    - [x] **PR 2 — project doctor consistency polish for the profile scaffold.** State-differentiated
          scaffold summary (all-present OK / none "missing" / partial "incomplete" listing missing
          files), state-aware root-`AGENTS.md` advisory (informational vs. "configuration mismatch";
          never advises removal), and lists `vibe context export` in the guide block. Advisory-only;
          READY/NOT-READY, dangerous-staged FAIL, git-unavailable warn unchanged; read-only.
    - [x] **PR 3 — context-export / guide invariant tests + vault consistency.** Locks export & guide
          profile sections: size-bounded, deterministic (no timestamp), gracefully degrading
          (byte-identical), wording-invariant ("advice to read, not commands"), vault consistency, and
          context-pack no-ingest (still 21/21). Tests + tiny docs only; no behavior change.
    - [x] **PR 4 — v0.7.1 release prep.** Version → `0.7.1` (`backend/__init__.py`/`pyproject.toml`/
          `uv.lock` self-version), dated `CHANGELOG.md` `[0.7.1]` section,
          [`docs/releases/v0.7.1.md`](../../releases/v0.7.1.md), README release status. No tag/Release
          (manual follow-up).
- [ ] **v0.8.x — "solidify the core, local-first"** *(v0.8.0 & v0.8.1 released; v0.8.2 prepared as a
      release).* v0.8.0 = `vibe init-agent` (dry-run-first launcher) + localhost CI guard;
      v0.8.1 = vault digest + capped `RELEASES.md`; v0.8.2 = tighten-only JSON preference schema +
      read-only doctor validator (**full** review; no application). Workbench UX / named profiles /
      profile store / notifications deferred. Planning:
      [`docs/fable/v0.8.x-phase-brief.md`](../../fable/v0.8.x-phase-brief.md) +
      [`v0.8.x-council-debate.md`](../../fable/v0.8.x-council-debate.md) +
      [`v0.8.x-fable-input.md`](../../fable/v0.8.x-fable-input.md) →
      [`v0.8.x-architecture-plan.md`](../../fable/v0.8.x-architecture-plan.md) (9-PR sequence).
    - [x] **PR 1 — `vibe init-agent` report/dry-run mode.** Read-only onboarding report (readiness +
          per-agent would-create/append/skip + next commands); writes nothing, no path argument, no
          `--write`. No behavior change to guide/export/doctor.
    - [x] **PR 2 — `init-agent --write` (guarded append).** Appends selected agents' guide sections to
          the fixed `CLAUDE.md`/`AGENTS.md`/`FABLE.md` (append-only, marker-skip idempotent, never
          overwrites); no path argument; requires explicit `--agent` + `--yes`. No `.council/`.
    - [x] **PR 3 — localhost-only guard (tests only).** Locks the local-first invariant: panel binds
          loopback only (non-local hosts rejected), a runtime `socket.bind` loopback check,
          `host_header_is_local` loopback-only, and a static "no second listener" scan (only
          `workbench_panel.py` may construct a listener). No production change.
    - [x] **PR 4 — v0.8.0 release prep.** Version → `0.8.0` (`backend/__init__.py`/`pyproject.toml`/
          `uv.lock` self-version), dated `CHANGELOG.md` `[0.8.0]` section,
          [`docs/releases/v0.8.0.md`](../../releases/v0.8.0.md), README release status. No tag/Release
          (manual follow-up).
    - [x] **PR 5 — capped `RELEASES.md` + STATUS-trimming workflow (docs + tests).** New
          [`RELEASES.md`](./RELEASES.md) release-history index (newest-first, hard cap 30, oldest
          entries roll up; pointers to `docs/releases/`, never inlined), a "Trimming STATUS history"
          workflow in [`WORKFLOWS.md`](./WORKFLOWS.md), and vault-README/STATUS pointers. Docs + tests
          only — no new command (`summarize-history` deferred), no pack-builder/behavior change.
    - [x] **PR 6 — v0.8.1 release prep.** Version → `0.8.1` (`backend/__init__.py`/`pyproject.toml`/
          `uv.lock` self-version), dated `CHANGELOG.md` `[0.8.1]` section,
          [`docs/releases/v0.8.1.md`](../../releases/v0.8.1.md), README release status. Docs + tests
          only (no code/behavior change). No tag/Release (manual follow-up).
    - [x] **PR 7 — tighten-only preference schema v1 (docs + tests).** Normative
          [`docs/fable/preference-schema-v1.md`](../../fable/preference-schema-v1.md) + a bounded fenced
          `json` example block in [`PREFERENCES.md`](./PREFERENCES.md): `schema: 1` + four tighten-only
          keys (review-preset floor `cheap|balanced|full`, additive sensitive-paths / never-stage,
          usage-flag warning bool); no vocabulary to loosen safety/trust, change the executor boundary,
          add shell/network/hosted behavior, override review policy, or suppress council dissent.
          Council personas documented as a **future v0.9.x** preset direction. Docs + tests only — no
          validator/parser, no application, no behavior change.
    - [x] **PR 8 — read-only preference validator in `vibe project doctor` (full review).** New pure
          [`backend/preferences.py`](../../../backend/preferences.py) validates the schema v1 `json`
          block in `PREFERENCES.md` and returns **findings only** (read-only, fail-closed, advisory);
          doctor gains a `Preferences (machine-readable, advisory):` section (valid → ok, missing →
          note, invalid → warn "ignored"). READY/NOT-READY unchanged. Hardening per §3 Q4;
          findings-only API (no module outside the doctor path imports it). No application, no behavior
          change, no `.council/profile.*` store, no dependency.
    - [x] **PR 9 — v0.8.2 release prep.** Version → `0.8.2` (`backend/__init__.py`/`pyproject.toml`/
          `uv.lock` self-version), dated `CHANGELOG.md` `[0.8.2]` section,
          [`docs/releases/v0.8.2.md`](../../releases/v0.8.2.md), README release status. Release metadata
          + docs only (no code/behavior change). No tag/Release (manual follow-up).
- [ ] **v0.9.x — "apply the proven; describe the personas; defer their behavior"** *(council planning
      done; Fable architecture next).* Council-backed planning:
      [`v0.9.x-council-debate.md`](../../fable/v0.9.x-council-debate.md) +
      [`v0.9.x-phase-brief.md`](../../fable/v0.9.x-phase-brief.md) +
      [`v0.9.x-fable-input.md`](../../fable/v0.9.x-fable-input.md). v0.9.0 = apply the four proven
      tighten-only preference keys (additive/reversible/override-flagged; CLI wins, suggest≠enforce);
      v0.9.1 = council personas as **pure documentation** (no schema/validator/behavior) + a v0.10.x
      dissent-preservation design sketch + a v0.9.0 dogfood pass; v0.9.2 = release prep. Persona
      *behavior* deferred to v0.10.x. **Next: the Fable architecture pass** (architecture + PR breakdown),
      then Opus/Sonnet implement.
    - [x] **Council phase brief** (two `vibe review --preset balanced` passes; docs-only). *This PR.*
    - [ ] Fable architecture plan (`docs/fable/v0.9.x-architecture-plan.md`) — next.
    - [ ] PRs per Fable's breakdown (v0.9.0 apply keys → v0.9.1 persona docs → v0.9.2 release prep).
- [ ] **v0.10.x — persona *behavior*** *(deferred: prompt-emphasis presets + dissent-preservation
      framework; its own council+Fable line).*
- [ ] **Mobile / LAN / voice** *(deferred to its own gated security line; pre-v0.9 threat model).*
- [ ] **hosted / team** *(deferred; separate planning).*

## How to update

- Tick a box when a phase is merged/released; add a one-line note if useful.
- Move detail into `docs/decisions/` (canonical) or the release notes — not here.
- Never store secrets, private paths, raw outputs, or runtime payloads.
