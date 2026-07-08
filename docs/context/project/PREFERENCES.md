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

## Machine-readable preferences (schema v1 — defined, **not active yet**)

Everything above is prose an agent reads. This section adds an **optional, machine-checkable** island:
a single fenced `json` block in the **tighten-only preference schema v1**. The full normative spec —
carrier format, the four allowed types, validation rules, tighten-only proofs, forbidden examples, and
the future council-persona direction — is
[`docs/fable/preference-schema-v1.md`](../../fable/preference-schema-v1.md).

> **Advisory / tighten-only application (v0.9.0).** `vibe project doctor` *reports* on this block
> (read-only validator, v0.8.2). As of **v0.9.0** all four keys are consulted in **advisory,
> tighten-only** ways — never enforcing, never blocking, never failing a command, and an explicit
> `--preset`/`--usage` (or `--no-preferences`) always wins:
> - **`default_review_preset`** — `vibe review`/`vibe diff` treat it as a preset **floor** (raise-only,
>   never lower, never `premium`). Because the baseline is already `balanced`, a `full` value is
>   **notice-only** (`full` is a council **mode**, not a `--preset` value — the CLI recommends `vibe
>   full` and leaves the preset at the baseline).
> - **`require_usage_flag`** — `vibe review`/`vibe diff` print one advisory stderr *warning* when
>   `--usage` is absent (they never add `--usage`, never fail).
> - **`extra_sensitive_paths` / `never_stage_extra`** — `vibe project doctor` emits advisory `[warn]`
>   lines for **staged** paths that match (capped; READY/exit code unchanged). They do **not** change
>   staging, git, the no-stage guard, or the trust/executor boundary.
>
> A `.council/profile.*` store, named personas, and any prompt/ranking/synthesis influence remain
> deferred (v0.10.x+).

**v1 has exactly four preference keys** plus the required `schema: 1`, each **tighten-only by
construction** (an ordered floor-raise or an additive constraint):

- `default_review_preset` — enum `"cheap" | "balanced" | "full"` (a review **floor**; `premium` is not
  in the enum, so it can never be named here).
- `extra_sensitive_paths` — array of **relative** path prefixes to treat as *extra*-guarded (additive
  deny; never removes anything).
- `never_stage_extra` — array of **relative** paths to *add* to the never-stage list (additive).
- `require_usage_flag` — boolean; only `true` is meaningful (adds a warning when `--usage` is absent;
  `false` == unset).

Unknown keys, wrong types, absolute paths, drive letters, or `..` segments are **invalid**; an unknown
`schema` version makes the whole block ignored. The block is **untrusted, ≤ 4096 bytes**, parsed with
stdlib `json` only. It has **no vocabulary to loosen** any safety/security/no-stage/trust rule, to
change the Workbench executor/trust boundary, to add shell/auto-execution/network/hosted behavior, to
override the review policy, or to hide/suppress dissenting council opinions — see the spec's "What the
schema explicitly cannot express."

Canonical example (this is the one machine-readable block; forbidden/invalid examples live in the spec
as non-`json` text so they can't be mistaken for it):

```json
{
  "schema": 1,
  "default_review_preset": "balanced",
  "extra_sensitive_paths": ["infra/prod/", "ops/deploy/"],
  "never_stage_extra": ["notes/local-scratch.md"],
  "require_usage_flag": true
}
```

Every field above only *adds* strictness; deleting the block is strictly *less* strict, never more
permissive-than-baseline. **Council personas** (Cost Skeptic, Security Guardian, Product Strategist,
Local-first Guardian, UX/User Advocate, Risk Officer, Commercialization Lens) are a **future v0.9.x**
direction — a persona will be a *curated preset of these same tighten-only values* plus advisory
review-emphasis, never a policy override and never able to suppress dissent. **No persona is defined,
selected, or applied here.**

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
