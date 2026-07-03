# 10 — Personalization layer (v0.7)

## Goal

A **Personal Workbench Profile** and per-project **Memory & Preferences** so the tool adapts to how a
user actually works — without ever weakening the security model.

## What it can capture

- **Working style** — verbosity, plan-first vs. dive-in, how much explanation to include.
- **Preset / model spending style** — default preset per project, when to allow balanced/full, a soft
  spend ceiling awareness.
- **Review strictness** — how aggressive `vibe diff`/`review` should be by default.
- **Approval preferences** — default risk threshold at which to require an extra confirmation; which
  kinds always warrant a closer look.
- **Sensitive paths** — additional paths to treat as extra-guarded for this project.
- **Recurring workflows** — named sequences the user runs often (e.g. "plan → review → propose").
- **Release / PR style** — commit message conventions, PR body shape, co-author lines.
- **Agent role preferences** — default role per agent.

## The one hard rule

**Personalization may TIGHTEN but never LOOSEN a guardrail** (security invariant #17). Concretely:

- It **may** raise review strictness, add sensitive paths, lower the auto-confirm risk threshold,
  narrow which command labels a project uses, or require extra confirmation.
- It **may not** widen the command allowlist, relax the trust boundary, enable any auto-execution,
  expand the network surface, disable Host/token checks, or mark a denied path allowed.

A preference that would loosen a guard is not "a setting" — it's a bug. The trust boundary ignores
preferences entirely; preferences only ever add friction on top of it, never remove it.

## Local-only vs. committed

- **Local-only / gitignored by default:** a personal profile (`.council/profile.json` or similar) —
  it's about *this user on this machine*, not the project. Never committed, never sent to a model.
- **Committed (optional, project-level):** a shared **project preferences** file (e.g. review policy,
  sensitive paths, PR style) that the team agrees on. This is the tighten-only, project-wide subset —
  and it still cannot loosen the trust boundary.

Keep the two separate: personal (local) vs. project (committed). Do not leak personal preferences
into commits or context exports.

## Why this comes after the bridge / onboarding / vault

Personalization **adjusts an existing loop**; it doesn't create one. There's nothing to personalize
until: the guarded execution core (v0.5) exists, agents can propose into it (v0.6.0), onboarding
generates the packs it would tune (v0.6.1), and the vault holds the project knowledge it would read
(v0.6.2). Building preferences before those exist personalizes a void.

## Non-goals (v0.7)

- No preference that loosens any invariant in [03-security-invariants.md](03-security-invariants.md).
- No auto-execute preference. No allowlist-widening preference. No committing the personal profile.
  No sending the profile to a provider.
- **Review level:** balanced (a preference change touching approval thresholds or sensitive-path
  handling is security-relevant — verify it only tightens).
