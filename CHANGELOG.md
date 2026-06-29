# Changelog

All notable changes to **vibe-council** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Status:** `0.2.0` is the current release. The repo reports `0.2.0`
> (`backend/__init__.py`). The `v0.2.0` git tag + GitHub Release are cut by a maintainer
> right after the release PR merges — see [`docs/release-checklist.md`](docs/release-checklist.md).

## [Unreleased]

_Nothing yet. Post-0.2.0 changes will be listed here as normal Keep-a-Changelog deltas
(Added / Changed / Fixed / Removed)._

## [0.2.0] - 2026-06-29

The **multi-provider** release: break the single-provider lock-in with a provider
abstraction, add a local **Ollama** provider, and ship `vibe doctor` diagnostics — all
while OpenRouter remains the default and existing behavior is unchanged.

### Added

- **Provider abstraction** — a minimal `Provider` seam with `ChatRequest` / `ChatResult`
  and an **OpenRouter adapter**; legacy helper functions delegate to it with no behavior
  change for OpenRouter users.
- **Provider selection** via `VIBE_PROVIDER`, defaulting to `openrouter`; unsupported
  values fail clearly before any model call.
- **Local Ollama provider** via `VIBE_PROVIDER=ollama` — non-streaming `/api/chat`,
  requires no API key, loopback-only `OLLAMA_HOST` validation (SSRF-safe), and never
  fabricates a dollar cost.
- **`VIBE_OLLAMA_MODEL`** — map the existing preset's OpenRouter-style model IDs to a
  local Ollama model name you've pulled, without redesigning presets.
- **`vibe doctor`** — provider diagnostics (key presence/placeholder, OpenRouter
  model-list reachability, Ollama host validation + `/api/tags` reachability + local model
  list + `VIBE_OLLAMA_MODEL` availability). Runs **no inference** and spends no tokens;
  supports `--offline`.
- **Provider-aware usage/cost messaging** — `--usage` and `--max-cost` now name the active
  provider and state honestly when a provider does not report cost.

### Fixed

- **`full` mode** no longer crashes when a ranking model returns `None` or empty content
  (`parse_ranking_from_text` tolerates missing/empty/whitespace/unparsable output).

### Removed

- **Unused upstream web UI subsystem** — the legacy React + Vite `frontend/`, the
  `backend/main.py` FastAPI server and `backend/storage.py` conversation storage, plus the
  related upstream `start.sh`, root `main.py`, and root `header.jpg` — and the now-unused
  **FastAPI/Uvicorn** dependencies. The product is the local-first CLI; a future app/TUI/web
  surface should be rebuilt intentionally rather than carried over from upstream.

### Changed

- **Project identity** metadata renamed from `llm-council` to `vibe-council`
  (`pyproject.toml`, `uv.lock`, `CLAUDE.md`).
- **Author identity** normalized with a `.mailmap` (display-only; no history rewrite).

### Known limitations

- **Ollama users should set `VIBE_OLLAMA_MODEL`** — presets still carry OpenRouter-style
  model IDs; provider-specific preset config is future work.
- **Local Ollama does not report billing cost**, so `--max-cost` cannot be enforced for
  Ollama runs (cost is never fabricated).
- **MCP, personas/advisors, app/TUI, and community** features are still future work.
- **License/provenance cleanup is ongoing** — parts of the backend still descend from the
  unlicensed upstream `karpathy/llm-council`; no `LICENSE` is added yet.

## [0.1.0] - 2026-06-28

First public release. Because this is the initial cut, the notes below are a
**feature inventory** of what the fork adds on top of upstream
[`karpathy/llm-council`](https://github.com/karpathy/llm-council) (the council concept:
query several models, peer-review/rank, chairman synthesis), not a since-last-tag delta.

### Added

- **Workflow modes** — `extract`, `mini` (default), `review`, and `full`. `full` is the
  only mode that uses anonymized peer ranking; `review` is the everyday plan/diff gate.
- **Presets** — `cheap`, `balanced` (default), and `premium`, each mapping council /
  chairman / extract roles to OpenRouter model IDs (env-overridable).
- **CLI** — run any mode via `python -m backend.cli`, plus a global **`vibe`** command:
  `--version`, `vibe status`, `vibe review`, `vibe diff`, `vibe extract`, `vibe mini`,
  `vibe full`, `vibe models`, `vibe presets`, `vibe last`, `vibe guide`, `vibe init`,
  `vibe projects`. Output goes to stdout; progress/usage/guard messages to stderr; the
  API key is never printed. Dedicated exit codes (`0`–`7`) for scripts and agents.
- **`.council/` workspace** — a project-local folder (`reviews/`, `diffs/`,
  `decisions/`, `runs/`, `stages/`, `usage/`, `locks/`, `config.json`) created when
  `vibe` runs inside a project, and auto-added to that project's `.gitignore`.
- **Decision memory** — `vibe extract --save` writes a structured decision as JSON +
  Markdown and appends to `.council/decisions/index.jsonl`; `vibe decisions list`,
  `search`, and `context` read it back. These commands call **no model** and need
  **no API key**. Search is plain local string matching (no embeddings/SQLite).
- **Guardrails** — premium guard (`--allow-premium`), pre-run token guard
  (`--max-tokens`, hard block before any call), best-effort cost guard (`--max-cost`),
  a loop guard against duplicate/concurrent/too-frequent runs (`--allow-repeat`,
  `--no-loop-guard`), `--usage` (provider-reported tokens/cost), and `--save-stages`.
- **First-run key guard** — a clear message and exit code **7** when
  `OPENROUTER_API_KEY` is missing for a model command, instead of a raw traceback.
- **Tests & CI** — stdlib `unittest` smoke and structural tests, run by GitHub Actions
  on Ubuntu, macOS, and Windows.
- **Cross-platform install** — `scripts/install-vibe.ps1` (Windows) and
  `scripts/install-vibe.sh` (macOS/Linux), with `vibe.ps1` / `vibe.cmd` / `vibe.sh`
  launchers that prefer the repo `.venv` and never print the key.
- **Examples & docs** — `examples/` (sample plans + workflow walkthroughs, readable
  without spending credits), [`docs/agent-integrations.md`](docs/agent-integrations.md),
  and committed plan docs under `docs/plans/`.
- **Demo guide & transcript** — [`docs/demo.md`](docs/demo.md) (safe terminal-recording
  guide) plus a committed, sanitized text walkthrough at
  [`docs/demo-transcript.md`](docs/demo-transcript.md).
- **Privacy / local-first docs** — explicit explanation that artifacts stay local while
  your prompts/files/diffs **are** sent to OpenRouter (not local inference), plus
  bring-your-own-key / cost transparency.
- **Web UI** — the original React + Vite council UI (stage tabs) still runs against the
  FastAPI backend.

### Known limitations

- **OpenRouter-only** — bring-your-own-key; no provider abstraction yet.
- **No Ollama / local inference** — prompts are sent to remote providers.
- **No MCP server** yet.
- **No real demo recording yet** — a sanitized text transcript
  ([`docs/demo-transcript.md`](docs/demo-transcript.md)) ships; an actual asciinema
  cast / GIF remains an approved follow-up.
- **Decision search is plain string matching** — no embeddings or SQLite.

<!-- The [0.1.0] tag link goes live once the maintainer pushes the v0.1.0 tag right
     after this release PR merges (a brief 404 between merge and tag is expected). -->
[Unreleased]: https://github.com/EfeAydinalp/vibe-council/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/EfeAydinalp/vibe-council/releases/tag/v0.1.0

