# Agent context

Curated, redacted **context for Claude Code and future agents**.

- [`agent-brief.md`](./agent-brief.md) — a hand-written **dogfood seed** distilling the committed
  [decision records](../decisions/). It is curated and redacted, **not** raw or generated output.

**Boundary:** future *generated* agent briefs should default to a **local, gitignored** location
(under `.council/`) and be committed only by explicit, redacted opt-in. Never commit raw council
output, secrets, local absolute paths, or `.obsidian/` state here.
