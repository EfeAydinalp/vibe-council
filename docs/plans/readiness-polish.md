# Plan: readiness-polish

Make vibe-council safer and clearer for first-time local users. Focused PR — no
cross-platform install, no Ollama/provider abstraction, no MCP, no demo GIF.

## Intended changes

1. **First-run OpenRouter key guard** — before any model call (`extract`, `mini`,
   `review`, `full`, `diff`), if `OPENROUTER_API_KEY` is missing/empty, print a
   friendly stderr message (copy `.env.example`, set the key, add credits, never
   commit `.env`) and exit with a dedicated code (`EXIT_NOKEY = 7`). No traceback.
   Never print the key. The guard fires **after** the premium guard and **before**
   workspace creation / token / loop / model call, by reading `os.environ` directly.
   **Bypass list (no-model commands never trigger it):** `--version`, `help`,
   `guide`, `status`, `last`, `projects list`, `decisions list/search/context`,
   `models`, `presets`, `init`.
2. **`vibe models`** — print configured model IDs per preset (council / chairman /
   extract) and which `MODEL_*` env overrides are active. No model call, no key.
3. **`vibe presets`** — list presets (cheap/balanced/premium), intended use, and the
   premium guard. No model call, no key.
4. **`--version`** — `vibe --version` / `python -m backend.cli --version`, using a
   single `0.1.0-dev` constant. No git tag, no release.
5. **Minimal pytest suite** — no-model + guard behavior (import, version, help,
   presets, models, status, decisions list, missing-key guard, premium guard, token
   guard). No real OpenRouter calls, no `.env` needed.
6. **GitHub Actions CI** — run compile/import + pytest on push/PR (Ubuntu + Windows),
   no API key, no real model calls.
7. **Privacy/local-first docs** — short section: what leaves the machine (prompts/
   files/diffs to OpenRouter) vs. what stays local (`.council/`), API-key handling,
   BYO-key/BYO-cost.

## Files likely to change

- `backend/cli.py` — key guard, `models`/`presets` commands, `--version`, dispatch.
- `backend/__init__.py` — `__version__ = "0.1.0-dev"` (conventional location).
- `backend/config.py` — a small model-slot/env-override helper for `vibe models`.
- `tests/` — new pytest suite + `conftest.py` helper.
- `.github/workflows/ci.yml` — new CI workflow.
- `pyproject.toml` — add `pytest` as a dev dependency (only if structured cleanly).
- `README.md` and/or `docs/agent-integrations.md` — privacy/local-first section.

## Risks

- Key-guard ordering: must fire before workspace creation and before model calls,
  but must NOT block no-model commands.
- Tests must be hermetic: `load_dotenv()` could pick up the repo `.env`; run tests
  from a temp cwd with `PYTHONPATH` and an explicit env so the missing-key test is
  reliable.
