# vibe-council


![vibe-council](docs/header.jpg)

**vibe-council** is a multi-model decision and review workflow for developers and
AI coding agents. It runs from the **terminal**, and
it helps you review plans, critique diffs, extract structured decisions, and keep
a **project-local decision memory**. It started from
[`karpathy/llm-council`](https://github.com/karpathy/llm-council) — this fork
extends that multi-model "council" idea into a practical local agent/developer
workflow tool with workflow modes, a CLI, project workspaces, decision memory,
and cost/token/loop guardrails.

---

## Why this exists

A single model has blind spots. Before you commit to a plan or merge a diff, it
helps to get a **cheap second opinion from several models at once** — and to keep a
local record of what you decided and why. vibe-council does exactly that from your
terminal: write a plan, get a consolidated multi-model critique, review your diff,
and save a structured decision.

Two things to be clear about up front:

- **The council's output is advice, not authority.** It is a second opinion to
  *filter*, not a gate that decides for you. Apply the findings that improve
  correctness, security, cost, or missing constraints; discard the style nits and
  speculative rewrites. You (or your agent, under your review) own the decision.
- **Local-first means the *artifacts* stay local — not that nothing leaves your
  machine.** Your prompts, files, and diffs (i.e. your code) **are sent to OpenRouter
  and the upstream model providers** to get a response — this is *not* local inference
  like Ollama, and "local-first" does **not** mean "never leaves my network." What it
  *saves* (`.council/`) stays on your machine. See
  [Privacy & local-first](#privacy--local-first).

New here? Skim [Quick demo](#quick-demo) and the
[`examples/`](examples/README.md) folder — short, realistic samples you can read
without spending any credits.

---

## Origin & credit

Based on and inspired by Andrej Karpathy's
[`llm-council`](https://github.com/karpathy/llm-council), which introduced the
core idea: send a query to several LLMs via OpenRouter, have them review/rank each
other's answers, and let a "chairman" model synthesize a final response.

This fork builds on that concept and turns it into a local workflow tool. The
additions here (modes, CLI, `vibe` command, `.council/` workspaces, decision
memory, guardrails) are **not** part of upstream and are **not** maintained by the
original author. Please credit the original project for the council concept.

---

## What this fork adds

- **Modes** — `extract`, `mini`, `review`, `full`
- **Presets** — `cheap`, `balanced`, `premium`
- **CLI bridge** — `python -m backend.cli ...`
- **Global command** — `vibe review --preset balanced --file plan.md`
- **Project workspace** — a local `.council/` folder per project
- **Decision memory** — `vibe decisions list` / `search` / `context`
- **Guardrails** — premium requires `--allow-premium`, plus `--max-tokens`,
  `--max-cost`, a loop guard, `--usage`, and `--save-stages`
- **Claude Code workflow** — plan → review → implement → diff review → extract decision

See [`docs/agent-integrations.md`](docs/agent-integrations.md) for the full agent guide.

---

## Quick start (Windows)

```powershell
git clone https://github.com/EfeAydinalp/vibe-council.git
cd vibe-council
```

Install backend dependencies. This is a [uv](https://docs.astral.sh/uv/) project,
so `uv sync` is the simplest path:

```powershell
uv sync
```

Prefer a plain virtualenv + pip? There is no `requirements.txt`; install the
dependencies declared in `pyproject.toml` directly:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install python-dotenv httpx pydantic
```

Then add your OpenRouter API key:

```powershell
Copy-Item .env.example .env
# edit .env and set OPENROUTER_API_KEY=sk-or-v1-...
```

- Get a key at [openrouter.ai](https://openrouter.ai/) and add credits.
- **Never commit `.env`** — it is gitignored.

You can now use the CLI directly:

```powershell
python -m backend.cli review --preset cheap --prompt "Review this tiny plan."
```

---

## Install the global `vibe` command

The wrappers set `VIBE_CALLER_CWD` so project-local `.council/` artifacts land in
**your** project, prefer the repo's `.venv` interpreter (so a bare `python` pointing
at the wrong environment is never used), and never print the API key. Set
`VIBE_COUNCIL_HOME` to override the repo location if it lives elsewhere.

### Windows (PowerShell)

```powershell
cd C:\path\to\llm-council
powershell -ExecutionPolicy Bypass -File scripts\install-vibe.ps1 --yes
```

This:

- creates/updates `%USERPROFILE%\bin\vibe.cmd`,
- adds `%USERPROFILE%\bin` to your **User PATH** if missing,
- does **not** require admin.

**Restart your terminal** after a PATH change. Preview with `--dry-run`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-vibe.ps1 --dry-run
```

Use the wrapper directly without installing (PowerShell or **CMD**):

```powershell
# PowerShell
powershell -ExecutionPolicy Bypass -File C:\path\to\llm-council\scripts\vibe.ps1 review --preset balanced --file plan.md
```

```bat
REM CMD (vibe.cmd forwards to vibe.ps1 from any directory)
C:\path\to\llm-council\scripts\vibe.cmd review --preset balanced --file plan.md
```

### macOS / Linux (shell)

```sh
cd /path/to/llm-council
sh scripts/install-vibe.sh --yes
```

This symlinks `~/.local/bin/vibe` → `scripts/vibe.sh`. It is **user-local** (no
sudo), idempotent, and never edits your shell rc files. Preview with `--dry-run`;
install elsewhere with `--bin-dir DIR`; replace a conflicting `vibe` with `--force`.

If `~/.local/bin` is not on your `PATH`, the installer prints the exact line to add
to your shell rc (e.g. `~/.zshrc` or `~/.bashrc`):

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Use the wrapper directly without installing:

```sh
sh /path/to/llm-council/scripts/vibe.sh review --preset balanced --file plan.md
```

The launcher picks a Python interpreter in this order: `VIBE_PYTHON` (escape hatch)
→ repo `.venv` → active virtualenv (`$VIRTUAL_ENV`) → `python3` → `python`. If the
chosen interpreter is missing project deps, it prints a clear message instead of a
raw `ModuleNotFoundError`.

> **Note:** the launcher prefers the repo's own `.venv` **over an activated
> virtualenv**. This is intentional — `vibe` is a tool you run *against* your
> project, so it uses its own dependencies, not your project's. Override with
> `VIBE_PYTHON` if you need a specific interpreter.

### Verify the install

```sh
vibe --version
vibe status
vibe presets
vibe models
```

> The examples below assume the global `vibe` command is installed. Otherwise,
> replace `vibe` with `python -m backend.cli` (from the repo), or the
> `scripts\vibe.ps1` (Windows) / `scripts/vibe.sh` (macOS/Linux) wrapper.

### Using the CLI directly (no global command)

Run any mode from the repo root with `python -m backend.cli`:

```powershell
python -m backend.cli extract --preset cheap --file plan.md --save
python -m backend.cli mini    --preset balanced --prompt "What should we do next?"
python -m backend.cli review  --preset balanced --file plan.md
python -m backend.cli full    --preset cheap --prompt "Compare these options."
```

---

## Quick demo

A first end-to-end run using a committed example plan (no setup beyond your
`.env` key). The wrappers write artifacts into the **current project's** `.council/`.

```sh
# 1. See where you are (and let vibe create a local .council/ workspace).
vibe status

# 2. Review a real example plan. No --yes the first time, so you see the
#    approval prompt and that this spends credits.
vibe review --preset balanced --file examples/plans/feature-plan.md --usage

# 3. Make some edits, then review your git diff.
vibe diff --preset balanced --yes --usage

# 4. Record the decision (single model, cheapest step).
vibe extract --preset balanced --file examples/plans/feature-plan.md --save --yes --usage
```

You'll get a consolidated review on stdout and saved artifacts under `.council/`
(`reviews/`, `diffs/`, `decisions/`). `--usage` prints provider-reported tokens/cost
when available. For a fuller walkthrough with expected output and artifact paths, see
[`examples/workflows/review-diff-extract.md`](examples/workflows/review-diff-extract.md).

> Tip: the cheapest way to see the tool work is `vibe extract` — it's a single model
> with no council. Use `--preset cheap` for smoke tests and retries.

### Demo

See [`docs/demo-transcript.md`](docs/demo-transcript.md) for a **sanitized text
walkthrough** of the full loop (`version → status → presets → models → review →
extract`) with real, redacted command output. It's a hand-sanitized transcript, **not**
a recording — a real asciinema cast / GIF is still a follow-up.

Want to **record** the loop yourself? See [`docs/demo.md`](docs/demo.md) for the
recommended asciinema-first approach, the exact safe demo script, and a redaction
checklist so you don't leak keys, `.env`, local paths, or raw `.council/` outputs.

---

## Core commands

```powershell
vibe status
vibe doctor
vibe review --preset balanced --file plan.md
vibe diff --preset balanced
vibe extract --preset balanced --file plan.md --save
vibe mini --preset balanced --prompt "What should we do next?"
vibe full --preset cheap --prompt "Compare these options."
vibe last
vibe last decision
vibe help
vibe guide claude
```

Output (the review/answer/decision) goes to **stdout**; progress, saved-file
paths, usage, and guard messages go to **stderr**, so stdout stays clean for
piping. The API key is never printed.

### `vibe doctor` (provider diagnostics)

`vibe doctor` checks your current **provider** setup — it runs **no inference**
and spends **no tokens**. It reports the selected provider (`VIBE_PROVIDER`,
default `openrouter`) and:

- **OpenRouter:** whether `OPENROUTER_API_KEY` is set (not the placeholder; the
  value is never printed) and, when online, whether the **model-list** endpoint is
  reachable (not chat/completions).
- **Ollama:** that `OLLAMA_HOST` is a valid loopback URL, whether the local server
  is reachable (`GET /api/tags`), which local models are installed, and whether your
  `VIBE_OLLAMA_MODEL` (if set) is one of them.

```powershell
vibe doctor            # config + reachability checks
vibe doctor --offline  # config checks only (no network)
```

For Ollama, set `VIBE_PROVIDER=ollama` and `VIBE_OLLAMA_MODEL=<model you pulled
locally>` (e.g. `llama3.1`). When set, Ollama runs use that local model name
instead of the OpenRouter-style preset IDs.

Exit code: `0` all checks pass, `1` a check failed, `2` unsupported provider. This
is diagnostics only — it does **not** auto-configure provider-specific model IDs
yet (presets still use OpenRouter-style IDs).

---

## Project-local `.council/` workspace

When you run `vibe` inside a target project, it creates a local workspace:

```text
.council/
  config.json
  reviews/
  diffs/
  decisions/
  runs/
  stages/
  usage/
  locks/
```

- `.council/` is **local runtime memory** and should stay **gitignored** (vibe
  adds it to the project's `.gitignore` automatically).
- `reviews/` — saved reviews · `diffs/` — raw `git diff` captures ·
  `decisions/` — formal decisions (JSON + Markdown + `index.jsonl`) ·
  `runs/` — saved `mini`/`full` outputs · `stages/` and `usage/` —
  stage/usage metadata (`--save-stages`) · `locks/` — loop-guard state.
- `data/projects.json` is a **local, ignored** global registry of workspaces.
  Nothing under `data/` is meant to be committed.

> Stage files contain model input/output content (responses, rankings,
> synthesis). They never contain the API key, but keep `.council/` gitignored.

---

## Decision memory

```powershell
vibe decisions list
vibe decisions search "sqlite"
vibe decisions context "agent workflow"
```

- `vibe extract --save` writes a decision as **JSON + Markdown** and appends an
  entry to `.council/decisions/index.jsonl`.
- `search` is **simple local string matching** for now — **no embeddings, no
  SQLite yet**.
- `context` returns a compact block of the most relevant prior decisions — handy
  to read (or paste) **before asking Claude Code to plan**.
- These commands call **no model** and need **no API key**.

---

## Claude Code workflow

```text
Use vibe-council for this project.

1. Run:
   vibe status

2. Before planning, search prior decisions:
   vibe decisions context "<topic>"

3. Write plan.md.

4. Review the plan:
   vibe review --preset balanced --file plan.md --yes

5. Implement.

6. Review the diff:
   vibe diff --preset balanced --yes

7. Extract the decision:
   vibe extract --preset balanced --file plan.md --save --yes

Do not use premium or full unless explicitly requested.
Use cheap for smoke tests.
Use balanced for real review.
Never expose API keys.
```

Run `vibe guide claude` to print this reusable instruction block (or
`vibe guide claude --write CLAUDE.md` to append it to a project's `CLAUDE.md`).

---

## Modes

| Mode | What it does | Notes |
|------|--------------|-------|
| `extract` | One model extracts a structured decision record from notes/plans | JSON + Markdown export |
| `mini` *(default)* | Models answer + chairman synthesis (no peer ranking) | everyday decisions |
| `review` | Multi-model critique → consolidated review (no ranking) | plans, diffs, security, architecture |
| `full` | Full council: collect → peer ranking → chairman synthesis | slower / more expensive |

- `full` is the only mode that uses anonymized peer review/ranking.
- `premium` is blocked unless you pass `--allow-premium`.

### Which mode & preset should I use?

Pick by situation, not by reading every definition:

| Your situation | Mode | Preset | Why |
|----------------|------|--------|-----|
| One-line docs/typo fix | `review` (or skip) | `cheap` | A full gate costs more than the change is worth. |
| Real feature plan / non-trivial diff | `review` / `diff` | `balanced` | The everyday quality gate — multi-model critique that catches real issues. |
| Quick "what should I do?" question | `mini` | `balanced` | Several models + a synthesis, no peer ranking. |
| Capture a decision you've made | `extract` | `cheap`/`balanced` | Single model → structured record; cheapest step. |
| Big, risky, ambiguous architecture call | `full` | `balanced` | Anonymized peer ranking adds signal when stakes are high. |
| Expensive/critical, explicitly requested | any | `premium` | Biggest models; requires `--allow-premium`. |

### Cost / quality policy

- **`cheap`** → smoke tests, retries, and changes too small to deserve a full gate.
- **`balanced`** *(default for real work)* → plan and diff quality gates.
- **`full`** → only for big strategic/architecture decisions; it costs more and
  rarely beats `balanced` for routine review.
- **`premium`** → only when explicitly requested; always requires `--allow-premium`.
- Always pass **`--usage`** so cost/tokens are visible. Rough anchors from real runs:
  a `balanced` review is **≈ $0.15–0.30** and an `extract` is **≈ $0.03** —
  approximate and provider-dependent. Cost scales with input size, so a very large
  plan/diff costs more; use **`--max-tokens N`** to hard-block oversized inputs before
  any model call (see [Token guard](#token-guard-pre-run-hard-block)).
- After any `full`/`premium` run, it's fair to ask: *did it earn its cost?*

---

## Presets and models

A preset decides **which models** fill the council, chairman, and extract roles.
These are the current defaults in [`backend/config.py`](backend/config.py) (all
env-overridable):

| Preset | Intended use | Council models | Chairman | Extract |
|--------|--------------|----------------|----------|---------|
| `cheap` | smoke tests, low-cost experiments | `google/gemini-2.5-flash`, `anthropic/claude-haiku-4.5` | `google/gemini-2.5-flash` | `google/gemini-2.5-flash` |
| `balanced` *(default)* | normal real work | `openai/gpt-5.1`, `anthropic/claude-sonnet-4.5`, `google/gemini-2.5-pro` | `anthropic/claude-sonnet-4.5` | `anthropic/claude-sonnet-4.5` |
| `premium` | expensive/critical only (**requires `--allow-premium`**) | `openai/gpt-5.1`, `anthropic/claude-opus-4.6`, `google/gemini-2.5-pro`, `x-ai/grok-4.3` | `anthropic/claude-opus-4.6` | `anthropic/claude-sonnet-4.5` |

- **Council** models answer/critique/rank; the **chairman** synthesizes the final
  result; **extract** is the single model used for decision extraction.

### Changing models

- Edit the defaults in [`backend/config.py`](backend/config.py), or override any
  ID via environment variables (see [`.env.example`](.env.example)).
- Use valid **OpenRouter model IDs** (e.g. `provider/model`).
- Model **availability and pricing change** — IDs get deprecated (xAI `grok-4` is
  already deprecated; the default is `grok-4.3`). Verify on OpenRouter if a call
  404s.
- After changing models, run a **cheap smoke test** first, e.g.
  `vibe mini --preset cheap --prompt "ping"`.
- Never hardcode secrets in `config.py` — the API key lives only in `.env`.

---

## Cost, token, usage, and loop guards

### Premium guard

```powershell
vibe full --preset premium --prompt "..."
```

fails unless you explicitly opt in:

```powershell
vibe full --preset premium --allow-premium --prompt "..."
```

### Token guard (pre-run, hard block)

```powershell
vibe review --preset balanced --file plan.md --max-tokens 10000
```

- A **rough estimate** of input tokens, labeled as an estimate.
- **Blocks before any model call** if the estimate exceeds the limit.
- Best option for a hard pre-run guardrail.

### Cost guard (best-effort, post-run)

```powershell
vibe review --preset balanced --file plan.md --max-cost 0.20
```

- **Optional.** If omitted, there is **no cost cap**.
- Cost is **provider-reported** when available — **never a fabricated exact dollar
  amount**.
- It **cannot reliably pre-block**, because exact cost is usually only known after
  the provider responds.
- If the provider reports a cost **over** the cap, the command **exits non-zero
  (code 6) while preserving stdout**.
- For real pre-run blocking, use `--max-tokens`.

### Usage and stages

```powershell
vibe review --preset balanced --file plan.md --usage
vibe review --preset balanced --file plan.md --save-stages
```

- `--usage` prints estimated input tokens plus provider-reported
  `prompt_tokens` / `completion_tokens` / `total_tokens` (and cost, if reported).
- `--save-stages` writes stage outputs + usage metadata under
  `.council/stages/` and `.council/usage/`.

### Loop guard

- **Enabled by default** when a project workspace is active.
- Blocks **duplicate/repeated** runs (same input within a short cooldown),
  **concurrent** identical runs, and **too many runs** in a short window.
- Override:

```powershell
vibe review --preset balanced --file plan.md --allow-repeat
vibe review --preset balanced --file plan.md --no-loop-guard
```

`--allow-repeat` bypasses the duplicate/cooldown checks (the rate limit still
applies); `--no-loop-guard` disables the loop guard entirely.

---

## Exit codes

CLI commands return dedicated exit codes (useful for agents and scripts):

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | runtime error (e.g. all model calls failed) |
| `2` | input/usage error (e.g. missing `--prompt`/`--file`) |
| `3` | premium guard (premium requested without `--allow-premium`) |
| `4` | token guard (estimated input exceeds `--max-tokens`, before any model call) |
| `5` | loop guard (duplicate/concurrent/rate-limited run) |
| `6` | cost cap exceeded (provider-reported cost over `--max-cost`; stdout preserved) |
| `7` | missing API key (`OPENROUTER_API_KEY` not set for a model command) |

---

## Privacy & local-first

vibe-council is local-first and **bring-your-own-key**. You install it on your
machine and pay your own provider bill.

- **What leaves your machine:** the prompts, files, and diffs you review are sent
  to the configured model provider — currently **OpenRouter** — to get a response.
  Treat that like any API call: see
  [OpenRouter's privacy policy](https://openrouter.ai/privacy) for how they handle
  data, and avoid putting secrets/PII in prompts or reviewed files.
- **What stays local:** everything under `.council/` — reviews, diffs, decisions,
  runs, and stage/usage metadata — plus the `data/` registry. Nothing is uploaded
  anywhere by vibe-council itself.
- **Your API key:** lives only in `.env`, is read from the environment, is **never
  printed by vibe-council itself**, and must **never be committed** (`.env` is
  gitignored).
- **`.council/` can contain sensitive content** (your prompts and the models'
  outputs). vibe keeps it gitignored automatically — keep it that way.
- **If you ever commit `.env` or `.council/` by accident:** rotate your OpenRouter
  key immediately (the old one should be considered exposed) and remove the files
  from history.
- **BYO cost:** you pay the provider directly. vibe-council does not mark up or hide
  cost; `--usage` shows provider-reported tokens/cost when available.

---

## Repository safety / ignored files

Do **not** commit:

- `.env`
- `data/` (including `data/projects.json`, `data/decisions/`, `data/cli_runs/`)
- `.council/` (any project workspace runtime)
- `node_modules/`
- `dist/`
- `__pycache__/`
- generated `reviews/` `diffs/` `decisions/` `runs/` `stages/` `usage/` `locks/`

These are local runtime/secret artifacts. The repo's `.gitignore` already covers
them.

---

## Roadmap / next ideas

**Recently shipped:** first-run API-key guard, `vibe models` / `vibe presets` /
`--version`, tests + CI (Ubuntu/macOS/Windows), privacy/local-first docs, decision
memory, cross-platform install scripts (Windows + macOS/Linux), a demo guide +
[sanitized transcript](docs/demo-transcript.md), and the **v0.1.0** release.

**Release status:** **v0.1.0 — first public release.** The repo reports `0.1.0`; the
`v0.1.0` git tag and GitHub Release are cut by a maintainer right after the release PR
merges. See [`CHANGELOG.md`](CHANGELOG.md) for the full notes and
[`docs/release-checklist.md`](docs/release-checklist.md) for the process. It's an early
`0.x` release — expect breaking changes between minor versions, and see the honest
limitations below.

**Near-term (after v0.1.0):**

- Record the real demo GIF / asciinema of the review → diff → extract loop *(follow-up)*

**Later (explicitly not in v0.1.0):**

- Ollama / multi-provider abstraction (local inference)
- MCP server
- SQLite / embedding-based decision search
- GitHub PR review bot
- Packaged install (`pipx`/`uvx`) and a unified launcher entry point
