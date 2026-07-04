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
- **Decision memory** — curated `vibe decisions list` / `show` / `new` / `lint` (over
  `docs/decisions/`), plus local `search` / `context`
- **Guardrails** — premium requires `--allow-premium`, plus `--max-tokens`,
  `--max-cost`, a loop guard, `--usage`, and `--save-stages`
- **Claude Code workflow** — plan → review → implement → diff review → extract decision

**Using vibe-council from another project or an AI coding agent?** Start with the short
[`docs/agent-quickstart.md`](docs/agent-quickstart.md) (a copy-paste-safe review/diff/decision
recipe). See [`docs/agent-integrations.md`](docs/agent-integrations.md) for the full agent guide.

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

You can now use the CLI directly. If you installed with `uv sync`, run it through `uv run` so it
uses the synced `.venv` (a bare `python -m backend.cli ...` will fail with `ModuleNotFoundError` if
your shell's `python` isn't that `.venv`'s interpreter):

```powershell
uv run python -m backend.cli review --preset cheap --prompt "Review this tiny plan."
```

If you installed with the manual `venv` + `pip install` path above and activated it in this shell,
`python -m backend.cli ...` (no `uv run` prefix) works directly.

---

## Install the global `vibe` command

The wrappers set `VIBE_CALLER_CWD` so project-local `.council/` artifacts land in
**your** project, prefer the repo's `.venv` interpreter (so a bare `python` pointing
at the wrong environment is never used), and never print the API key. Set
`VIBE_COUNCIL_HOME` to override the repo location if it lives elsewhere.

### Windows (PowerShell)

```powershell
cd C:\path\to\vibe-council
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
powershell -ExecutionPolicy Bypass -File C:\path\to\vibe-council\scripts\vibe.ps1 review --preset balanced --file plan.md
```

```bat
REM CMD (vibe.cmd forwards to vibe.ps1 from any directory)
C:\path\to\vibe-council\scripts\vibe.cmd review --preset balanced --file plan.md
```

### macOS / Linux (shell)

```sh
cd /path/to/vibe-council
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
sh /path/to/vibe-council/scripts/vibe.sh review --preset balanced --file plan.md
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

Run any mode from the repo root with `python -m backend.cli` (prefix with `uv run` if you installed
via `uv sync` and haven't activated `.venv` in this shell — see the Quick start note above):

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

### Providers (OpenRouter / Ollama)

The provider is selected with `VIBE_PROVIDER` (default `openrouter`). Run
`vibe doctor` to check your setup.

```powershell
# OpenRouter (default) — uses OPENROUTER_API_KEY
VIBE_PROVIDER=openrouter

