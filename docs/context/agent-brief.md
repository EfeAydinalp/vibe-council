# vibe-council — agent brief (curated dogfood seed)

A concise, **curated and redacted** project brief for Claude Code and future agents. This is a
hand-written **dogfood seed**, not generated output — it distills the committed decision records
under [`docs/decisions/`](../decisions/). Future *generated* agent briefs should default to a
local, gitignored location and be committed only by explicit, redacted opt-in.

_Last curated: 2026-06-30 (vibe-council 0.3.1)._

## Project identity

**vibe-council** is a local-first AI "council" CLI: multiple LLMs collaboratively review or
answer, with anonymized peer ranking, decision memory, and cost/safety guardrails. The product
is the command-line interface; everything runs on the user's machine with their own API key.
Forked from and crediting [`karpathy/llm-council`](https://github.com/karpathy/llm-council) —
**preserve that attribution**.

## Current released state

- **v0.2.0** (tagged) — the multi-provider milestone (provider abstraction + local Ollama +
  `vibe doctor`). See [v0.2.0 release decision](../decisions/2026-06-29-v0.2-release.md).
- **v0.3.0** (released) — **local-first decision memory + curated project context**. The v0.3 loop
  exists **end-to-end**: extract (`decisions new --from-run`) → review/redact → `decisions promote`
  → `decisions lint` → `context build` → `context check` → `context export claude-code`, plus
  `vibe lint --redaction` and `operator status`. All deterministic and local-first; **generated
  context packs/exports stay local/gitignored**. See [v0.3.0 release notes](../releases/v0.3.0.md).
- **v0.3.1** (released) — **dogfood hardening** of that loop, **no new command surface**:
  `decisions promote` rejects placeholder-only drafts and writes curated `YYYY-MM-DD-slug.md`
  records; `decisions new --from-run` maps review sections into the draft; `context check` passes
  **21/21** on the real repo (explicit human-review signal in packs; default char budget 14000);
  plus a CLI UX pass. See [v0.3.1 release notes](../releases/v0.3.1.md). No commercial-clearance
  claim — license/provenance remains "Question 0".
- **v0.4** (planning) — a **read-only** MCP / Claude Code workflow: expose curated decisions, status,
  rejected alternatives, constraints, and the generated context pack to Claude Code / local agents
  **with no write/action authority** (no promotion, file, git, shell, or remote-approval tools).
  Curated docs stay source-of-truth; generated/local/private artifacts excluded by default. See
  [v0.4 read-only MCP plan](../plans/v0.4-read-only-mcp-workflow.md) and
  [v0.4 scope decision](../decisions/2026-07-01-v0.4-read-only-mcp-scope.md).

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
- The context-pack budget is a **naive char budget** (default 14000); trim order now keeps the
  rejected-alternatives index + human-review signal stable (a **token-aware budget** is deferred).
  See [budget headroom decision](../decisions/2026-07-01-context-pack-budget-headroom.md).
- MCP (read-only, planned for v0.4), personas/advisors, app/TUI, and community features are
  **future work**.

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
4. **Roadmap:** direction is organized as parallel tracks (core/release, decision-memory + context
   pack, project memory, MCP/Remote-Control, operator inbox, packs, orchestration, commercial,
   retrieval, security) with prerequisite-driven version sections. See
   [track-based roadmap](../plans/track-based-roadmap.md).
5. **Project memory (dogfood):** public-safe project-memory seed at
   [`docs/context/project/README.md`](project/README.md) and [`STATUS.md`](project/STATUS.md).
6. **Operator loop:** an approval/status inbox is planned as a minimal local-first layer — not a
   dashboard or custom mobile transport. See
   [operator control loop spec](../plans/operator-control-loop-and-approval-inbox.md).
7. **Redaction guard:** `vibe lint --redaction` scans public docs for leaks (secrets, local paths,
   raw `.council/` artifacts) before promote/commit/export. See [redaction policy](../redaction-policy.md).
8. **License/provenance** remains **Question 0** before serious commercialization; public/local-first
   development continues while the review is clarified. See
   [license & provenance resolution](../plans/license-and-provenance-resolution.md).
9. **Decision CLI:** `vibe decisions list/show/new/lint/promote` operate on curated `docs/decisions/`
   (source of truth); `search/context` stay on the local `.council/` index. `new` is template-only;
   `new --from-run <review>` extracts a **local** draft (gitignored `.council/decisions/drafts/`, no
   LLM, never under `docs/decisions/`); `promote <draft>` validates (frontmatter/headings/redaction) +
   writes into `docs/decisions/` with no auto-stage/commit; `lint` reuses the redaction guard.
10. **Context pack:** `vibe context build` deterministically assembles a compact pack from
    `docs/decisions/` + STATUS (metadata, identity, status, pinned/recent decisions, indexes,
    constraints). No LLM/vector/MCP; runs redaction (blocks on critical); writes gitignored
    `.council/context/pack-latest.md` by default (refuses `docs/` unless `--allow-docs`).
    `vibe context check` is a deterministic quality harness (not an LLM eval): required sections/
    constraints + advisory facts/signals + redaction, scored `passed/total` (`--strict`/`--json`/`--min-score`).
11. **Operator status:** `vibe operator status` (+ `set`/`clear`) is a tiny local-first status surface
    — one gitignored `.council/operator/status.json` (state/message/next_action/severity). Not an
    event log, dashboard, notifications, or remote transport; Remote-Control-friendly, no model calls.
12. **Claude Code export:** `vibe context export claude-code` wraps the pack (usage note + paste-able
    operator instruction + pack body + next commands) into gitignored
    `.council/context/claude-code-context.md`. Gates on check + redaction; refuses `docs/` unless
    `--allow-docs`; never modifies `CLAUDE.md`; no MCP/Remote-Control integration yet.
