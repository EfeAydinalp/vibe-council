# Plan: demo-and-release-prep

Prepare vibe-council for a **safe v0.1.0 public release** by adding the
documentation and release scaffolding a first-time tagger needs: a demo recording
guide, a release checklist, and a changelog draft. **Docs and release polish only**
— no core council logic, config, or preset changes, and **no binary media** (no real
GIF / asciinema recording) in this PR. This builds directly on the
`examples-workflow-polish`, `cross-platform-install`, and `readiness-polish` work.

## Scope at a glance

| Want | In this PR? |
|------|-------------|
| Demo *instructions* (how to record safely) | ✅ `docs/demo.md` |
| v0.1.0 release *checklist* | ✅ `docs/release-checklist.md` |
| Changelog *draft* (Unreleased + v0.1.0) | ✅ `CHANGELOG.md` |
| README "Demo" pointer + release-status note | ✅ minimal README edits |
| examples/README link to the demo guide | ✅ one link + one note |
| An actual recorded GIF / asciinema asset | ❌ deferred (follow-up, needs approval) |
| Version bump `0.1.0-dev` → `0.1.0` | ❌ release-time action, listed in checklist only |
| Tagging / cutting the release | ❌ documented, not executed |

## Demo format decision

**asciinema-first, GIF optional/later.**

- **asciinema** is the recommended primary format for a *terminal* tool: it records
  real selectable text (not pixels), stays tiny, and a reader can copy commands out
  of the player. The cast file is also diff-reviewable and easy to redact.
- **GIF** is a *secondary, optional* artifact for places that can't embed a player
  (e.g. an inline README thumbnail). It's heavier and lossy; generate it *from* the
  asciinema cast later (`agg`) rather than screen-recording separately.
- **This PR ships only the *guide*, not the asset.** Recording a real cast/GIF is a
  follow-up that needs explicit approval, because it (a) spends real credits and (b)
  risks leaking local paths/keys if not carefully redacted.

## Exact safe demo scenario (to document in `docs/demo.md`)

The canonical happy-path loop, using a **committed example plan** so it's runnable
and never points at a throwaway file:

1. **Install / verify** — `vibe --version`, `vibe status`, `vibe presets`.
2. **Status** — `vibe status` (shows workspace, default/max preset, last artifacts).
3. **Review a plan** — `vibe review --preset balanced --file examples/plans/feature-plan.md --usage`.
4. **Review a diff** — `vibe diff --preset balanced --yes --usage`.
5. **Extract a decision** — `vibe extract --preset balanced --file examples/plans/feature-plan.md --save --yes --usage`.
6. **Read decision memory** — `vibe decisions context "demo"`.

Notes baked into the guide:

- The **first** model command is shown **without `--yes`** so the viewer sees the
  approval prompt and that real credits are spent (consistent with the README quick
  demo). `--yes` appears on later steps.
- Use `--preset cheap` for a **dry rehearsal** so you don't burn `balanced` credits
  while getting the recording timing right; switch to `balanced` only for the take.
- Keep the recording short (target < 90s) — trim long model-wait gaps in post, or
  narrate that the wait is normal.

## How to avoid leaking (redaction checklist for `docs/demo.md`)

A terminal recording captures **everything on screen**, so the guide must call out:

- **API keys** — never `cat .env`, never `echo $OPENROUTER_API_KEY`, never run with
  the key visible in scrollback. vibe never prints the key itself, but *your shell
  history* might. Clear the screen before recording.
- **`.env`** — don't open, print, or `ls -la` it on camera.
- **Local usernames / paths** — `vibe status` prints the absolute project path
  (e.g. `C:\Users\F\...`). Record from a **neutral path** (e.g. `~/demo/vibe-council`
  or `C:\demo\...`) or redact in post. Set a generic shell prompt (no `user@host`).
- **`.council/` raw outputs** — fine to *show that artifacts were written* (the
  stderr "saved to ..." lines), but don't open and scroll a full raw review/decision
  file on camera; those contain your prompts and full model outputs.
- **Provider request details** — don't enable `--save-stages` on camera and then open
  a stage file; don't show verbose HTTP/debug logs that could include request bodies.
- **Window chrome** — close other tabs/windows; a terminal recorder still captures a
  visible title bar with a path. asciinema avoids this (text-only), which is another
  reason to prefer it.

The guide ends with a **post-record review step**: watch the cast/GIF once fully
before publishing and confirm none of the above appears.

## Files to add / change

**Add**

