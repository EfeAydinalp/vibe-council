# Plan: examples-workflow-polish

Make vibe-council easy for a new developer or Claude Code user to understand and
try in their first 10 minutes, after the readiness-polish and cross-platform-install
work. **Docs and examples only** — no core council logic changes (at most a tiny
typo/link fix if unavoidable). This prepares the project for a future v0.1.0 release.

## Current README / docs gaps

The README is already comprehensive (install, modes, presets, guards, exit codes,
privacy). The gaps are about *onboarding and discoverability*, not missing reference:

1. **No "Why this exists" framing.** The intro explains *what* it is but not the
   problem it solves (single-model blind spots; wanting a cheap, local, multi-model
   second opinion before committing to a plan or diff). A new reader can't tell in
   one breath why they'd reach for it.
2. **No runnable end-to-end demo.** Quick start stops at "review a tiny prompt."
   There is no `init → status → review → diff → extract` walkthrough a user can paste
   and watch produce real `.council/` artifacts. (The task brief references
   `docs/plans/example.md`, which **does not exist** — the demo must point at a real
   committed file; see Decisions below.)
3. **No `examples/` directory.** Nothing to read offline that shows realistic plan
   inputs, the workflow, expected artifacts, and what *not* to commit — without
   spending API credits.
4. **Mode/preset guidance is reference-shaped, not decision-shaped.** The tables say
   what each mode/preset *is*; they don't answer "which do I pick right now, and what
   will it cost me?" A short "when to use which" guide is missing.
5. **Cost/quality policy is implicit.** The cheap-vs-balanced-vs-full-vs-premium
   policy lives in scattered warnings; it should be one clear, quotable block.
6. **`agent-integrations.md` workflow is a bare 8-step list.** It doesn't stress that
   council output is *advice to be filtered by the developer/agent*, that balanced may
   over-review a tiny docs change (use cheap for smoke), or that final reports should
   include cost/tokens when available.
7. **Roadmap is partly stale.** Cross-platform install shipped; there is no mention of
   the near-term docs/examples polish, a demo GIF/asciinema, or the v0.1.0 release that
   this PR is preparing for.
8. **"council output is advice, not authority"** is nowhere stated explicitly, even
   though it is the single most important framing for safe use.

## Proposed `examples/` structure

A small, realistic, **read-only** (no API calls needed to read) examples tree:

```
examples/
  README.md                         # index: what these are, how to run, what not to commit
  plans/
    small-doc-fix.md                # a tiny plan (the "cheap is enough" case)
    feature-plan.md                 # a meatier plan (the "balanced gate" case)
  workflows/
    claude-code-loop.md             # the plan→review→implement→diff→extract loop for agents
    review-diff-extract.md          # a copy-pasteable terminal walkthrough w/ expected artifacts
```

Principles:

- **Realistic but short** — each plan is a believable change, a screenful, not a toy.
- **Readable without spending credits** — the example *plans* are just markdown; the
  *workflow* docs show the commands and **representative** (clearly-labeled) output and
  artifact paths, not transcripts that must be regenerated.
- **Teach the safety rails inline** — every example ends with a "what not to commit"
  note (`.council/`, `data/`, `.env`).
- **The README quick demo points at `examples/plans/feature-plan.md`** so the demo is
  a real, runnable command rather than a dangling path.

## Recommended council workflow (to document)

Single canonical loop, stated once and linked from README + agent-integrations:

1. (optional) `vibe decisions context "<topic>"` — read prior decisions before planning.
2. Write `plan.md`.
3. `vibe review --preset balanced --file plan.md --yes --usage` — plan quality gate.
4. Revise the plan — **apply only useful feedback; council output is advice, not orders.**
5. Implement.
6. `vibe diff --preset balanced --yes --usage` — diff quality gate.
7. Apply only useful feedback.
8. `vibe extract --preset balanced --file plan.md --save --yes --usage` — record the decision.
9. Final report: what changed, council commands run, cost/tokens, and `.council/`
   artifact paths — while keeping those artifacts local.

## How to explain the modes

A "pick one" framing, not just definitions:

- **`extract`** — turn a plan/notes into a structured decision record (JSON+MD). One
  model, no council. Use to *capture* a decision, not to debate it.
- **`mini`** *(default)* — several models answer + a chairman synthesis, **no peer
  ranking**. Fast everyday "what should I do?" multi-model second opinion.
