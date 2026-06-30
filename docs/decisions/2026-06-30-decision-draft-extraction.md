---
id: DEC-20260630-decision-draft-extraction
status: accepted
date: 2026-06-30
tags: [cli, decision-memory, extract, v0.3, safety]
related: [DEC-20260630-decision-promote, DEC-20260630-decision-cli-skeleton, DEC-20260629-linked-decision-memory]
published: true
---

# Decision draft extraction (`vibe decisions new --from-run`)

## Context

`vibe decisions promote` ([decision promote](./2026-06-30-decision-promote.md)) turns a reviewed draft
into a curated record, but drafts still had to be written by hand. The missing step is turning a local
raw council/review output into a **draft** to start from — without LLM calls and without ever
promoting raw output directly into `docs/decisions/`.

## Decision

Add `vibe decisions new --from-run <path>` (in `backend/decisions_docs.py`, stdlib-only, no model/
API/network):

- **Reads** a local `.council/` review/run output or any explicit Markdown/text file (path-only;
  run/review **id lookup is deferred** to a later PR).
- **Deterministic heuristics, no LLM:** source title (first `# ` heading or filename), a verdict-like
  line, and the first few risk / next-action items if the source is sectioned; otherwise a mostly-blank
  template with a source reference and `_TODO_` markers.
- **Writes a draft** with `status: proposed` / `published: false`, the minimal frontmatter, and the
  seven stable headings, plus a source note: *"Draft extracted from local council output; review/redact
  before promotion."*
- **Default output:** gitignored `.council/decisions/drafts/<date>-<slug>.md`; `--out` to override.
- **Safety:** sanitizes the filename, refuses path traversal, **refuses writing under
  `docs/decisions/`**, refuses overwrite without `--force`, supports `--dry-run`. **Never stages/
  commits.** Runs a redaction scan and **reports** masked findings (advisory, since drafts are local);
  `vibe decisions promote` still **blocks** unsafe final promotion.

## Rationale

- Raw `.council/` outputs can usefully **feed** local draft decisions, but they must pass through human
  review/redaction before becoming curated records.
- Keeping extraction deterministic (no LLM) makes it cheap, predictable, and safe.
- Separating *extract a local draft* from *promote a reviewed draft* preserves the curation gate and the
  no-auto-commit posture.

## Alternatives considered

- **Auto-promote extracted content into `docs/decisions/`** — rejected; removes human review and risks
  leaking raw output.
- **LLM-based summarization for extraction** — rejected for this PR; adds cost/nondeterminism/model
  dependency.
- **Archive the raw transcript alongside the draft** — rejected; raw outputs stay in gitignored
  `.council/`, never committed.
- **id-based source lookup now** — deferred; path-only is enough for the MVP.

## Consequences

- A fast path from a local review to an editable draft; promotion stays the only route into curated
  `docs/decisions/`.
- Extracted drafts remain **local/gitignored**; `docs/decisions/*.md` remains the curated
  source-of-truth.
- No auto-promotion, no auto-commit, no raw transcript archival.
- New functions + tests; no provider behavior change, no new dependencies.

## Next actions

- Follow-up: optional run/review **id lookup** for `--from-run`; then the context-pack builder MVP.
- Encourage the flow: `--from-run` → review/redact → `vibe decisions promote` → `git diff` → commit.

## Related links

- Related: [decision promote](./2026-06-30-decision-promote.md),
  [decision CLI skeleton](./2026-06-30-decision-cli-skeleton.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md)
- Policy: [redaction policy](../redaction-policy.md)