- `docs/demo.md` — safe terminal-demo recording guide (asciinema-first; optional GIF
  note; the demo script above; redaction checklist; "what not to show"; where a
  future asset should live: `docs/assets/` — *empty until a recording is approved*;
  reminder not to commit secrets / `.env` / `.council/` / `data/`).
- `docs/release-checklist.md` — the v0.1.0 release checklist (see below).
- `CHANGELOG.md` — Keep a Changelog–style file: `Unreleased` + a drafted `v0.1.0`.

**Change**

- `README.md` — add a short **Demo** section linking to `docs/demo.md`; add a small
  **release status** note (pre-v0.1.0; version currently `0.1.0-dev`); link
  `CHANGELOG.md` and `docs/release-checklist.md` where natural (Roadmap section).
- `examples/README.md` — add a link to `docs/demo.md` and a one-line note that the
  examples are safe to read without running real model calls.
- `docs/plans/README.md` *(optional, minimal)* — add this plan to the index.

**Do NOT add**

- Any binary media (`.gif`, `.cast`, `.mp4`, `.png`). `docs/assets/` may be created
  with a `.gitkeep` + README note *only* if it doesn't add binary weight; otherwise
  just document the intended location.

## v0.1.0 release checklist (content for `docs/release-checklist.md`)

Grouped, copy-pasteable, each item verifiable:

- **Pre-release**
  - Bump `backend/__init__.py` `__version__` from `0.1.0-dev` → `0.1.0` (and confirm
    it matches `pyproject.toml version = "0.1.0"`).
  - `vibe --version` prints `vibe-council 0.1.0`.
  - `CHANGELOG.md` `Unreleased` items moved under a dated `## [0.1.0] - YYYY-MM-DD`.
- **CI / tests**
  - `python -m unittest discover -s tests -t .` green (use the repo `.venv`
    interpreter if a system `python` mismatches the environment).
  - GitHub Actions CI green on Ubuntu / macOS / Windows.
- **README / docs**
  - README install steps, quick demo, and links resolve (`docs/demo.md`,
    `CHANGELOG.md`, `examples/`).
  - Roadmap "Recently shipped" / "Near-term" reflect reality.
- **Install checks (all three OSes)**
  - Windows: `scripts\install-vibe.ps1 --dry-run` then `--yes`; `vibe --version`.
  - macOS/Linux: `sh scripts/install-vibe.sh --dry-run` then `--yes`; `vibe --version`.
  - Direct wrappers (`scripts/vibe.ps1`, `scripts/vibe.sh`, `scripts/vibe.cmd`) work.
- **Security / safety**
  - No secrets in the diff; `.env`, `.council/`, `data/` not staged.
  - `git grep -nI "sk-or-v1-"` returns nothing committed.
  - First-run key guard still fires with no `OPENROUTER_API_KEY` (exit code 7).
- **Local runtime artifacts**
  - `git status --short` shows no `.council/`, `data/`, `.env`, `.venv/` staged.
  - `.gitignore` still covers all of the above.
- **Tagging**
  - `git tag -a v0.1.0 -m "vibe-council v0.1.0"` then `git push origin v0.1.0`
    (documented; performed by a maintainer, not by this PR).
- **GitHub release notes**
  - Create a Release for `v0.1.0`; paste the `CHANGELOG.md` v0.1.0 section; mark
    "latest". Note known limitations (OpenRouter-only, no Ollama/MCP, no demo asset).
- **Post-release verification**
  - Fresh clone → install → `vibe --version` shows `0.1.0`.
  - Release page renders; tag points at the right commit; CHANGELOG link works.

## Release notes / changelog scope (content for `CHANGELOG.md`)

