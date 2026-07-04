# Project preferences

Project-specific, team-agreed **working preferences** for vibe-council — a curated, committed part of
the [project vault](./README.md). These describe how work should be done in this repo (review levels,
model budget, implementation style) so humans and agents don't re-derive them each session.

> **Scaffold only (v0.7 PR A).** These preferences are **documentation an agent reads and follows**;
> no command reads or enforces them yet. Wiring them into `vibe guide` / `vibe context export` /
> `vibe project doctor` is a later v0.7 PR, per
> [`docs/fable/v0.7-personalization-and-project-profile-plan.md`](../../fable/v0.7-personalization-and-project-profile-plan.md).
>
> **Tighten-only.** Every preference here may make the workflow *stricter*; none may loosen a
> safety/security rule (security invariant #17).

## Review preset policy

Which council review level to run (`vibe review`/`vibe diff --preset <p> --usage`):

- **cheap** — small/routine PRs, docs, scaffold slices, mechanical changes.
- **balanced** — phase / major-version **planning briefs**, non-trivial diffs, and anything
  security- or architecture-relevant.
- **full council** — reserved for **critical** trust/security/hosted/network/executor/payment/
  payload/secrets risk (major architecture or security-boundary questions). Not by default.
- **premium** — only with explicit human approval (`--allow-premium`).

Always pass `--usage` on model-spending commands, and `--yes` in non-interactive agent workflows.
This policy is **tighten-only**: a change may *require* a stricter preset; it may never authorize
`premium`/`full` implicitly or downgrade a security review.

## Fable usage policy

- **Fable is an expensive technical lead / architect**, not a routine implementer.
- Use Fable **only** for: phase planning, a critical blocker, or a high-leverage architecture/security
  review.
- **No routine implementation** by Fable — Opus/Sonnet implement routine PRs.
- **No broad Fable repo scans** — Fable reads the curated brief + the phase's minimal reading set, not
  the whole tree.
- Every task prompt carries a model header (see [`AGENT-ROLES.md`](./AGENT-ROLES.md)):
  `MODEL: OPUS/SONNET CODE` or `MODEL: FABLE CODE`.

## Implementation style

- **Small, scoped PRs** — one phase is several PRs; each reviewable in one sitting. No broad refactors
  unless the task explicitly asks.
- **Docs / brief first** — non-trivial work starts from a short `plan.md` or a phase brief, reviewed by
  the council before implementation.
- **Opus/Sonnet implement routine PRs**; **the council reviews plans/diffs** (cheap/balanced/full per
  the policy above); **the user is the final authority** (approves, merges, tags, releases).
- Stdlib-only by default — no new runtime dependency without a stated reason and approval.
- Keep stdout machine-clean; diagnostics/usage go to stderr.

## No-stage policy

Never stage runtime/private/generated artifacts. This restates the canonical **no-stage checklist** in
[`WORKFLOWS.md`](./WORKFLOWS.md) — that file remains the source of truth; confirm every commit with
`git status --short` and `git diff --cached --name-only`. Never stage: `.council/` (incl.
`.council/runtime/` and `.council/runtime/payloads/`), raw outputs, generated packs/exports/decision
drafts, the private local plans, `.env`, `.venv/`, `data/`, `.obsidian/`, cloned repos, API keys, or
secrets; and no unrelated `uv.lock` churn.

## Tighten-only personalization principle

**Personalization may tighten rules but never loosen safety/security rules.** A preference is allowed
only if it **cannot** cause an action, command, or approval to succeed that would have been rejected
without it. Tightening (stricter), keeping (neutral), and adding constraints are allowed; loosening
(widening an allowlist, relaxing a deny, lowering a gate, enabling auto-execute, expanding the network
surface) is prohibited — that is a bug, not a setting. The deterministic trust boundary ignores
preferences entirely. See security invariant #17 in
[`docs/fable/03-security-invariants.md`](../../fable/03-security-invariants.md).

## Safe-to-commit boundary

Content is **safe to commit** here if it holds no secrets, no private user data, no absolute machine
paths/usernames, and the author would be comfortable seeing it in a public GitHub repo. All vault
files are subject to `vibe lint --redaction`; a **critical** finding blocks the commit.

## What must never go here

This file is **committed and world-readable**. Never put:

- Secrets, API keys, credentials, or tokens.
- Raw model / council outputs.
- Runtime payloads or any `.council/runtime/` artifact.
- Private local plans (see the never-stage list in [`WORKFLOWS.md`](./WORKFLOWS.md)).
- `.env` / `.venv/` / `data/` contents or any data dump.
- Precise private local data (absolute machine paths, usernames-in-paths, private hostnames).
- Sensitive personal facts (health/medical/political/etc.) **unless** the user explicitly requests it
  *and* it is safe and appropriate for a committed, public file. Default: omit.
