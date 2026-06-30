---
id: DEC-20260630-context-pack-builder-mvp
status: accepted
date: 2026-06-30
tags: [cli, context-pack, decision-memory, v0.3, local-first]
related: [DEC-20260630-decision-cli-skeleton, DEC-20260629-linked-decision-memory, DEC-20260630-redaction-guard]
published: true
---

# Context pack builder MVP (`vibe context build`)

## Context

The linked decision-memory direction names the **context pack / agent brief** as the likely moat: a
durable, low-token project memory an agent can consume. With curated decision records and `STATUS.md`
in place, the next step is to assemble them into a compact pack — deterministically, with no model
calls, vectors, or hosted services.

## Decision

Add `vibe context build` (in `backend/context_pack.py`, stdlib-only):

- **Inputs:** curated `docs/decisions/*.md` + `docs/context/project/STATUS.md` (overridable via
  `--decisions-dir` / `--status`).
- **Deterministic assembly, no LLM:** metadata · project identity · current status · pinned/
  high-priority decisions (frontmatter `pinned`/`priority`, skipped gracefully if absent) · recent
  full decisions (last few by date) · decision index (older) · rejected-alternatives index (from
  `Alternatives considered`) · constraints/safety notes.
- **Character budget** (`--max-chars`, default 12000): when over budget, reduce recent-full count →
  drop rejected index → truncate the decision index → (last) truncate status; **never drop metadata
  or status**, and warn.
- **Output** defaults to gitignored **`.council/context/pack-latest.md`** (local-first); `--output`
  to override. **Refuses to write under `docs/` unless `--allow-docs`**; prevents writing the pack
  into public docs by default; creates parent dirs; **never stages/commits**.
- **Redaction:** runs `backend/redaction.py` on the generated pack and **blocks the write on any
  critical finding** (prints the masked result either way).
- **No** vector retrieval, MCP, hosted/sync, dashboard, or operator-inbox work in this MVP.

## Rationale

- Deterministic, local-first assembly is cheap, predictable, and safe — the right first version
  before any embeddings or semantic retrieval.
- Blocking on critical redaction findings keeps a generated artifact safe by default even though it
  is gitignored.
- Curated decision records remain the source of truth; the pack is a derived, regenerable view.

## Alternatives considered

- **LLM summarization for the pack** — rejected for the MVP; adds cost/nondeterminism/model
  dependency. Tiered inclusion + a char budget is enough first.
- **Vector/semantic selection of decisions** — deferred; plain recency + index first.
- **Writing the pack into `docs/` by default** — rejected; it is a generated artifact and stays
  local/gitignored unless explicitly `--allow-docs`.
- **A real tokenizer budget** — deferred; a character budget is a good-enough MVP proxy.

## Consequences

- A regenerable, low-token context pack exists for agents/humans; it is local/gitignored by default.
- Human-curated decision records remain the source-of-truth; the pack never replaces them.
- New module + tests; no provider behavior change, no new dependencies.
- Token-accurate budgeting, semantic retrieval, and MCP exposure remain follow-up work.

## Next actions

- Follow-up: a token-aware budget; optional MCP read-only export of the pack; rolling summaries.
- Use `vibe context build` before feeding an agent project context; keep the output gitignored.

## Related links

- Related: [decision CLI skeleton](./2026-06-30-decision-cli-skeleton.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md),
  [redaction guard](./2026-06-30-redaction-guard.md)
- Roadmap: [track-based roadmap](../plans/track-based-roadmap.md)
