---
id: DEC-20260629-open-core-commercial-hypothesis
status: proposed
date: 2026-06-29
tags: [commercial, open-core, hypothesis, monetization]
related: [DEC-20260629-external-tools-and-obsidian-research, DEC-20260629-linked-decision-memory]
published: true
---

# Open-core commercial hypothesis (proposed)

> **Status: proposed — a hypothesis pending the commercial feasibility review, not a final
> product decision.**

## Context

The external-tools audit surfaced a repeatable monetization shape (ECC's MIT core + hosted Pro
GitHub App; gstack's MIT core + optional hosted GBrain sync; Obsidian's free local core + paid
Sync/Publish). The founder wants to know whether vibe-council could follow an analogous model
without diluting its local-first, BYO-key ethos.

## Decision (hypothesis)

Keep a **public, local-first core** and, *if and only if demand is validated*, consider a
**separate private commercial layer** for hosted/team/billing/sync convenience:

- **Public core stays free and local-first**, BYO API key, council + local decision memory +
  context pack — never gated.
- A potential paid layer (in a **separate private repo**) = hosted/team **sync of curated
  decision records + an org-shared agent brief**, plus support/templates.
- **Prefer BYOK + subscription / support / templates / team sync over a prepaid credit wallet**
  for now (avoid wallet/credit liability and token-resale).
- **Self-hosted inference / GPU is later, not the first MVP.**
- **Security / product / code "council packs"** may be monetizable but require **clear boundaries
  and validation** (and a safety layer — no raw uncensored passthrough).

## Rationale

- Monetize **convenience (sync, team, publish, support), not the core files** — the common thread
  across ECC, gstack/GBrain, and Obsidian.
- BYOK keeps inference cost on the user and sidesteps credit/wallet and token-resale risk.
- A separate private repo keeps the OSS promise intact while allowing a commercial layer.

## Alternatives considered

- **Prepaid credit / token-resale wallet** — disfavored now; liability and margin risk.
- **Sell the core / closed-source the CLI** — rejected; breaks local-first positioning and OSS
  trust.
- **Self-hosted inference appliance as MVP** — deferred; heavy, not the cheapest path to validate.

## Consequences

- This is a **direction to test, not a commitment** — the commercial feasibility review owns the
  go/no-go and the first paid MVP definition.
- If pursued, a **public/private boundary** must be drawn deliberately (what stays MIT/public).
- Any hosted/team tier inherits a **mandatory security bar** (redaction, scoped credentials,
  local-by-default, opt-in sync).

## Next actions

- Run the **commercial feasibility review** using this hypothesis and the research audit as input.
- Define candidate first paid MVP: *free CLI + paid team sync of curated decisions / shared brief*.
- Revisit after the decision-memory dogfood shows whether the context pack is a real moat.

## Related links

- Research audit (monetization patterns): [agent-skills / knowledge-graph repo audit](../research/agent-skills-knowledge-graph-repo-audit.md)
- Strategy plan: [linked decision-memory strategy](../plans/linked-decision-memory-strategy.md)
- Related: [external tools & Obsidian research](./2026-06-29-external-tools-and-obsidian-research.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md)
