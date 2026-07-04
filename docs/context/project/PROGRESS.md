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
- [ ] **v0.7+ — personalization / mobile / hosted** *(deferred; separate planning).*

## How to update

- Tick a box when a phase is merged/released; add a one-line note if useful.
- Move detail into `docs/decisions/` (canonical) or the release notes — not here.
- Never store secrets, private paths, raw outputs, or runtime payloads.
