# CLAUDE.md — agent guidance for vibe-council

Notes for coding agents (and humans) working in this repository. Read this before making
changes.

## Project identity

**vibe-council** is a **local-first AI "council" workflow tool**: multiple LLMs
collaboratively review or answer, with anonymized peer ranking, decision memory, and cost/
safety guardrails. The product is the **command-line interface** — everything runs on the
user's machine with their own API key; nothing is sent anywhere except the model calls the
user explicitly triggers.

The project began as a fork of [`karpathy/llm-council`](https://github.com/karpathy/llm-council)
and has diverged substantially. **Preserve that attribution/provenance** — do not remove or
weaken credit to the upstream project.

## What it does (CLI)

- **Modes** (which stages run): `extract`, `mini`, `review`, `full`.
- **Presets** (which models fill the roles): `cheap`, `balanced`, `premium` (premium is
  gated behind `--allow-premium`).
- **Project-local `.council/` workspace** for reviews, decisions, stages, usage, and locks.
- **Decision memory** (`vibe extract --save`, `vibe decisions ...`).
- **Guardrails**: premium guard, pre-run token guard, best-effort cost guard, loop guard,
  first-run API-key guard, `--usage` reporting.

## Important commands

```sh
# Version (global launcher)
scripts\vibe.ps1 --version          # Windows PowerShell
scripts/vibe.sh --version           # macOS / Linux

# Run the CLI directly (from repo root)
python -m backend.cli review --preset balanced --file plan.md --yes --usage
python -m backend.cli extract --preset balanced --file plan.md --save --yes

# Tests (stdlib unittest; use the repo venv interpreter)
.venv\Scripts\python.exe -m unittest discover -s tests -t .     # Windows
.venv/bin/python -m unittest discover -s tests -t .             # POSIX
```

The global `vibe` launcher (`scripts/vibe.ps1` / `.cmd` / `.sh`) wraps `python -m
backend.cli` while remembering the caller's working directory so `.council/` artifacts land
in the caller's project.

## Important directories

- **`backend/`** — the application. CLI entry `cli.py`; council orchestration `council.py`;
  model client `openrouter.py`; config/presets/modes `config.py`; guards `guards.py`;
  decision memory `decision_memory.py`; project workspace `project_workspace.py`. (`main.py`
  + `storage.py` are the older web-UI subsystem; the CLI does not depend on them.)
- **`scripts/`** — global launchers (`vibe.ps1`/`.cmd`/`.sh`) and installers (`install-vibe.*`).
- **`tests/`** — stdlib `unittest` suite; CI runs on Ubuntu/macOS/Windows.
- **`docs/`** — README-adjacent docs, `docs/plans/` (committed plan documents reviewed by
  the council), `docs/releases/`, release checklist, examples guidance.
- **`.council/`** — **local runtime workspace, gitignored.** Per-project reviews, decisions,
  stages, usage, locks. Never committed; can contain prompts/outputs.

## Safety rules (do not violate)

- **Never commit** `.council/`, `data/`, `.env`, `.venv/`, raw council outputs, or any API
  key/secret. Only `.env.example` is tracked. The API key is never printed.
- **Stay in scope.** Do not start provider-abstraction, app/TUI/web, MCP, persona/advisor, or
  community work unless a task explicitly scopes it.
- **Preserve attribution/provenance** to `karpathy/llm-council`. Do not add or change a
  `LICENSE`, and do not alter legal/attribution wording, unless a task explicitly asks.
- **No history rewrite, no force-push, no merge** unless explicitly requested.
- Default council preset for real runs is `balanced`; do not use `premium`/`full` unless
  asked (premium needs `--allow-premium`; see known issues for `full`).

## Known issues

- **`full` mode has a None-content ranking-parser fragility:** if a council model returns
  empty content, `parse_ranking_from_text` (in `backend/council.py`) can raise. Prefer
  `review` for plan/diff critique until this is fixed.
- **Upstream / license / provenance cleanup is in progress.** Several files still descend
  from the unlicensed upstream; see `docs/plans/clean-repo-migration-manifest.md` and
  `docs/plans/rehome-repo-identity-strategy.md`. Licensing is unresolved — do not add a
  `LICENSE` yet.

## Current roadmap

- **v0.2:** provider abstraction + Ollama/local provider (break the single-provider lock-in).
  See `docs/plans/v0.2-provider-abstraction.md`.
- **Later (not now):** `vibe doctor`, experimental MCP, personas/advisors, local app/TUI, and
  community/gallery features — deferred behind v0.2 and explicit demand. Hosted SaaS / credit
  wallet is out of scope (see `docs/plans/hosted-service-strategy.md`).

## Conventions

- Run the backend as `python -m backend.cli` from the repo root; backend modules use relative
  imports.
- Keep stdout clean (machine-readable); diagnostics and usage go to stderr.
- Tests are stdlib-only (`unittest`) — avoid adding new runtime dependencies without a reason.
