# Plan: terminal-demo-asset

Add a **safe, small, public** terminal demo artifact for vibe-council that shows the
real user-facing workflow — without exposing secrets, API keys, local private
paths/usernames, or raw `.council/` outputs. Follows the redaction rules in
[`docs/demo.md`](../demo.md). **Demo asset + docs only** — no core council logic,
config, preset, or CLI changes, and **no version bump**.

## Artifact decision: fallback transcript (asciinema unavailable)

- **Preferred** would be a committed asciinema `.cast` under `docs/assets/demo/`.
- **Reality:** `asciinema` is **not installed / not available on this Windows dev
  environment** (it is a Unix-oriented tool with no first-class Windows recorder), and
  `agg` (the cast→GIF converter) is also absent. Installing a recorder and producing a
  real cast is out of reach for this PR.
- **Therefore this PR ships the fallback:** a **sanitized terminal transcript** at
  **`docs/demo-transcript.md`**, honestly labeled as a *hand-sanitized transcript of
  real command output* — **not** an asciinema recording. The real `.cast` / GIF stays
  an explicit follow-up.

**Honesty rule (non-negotiable):** the transcript must **not** claim to be a real
recording. It is captured from genuinely-run commands with local paths/usernames
replaced by generic placeholders; that provenance is stated at the top of the file.

## What the transcript will contain (exact safe demo scenario)

A short, linear walkthrough of the user-facing loop. Commands are run for real; output
is pasted then sanitized.

1. `vibe --version` → `vibe-council 0.1.0-dev` (no-model, free).
2. `vibe status` → workspace summary (no-model, free) — **project path shown as a
   generic placeholder**, e.g. `/home/dev/vibe-demo`.
3. `vibe presets` → preset table (no-model, free).
4. `vibe models` → configured model IDs per preset (no-model, free).
5. Show a short, **self-contained generic throwaway plan** (`~/vibe-demo/plan.md`,
   created in the disposable dir — references nothing private; the committed
   `examples/plans/*.md` work identically) with `cat`.
6. A **small review** command — `vibe review --preset cheap --file ... --usage`.
   Show the command, a **short representative** consolidated-review excerpt (the review
   text is plain markdown advice — no provider headers), and the `[saved] …` +
   `[usage] …` lines with the **artifact path placeholder-ized**.
7. A **small extract** command — `vibe extract --preset cheap --file ... --save --usage`.
   Show the decision summary block, the `[saved] …` JSON/MD **artifact paths only**
   (placeholder-ized), and the `[usage] …` cost line.
8. Show **only the artifact paths** that were written under `.council/` — never the raw
   file contents.
9. `git status --short` proving **`.council/` is untracked / not staged**.

The model steps use **`--preset cheap`** (smoke/retry tier per council policy) to keep
cost minimal; the real cost is reported in the final report.

## How secrets / local paths are prevented

- **Disposable demo directory** — run the model steps from a throwaway dir (under the
  session scratchpad, never the real repo root for anything that prints an absolute
  path), so the workspace path isn't my real home path. Any path that still appears is
  **replaced with a generic placeholder** (`/home/dev/vibe-demo`, `~/vibe-demo`).
- **No secrets on screen** — never `cat .env`, never echo `OPENROUTER_API_KEY`; vibe
  never prints the key itself.
- **No raw `.council/` contents** — show the `[saved] …` *paths* only, not the files.
- **No provider request details** — `--save-stages` is **not** used; no HTTP/debug
  logs; the review excerpt is the model's plain-markdown advice, which carries no
  request headers, tokens of the key, or endpoints.
- **Generic prompt / filenames** — use the committed `examples/plans/*.md` as inputs so
  nothing private is referenced.

## How the artifact is reviewed before commit

