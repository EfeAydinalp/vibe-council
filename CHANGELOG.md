# Changelog

All notable changes to **vibe-council** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Status:** `0.1.0` is the first public release. The repo reports `0.1.0`
> (`backend/__init__.py`). The `v0.1.0` git tag + GitHub Release are cut by a maintainer
> right after the release PR merges — see [`docs/release-checklist.md`](docs/release-checklist.md).

## [Unreleased]

### Removed

- **Unused upstream web UI subsystem** — the legacy React + Vite `frontend/`, the
  `backend/main.py` FastAPI server and `backend/storage.py` conversation storage, plus the
  related upstream `start.sh`, root `main.py`, and root `header.jpg`. The product is the
  local-first CLI and none of these were used by it. No dependency cleanup in this change
  (FastAPI/Uvicorn remain declared); a future app/TUI/web surface should be rebuilt
  intentionally rather than carried over from upstream.

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

