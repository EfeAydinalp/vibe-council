# Plan: linked decision-memory / knowledge-graph layer

A **strategic product-direction review**, not an implementation plan. `vibe-council
v0.2.0` is released (provider abstraction, OpenRouter + local Ollama, `vibe doctor`,
provider-aware cost). This doc asks: should vibe-council grow from today's flat decision
memory into a **local-first linked decision notebook / knowledge graph** — a markdown-first
web of decisions, alternatives, PRs, plans, and agent context — and if so, how, in what
order, and where's the commit boundary?

**No code is written in this task; no dependencies; no vector DB; no raw `.council/`
outputs committed.** Council runs use **`review --preset balanced`** (then optionally
`full` only if the review says it's worth it), always `--usage`; raw `.council/` output
stays local.

Review date: **2026-06-29**.

---

## Current decision-memory state (verified from code)

vibe-council **already has a decision-memory primitive** — this plan extends it, it
doesn't start from zero:

- **`vibe extract --save`** produces a `DecisionRecord` (`backend/decision_memory.py`):
  `decision`, `rationale`, `risks[]`, `open_questions[]`, `next_actions[]`, `tags[]`,
  `timestamp`. Rendered to **JSON + Markdown**.
- **Storage:** per-project, under **gitignored `.council/decisions/`**, plus an
  **append-only `.council/decisions/index.jsonl`** (id, timestamp, title, project,
  source_file, tags, paths).
- **CLI:** `vibe decisions list / search / context` — **plain string** search, no model
  call, no key. (`backend/project_workspace.py` owns the workspace + index.)
- **Boundary today:** everything decision-memory is **local-only / gitignored**. Nothing
  is committed; nothing is linked; search is substring.

So the gaps the "knowledge graph" idea targets are: (1) records are **not curated or
committed** (so they can't be shared, reviewed, or fed to agents from the repo), (2) there
are **no links** between records/PRs/plans, and (3) there's **no agent-facing context
export**.

---

## Proposed product vision

A **local-first, markdown-first linked decision notebook**: a small, durable web of
**curated** records — council outputs distilled into decisions, with their alternatives,
consequences, and links to the PRs/plans/releases that enacted them — usable by humans
*and* by agents (Claude Code) as project memory. Lightweight structure (frontmatter +
backlinks + tags + a JSON index) **before** any embeddings/vector search; read-only agent
context **before** any MCP write path. It must not require cloud, must not bloat the repo
with raw model output, and must not pull focus from v0.2.x stability.

The system is meant to capture, and link: council outputs, extracted decisions, Claude/
agent notes, PR decisions, planning docs, release decisions, **rejected alternatives**,
future todo/context, and strategy discussions.

---

## The committed-vs-local boundary (the central design question)

Two stores with **different commit policies** — getting this line right is the whole game:

| Layer | Location | Committed? | Content |
|-------|----------|:---:|---------|
| **Raw council output** | `.council/reviews|runs|stages|usage` | **No (gitignored)** | Full model prompts/outputs — can contain sensitive content |
| **Local decision records** (today) | `.council/decisions/` + `index.jsonl` | **No (gitignored)** | Auto-extracted JSON/MD per project |
| **Curated decision records** (new) | **`docs/decisions/`** | **Yes (committed)** | Human-reviewed, redacted markdown ADRs with frontmatter/links |
| **Committed index** (new) | `docs/decisions/index.json` | **Yes** | Fast list/search of the *curated* set |
| **Agent brief** (new) | `.council/agent-brief.md` (default) | **No by default** | Generated context; opt-in to commit a redacted version |

**Rule:** raw `.council/` outputs are **never** committed by default. Only **curated**
records — explicitly promoted by a human/`--save`-to-docs step — land in `docs/decisions/`.
This keeps the repo a clean, shareable design record while the messy/sensitive material
stays local. (This is the same "plan docs committed, raw reviews gitignored" split the
project already uses for `docs/plans/` vs `.council/reviews/`.)

---

## A. Markdown decision records (frontmatter schema)

`docs/decisions/YYYY-MM-DD-short-title.md` — an ADR-style record:

```yaml
---
id: 2026-06-29-linked-decision-memory     # stable slug, == filename stem
status: proposed                          # proposed | accepted | superseded | rejected
date: 2026-06-29
topic: knowledge-graph                    # coarse area for grouping
linked_prs: [ "#32" ]                     # PRs that enacted/relate to it
linked_release: ""                        # e.g. v0.3.0 (when shipped)
related_council_run: ""                   # opaque local ref, NOT a path into .council/
related: []                               # other decision ids
supersedes: []                            # decision ids this replaces
depends_on: []                            # decision ids that must hold first
blocks: []                                # decision ids this gates
source_prs: []
source_docs: [ "docs/plans/linked-decision-memory-strategy.md" ]
tags: [strategy, memory]
---
```

Body sections (stable headings so they're parseable and agent-friendly): **Decision** ·
**Context** · **Alternatives considered** (incl. *rejected* ones + why) · **Consequences**
· **Next actions**. This is a superset of today's `DecisionRecord`, so `vibe extract` can
emit a *draft* of this format that a human curates before committing.

## B. Local index

A generated index for fast list/search without parsing every file:

- **Committed:** `docs/decisions/index.json` — derived from the committed records'
  frontmatter (id, status, date, topic, tags, links). Regenerable (a build artifact that
  happens to be committed for convenience); CI can verify it's in sync.
- **Local (today, keep):** `.council/decisions/index.jsonl` stays as the per-project,
  gitignored auto-extract log. The two indexes serve different sets (raw-local vs curated-
  committed) and shouldn't be merged.

## C. Backlinks and topic graph

The graph is just frontmatter link fields resolved by id (no DB): `related`,
`supersedes`, `depends_on`, `blocks`, `source_prs`, `source_docs`. A small resolver can
compute **backlinks** (who points at me) and render a topic/status view. Markdown-native,
diff-friendly, greppable. No embeddings needed to be useful.

## D. CLI command ideas

Extend the existing `vibe decisions` surface incrementally:

- `vibe decisions list [--status --topic --tag]` — over the curated set (and/or local).
- `vibe decisions search <q>` — string/tag search first (today's behavior, widened).
- `vibe decisions show <id>` — render a record + its resolved backlinks.
- `vibe decisions new` / `--from-extract` — scaffold a `docs/decisions/` record (draft
  for human curation; **does not auto-commit**).
- `vibe decisions link <id> --related/--supersedes/...` — edit link frontmatter safely.
- `vibe decisions index` — (re)generate `docs/decisions/index.json`.
- *(Later)* `vibe context build` / `vibe context export --for claude` — see E.

Keep stdout clean/machine-readable; never print secrets; no model call for list/search/
show/index (only `new --from-extract` may use a model, like `extract` does today).

## E. Agent / Claude context export

`vibe context export --for claude` → a concise **`agent-brief.md`** (default under
`.council/`, **not committed** unless explicitly opted-in + redacted): active/accepted
decisions, current constraints, recent PRs, **rejected paths** (so agents don't re-propose
them), and open next-actions. Built **only** from *curated committed records* (never from
raw `.council/` outputs), capped in size, with a redaction pass. This is the highest-
leverage payoff: durable, low-token project memory for Claude Code and future agents.

## F. MCP connection (later)

Expose decisions/context to MCP-speaking agents **read-only first** (list/show/export);
any **write** (create/link/accept a decision) requires explicit human approval. Rides on
the v0.2.1 experimental MCP work — do not build a bespoke server here. Strictly downstream
of E working locally.

## G. Vector / embedding search (later, optional)

Only after frontmatter/index/string-search proves insufficient. **Local embeddings first**
(no cloud, no new hard dependency in core), as an *optional* extra — the markdown + index
must remain fully functional without it. Most "find related decisions" needs are met by
tags + links + grep long before embeddings earn their complexity.

## Privacy / security risks

- **Leaking raw model output / secrets into the repo** — the #1 risk. Mitigation: only
  *curated* records are committed; a redaction step on promote/export; never read raw
  `.council/` into committed artifacts or the agent brief; reuse the demo redaction
  discipline. CI guard that `docs/decisions/` contains no `.council/` paths or key-shaped
  strings.
- **Agent-brief over-sharing** — could concentrate sensitive context in one file.
  Mitigation: local-by-default, size cap, explicit opt-in + redaction to commit.
- **Index drift / contradiction** — committed index out of sync with records. Mitigation:
  regenerable + CI check.
- **Provenance/links rot** — referenced PR/doc/decision ids go stale. Mitigation: a
  `vibe decisions doctor`-style lint (later) flagging dangling links.
- **Repo bloat / noise** — committing low-value auto-extracts. Mitigation: curation gate;
  only human-promoted records are committed.

## Phased roadmap

- **Phase 0 (now):** this strategy doc + decision. No code.
- **Phase 1 — markdown + curation (v0.2.x docs / small):** adopt the `docs/decisions/`
  ADR format + frontmatter **as a documentation convention** (write a couple by hand),
  define the committed-vs-local boundary, add a CI redaction/secret guard for
  `docs/decisions/`. *No new runtime code required* — pure convention + guard.
- **Phase 2 — tooling (v0.3.0):** `vibe decisions show/new --from-extract/link/index` +
  committed `index.json`; backlink resolver. Extends existing CLI; stdlib-only.
- **Phase 3 — agent context (v0.3.x):** `vibe context export --for claude` → local
  `agent-brief.md` from curated records, with redaction + size cap.
- **Phase 4 — MCP (later):** read-only decision/context exposure; writes behind approval.
  Gated on v0.2.1 MCP.
- **Phase 5 — vector search (later, optional):** local embeddings, only if search demand
  proves it; never a hard core dependency.

## Proposed stance (before council)

1. **Build a lightweight markdown/index layer first** — frontmatter + backlinks + tags +
   a JSON index. Backlinks/tags/frontmatter **before** embeddings.
2. **Keep raw council outputs local/gitignored** — `.council/` is never committed by
   default.
3. **Commit only curated decision records** in `docs/decisions/` — human-promoted,
   redacted; the auto-extract local set stays in `.council/decisions/`.
4. **Delay vector search** until list/search/export proves useful with plain text + links.
5. **Delay MCP write integration** until read-only local context export works; MCP rides
   on the existing v0.2.1 experimental track, read-only first.
6. **Target this as v0.2.1/v0.3 planning, not immediate hotfix work** — Phase 1 can be a
   docs convention now; Phase 2 tooling is v0.3.0. Don't bloat v0.2.x.

## Main question for the council

> **Is a local-first, markdown-first linked decision notebook the right evolution of
> vibe-council's memory — and is the phased "convention → CLI tooling → agent context →
> (later) MCP/vectors" sequence, with raw outputs gitignored and only curated records
> committed, the right shape and order?**

Sub-questions:
- Is this strategically valuable, or scope creep on a young CLI?
- Minimum useful version? Should records live in `docs/decisions/`, `.council/decisions/`,
  or both — and what's committed vs gitignored?
- How do we avoid repo bloat with raw model output and preserve useful history without
  leaking private data?
- What is v0.2.1 vs v0.3? Should vector search wait? How does this relate to MCP / a future
  app/TUI?
- Biggest risks we're underweighting?

## Council guidance summary

Ran `review --preset balanced` (2026-06-29). `full` was **not** run: the review was
decisive and complete, so a `full` pass wasn't worth the extra spend (cost discipline).
Output is advice to filter — the section below is the **human-curated** reading. Verdict:
**Conditional YES — radically simplify, validate value before building infrastructure, and
invert the phases.**

### Is this strategically valuable?
**Yes, with discipline.** The vision (local-first, markdown-native, linked, raw-outputs-
gitignored, only-curated-committed, no cloud) was called "fundamentally sound" and the
boundaries "exemplary." The danger is **strategic drift** — turning a code-review CLI into a
half-built knowledge-graph product during the fragile v0.2.x adoption window. Keep it small
and downstream of core stability.

### Strongest warning (adopt)
**"No one will curate."** The whole plan hinges on humans doing non-code work (extract →
edit → redact → commit) with no immediate payoff. If optional, it won't happen; if
mandatory, it's resented. **Mitigation I adopt:** prove a *killer feature* (the agent brief
measurably helps Claude Code) before building tooling, and dogfood it in *this* repo as the
forcing function. If our own team won't keep it up for a month, that's the kill signal.

### Minimum useful version (adopt the inversion)
**Validate value first, build infra second.** Hand-write 5–10 real decision records for
vibe-council itself (e.g. "Why OpenRouter?", "Why gitignore `.council/`?", this decision),
hand-assemble an `agent-brief.md`, and check it *measurably* improves Claude Code's answers
on architecture questions. **Only if that succeeds** build tooling. The MVP is a
**documentation convention + a couple of real records + a manual brief** — not a CLI.

### docs/decisions/ vs .council/decisions/ vs both? (curated divergence)
The council strongly pushed **one store with a `published: bool` frontmatter flag** (commit
the `published: true` ones) over my dual-store design, to kill the "which is canonical?"
ambiguity. **I partially adopt:** use a **single canonical record + an explicit `published`
flag**, but when published, the curated/redacted markdown still **lands in committed
`docs/decisions/`** (the project's shareable design record, parallel to `docs/plans/`). So:
one authoring mechanism, one flag, two *rendered* locations — not two competing stores with
an undefined promotion path. This keeps the committed ADR set (which the council itself
liked) without the dual-index drift it warned about.

### What's committed vs gitignored?
- **Committed:** only **curated, redacted** decision records (`docs/decisions/*.md`).
- **Gitignored (unchanged):** all raw `.council/` (reviews/runs/stages/usage), the auto-
  extract local set, and the agent brief by default.
- **Adopt the council's index call:** **do NOT commit `index.json`** — generate it
  on-demand (or cache under `.council/`) to avoid guaranteed sync drift + CI friction.

### Avoiding repo bloat / preserving history without leaking
- **Curation gate:** only human-promoted records are committed (no auto-extract dumps).
- **Redaction is under-specified — fix it:** adopt a **real secrets scanner (gitleaks/
  trufflehog) in CI**, not just a regex, plus a concrete redaction checklist; the agent
  brief is a **concentration risk** (local-by-default, size cap, opt-in to commit).
- **Schema: radically simplify** — start with **5 fields** (`id`, `status`, `date`, `tags`,
  `related`); defer `supersedes/depends_on/blocks/linked_prs/...` until real demand. (My
  original 13-field schema was over-specified for v1 — adopt the trim.)

### v0.2.1 vs v0.3?
- **v0.2.x:** **nothing but a docs convention + dogfooded records + manual brief
  experiment.** No new runtime code. (My original "Phase 1 as convention now" stands; the
  council merged convention+tooling but I keep the *validation* in v0.2.x precisely because
  the curation hypothesis is unproven.)
- **v0.3.0:** *only if validation passes* — ship convention **and** tooling together (the
  council was right that convention-without-tooling under-delivers): `decisions
  new/show/index`, an interactive **`vibe decisions promote`** (copy→edit→lint→commit-
  reminder in one guided command), and a **`decisions lint`** to prevent decay.
- **Later:** agent context export (v0.3.x), then MCP read-only, then (optional) vectors.

### Should vector search wait? (yes — with one tweak)
**Yes**, defer full vector integration. But adopt the council's nuance: a **time-boxed
1-day local-embeddings prototype** during v0.3 to *test* whether semantic search materially
changes the value — cheap signal, no commitment, never a hard core dependency.

### Relation to MCP and a future app/TUI
MCP is the natural agent surface but **read-only first**, **writes behind approval**, and
**gated on the agent-brief proving useful** — do not start MCP write integration until the
local brief earns it. A future app/TUI would *consume* the same committed records/index;
this layer is the data model under it, not a reason to build UI now.

### Biggest risks (curated)
1. **Curation never happens** (the existential one) → validate + dogfood + killer-feature.
2. **Strategic drift** off core review UX during v0.2.x → keep this downstream/optional.
3. **Leakage** via curated prose/frontmatter/brief → real scanner + redaction checklist +
   local-by-default brief.
4. **Dual-store / index-sync footguns** → single record + `published` flag, don't commit
   the index.
5. **Schema over-engineering** locking in complexity pre-validation → 5-field v1.

### Recommended next 3 actions
1. **Dogfood, don't build:** hand-author ~6 `docs/decisions/` records for vibe-council's
   own past calls + a manual `agent-brief.md`; run a quick A/B on whether it improves Claude
   Code's answers about this repo. (No code.)
2. **If it helps,** scope a v0.3.0 PR for the **minimal** version: 5-field schema, single
   record + `published` flag, on-demand index, `vibe decisions show/new/promote/lint`, and a
   **CI secrets/redaction guard** for `docs/decisions/`.
3. **Write the kill criteria up front:** if our own team doesn't sustain records for ~1
   month, or the brief doesn't measurably help, **stop** — don't proceed to MCP/vectors.

### Where I diverge from the council (curated, not blind)
- Keep **committed `docs/decisions/`** (the council liked the curated committed set) but
  reconcile its "single store" concern via **one record + `published` flag → rendered to the
  committed location**, not two competing stores.
- I keep the value-validation in **v0.2.x as docs-only** rather than the council's
  "ship convention+tooling together in v0.3" — because building tooling before the curation
  hypothesis is proven is exactly the risk it flagged. Tooling waits for the green light.
- Treat the alternatives (SQLite source-of-truth, decisions-as-PR-metadata, ADR tooling like
  Log4brains/adr-tools, graphviz view) as **inputs to study**, not commitments — note them,
  don't adopt now.

## Constraints

- Strategy/planning only. **No** implementation, no code changes, no dependencies, no
  vector DB, no raw `.council/` outputs committed.
- Council runs use **`balanced`** only (no premium), always `--usage`; `review` first,
  `full` only if the review says it's worth it and cost is acceptable.
- Raw `.council/` outputs stay local and are **never** committed. No PR from this task.