A scripted secret/path scan over `docs/demo-transcript.md` (and any other added file)
**before staging and again in final checks**, grepping for:
`sk-`, `sk-or-v1-`, `OPENROUTER_API_KEY`, `.env`, `C:\Users\`, my real username, other
absolute home paths, raw `.council/` content markers, and provider request headers.
Any hit blocks the commit until sanitized.

## Files to add / change

**Add**

- `docs/demo-transcript.md` — the sanitized transcript (clearly labeled; provenance
  note; the scenario above; a "what's redacted and why" footer; link back to
  `docs/demo.md`).

**Change**

- `README.md` — in the existing **Demo** subsection, link `docs/demo-transcript.md` as
  a *sanitized text walkthrough*, and keep the note that a real asciinema/GIF is still
  a follow-up.
- `docs/demo.md` — add a short note that a **sanitized transcript is committed** at
  `docs/demo-transcript.md` as the current best-available artifact, while the real
  `.cast`/GIF recording remains the approved follow-up (the recording *guide* itself is
  unchanged).

**Maybe (only if trivial)**

- `docs/plans/README.md` — add this plan to the index (consistent with prior plans).

**Do NOT add**

- Any **binary media** (`.cast` is text, but we're not producing one here; no `.gif` /
  `.mp4` / `.png`). `docs/assets/demo/` stays unborn until a real recording is approved.

## Out of scope (intentionally)

- **No real asciinema/GIF recording** — the tool isn't available here; that asset is a
  separately-approved follow-up. We do **not** fake a recording.
- **No core council logic / config / preset / CLI changes** — demo + docs only.
- **No version bump / tagging** — stays `0.1.0-dev`.
- **No new dependencies** (not installing asciinema in CI/repo), **no new tests
  required** — existing `unittest` suite must stay green; a structural test for the
  transcript is optional and only if trivially high-value.
- **No provider abstraction / Ollama / MCP / Headroom / SaaS / PyPI / CLI refactor.**
- **No `.council/` artifacts committed** — raw plan/diff reviews stay local.

## Decisions (resolved up front)

- **Fallback over nothing:** asciinema being unavailable, a clearly-labeled sanitized
  transcript is the honest best-available artifact; it delivers real user-facing value
  now and doesn't block on tooling we can't install here.
- **`cheap` for the model steps:** the demo only needs to *show the workflow runs and
  writes artifacts*, not to produce a flagship review — so the smoke/retry tier is the
  right cost/quality trade-off and matches council policy for non-gate runs.
- **Input is a self-contained generic plan** authored in the disposable dir (the
  committed `examples/plans/*.md` work the same) so the transcript references nothing
  private and stays reproducible.

## Council feedback applied

Reviewed by vibe-council (`vibe review --preset balanced` on this plan; consolidated
multi-model critique; raw output local-only under `.council/`, cost ≈ $0.17).
"Conditional approval with hardening." The review pushed hard toward CI enforcement,
pre-commit hooks, a two-person review, generation/scan scripts, and a dedicated
revocable demo key — most of which are **infra/process changes the brief explicitly
excludes** ("demo asset/docs only", no CLI/tooling drift). Applied the useful,
**doc-only** hardening; declined the scope creep (recorded, not silently dropped).

**Applied (doc-only, in scope):**

- **Strong provenance header** in `docs/demo-transcript.md`: states it is a
  **sanitized transcript, not a byte-for-byte recording**; the **CLI version + commit
  SHA** it was captured at; the **capture date**; that **live output may differ**
  (terminal width, colours, model wording, pricing); and a link to `docs/demo.md` for
  the redaction methodology. Directly answers the "honest labeling + staleness" risks.
- **Centralized placeholder/redaction table** — a single "what was replaced and why"
  section listing every placeholder (`/home/dev/vibe-demo`, generic prompt, etc.) so
  redaction is explicit and consistent, not ad-hoc.
- **Capture-from-real-output discipline** — the transcript is pasted from genuinely-run
  commands at the stated commit (not hand-invented), which *is* the "verify against
  reality before commit" step the review asked for; the Task-8/Task-14 secret scans
  bracket it.
- **`.council/` is internal, not an API** — added a one-line note that the workspace
  layout/filenames are local runtime detail and **not a stable interface**, so showing
  artifact paths doesn't create a quasi-contract.
- **Scanner is a floor, not a guarantee** — the prescribed grep set (`sk-`,
  `sk-or-v1-`, `OPENROUTER_API_KEY`, `.env`, `C:\Users\`, username, home paths,
  `.council/` content, provider headers) is run, but the transcript/footer points to
  `gitleaks`/`trufflehog` as the stronger control (already recommended in
  `docs/demo.md` and the release checklist).
- **Name the real-recording path** — the follow-up note says the genuine `.cast` should
  be produced on **Linux / WSL / a container / Codespaces** (where asciinema runs),
  acknowledging the review's "Windows isn't a permanent constraint" point.
- **No key material is ever rendered** — the model steps run from a disposable dir on
  the existing key; the transcript shows only commands, advice text, artifact *paths*,
  and `[usage]` cost lines — never the key, `.env`, or raw `.council/` files.

**Declined (out of scope for a demo-asset/docs PR — the brief excludes these):**

- **`tools/gen-demo-transcript.sh` + `tools/scan-demo-secrets.sh` scripts, pre-commit
  hook, CI secret-scan job, build-fails-on-detection** — net-new tooling/CI/behavioral
  changes; the brief says demo asset/docs only and "no CLI refactors". Recorded as
  *future automation* (the release checklist already tracks gitleaks/trufflehog-in-CI).
- **Dedicated, rate-limited, revoked demo API key** — sensible for a *video* where a
  key could flash on screen; unnecessary for a **text transcript that never renders the
  key**. Noted in the provenance header that no key is shown.
- **Mandatory two-person sign-off + a tracking issue with a hard deadline** — process
  the brief doesn't ask for; the human approval gate on this PR is the review step, and
  the follow-up is documented in `README.md`/`docs/demo.md` rather than auto-filed.
- **Showing error/failure scenarios** — the demo is the happy-path user loop; failure
  modes are documented elsewhere (exit codes in README).
- **Switching tools to `terminalizer`/PowerShell `Start-Transcript`** — would still
  produce a redaction-sensitive artifact; a clearly-labeled sanitized transcript is the
  honest best-available artifact now, with the real `.cast` as the approved follow-up.

### Diff review feedback applied

The implemented diff was reviewed by vibe-council (`vibe review --preset balanced` on a
gitignored temp diff under `.council/tmp/`; one model hit a transient network error, the
others produced a full consolidated review). "Conditional approval." Applied the useful
doc-only items; declined the (again) CI/automation/tooling scope creep.

**Applied:**

- **Real plan↔transcript inconsistency (the legitimate catch).** The plan said the demo
  would `cat examples/plans/small-doc-fix.md`, but the transcript actually uses a
  self-contained generic `~/vibe-demo/plan.md`. Reconciled the **plan** to match the
  implementation (self-contained generic plan; committed examples work identically), so
  plan and artifact agree.
- **Regeneration recipe + staleness policy.** Added a "Status: stopgap, not the final
  demo" section to `docs/demo-transcript.md` with a concrete **how-to-regenerate-safely**
  procedure and an explicit "regenerate when CLI version / presets / models / output
  format change" rule — the doc-only answer to the staleness risk (no CI needed).
- **Stopgap framing sharpened.** The transcript now states plainly it's a **placeholder**
  and the **real asciinema cast is the accepted target** (not merely a "nice-to-have").
- **Trimmed a possible path hint.** Softened the redaction-table wording from
  "`Temp\…\vibe-demo`" to "a disposable temp directory" so the header doesn't even
  suggest the local path shape.

**Declined (out of scope / scope creep — brief excludes tooling/CI):**

- **Produce the asciinema cast now via WSL/Docker/Codespaces** — that *is* the approved
  follow-up; this PR's whole remit is the best-available fallback. Documented the
  Linux/WSL/container path for the follow-up rather than installing it here.
- **`tools/generate-demo-transcript.sh` / `sanitize-demo.sh` / `scan-demo.sh`, CI
  staleness check, golden-file output test, build-fails-if-HEAD-ahead** — net-new
  scripts/CI/tests; recorded as future automation, not built in a docs PR.
- **Auto-file a tracking issue** — outside this PR's approved actions; the follow-up is
  documented in `README.md`, `docs/demo.md`, and the transcript instead.
- **Soften exact `$0.014958`/token figures to "cents"** — those are the **real `[usage]`
  lines vibe printed**; keeping them is more honest, and the provenance header already
  disclaims that pricing/output drift over time.
- **Slim to 4–5 commands** — the brief's suggested flow is the 8 steps shown; the length
  matches the requested walkthrough.
