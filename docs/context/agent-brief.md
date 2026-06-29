# vibe-council — agent brief (curated dogfood seed)

A concise, **curated and redacted** project brief for Claude Code and future agents. This is a
hand-written **dogfood seed**, not generated output — it distills the committed decision records
under [`docs/decisions/`](../decisions/). Future *generated* agent briefs should default to a
local, gitignored location and be committed only by explicit, redacted opt-in.

_Last curated: 2026-06-29 (vibe-council 0.2.0)._

## Project identity

**vibe-council** is a local-first AI "council" CLI: multiple LLMs collaboratively review or
answer, with anonymized peer ranking, decision memory, and cost/safety guardrails. The product
is the command-line interface; everything runs on the user's machine with their own API key.
Forked from and crediting [`karpathy/llm-council`](https://github.com/karpathy/llm-council) —
**preserve that attribution**.

## Current released state

- **v0.2.0** — the multi-provider milestone. 118 tests passing; default OpenRouter path
  unchanged. See [v0.2.0 release decision](../decisions/2026-06-29-v0.2-release.md) and
  [release notes](../releases/v0.2.0.md).

## Provider architecture

- A minimal `Provider` seam (`ChatRequest` / `ChatResult`) sits under the council.
- **OpenRouter** is the default (`VIBE_PROVIDER=openrouter`).
- **Local Ollama** (`VIBE_PROVIDER=ollama`): no API key, loopback-only host, never fabricates a
  cost; set `VIBE_OLLAMA_MODEL` to a model you've pulled.
- **`vibe doctor`** runs provider diagnostics with no inference (`--offline` supported).
- Details: [provider-abstraction decision](../decisions/2026-06-29-provider-abstraction.md).

## Local-first / privacy rules

- Nothing is sent anywhere except the model calls the user explicitly triggers.
- **The API key is never printed.** Only `.env.example` is tracked.
- Keep stdout machine-readable; diagnostics/usage go to stderr.
- **Never commit** raw council outputs, secrets, `.env`, or local runtime state. Raw `.council/`
  runtime workspace stays **gitignored**.

## Decision-memory boundary

- **Committed:** curated, redacted Markdown records in [`docs/decisions/`](../decisions/) and
  this brief (`docs/context/agent-brief.md`).
- **Local / gitignored:** auto-extracted records and raw council output stay on the machine.
- **No committed generated index** yet; **no vector DB**; portable Markdown links are canonical
  (Obsidian-openable, but **Obsidian is not a dependency**; never commit `.obsidian/`).
- Rationale: [linked decision-memory decision](../decisions/2026-06-29-linked-decision-memory.md).

## Current known limitations

- Ollama users must set `VIBE_OLLAMA_MODEL` (presets carry OpenRouter-style model IDs).
- Local Ollama reports no billing cost, so `--max-cost` cannot be enforced for it.
- `full` mode had a None-content ranking fragility (fixed in v0.2.0); prefer `review` for
  plan/diff critique.
- License/provenance cleanup is **ongoing** — no `LICENSE` added yet.
- MCP, personas/advisors, app/TUI, and community features are **future work**.

## Accepted decisions (curated set)

- [Provider abstraction (OpenRouter + Ollama)](../decisions/2026-06-29-provider-abstraction.md)
- [Repo cleanup & provenance stance](../decisions/2026-06-29-repo-cleanup-and-provenance.md)
- [Publish v0.2.0](../decisions/2026-06-29-v0.2-release.md)
- [Dogfood linked decision memory](../decisions/2026-06-29-linked-decision-memory.md)
- [External tools & Obsidian research (borrow concepts, not code)](../decisions/2026-06-29-external-tools-and-obsidian-research.md)

## Proposed commercial hypothesis (not decided)

- [Open-core commercial hypothesis](../decisions/2026-06-29-open-core-commercial-hypothesis.md)
  — **proposed**, pending the commercial feasibility review: keep a public local-first core;
  consider a *separate private* hosted/team/sync layer only if demand is validated; prefer
  BYOK + subscription/support/team-sync over a prepaid wallet; self-hosted inference is later.
- **Commercial direction:** public-core/local-first first; detailed hosted/billing strategy remains
  private until validated. See [open-core commercial direction](../decisions/2026-06-29-open-core-commercial-direction.md).

## What not to touch without explicit scope

- Do not start provider-abstraction-2, app/TUI/web, MCP, persona/advisor, or community work.
- Do not add or change a `LICENSE`, or weaken upstream attribution/provenance.
- Do not commit `.council/`, `data/`, `.env`, `.venv/`, raw outputs, or `.obsidian/`.
- Do not use `premium`/`full` for real runs unless asked; default preset is `balanced`.
- No history rewrite, force-push, or merge unless explicitly requested.

## Next recommended work

1. **Dogfood** this decision-memory batch for ~1 month; check whether this brief measurably
   improves agent answers about the repo (the kill/keep signal).
2. Run the **commercial feasibility review** using the research audit + the open-core hypothesis.
3. Only if dogfooding proves value: scope a **minimal** v0.3 tooling PR with a CI secrets/redaction
   guard — not before. Keep vector/hybrid retrieval and MCP deferred.