# Local Ollama — no API key; run a local Ollama server with a model pulled
VIBE_PROVIDER=ollama
VIBE_OLLAMA_MODEL=llama3.1   # a model you've `ollama pull`ed
vibe doctor
```

`VIBE_OLLAMA_MODEL` maps the preset's OpenRouter-style model IDs to your local Ollama
model (provider-specific preset config is future work). Local Ollama reports no billing
cost, so `--max-cost` can't be enforced for Ollama runs.

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

Two layers: **curated, committed** records under `docs/decisions/*.md` (the source of
truth), and a **gitignored local** auto-extract index under `.council/decisions/`.

**Curated `docs/decisions/` records:**

```powershell
vibe decisions list                       # list curated records (date, status, id, title, tags)
vibe decisions list --tag strategy        # filter by tag or --status
vibe decisions show 2026-06-30-redaction-guard   # print a record (by stem or path)
vibe decisions new --title "My decision"  # print a new record template (stdout)
vibe decisions new --from-run review.md   # extract a LOCAL draft from raw council output
vibe decisions promote draft.md --dry-run # check a reviewed draft; drop --dry-run to write it
vibe decisions lint                       # lint records (frontmatter, headings, links, redaction)
```

- `vibe decisions new` prints a draft template (frontmatter + stable headings); it
  **never auto-commits or auto-promotes**. Pass `--out PATH` to write it somewhere.
- `vibe decisions new --from-run <review.md>` extracts a **local** draft into gitignored
  `.council/decisions/drafts/`, mapping a review's verdict, rationale, alternatives, risks/
  consequences, and next actions into the matching record sections (deterministic heuristics,
  no LLM; unmatched sections keep `TODO` markers). It runs a redaction scan and **reports**
  findings (advisory — fix before promote), refuses to write under `docs/decisions/`, and
  **never stages/commits**. Then review/redact the draft and run `vibe decisions promote <draft>`.
- `vibe decisions promote <draft.md>` validates a **human-reviewed** draft (frontmatter,
  headings, redaction) and writes the curated record into `docs/decisions/` as a
  `YYYY-MM-DD-slug.md` file. It requires **meaningful (non-placeholder) content** in the core
  sections (Decision, Rationale, and Consequences/Next actions) — an all-`TODO` scaffold is
  refused. It refuses unsafe paths, refuses overwrite without `--force`, supports `--dry-run`,
  and **never auto-stages, commits, or reads raw `.council/` run logs**. It prints the created
  path and suggests `git diff` / `vibe decisions lint` as the next steps.
- `vibe decisions lint` reuses the redaction guard ([`docs/redaction-policy.md`](docs/redaction-policy.md))
  and exits non-zero on serious errors. `show` is path-traversal guarded to
  `docs/decisions/` only.

**Local auto-extract index (`.council/decisions/`, gitignored):**

```powershell
vibe decisions search "sqlite"
vibe decisions context "agent workflow"
```

- `vibe extract --save` writes a decision as **JSON + Markdown** and appends an
  entry to `.council/decisions/index.jsonl`.
- `search` is **simple local string matching** for now — **no embeddings, no
  SQLite yet**; `context` returns a compact block to read before planning.
- All of these commands call **no model** and need **no API key**.

## Context pack

```powershell
vibe context build                        # assemble a local context pack from curated memory
vibe context build --max-chars 8000       # tighten the budget
vibe context check                        # check pack quality (deterministic, no LLM)
vibe context check --json --strict        # machine-readable; fail on advisory misses/warnings
vibe context export claude-code           # wrap the pack as a local Claude Code context file
```

- `vibe context build` **deterministically** assembles a compact agent context pack from
  `docs/decisions/*.md` + `docs/context/project/STATUS.md` — metadata, project identity, current
  status, pinned/recent decisions, a decision index, a rejected-alternatives index, and constraints.
- **No LLM, no model/API/network, no vector retrieval.** It runs the redaction guard on the output
  and **blocks on critical findings**.
- Output defaults to **gitignored `.council/context/pack-latest.md`** (local-first); it **refuses to
  write under `docs/` unless `--allow-docs`** and **never stages/commits**. A character budget
  (`--max-chars`) trims recent decisions / indexes before status, never dropping metadata or status.
- `vibe context check` is a **deterministic quality harness (no LLM eval)**: it checks the pack has the
  required sections, constraints, current-state facts, decision-memory signals, and a rejected-
  alternatives signal, runs the redaction scan (critical findings fail), and scores `passed/total`.
  It exits non-zero below `--min-score` (default 0.8) or on any required/critical miss; `--strict`
  also fails on advisory misses and redaction warnings; `--json` for a machine-readable report.
- `vibe context export claude-code` wraps the pack as a **Claude Code-friendly** local context file
  (title, usage note, a paste-able operator instruction block, the pack body, and next commands). It
  runs the quality check + redaction scan first and **refuses to export** on a failing check or a
  critical finding. Output defaults to **gitignored `.council/context/claude-code-context.md`**;
  `--input`/`--output`/`--dry-run`; it **refuses `docs/` unless `--allow-docs`**, **never modifies
  `CLAUDE.md`**, and **never stages/commits**.

## Operator status

```powershell
vibe operator status                      # show local workflow status (or "No operator status yet.")
vibe operator status --json               # machine-readable
vibe operator set --state needs_input --message "review awaiting approval" --next-action "promote"
vibe operator clear                       # remove the local status file
```

- A tiny **local-first** status surface: a single gitignored `.council/operator/status.json` with
  `state` (`needs_input` / `failed` / `done` / `running` / `idle`), `message`, `next_action`,
  `source`, and `severity`. `set` validates the state/severity, sanitizes + caps free text, and only
  ever writes `.council/operator/status.json` — **never staged/committed**.
- This is **not** an event log, dashboard, notification system, or remote transport. Human-readable
  state is meant to be **Remote Control-friendly** (surface a clear decision point inside a
  Remote-Control'd session) without any custom mobile/remote transport. No model/API/network.

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
- **Provider-dependent.** Cost enforcement relies on provider-reported billing data:
  OpenRouter may report cost; **local Ollama does not**, so `--usage` says cost is not
  reported and `--max-cost` **cannot be enforced** for Ollama runs (never fabricated).

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

**Recently shipped (v0.5.1 — Workbench dogfood & hardening patch):** a checklist-driven hardening
pass over the v0.5.0 AI Council Workbench MVP — clean-clone/Windows dogfood, an interactive
Workbench smoke pass, localhost bind/shutdown defense-in-depth, a manual execution dogfood pass
that exercised the real guarded-executor path end-to-end (file write + allowlisted command, both
through the panel's actual HTTP API, both with crafted-request-body override attempts confirmed to
have zero effect), and a `uv.lock` self-version hygiene fix. **No new command, no new panel
capability, no allowlist growth.** See [`docs/releases/v0.5.1.md`](docs/releases/v0.5.1.md). (v0.5.0
shipped the AI Council Workbench MVP itself: a task moves through **visible stages**, an AI proposes
a change, an **audited approval** step gates it (deterministic guards are the boundary; the Approval
Auditor is advisory only), and — as a **separate, explicit** step — an approved action can actually
run: a bounded `write_file`/`edit_file` behind a verified local payload artifact, or an exact
allowlisted command behind a fixed-argv resolver (`shell=False`, sanitized environment, timeout,
bounded/redacted output). v0.4.0 shipped the read-only MCP / Claude Code workflow — `vibe mcp
contract` / `inspect` / `serve --stdio`, a minimal **stdlib** JSON-RPC stdio transport, no `mcp` SDK,
in-memory context reads. v0.3.1 hardened the decision-memory / context loop; v0.3.0 shipped the
redaction guard, the curated decision CLI, draft extraction + safe promotion, the context-pack
builder/check/export, operator status, and the license/provenance "Question 0" checklist; v0.2.0
shipped the provider abstraction + local Ollama + `vibe doctor`; v0.1.0 shipped the first-run
API-key guard, `vibe models`/`presets`/`--version`, CI, and decision memory.)

**The v0.3 decision-memory / context loop:**

```text
vibe decisions new --from-run <local-review.md>   # extract a LOCAL draft (gitignored)
# edit / review / redact the draft
vibe decisions promote <draft.md>                 # promote into docs/decisions/ as YYYY-MM-DD-slug.md
vibe decisions lint                               # lint the curated records
vibe context build                                # build a local context pack (gitignored)
vibe context check                                # check pack quality (deterministic; 21/21 on a curated repo)
vibe context export claude-code                   # wrap as a local Claude Code context file (gitignored)
```

```text
vibe lint --redaction                             # scan public docs for leaks
vibe operator status                              # show local workflow status
```

**Release status:** **v0.6.3 — cross-project agent onboarding.** The repo reports `0.6.3`; the
`v0.6.3` git tag and GitHub Release are cut by a maintainer right after the release PR merges. On top
of the v0.6.0 agent-to-Workbench proposal bridge, this bundles the onboarding arc — a role-aware
`vibe guide {claude|codex|fable}` layer (opt-in append-only `--write`), a local-first Markdown
**project vault** (`docs/context/project/`), a read-only `vibe project doctor` readiness check, and a
read-only `vibe context export --for <agent>` handoff. All read-only/local: no model/provider/network
call, no Workbench trust-boundary change, no `/council` command (`vibe` is the real CLI), no new
dependency (see [`docs/releases/v0.6.3.md`](docs/releases/v0.6.3.md)). The v0.6.0 bridge and v0.5.2
panel hardening remain in force, and the underlying Workbench model is unchanged: a task moves through
visible stages, an audited approval gates it, and an approved bounded file action or exact allowlisted
command can be explicitly executed — approving never auto-executes, and the deterministic trust
boundary re-runs at execution time. See [`CHANGELOG.md`](CHANGELOG.md) and
[`docs/releases/v0.6.3.md`](docs/releases/v0.6.3.md) for the notes (v0.6.0:
[`docs/releases/v0.6.0.md`](docs/releases/v0.6.0.md); v0.5.2:
[`docs/releases/v0.5.2.md`](docs/releases/v0.5.2.md); v0.5.1:
[`docs/releases/v0.5.1.md`](docs/releases/v0.5.1.md)), and
[`docs/release-checklist.md`](docs/release-checklist.md) for the process. It's an
early `0.x` release — expect breaking changes between minor versions, and see the honest limitations
below. **No commercial-clearance claim; license/provenance remains "Question 0".**

**Agent proposal bridge (v0.6.0):** AI agents can **propose** a bounded code action into the local
Workbench instead of acting directly — a human still approves and executes. It's **local file/CLI
intake only** (no network endpoint): an agent writes a schema-v1 proposal JSON and runs

```sh
vibe workbench propose proposal.json       # or:  vibe workbench propose -   (stdin)
```

which validates it, mints ids/hash server-side, and records a **pending** approval; nothing runs
until you approve it in `vibe workbench serve` and explicitly execute it. See
[`docs/workbench-agent-bridge.md`](docs/workbench-agent-bridge.md).

**Role-aware onboarding (in progress on `master`, unreleased):** `vibe guide {claude|codex|fable}
--role <role>` prints a topic- and role-tailored instruction pack (`task-shaper` / `planner` /
`coder` / `reviewer` / `release-manager`) to reduce per-session re-onboarding — Codex and Fable get
their own emphasis (Codex: reviewer/guardrail, propose-don't-bypass; Fable: cost/technical-lead,
plan-first). Add `--write [FILE]` to **append** the section to a file (per-topic defaults
`CLAUDE.md`/`AGENTS.md`/`FABLE.md`); it never overwrites (re-runs are skipped, and topics/roles
coexist in one file). See [`docs/agent-quickstart.md`](docs/agent-quickstart.md) §11.

**Project vault (local project memory):** [`docs/context/project/`](docs/context/project/README.md)
is the canonical, curated, public-safe Markdown project memory — `STATUS.md`, `ROADMAP.md`,
`DECISIONS.md` (an index into `docs/decisions/`), `PROGRESS.md`, `RISKS.md`, `WORKFLOWS.md`, `NOTES.md`,
plus the v0.7 personalization scaffold `PROFILE.md` (project identity/profile), `PREFERENCES.md`
(review-preset / Fable-usage / implementation-style policy), and `AGENT-ROLES.md` (per-agent roles +
the `MODEL:` header convention). Agents should **read the vault before planning or coding** so they
don't start from zero each session; the profile/preferences are read-as-documentation and tighten-only
(no command enforces them yet). Secrets, raw outputs, runtime payloads, and private plans never go there.

**Onboarding readiness:** `vibe project doctor` is a **read-only** check (no writes, no `.council/`,
no model calls) that reports whether a repo is ready for agent onboarding — vault/core docs present,
no dangerous staged files (`.env`/`.council/`/private plans), context health, and the available
`vibe guide` commands. Exit 0 when ready; non-zero with next steps when something's missing.

**Agent context handoff:** `vibe context export --for {claude|codex|fable} [--role <role>]` prints a
**read-only** onboarding context pack for a target agent — header (`vibe` real / `/council` future),
operating rules, project-vault **pointers** (not a full dump), a context-health summary (built
in-memory, no `.council/`), the Workbench proposal flow, and a `vibe project doctor` recommendation.
Prints to stdout by default; `--output FILE` writes it (never overwriting an existing file).

**Implementation pack:** the phase-by-phase plan for upcoming work (v0.6 agent-to-Workbench bridge,
onboarding, project vault, personalization, positioning, and the open-core path) lives in
[`docs/fable/`](docs/fable/README.md) — a structured pack for driving future implementation with a
long-running model while keeping the product/security direction intact.

**Near-term:**

- **v0.5 — AI Council Workbench MVP** *(shipped in v0.5.0; hardened in v0.5.1)* — a
  user-visible **vertical slice**: a task moves through **visible stages**, an AI proposes a plan/diff,
  an **audited approval** step (deterministic guards are the boundary; the Approval Auditor is
  advisory) gates it, and only **approved, explicitly executed** actions run — everything logged.
  Reuses the v0.2–v0.4 infrastructure (MCP = read-only knowledge source; decisions/context = memory;
  `.council/` = local runtime). Near-term product name is **"AI Council Workbench"**; a broader
  **local-first AI project OS** is a **long-term / internal** direction, not near-term external
  messaging. Landed: the gitignored `.council/runtime/` JSON store, a deterministic task orchestrator,
  the deterministic trust boundary, the advisory Approval Auditor, and a **localhost-only panel**
  (`vibe workbench serve`) that shows task progress + approval cards, records approve/reject/hold, and
  — as a **separate, explicit** step — can **execute** an approved bounded `write_file`/`edit_file`
  action (behind a verified local payload artifact) or an approved **exact allowlisted** command
  (fixed argv, `shell=False`, sanitized environment, timeout, bounded/redacted output). Approving never
  auto-executes; the trust boundary re-runs at execution time; the browser only ever sends an action
  id. `vibe workbench serve` opens the localhost panel; it starts empty — use the **"Create demo
  task"** button to seed a safe local approval (the demo intentionally seeds no executable action; see
  [`docs/plans/v0.5-release-readiness.md`](docs/plans/v0.5-release-readiness.md) for the manual
  dogfood recipe that does exercise real execution — now proven end-to-end through the panel's real
  HTTP API by v0.5.1's manual execution dogfood pass). Release notes: `v0.5.0`:
  [`docs/releases/v0.5.0.md`](docs/releases/v0.5.0.md); `v0.5.1` (dogfood/hardening patch):
  [`docs/releases/v0.5.1.md`](docs/releases/v0.5.1.md). The repo reports `0.5.1`; the `v0.5.1` git tag
  and GitHub Release are cut once this release-prep PR merges. Next up: v0.6 scoping (the
  agent-to-Workbench bridge is the leading candidate — not started).
  See [`docs/plans/v0.5-workbench-mvp.md`](docs/plans/v0.5-workbench-mvp.md) and
  [`docs/plans/v0.5-guarded-executor.md`](docs/plans/v0.5-guarded-executor.md).
- **v0.4 read-only MCP / Claude Code workflow** *(shipped in v0.4.0)* — query curated decisions,
  status, and the context pack from Claude Code / local agents with **no write/action authority**.
  Browse the contract with `vibe mcp contract`; run a read-only smoke with `vibe mcp inspect`
  (`--id <id>`, `--context`, `--health`, `--json` — context pack/health are built **in memory**, no
  `.council/` file written); and start the read-only MCP server for Claude Code / MCP clients with
  `vibe mcp serve --stdio` (a minimal stdlib JSON-RPC stdio transport — **no extra dependency**, no
  HTTP port, no daemon). **No write/action tools are exposed** (no promote/file/git/shell/provider);
  only status, curated decisions, the context pack, and a health check are readable. See
  [`docs/plans/v0.4-read-only-mcp-workflow.md`](docs/plans/v0.4-read-only-mcp-workflow.md).

  ```sh
  vibe mcp contract                 # planned read-only resources/tools + forbidden tools
  vibe mcp inspect --context --health   # read-only smoke (in memory; nothing written)
  vibe mcp serve --stdio            # read-only MCP server over stdio (no write tools)
  ```

  Local setup for Claude Code / MCP clients: see
  [`docs/mcp/claude-code-setup.md`](docs/mcp/claude-code-setup.md) (generic MCP stdio pattern +
  safety checklist).
- Record the real demo GIF / asciinema of the review → diff → extract loop *(follow-up)*
- Provider-specific preset/model config (so Ollama doesn't need `VIBE_OLLAMA_MODEL` per run)

**Later:**

- MCP **write/action** surface (deferred; v0.4 is read-only first)
- SQLite / embedding-based decision search
- GitHub PR review bot
- Packaged install (`pipx`/`uvx`) and a unified launcher entry point
