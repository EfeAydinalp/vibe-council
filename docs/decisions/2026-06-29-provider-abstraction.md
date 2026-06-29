---
id: DEC-20260629-provider-abstraction
status: accepted
date: 2026-06-29
tags: [architecture, providers, local-first, v0.2]
related: [DEC-20260629-v0.2-release, DEC-20260629-repo-cleanup-and-provenance]
published: true
---

# Provider abstraction (OpenRouter + local Ollama)

## Context

vibe-council began as a single-provider tool hard-wired to OpenRouter. That tied the
"local-first AI council" promise to one hosted vendor and one API key, undercutting the
local-first story and limiting where a council run could happen.

## Decision

Introduce a minimal **provider seam** under the council and ship multi-provider support in
v0.2.0:

- **OpenRouter remains the default** provider; its behavior is unchanged (no regression).
- Add a small `Provider` abstraction (`ChatRequest` / `ChatResult`) with an OpenRouter
  adapter, selectable via `VIBE_PROVIDER` (default `openrouter`).
- Add a **local Ollama provider** (`VIBE_PROVIDER=ollama`): talks to a local server,
  no API key, **loopback-only `OLLAMA_HOST`** (SSRF-safe), and never fabricates a cost.
- Add **`VIBE_OLLAMA_MODEL`** so a preset's OpenRouter-style model IDs can map to a local
  model the user has pulled, without redesigning presets.
- Add **`vibe doctor`** for provider diagnostics that spends **no tokens** (supports
  `--offline`).
- Add **provider-aware cost messaging**: `--usage` / `--max-cost` name the active provider
  and are honest when a provider reports no cost.

## Rationale

- **Local-first credibility** — a council you can run entirely on your machine with Ollama.
- **Provider flexibility** — break the single-vendor lock-in behind a thin seam.
- **No OpenRouter behavior regression** — the default path is byte-for-byte the prior path.

## Alternatives considered

- **Full provider-plugin framework now** — rejected as over-engineering for v0.2; the
  minimal `ChatRequest`/`ChatResult` seam is enough.
- **Per-provider preset configs** — deferred; presets still carry OpenRouter-style model
  IDs and Ollama users override with `VIBE_OLLAMA_MODEL` for now.
- **Stay single-provider** — rejected; it blocks the local-first positioning.

## Consequences

- **Ollama users must set `VIBE_OLLAMA_MODEL`** — presets carry OpenRouter-style model IDs;
  provider-specific preset config is future work.
- **Local providers report no billing cost**, so `--max-cost` cannot be enforced for Ollama
  runs (cost is never fabricated).
- The provider seam is now a stable extension point, but adding providers is **out of scope**
  unless a task explicitly asks.

## Next actions

- Keep OpenRouter the default for real runs; document Ollama setup clearly.
- Treat provider-specific preset config as future work, not v0.2.x.

## Related links

- Release notes: [v0.2.0](../releases/v0.2.0.md)
- Provider-aware cost messaging PR: <https://github.com/EfeAydinalp/vibe-council/pull/30>
- Related: [v0.2.0 release decision](./2026-06-29-v0.2-release.md)