[Keep a Changelog](https://keepachangelog.com/) format, semver. Two sections:

- **`## [Unreleased]`** — empty/placeholder for post-0.1.0 work.
- **`## [0.1.0] - <release date>` (draft)** — summarize what shipped across the prior
  PRs (this is a *first* public cut, so it's a feature inventory, not a delta):
  - **Workflow modes** — `extract`, `mini`, `review`, `full`.
  - **Presets** — `cheap`, `balanced`, `premium` (premium gated).
  - **CLI** — `python -m backend.cli` + global `vibe` command; `--version`,
    `vibe models`, `vibe presets`, `vibe status`, `vibe last`, `vibe guide`.
  - **`.council/` workspace** — project-local reviews/diffs/decisions/runs/stages/usage/locks.
  - **Decision memory** — `vibe extract --save`, `vibe decisions list/search/context`.
  - **Guards** — premium guard, token guard, cost guard, loop guard, `--usage`,
    `--save-stages`, dedicated exit codes.
  - **First-run key guard** — clear message + exit code 7 when `OPENROUTER_API_KEY`
    is missing.
  - **Tests / CI** — stdlib unittest smoke + structural tests; GitHub Actions on
    Ubuntu/macOS/Windows.
  - **Cross-platform install** — `install-vibe.ps1` / `install-vibe.sh`, POSIX + PS
    launchers, `vibe.cmd`.
  - **Examples / docs** — `examples/`, agent-integrations guide, plan docs.
  - **Privacy / local-first docs** — what leaves your machine vs. what stays local.
  - **Known limitations** — OpenRouter-only (BYO key); no Ollama / provider
    abstraction yet; no MCP yet; no real demo asset yet; decision search is plain
    string matching (no embeddings/SQLite).

## Out of scope (intentionally)

- **No real demo recording** (GIF / asciinema / mp4) and **no binary media** — guide
  only; the asset is a separately-approved follow-up.
- **No version bump or tagging executed here** — the checklist documents it; cutting
  the release is a maintainer action after this PR merges.
- **No core council logic / config / preset / CLI behavior changes** — docs only.
- **No Headroom / token-optimization spike** — later.
- **No Ollama / provider abstraction / MCP / SaaS / PyPI / `pipx`/`uvx` packaging** —
  post-v0.1.0 roadmap.
- **No new dependencies, no new tests required** — existing
  `python -m unittest discover -s tests -t .` must stay green (a trivial structural
  doc test is acceptable only if clearly high-value; default is to add none).
- **No `.council/` artifacts committed** — raw plan/diff reviews stay local-only.

## Decisions (resolved up front)

- **asciinema over GIF as the primary format** — text-based, tiny, copy-pasteable,
  redaction-friendly, and avoids capturing window chrome/paths. GIF is documented as
  an optional later derivative generated from the cast.
- **Ship the guide, not the asset** — recording spends credits and risks leaks;
  defer the actual recording to an approved follow-up. `docs/demo.md` carries a clear
  "asset not recorded yet" note so a reader isn't surprised by a missing player.
- **Changelog is a feature inventory for 0.1.0**, not a since-last-tag delta, because
  this is the first public release; `Unreleased` stays as the forward-looking bucket.
- **Don't bump the version in this PR** — keep `0.1.0-dev` so `main` stays clearly
  pre-release; the bump to `0.1.0` is the first checklist item at actual release time,
  avoiding a half-released state if this PR sits in review.

## Council feedback applied

Reviewed by vibe-council (`vibe review --preset balanced` on this plan; consolidated
multi-model critique; raw output local-only under `.council/`, cost ≈ $0.20).
"Conditionally approve with scope reduction and hardening." Applied the useful,
**in-scope** items; declined the code/CI/automation scope creep that the PR brief
explicitly defers.

**Applied (all documentation-only, fit the docs/release-prep scope):**

- **Harden the demo guide technically, not just procedurally.** `docs/demo.md` now
  recommends recording from a **disposable, hardened environment**: a neutral throwaway
  directory (e.g. `~/demo` / `C:\demo`), a **generic shell prompt**, **shell history
  disabled / a temp profile**, and a **dedicated low-quota demo API key that is
  rotated after recording**. Added a warning that **copy/pasting commands from another
  window can flash URLs/tokens** on screen.
- **Recommend concrete redaction tooling**, not "redact in post" hand-waving:
  `asciinema`'s text `.cast` is editable directly (`sed`/`asciinema` edit) to scrub
  paths/usernames, and the guide says to **scan the finished `.cast`/output for home
  paths, usernames, and `sk-or-v1-` before publishing**.
- **Concrete cost cap for the (future) recording.** The guide states a `balanced`
  demo run is **≈ $0.15–0.30 per review step** (real anchors from this project) and
  to **rehearse on `cheap`** so only the final take spends `balanced` credits — with a
  reminder that `--max-tokens` / `--max-cost` bound the blast radius.
- **Content-review the demo input.** Added a step to **eyeball `examples/plans/
  feature-plan.md`** for anything confidential before using it on camera (it's a
  committed sample, but the habit matters).
- **Release checklist: add a Rollback / abort procedure.** New section covering "a
  step failed / v0.1.0 is broken": delete the local + remote tag, fix forward with
  `v0.1.1`, and how to communicate it.
- **Release checklist: tier the items** into **Critical (blocking)**, **Recommended**,
  and **Contextual (OS-specific / if available)** so it's auditable, not a flat 20-item
  wall.
- **Define "safe v0.1.0" up front.** The checklist opens with a one-line threat model:
  the main release risks are leaking secrets/paths and shipping broken install/version
  state; "safe" = none of those reach the published tag.
- **Note tooling versions.** The demo guide names the `asciinema` it was written
  against; the checklist notes recording the Python version the release was validated
  with.
- **Record the `vibe status` path-leak as a real follow-up**, not just a documentation
  band-aid: the checklist/roadmap notes a future `--sanitize`/`--no-paths` flag so the
  root cause gets fixed later (out of scope to implement here).

**Declined (out of scope for a docs/release-prep PR — the brief defers these):**

- **Cut `docs/demo.md` entirely / replace with a GitHub issue** — the brief explicitly
  asks for the demo guide; a guide that says "asset pending" is the intended deliverable.
- **Record a real cheap/canned demo in this PR** — the brief says **no real demo asset
  yet unless approved**; recording (or building a canned-output simulator) is a
  separately-approved follow-up.
- **Reduce CHANGELOG to "Initial public release" + README link** — the brief asks for a
  feature inventory; that's the chosen format. (Future *deltas* will be normal Keep-a-
  Changelog entries from v0.1.1 on — noted in the file.)
- **`scripts/prepare-release.sh`, version-consistency CI, broken-link CI, secrets
  scanner in pre-commit, GitHub Issue-template checklist, `--sanitize` flag** — all are
  **net-new code / CI / behavioral changes**, explicitly out of scope. They're recorded
  as **future automation** in the checklist so the intent isn't lost.
- **Success metrics / launch-timeline / KPIs** — product-strategy concerns beyond a
  docs PR; a single "post-release verification" bullet is enough here.

### Diff review feedback applied

The implemented diff was reviewed by vibe-council (`vibe review --preset balanced` on a
gitignored temp diff under `.council/tmp/`). "Conditional approval — address security
and cost wording before merge." All the must-fix items were **documentation-only** and
applied; the code/CI suggestions were declined as out of scope (and recorded as future
automation).

**Applied (all doc-only, no scope expansion):**

- **Key rotation timing was too loose.** `docs/demo.md` now mandates a **fresh,
  dedicated, low-quota key created right before recording, rotated immediately after**,
  and states that **if a key is visible in the recording at all — even one frame — you
  delete the recording and treat the key as exposed** (don't ship an edited cast that
  ever held a live key).
- **Concrete username-safe demo path.** Replaced `~/demo` (which expands to
  `/home/<you>`) with `/tmp/vibe-demo-$(uuidgen | cut -d- -f1)` / `C:\Temp\vibe-demo`.
- **Secret detection is a floor, not a guarantee.** Both the demo guide and the release
  checklist now state `sk-or-v1-` is **OpenRouter-specific**, that a keyword grep misses
  cross-frame/escape-sequence/other-provider secrets, and recommend **`gitleaks` /
  `trufflehog`** as the real control — plus scanning any committed binary asset.
- **CHANGELOG links pointed at a non-existent tag.** Changed the `[0.1.0]` /
  `[Unreleased]` reference links to repo/tree URLs with a comment that they're
  **activated when the tag is cut**, so they don't 404 pre-release.
- **Cost figures are time-bound.** Timestamped the demo cost anchors ("as of 2026-06")
  and added an explicit **`--max-cost 0.50` per step** so re-takes can't drain the key.
- **Toolchain test before spending.** Added a 10-second hello-world recording step and
  an **8-item "minimal safe checklist"** at the top of the demo guide (addresses the
  "guide is dense, people will skim" concern without splitting into two files).
- **Rollback covers leaked secrets.** The checklist rollback section now has a
  "secret was committed/leaked" path (rotate, scrub history, re-cut), and an asset
  **size ceiling (~2 MB)** was added to the demo guide.

**Declined (out of scope / scope creep — recorded as future automation in the checklist):**

- **`--no-paths`/`VIBE_STATUS_REDACT` flag, `--mock`/`--dry-run` mode, `scripts/
  bump-version.py`, `scripts/scan-secrets.sh`, version-consistency CI, broken-link CI,
  GitHub issue-template checklist** — all **code/CI/new-script changes** the brief
  defers; left as a clearly-labeled "Future automation" list, not built here.
- **Splitting `docs/demo.md` into quick + deep-dive files** — addressed instead with
  the top-of-file minimal checklist; avoids more cross-linked files to keep in sync.
- **Consolidating the checklist's install + post-release sections** — kept distinct
  because the release brief calls for install checks *and* post-release verification as
  separate, separately-tickable steps; tiering already manages the cognitive load.
- **Pricing/Python-version pinning, demo refresh-cadence policy, deprecation policy** —
  speculative for a first cut; the timestamped estimates and "re-validate on CLI change"
  note are enough.
