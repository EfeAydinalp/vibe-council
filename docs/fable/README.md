# `docs/fable/` — vibe-council implementation pack

A structured, phase-by-phase implementation pack for driving future vibe-council work with a
strong long-running model — **Fable 5**, **Opus**, or **Claude Code**. It encodes the product
vision, the non-negotiable security invariants, the roadmap, the v0.6 agent-bridge design, the
onboarding/vault/website/commercial strategy, and copy-paste prompt templates, so that a capable
implementer can pick up any phase later **without losing the product or security direction**.

This folder is **documentation only**. Nothing here implements v0.6. It is the map, not the trip.

## Who should use this

- A maintainer about to hand a scoped phase to Fable/Opus/Claude Code.
- The implementing model itself, which should read the relevant phase doc(s) **before** writing code.
- A reviewer checking that a proposed change stays inside the agreed scope and security model.

## How to use it with Fable / Opus / Claude Code

1. Pick **one** roadmap phase ([04-roadmap.md](04-roadmap.md)). Do not batch phases.
2. Have the model read, in order: [01-operating-rules.md](01-operating-rules.md),
   [03-security-invariants.md](03-security-invariants.md), and the specific phase doc
   (e.g. [05-v0.6-agent-bridge.md](05-v0.6-agent-bridge.md) + [06-proposal-schema.md](06-proposal-schema.md)).
3. Use the matching prompt template from [14-fable-prompt-templates.md](14-fable-prompt-templates.md).
4. Require the phase's **verification** and **final report** before merge.
5. Keep PRs small. One phase is usually several PRs, not one.

## Hard rules for anyone using this pack

- **Do not paste secrets, API keys, `.env`, `.council/runtime/` contents, payload artifacts, raw
  council outputs, or the private local plan files into any prompt or commit.** See
  [00-current-state.md](00-current-state.md) for the never-stage list.
- **Fable/Opus/Claude is an implementer and reviewer, not the final authority.** A human merges,
  tags, and releases. The model proposes; the maintainer decides.
- **Our roadmap is the source of truth.** The implementer *may* challenge it — and should, when it
  spots a real problem — but must **separate** "must change / strong recommendation / optional
  alternative / not worth doing now" and must **not casually replace** the agreed direction. A
  challenge is a proposal, subject to the same approve/reject the product itself is built around.

## Map of this folder

| File | What it covers |
|---|---|
| [00-current-state.md](00-current-state.md) | Where the product is today (v0.3→v0.5.2), health expectations, never-stage list |
| [01-operating-rules.md](01-operating-rules.md) | How an implementing model must behave in this repo |
| [02-product-vision.md](02-product-vision.md) | What the product is and the problem it solves |
| [03-security-invariants.md](03-security-invariants.md) | Non-negotiable security invariants |
| [04-roadmap.md](04-roadmap.md) | v0.5.2 → v0.9+ phase-by-phase |
| [05-v0.6-agent-bridge.md](05-v0.6-agent-bridge.md) | The v0.6 agent-to-Workbench bridge design |
| [06-proposal-schema.md](06-proposal-schema.md) | Concrete proposal schema + examples |
| [07-agent-session-launcher.md](07-agent-session-launcher.md) | Onboarding / session launcher |
| [08-obsidian-project-vault.md](08-obsidian-project-vault.md) | Durable local project-knowledge vault |
| [09-cross-project-onboarding.md](09-cross-project-onboarding.md) | Using vibe-council in arbitrary repos |
| [10-personalization-layer.md](10-personalization-layer.md) | Personal profile / preferences (tighten-only) |
| [11-website-and-positioning.md](11-website-and-positioning.md) | Positioning + landing-page outline |
| [12-open-core-commercial-path.md](12-open-core-commercial-path.md) | Open-core / hosted strategy |
| [13-fable-implementation-playbook.md](13-fable-implementation-playbook.md) | How to run Fable safely, phase by phase |
| [14-fable-prompt-templates.md](14-fable-prompt-templates.md) | Copy-paste prompts per phase |

## What this pack deliberately is not

Not marketing copy, not a spec that authorizes shipping, and not a substitute for the committed
canonical docs (`CLAUDE.md`, `docs/decisions/`, `docs/releases/`, `docs/context/`). Where this pack
and a canonical doc disagree, the canonical doc and the maintainer win — open an issue rather than
quietly diverging.
