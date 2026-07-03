# 11 — Website & positioning

## Positioning

Lead with **guarded execution**, not "multi-model council." The council/ranking is one input; the
product is the propose → approve → guarded-execute loop. The one-liner:

> **vibe-council is a local-first workbench where AI agents propose code actions and nothing runs
> until you approve it — with a deterministic guard, not the model, deciding what's even allowed.**

Taglines:
- "Agents propose. You approve. The Workbench guards execution."
- "AI agents are powerful. Don't let them act blindly."
- "Local-first control plane for reviewing, approving, and safely executing agent-proposed code
  actions."

## Hero copy

- **H1:** "Agents propose. You approve. The Workbench guards execution."
- **Sub:** "A local-first control plane for AI coding agents. Every file write and command an agent
  wants is a proposal you inspect, approve, or reject — executed behind a deterministic trust
  boundary, on your machine, with your keys."
- **CTA:** `uv sync && vibe workbench serve`

## Landing page outline

1. **Hero** (above).
2. **Problem** — "AI agents are getting write access. Most tools let them act first and ask later."
   The user loses visibility and control.
3. **Solution** — the propose → approve → guarded-execute loop, one clear diagram.
4. **How it works** — the six stages; call out "the browser only ever sends an action id."
5. **Security posture** — the honest list: approval ≠ execution; fixed argv + `shell=False`;
   localhost-only + token-gated (incl. `/api/state`) + Host-header validated; deterministic guard is
   the boundary; auditor advisory-only; payload artifacts local/gitignored, hash-verified.
6. **Local-first, honestly** — *the* differentiator, stated precisely (see below).
7. **CLI / Workbench demo** — an asciinema of `serve → propose → approve → execute`.
8. **Roadmap** — bridge → onboarding → vault; an open-core note.
9. **Get started** — install + first run.

## Security posture section (what to say)

State the real guarantees, plainly: approval is separate from execution; the client sends only an
action id; the server resolves argv/payload; commands are exact allowlist labels via fixed argv with
no shell; the panel is `127.0.0.1`-only, token-gated, and Host-validated; the deterministic trust
boundary re-runs at execution time and the auditor can't relax it. Frame it as **"designed to fail
closed,"** not "unbreakable."

## Local-first honesty section (what to say)

Say it directly: runtime state, payloads, decisions, and approvals stay on your machine; the panel is
localhost-only; the executor makes no network call. **But** the council/review features send prompts,
files, and diffs to whatever model provider you configure (e.g. OpenRouter) unless you use a local
provider (Ollama). Putting this on the page builds trust and preempts the obvious critique — the
honesty is part of the pitch.

## Demo / screenshot ideas that sell it

- **20-second asciinema:** agent proposes a file edit → card appears in the panel → approve → the
  file changes → a content-free result summary. That single loop *is* the product.
- **"Crafted request has zero effect" clip** (from the PR #89 dogfood) for the security-minded.
- A **before/after** of the approval card: risk label, human-readable rewritten prompt, the exact
  target/argv, and the explicit Execute button.

## What NOT to claim yet

- No "autonomous agents." No "runs on top of your Claude/Codex session directly" (that mode doesn't
  exist). No "team / hosted." No "mobile approvals." No security *guarantee* against a determined
  local attacker — say "fail closed," not "unbreakable." **No commercial-use / license grant** while
  Question 0 is unresolved — the site must not imply a grant.

## Connecting to the hosted/team path later

The website can carry a clearly-labeled "coming later" / "for teams" strip that hints at the hosted
layer ([12-open-core-commercial-path.md](12-open-core-commercial-path.md)) — a mailing-list capture,
not a product claim. Keep the open core the hero; the hosted layer is an add-on, never the pitch.
Don't build the hosted messaging into the core value proposition, and don't ship it before Question 0
is resolved.