- Token-guard test must pass a dummy key (so the key guard doesn't fire first) while
  still never making a real call (`--max-tokens 1` blocks pre-call).
- CI on Windows + Ubuntu: keep it simple; no secrets.
- Adding `pytest` shouldn't disturb `uv.lock` or runtime deps.

## Tests

- import/compile; `--version`; `help`; `presets`; `models`; `status` (temp dir,
  no workspace); `decisions list` (empty); missing-key guard (exit code, no
  traceback); premium guard (blocks before call); token guard (blocks before call).
- All without real model calls or a real key.

## Out of scope (intentionally)

- Cross-platform install (bash/zsh shim, pipx/uvx).
- Ollama / multi-provider abstraction.
- MCP server.
- Demo GIF/asciinema.
- `vibe models check` network validation (only if trivial; otherwise deferred).
- Web UI changes; SQLite/embedding decision search; release tagging.
- CI linting (ruff/black/mypy) and coverage targets — deferred to keep CI simple.
- `vibe config` / `vibe privacy` commands and dynamic version from `pyproject.toml`.

## Council feedback applied

The plan was reviewed by vibe-council (`vibe review --preset cheap`). Summary:

- **Main criticism:** ambiguity in (a) exactly which commands bypass the key guard,
  (b) test hermeticity vs. `load_dotenv()` picking up the repo `.env`, and (c) the
  conventional location for the version constant. The council also suggested clearer
  `models`/`presets` output, a privacy-policy link, and CI linting.
- **What changed:** added an explicit key-guard **bypass list** and dispatch order;
  moved `__version__` to `backend/__init__.py`; hardened the test approach (run the
  CLI in a subprocess from a **temp cwd** with an **explicit env** and a clearly fake
  key `sk-test-fake`, so `.env` is never picked up and no real call is made); and
  expanded the privacy section to link OpenRouter's policy and warn about sensitive
  content in prompts/files.
- **What was not changed, and why:** declined **CI linting/coverage targets**,
  `vibe config`/`vibe privacy` commands, and dynamic `tomllib` versioning — all are
  out of scope for this focused readiness PR (keep it small, stdlib-friendly). The
  premium-guard test needs no HTTP mocking because the guard checks the preset
  argument **before** any API call, so it was left as planned.

## Diff review feedback applied

After implementation, the diff was reviewed by vibe-council (`vibe review
--preset cheap` on a gitignored temp diff). Summary:

- **Main issue found:** test hermeticity — `load_dotenv(override=False)` could
  theoretically pick up the repo's real `.env`; and the exit codes weren't
  documented in code.
- **Fix applied:** hardened the test helper to run the CLI from a **throwaway temp
  cwd** with **PYTHONPATH** to the repo (so no `.env` is ever discovered), and added
  a **documented exit-code table** in `backend/cli.py` (and code `7` to the README
  table). The premium+missing-key ordering is already covered by an existing test.
- **Deliberately not changed:** the **premium-guard-before-key-guard ordering**
  (intentional: premium policy is checked first; documented), and the larger
  suggestions (Typer/Click migration, runtime "no-model" enforcement decorators,
  model-ID network validation) — all out of scope for this focused PR.

## Balanced/full council feedback applied

A higher-quality gate was run before commit:
`vibe review --preset balanced` (plan), `vibe review --preset balanced` (diff),
and `vibe full --preset balanced` (plan). Raw outputs are local-only under
`.council/reviews/`.

**What balanced/full found that cheap missed:**
- **Test hermeticity was overstated.** The balanced *diff* review correctly noted
  that running tests from a temp cwd does **not** isolate `.env`: `load_dotenv()`
  discovers the repo `.env` from `config.py`'s location, not the cwd. Verified
  empirically (a key-unset run from a temp cwd still loads the real key). The
  missing-key test is still deterministic because the key is set **explicitly** and
  config uses `load_dotenv(override=False)`.
- **Windows-only key-guard message** (`Copy-Item ...`) would mislead macOS/Linux
  users — CI runs on Ubuntu too.
- **First-run placeholder trap:** a user who copies `.env.example` but doesn't edit
  it has the literal placeholder as their "key".

**What was changed (small, safe):**
- Corrected the test helper comment to describe the real isolation mechanism
  (explicit env value + `override=False`), not the temp cwd.
- Made the key-guard message **cross-platform** (PowerShell + `cp`).
- The guard now treats the **`.env.example` placeholder** as not-configured, with a
  dedicated message; added a test for it.
- Privacy docs: softened "never printed" → "never printed by vibe-council itself"
  and added accidental-commit **key-rotation** guidance.

**Intentionally not changed:**
- **Guard order (premium before key):** a UX preference, not a correctness/safety
  issue; left as the documented intentional behavior (flagged for owner decision).
- **Exit code 7 → 2:** keeping the **dedicated** code 7 is more useful for agents
  than overloading the generic usage code 2.
- **Decorator/registry guard refactor, Typer/Click, CI dependency pinning/linting,
  network-blocking in tests, `vibe doctor`/`--dry-run`:** out of scope for this PR.
- The balanced diff review's "exit code 6 unimplemented" note is a **false positive**
  (cost cap is implemented on `master`; the reviewer only saw this PR's diff).

**Did full + balanced justify its cost?** No. The balanced **diff** review (~$0.23)
caught the one real, actionable issue (hermeticity wording). `full + balanced`
(~$0.35) on the *plan* produced the most exhaustive output but added **no new
actionable finding** beyond the balanced reviews — and, reviewing the plan rather
than the diff, it repeated the same temp-cwd hermeticity assumption without catching
the bug. Recommended default: **`review + balanced` on the diff** for quality gates;
reserve `full` for genuinely high-stakes, ambiguous decisions.
