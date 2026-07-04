# Project profile

Public-safe project identity/profile for **vibe-council** — a curated, committed part of the
[project vault](./README.md). This is the "what this project is" page that humans and agents read to
understand the product's shape and stance before working on it.

> **Scaffold only (v0.7 PR A).** This file is **read by humans/agents as documentation**; no command
> reads or acts on it yet. Personalization *behavior* (guide/context-export/doctor integration) is a
> later v0.7 PR, per [`docs/fable/v0.7-personalization-and-project-profile-plan.md`](../../fable/v0.7-personalization-and-project-profile-plan.md).

## What the project is

**vibe-council** is a **local-first AI "council" workflow tool**: multiple LLMs collaboratively review
or answer, with anonymized peer ranking, decision memory, and cost/safety guardrails. The product is
the **command-line interface** (`vibe`) — everything runs on the user's machine with their own API
key; nothing leaves the machine except the model calls the user explicitly triggers.

It began as a fork of [`karpathy/llm-council`](https://github.com/karpathy/llm-council) and has
diverged substantially into a practical developer/agent workflow tool. **Preserve that
attribution/provenance.**

## Current product shape

- **Council review/answer workflow** — `vibe review` / `vibe diff` give a cheap multi-model second
  opinion on plans and diffs; council output is **advice to filter, not authority**.
- **Decision memory** — `vibe decisions …` + curated `docs/decisions/` records; `vibe context build` /
  `vibe context check` assemble a budgeted, deterministic context pack.
- **Read-only MCP** (v0.4) — exposes status/decisions/context to Claude Code and local agents with no
  write/action authority.
- **AI Council Workbench** (v0.5) — task → visible stages → **audited approval** → **guarded
  execution** → logged, all localhost-only; approval is separate from execution, the deterministic
  trust boundary is the real gate, the auditor is advisory.
- **Agent-to-Workbench proposal bridge** (v0.6.0) — agents **propose** bounded actions
  (`vibe workbench propose`); a human approves and executes through the existing guarded executor.
- **Cross-project onboarding** (v0.6.1–v0.6.3) — role-aware `vibe guide`, this **project vault**,
  `vibe project doctor`, and `vibe context export --for <agent>`.

## Local-first stance

- Runs on the user's machine with their own API key. **The API key is never printed**; only
  `.env.example` is tracked.
- Nothing is sent anywhere except the model calls the user explicitly triggers. **Local caveat:** when
  a cloud provider is used, `vibe review`/`diff` do transmit the plan/diff content they review to that
  provider; a local provider (Ollama) keeps even that on-machine.
- Runtime state, payloads, decisions drafts, and approvals stay in a **gitignored `.council/`**
  workspace — never committed.
- Markdown is the source of truth; **no database, no vector DB, no hosted/SaaS** in the local core.

## Current release state

- **`v0.6.3` released** (cross-project agent onboarding) — the repo reports `0.6.3`.
- **v0.7 personalization is in progress**: this file is **PR A** (project profile/preferences
  scaffold) of the A–E breakdown in the
  [v0.7 brief](../../fable/v0.7-personalization-and-project-profile-plan.md). No personalization
  *behavior* is wired up yet.
- License/provenance remains an unresolved **"Question 0"** commercial gate; no `LICENSE` is added.

## What belongs here

- Public-safe project identity: what vibe-council is, its product shape, its local-first stance, and
  the current release state.
- Stable, curated facts a newcomer (human or agent) needs to understand the project — kept **generic
  and public-safe**.

## What must never go here

This file is **committed and world-readable**. Keep it generic; never put:

- Secrets, API keys, credentials, or tokens.
- Raw model / council outputs.
- Runtime payloads or any `.council/runtime/` artifact.
- Private local plans (the private feasibility/hardening plans — see the never-stage list in
  [`WORKFLOWS.md`](./WORKFLOWS.md)).
- `.env` / `.venv/` / `data/` contents or any data dump.
- Precise private local data (absolute machine paths, usernames-in-paths, private hostnames).
- Sensitive personal facts (health/medical/political/etc.) **unless** the user explicitly requests it
  *and* it is safe and appropriate for a committed, public file. Default: omit.
- A detailed, exploitable map of the most sensitive paths — state *that* a class is sensitive without
  enumerating the crown jewels (committed preference files are public, reconnaissance-adjacent
  metadata).

## Safe-to-commit boundary

Content is **safe to commit** here if it holds no secrets, no private user data, no absolute machine
paths/usernames, and the author would be comfortable seeing it in a public GitHub repo. All vault
files (including this one) are subject to `vibe lint --redaction`; a **critical** finding blocks the
commit.

## Personalization principle

**Personalization may tighten rules but never loosen safety/security rules.** Nothing stated in the
profile/preferences can widen the command allowlist, relax the trust boundary, enable auto-execution,
or expand the network surface — it may only add friction, never remove it. See
[`PREFERENCES.md`](./PREFERENCES.md), [`AGENT-ROLES.md`](./AGENT-ROLES.md), and security invariant #17
in [`docs/fable/03-security-invariants.md`](../../fable/03-security-invariants.md).