- **`review`** — several models critique → one consolidated review, **no ranking**.
  The workhorse for **plans and diffs** (this PR's recommended gate).
- **`full`** — full council: collect → anonymized peer ranking → chairman synthesis.
  Slower/pricier; reserve for **genuinely high-stakes, ambiguous decisions**.

## How to explain the presets

- **`cheap`** — small/fast models. Smoke tests, retries, tiny docs changes.
- **`balanced`** *(default)* — the real-work gate for plans and diffs.
- **`premium`** — biggest models; **blocked unless `--allow-premium`**. Expensive/
  critical only.

## Cost / quality policy (to state once, clearly)

- **cheap** → smoke tests, quick retries, and changes too small to deserve a full gate.
- **balanced** → the default quality gate for real plan and diff review.
- **full** → only for big strategic/architecture decisions where peer ranking adds
  signal; it costs more and is rarely worth it for routine review.
- **premium** → only when explicitly requested; always requires `--allow-premium`.
- Always pass **`--usage`** on review/extract so cost/tokens are visible.
- "Did the expensive run earn its cost?" is a fair question to ask after `full`/premium.

## How to avoid committing `.council/`, `data/`, `.env`

Documented in README, `examples/README.md`, and each example:

- `.council/` (reviews, diffs, decisions, runs, stages, usage, locks) is **local-only**
  and auto-gitignored; it can contain your prompts and model outputs.
- `data/` (registry, `data/decisions/`, `data/cli_runs/`) is local-only.
- `.env` holds the API key — **never commit**; rotate the key if it leaks.
- The repo `.gitignore` already covers all of these; examples restate it so a reader
  copying commands doesn't accidentally `git add .` the artifacts.

## Files to add / change

**Add**

- `examples/README.md`
- `examples/plans/small-doc-fix.md`
- `examples/plans/feature-plan.md`
- `examples/workflows/claude-code-loop.md`
- `examples/workflows/review-diff-extract.md`

**Change**

- `README.md` — add "Why this exists"; tighten "What changed from upstream"; add a
  runnable **Quick demo** (`init → status → review → diff → extract`, pointing at
  `examples/plans/feature-plan.md`); add a **Mode selection guide** and a **Cost/quality
  policy** block; add a **"council output is advice, not authority"** safety note; update
  the **Roadmap** (examples/docs polish, demo GIF/asciinema, v0.1.0, Ollama/provider &
  MCP later). Link to `examples/`.
- `docs/agent-integrations.md` — expand the loop with: filter feedback (advice not
  authority), cheap-for-smoke on tiny changes, final reports include cost/tokens, and
  the never-commit list. Link to `examples/workflows/`.
- `docs/plans/README.md` *(new, optional)* — a one-screen index of what `docs/plans/`
  holds (plan docs are committed design records; raw reviews are not).

## Out of scope (intentionally)

- **No Ollama, no MCP, no SaaS, no provider abstraction, no PyPI publishing, no large
  CLI refactor** — explicitly deferred.
- **No core council logic / config / preset changes** (only a tiny typo/link fix if
  truly unavoidable).
- **No new tests required** — this is docs/examples; existing
  `python -m unittest discover -s tests -t .` (22 tests) must still pass. A structural
  test for `examples/` is optional and only if it's trivial and high-value.
- **No actual demo GIF/asciinema asset** in this PR — only the roadmap entry and a
  placeholder note (recording is a follow-up).
- **No version bump / release tagging** — v0.1.0 is *prepared for*, not cut here.
- **No `.council/` artifacts committed** — raw outputs stay local and gitignored.

## Decisions (resolved up front)

- **Quick-demo target file:** the brief names `docs/plans/example.md`, which does not
  exist. Rather than create a throwaway, the demo points at the committed
  `examples/plans/feature-plan.md`, so every documented command actually runs.
- **No duplicate workflow text:** the canonical loop lives in `agent-integrations.md`;
  README shows the short demo and links there, to avoid drift between two copies.

## Council feedback applied

Reviewed by vibe-council (`vibe review --preset balanced` on this plan; one model,
gemini-2.5-pro, hit a transient network error but the other two produced a full
consolidated review; raw output local-only under `.council/`). Applied the useful,
in-scope feedback; declined scope creep and behavioral code changes.

**Applied:**

- **Examples drift / validation (the #1 blocker).** Added a lightweight stdlib
  `tests/test_examples_docs.py` that asserts every referenced example file exists, the
  README links to `examples/`, and no `.council/`/`data/` artifact path is committed
  under `examples/`. Keeps the suite green and catches the most likely rot cheaply —
  without mocked-API CI or regenerated transcripts. `examples/README.md` also states
  the examples are **illustrative** and carries a "last verified" date.
- **"Council output is advice, not authority" must be prominent**, not buried. It goes
  **near the top of the README** (in "Why this exists") and is repeated in the agent
  loop, with concrete **filtering criteria**: accept findings about correctness,
  security, cost, and missing constraints; be skeptical of style nits, speculative
  rewrites, and over-engineering. "Apply only useful feedback" now has teeth.
- **`--yes` was teaching bypass-first.** The human Quick demo shows the **first command
  without `--yes`** so a new user sees the approval prompt and that real credits are
  spent; `--yes` is then introduced for repeat/agent use. (Agent docs still use `--yes`
  — that is correct for non-interactive agents.)
- **"cheap/local" framing was misleading.** "Why this exists" now states plainly that
  vibe-council is **local-first / bring-your-own-key but calls external provider APIs
  (OpenRouter)** — it is *not* local inference like Ollama.
- **Scenario-based guidance** beats flat matrices: a small "pick by situation" table
  (tiny docs → `cheap`, real feature/diff → `balanced`, big risky refactor → `full`,
  critical & explicitly requested → `premium`).
- **Concrete cost anchors.** Use the **real observed costs** from this project's own
  balanced runs as rough anchors (≈ $0.15–0.30 per balanced review, ≈ $0.03 per
  extract), clearly labeled approximate and provider-dependent.
- **Extract is the cheap first taste.** Note that `extract` is single-model (no council)
  and the lowest-cost way to see the tool work.

**Declined (scope creep / out of scope for a docs PR):**

- **First-run CLI onboarding banner + `.council/onboarding-shown` flag**, mocked-API
  output generation in CI, a maintained `examples/quick-demo.sh`, and a pre-commit
  hook — all are **code/behavioral changes**, explicitly out of scope here.
- **Splitting into separate `docs/concepts.md` / `docs/cost-guide.md` pages** — the same
  review warns about drift from too many files; definitions stay centralized in the
  README. Net file count is kept low.
- **Phasing the brief's 5 example files down to 2** — the brief specifies the set; the
  drift risk is instead mitigated by the structural test above. Examples are kept short.

### Diff review feedback applied

The implemented diff was reviewed by vibe-council (`vibe review --preset balanced` on a
gitignored temp diff under `.council/tmp/`). "Conditionally approve." Applied the useful
items; declined a false positive and scope creep:

- **"Documents a feature that doesn't exist" (`vibe decisions show`).** Added a clear
  banner to `feature-plan.md` that it is a *hypothetical* sample plan (input for the
  council), not a shipped command — and pointed at the real way to read a decision
  today (`vibe last decision`). Kept the example, since "planning a new feature" is
  exactly what it should illustrate.
- **Secrets-in-artifacts.** Added a note to `examples/README.md`: input is sent to the
  provider *and* written into `.council/`, so don't review secret-bearing content or
  sync `.council/`.
- **"Local-first" ambiguity.** Sharpened the README "Why this exists" wording to state
  that local-first means *artifacts* stay local — your code **is** sent to OpenRouter
  and upstream providers; it does not mean "never leaves my network."
- **Large-input cost.** Added a one-liner in the cost policy noting cost scales with
  input size and pointing to the existing `--max-tokens` pre-run guard.
- **Workflow duplication / long doc.** Added a TL;DR to `review-diff-extract.md` and a
  cross-link from `claude-code-loop.md` naming `agent-integrations.md` as canonical, to
  cut drift between the copies.

**Declined:**

- **"Fix the date typo: 2026 → 2024/2025."** False positive — `2026-06-27` is the
  actual current date; the reviewer's training cutoff misjudged it. Left as-is.
- **First-run onboarding banner, mocked-API CI, `vibe clean`/retention command,
  artifact-retention docs, a worked three-finding filtering example, splitting into
  `docs/concepts.md`/`docs/cost-guide.md`** — all scope creep or new behavior for a
  docs PR; declined. The structural test already accepts several "don't commit"
  phrasings, so it is not as brittle as flagged.
