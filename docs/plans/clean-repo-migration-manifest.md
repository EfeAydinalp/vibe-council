# Plan: upstream-derived inventory & clean-repo migration manifest

A **file-by-file inventory and migration manifest**, not an implementation. `vibe-council
v0.1.0` is published; it began as a fork of **`karpathy/llm-council`**. Prior audits
established: the upstream has **no clear LICENSE**, all **39 upstream baseline files still
survive in HEAD**, **no secrets/runtime artifacts** were ever committed, and the `.mailmap`
identity-normalization has merged. This manifest maps exactly what is upstream-derived, what
a clean public repo would include/exclude, and the recommended re-home sequence.

**Nothing is moved, deleted, rewritten, relicensed, or committed in this task.** Attribution
is preserved throughout. This is inventory/reporting only.

> **Status update (2026-06-29):** several recommended cleanups have since landed on
> `master`, so the inventory/tables below now describe the **pre-cleanup** HEAD and are
> kept as the design record. Done: `.mailmap` identity unify (#17); project-metadata
> rename + `CLAUDE.md` rewrite (#18); `uv.lock` sync (#19); **removal of the unused
> upstream web UI** — `frontend/`, `backend/main.py`, `backend/storage.py`, root `main.py`,
> `start.sh`, root `header.jpg` (#20); FastAPI/Uvicorn dependency removal (#21) and stale
> install-ref cleanup (#22); the `full`-mode ranking-parser fix (#23). **Still open:**
> licensing/provenance resolution and the `backend/council.py` clean-room rewrite.

Review date: **2026-06-28**. Baseline reference: last upstream commit
**`92e1fcc`** (karpathy, 2025-11-22), **39 files**. First vibe commit: `21884b6`
(2026-06-25). HEAD tracks **81 files** total (39 baseline + 42 vibe-original).

---

## A. Executive summary

- **Is a clean new repo technically feasible?** **Yes.** The product — the CLI — is almost
  entirely vibe-original (`backend/cli.py`, `guards.py`, `decision_memory.py`,
  `project_workspace.py`, all of `scripts/`, `tests/`, `examples/`, and nearly all `docs/`).
  The upstream-derived code is concentrated and separable.
- **Biggest blockers:**
  1. **Licensing (the gating blocker).** Upstream is unlicensed (= All Rights Reserved), so
     any code still *derived* from it cannot simply be relicensed. This must be resolved
     (permission from Karpathy and/or removal/rewrite of derived code) **before** a clean
     repo — see the separate [re-home strategy](rehome-repo-identity-strategy.md).
  2. **`backend/council.py`** — CLI-critical *and* the most upstream-derived backend file
     (the stage-orchestration + ranking concept descends directly from upstream). It can't
     just be deleted; it needs a clean-room rewrite to fully clear provenance.
  3. **The web-UI subsystem** (entire `frontend/` + `backend/main.py` + `backend/storage.py`)
     is ~28 files, largely *unchanged* from upstream, and **unused by the CLI** — high
     provenance liability, low product value.
- **Two concrete provenance defects found:** `CLAUDE.md` is **byte-identical to upstream**
  (still titled "Technical Notes for LLM Council", describes upstream behavior), and
  `pyproject.toml` is **byte-identical to upstream** — still `name = "llm-council"`,
  `description = "Your LLM Council"`. The package literally still identifies as upstream.
- **Recommended timing:** do the **license/provenance resolution + legacy cleanup in the
  current repo first**; create a clean repo (if at all) only **after** v0.2 provider
  abstraction rewrites the most-derived backend, and only after the manifest checklist (§H)
  passes. Do **not** re-home now.

---

## B. Upstream-derived inventory (all 39 baseline files — every one survives in HEAD)

Divergence is measured baseline(`92e1fcc`)→HEAD. Status legend: **A** delete/obsolete
candidate · **B** heavily modified / vibe-owned enough · **C** still substantially
upstream-derived · **D** unclear / needs manual review.

| Path | In baseline? | Current purpose | Divergence (±lines) | Status | Recommended action | Rationale |
|------|:---:|---|---|:---:|---|---|
| `backend/council.py` | yes | CLI core: stage orchestration, ranking parser | +279/−170 (335→444) | **D** | **rewrite (clean-room)** | CLI-critical *and* core concept/expression descends from upstream; heavy edits don't clear derivation. Top backend rewrite. |
| `backend/openrouter.py` | yes | OpenRouter HTTP client | +97/−27 (79→149) | **C** | **rewrite** (folds into v0.2 provider abstraction) | Derived httpx call; v0.2 replaces it with a provider interface anyway. |
| `backend/config.py` | yes | models/presets/modes config | +120/−12 (26→134) | **B** | keep (light review) | Mostly vibe (presets/modes/env), descends from a thin upstream skeleton. |
| `backend/storage.py` | yes | **web-UI** conversation storage | +21/−8 (172→185) | **C** | **delete** (with web UI) | ~8% changed; used only by `main.py`/frontend, **not** the CLI. |
| `backend/main.py` | yes | **web-UI** FastAPI server | +62/−23 (199→238) | **C** | **delete** (with web UI) | Web server for the React UI; CLI doesn't import it. |
| `backend/__init__.py` | yes | package + `__version__` | +2 (1→3) | **B** | keep | Trivial; vibe version string. |
| `frontend/**` (26 files) | yes | React web UI | mostly **0/0**; a few small | **C** | **delete / extract** | Near-identical to upstream, **unused by the CLI**, biggest provenance liability. (Incl. 2 vibe-added `DecisionRecord.*` that go with it.) |
| `CLAUDE.md` | yes | repo agent notes | **0/0 — IDENTICAL** | **C** | **rewrite** | 100% upstream, unchanged; still says "LLM Council" and describes upstream behavior. |
| `pyproject.toml` | yes | package metadata | **0/0 — IDENTICAL** | **D** | **rewrite** | Still `name="llm-council"`, `description="Your LLM Council"`; must become vibe-owned. |
| `header.jpg` | yes | upstream banner image | 0/0 (binary) | **C** | **delete/replace** | Upstream asset; `docs/header.jpg` (vibe) exists. Replace with vibe branding. |
| `main.py` | yes | 6-line entry shim | 0/0 | **C** | **delete/replace** | Upstream shim; CLI uses `python -m backend.cli`. |
| `start.sh` | yes | start backend+frontend | 0/0 | **C** | **delete** | Upstream script; superseded by `scripts/vibe.*` and tied to the web UI. |
| `README.md` | yes | project README | +575/−48 (87→614) | **B** | keep | Overwhelmingly vibe content; already carries karpathy attribution. |
| `.gitignore` | yes | ignore rules | +4 | **B** | keep | Vibe-owned enough. |
| `uv.lock` | yes | dependency lockfile | 0/0 | **B** | keep/regenerate | Generated artifact, not creative content; regenerate after pyproject rewrite. |
| `.python-version` | yes | `3.x` pin | 0/0 | **B** | keep | Trivial config, not derivative in any meaningful sense. |

> **Survival summary:** 0 of 39 baseline files were deleted; **39/39 survive.** The
> derivation is concentrated in (a) the web-UI subsystem (~28 files, mostly verbatim), (b)
> the shared backend core (`council.py`, `openrouter.py`), and (c) a handful of unchanged
> root assets (`CLAUDE.md`, `pyproject.toml`, `header.jpg`, `main.py`, `start.sh`).

### Vibe-original files (clean provenance — 42 files, not in baseline)
`backend/cli.py`, `backend/guards.py`, `backend/decision_memory.py`,
`backend/project_workspace.py`; all of `scripts/` (`vibe.ps1/cmd/sh`, `install-vibe.*`);
all of `tests/`; `CHANGELOG.md`, `.gitattributes`, `.mailmap`, `.env.example`,
`.github/workflows/ci.yml`; nearly all of `docs/` (plans, releases, demo, agent-integrations,
checklist) and `docs/header.jpg`; all of `examples/`; the 2 `frontend/.../DecisionRecord.*`
components (vibe-added, but live inside the to-be-removed web UI).

---

## C. Clean-repo include list (future baseline)

The product + its clean-provenance scaffolding:

- **CLI core (post-rewrite):** `backend/__init__.py`, `backend/cli.py`, `backend/config.py`,
  `backend/guards.py`, `backend/decision_memory.py`, `backend/project_workspace.py`, and
  **`backend/council.py` only after clean-room rewrite**, **`backend/openrouter.py` (or its
  v0.2 provider-abstraction replacement)**.
- **Tooling:** `scripts/` (all), `.github/workflows/ci.yml`.
- **Tests:** `tests/` (all).
- **Docs:** `docs/` (plans, releases, demo, agent-integrations, release-checklist),
  `examples/`, `README.md` (with strengthened attribution), `CHANGELOG.md`.
- **Config:** `.gitignore`, `.gitattributes`, `.python-version`, `.mailmap`, `.env.example`,
  a **rewritten** `pyproject.toml` (vibe name/metadata) + regenerated `uv.lock`.
- **Branding:** vibe banner (`docs/header.jpg` or new), **not** upstream `header.jpg`.
- **New provenance files (see §F):** `LICENSE` (once cleared), `THIRD_PARTY_NOTICES.md`,
  `NOTICE`, a rewritten vibe-specific `CLAUDE.md`.

## D. Clean-repo exclude list (must NOT enter a clean baseline)

- **Runtime / secrets (never were committed — keep it that way):** `.council/`, `data/`,
  `.env`, `.venv/`, raw council outputs, `__pycache__/`, `node_modules/`, `frontend/dist/`.
- **Upstream web-UI subsystem:** entire `frontend/`, `backend/main.py`, `backend/storage.py`
  (unless a deliberate decision is made to keep a UI — then it needs its own rewrite).
- **Upstream root assets:** `header.jpg` (upstream), `main.py` (shim), `start.sh`.
- **Un-rewritten derived code:** `council.py`/`openrouter.py` in their *current* form (include
  only the rewritten versions); upstream `CLAUDE.md` and `pyproject.toml` as-is.
- **Local-path leaks / stale demo-asciinema artifacts:** none currently tracked (verified);
  ensure none are introduced.
- **Stale branches & messy history:** a clean repo starts from a curated baseline commit; do
  not carry the pre-genericization historical commits or merged feature branches. (History
  itself is preserved in the *old* repo, kept public/archived — never hidden.)

## E. Rewrite / delete candidates (prioritized)

1. **Unused upstream web UI (delete/extract):** entire `frontend/` (26) + `backend/main.py` +
   `backend/storage.py`. **Highest value, lowest risk** — removes ~28 mostly-verbatim
   upstream files that the CLI doesn't use. Confirmed: nothing in the CLI path imports
   `main.py`/`storage.py`.
2. **Backend modules closely matching upstream (rewrite):** `backend/council.py`
   (clean-room — CLI-critical, most-derived), then `backend/openrouter.py` (naturally
   rewritten by the v0.2 provider abstraction).
3. **Unclear provenance (rewrite/verify):** `pyproject.toml` (still `name="llm-council"`),
   `CLAUDE.md` (byte-identical upstream) — both must become vibe-authored.
4. **Old docs describing upstream behavior (rewrite/retire):** `CLAUDE.md` is the prime case
   (describes the original architecture); audit any doc that still says "LLM Council" rather
   than vibe-council's CLI model.
5. **Upstream assets (replace):** `header.jpg`, `main.py`, `start.sh`.

## F. Required provenance / attribution files for a clean repo

- **README attribution:** keep + strengthen the existing visible credit to
  `karpathy/llm-council` ("derived from / inspired by"), with a short provenance paragraph —
  never weaker than today.
- **`THIRD_PARTY_NOTICES.md`:** list upstream (`karpathy/llm-council`) and all dependency
  licenses (audit `pyproject.toml`/`package.json` transitive deps for GPL/AGPL before
  choosing a project license).
- **`NOTICE`:** a concise attribution/credits file (useful if the project lands on Apache-2.0;
  optional under MIT but a clear provenance signal either way).
- **LICENSE decision status:** **UNRESOLVED — blocking.** Upstream has no license; do **not**
  add a `LICENSE` until the right to relicense the derived portions is established (Karpathy
  grant and/or full removal/rewrite of derived code). Tracked in the re-home strategy doc.
- **Release-notes attribution wording:** every release body should retain the
  "Based on and crediting `karpathy/llm-council`" line (already present in `v0.1.0.md`).

## G. Migration options

| # | Option | Pros | Cons | Verdict |
|---|--------|------|------|---------|
| 1 | **Current repo stays canonical after cleanup** | Zero migration risk; preserves history/stars/links; most transparent; fastest | Carries upstream history; personal-account branding | **Default / recommended** — cleanup *in place* delivers most of the benefit |
| 2 | **Clean new repo before v0.2** | Pristine first impression early | Ships still-derived `council.py`/`openrouter.py` → **moves the legal problem**; loses history/stars; looks like laundering at v0.1 | **Not recommended** — premature; derived code not yet cleared |
| 3 | **Clean new repo after provider abstraction** | v0.2 already rewrites `openrouter.py`; smaller derived surface to clear | Still needs `council.py` rewrite + licensing resolved first | **Viable later** — the realistic clean-repo window, *if* a move is still wanted |
| 4 | **Progressive clean-room rewrite, then (maybe) clean repo** | Strongest provenance; integrates into normal dev; keeps history/transparency | Slower; needs per-module tracking | **Recommended companion to #1** — rewrite derived modules incrementally; re-home becomes optional |

## H. Recommended sequence (checklist-gated)

1. **Commit the planning docs** (this manifest + the re-home/strategy docs) — record of intent.
2. **Upstream/legacy delete PR** — remove the unused web-UI subsystem (`frontend/` +
   `backend/main.py` + `backend/storage.py`) transparently (PR clearly states what/why). Biggest
   provenance-surface reduction, lowest risk. *(Separate task — not done here.)*
3. **Provenance fixes PR(s)** — rewrite `pyproject.toml` to vibe metadata + regenerate
   `uv.lock`; rewrite `CLAUDE.md` to describe vibe-council; replace upstream `header.jpg`/
   `main.py`/`start.sh`.
4. **Backend clean-room rewrites** — `council.py` (clean-room from behavioral spec), and
   `openrouter.py` via the v0.2 provider abstraction.
5. **License/attribution notices** — only after licensing is *resolved*: add `LICENSE`,
   `THIRD_PARTY_NOTICES.md`, `NOTICE`; strengthen README attribution.
6. **Decide clean-repo timing** — only once the manifest checklist (derived code cleared,
   notices in place, secret/artifact scan clean) passes.
7. **Create a clean-repo baseline only if chosen** — curated initial commit; keep the old repo
   public + archived with cross-links (never hide provenance).
8. **Continue v0.2 provider abstraction** throughout — cleanup must not block the roadmap.

## I. Risk matrix

| Dimension | Risk | Likelihood | Impact | Mitigation |
|-----------|------|:---:|:---:|-----------|
| Legal / provenance | Relicensing un-cleared derivative code | Med | **High** | Resolve upstream license first; rewrite/remove derived code before any LICENSE |
| Trust / attribution | Clean repo *looks like* hiding history | Med | High | Loud README provenance + `THIRD_PARTY_NOTICES` + keep old repo public/archived + cross-links |
| Development speed | Cleanup/rewrite delays v0.2 | Med | Med | Sequence delete-PR first (cheap), fold `openrouter` rewrite into v0.2, keep `council.py` rewrite incremental |
| Sponsor readiness | Package still identifies as `llm-council` | High (now) | Med | Rewrite `pyproject.toml`/`CLAUDE.md` early (cheap, high-signal) |
| Official-site branding | Personal-account/messy-history optics | Med | Med | Cleanup in place first; defer re-home decision to §G option 3/4 |
| Secret / runtime artifact inclusion | Artifacts leak into a new baseline | Low | High | Exclude list (§D) + full scanner pass before publishing any baseline; verified clean today |

---

## Constraints

- Inventory/reporting only. **No** repo move/creation, no deletions, no history rewrite, no
  LICENSE change, no attribution removal, no code changes, no dependencies.
- No council run in this task (inventory only).
- `.council/`, `data/`, `.env`, `.venv/` untouched and never staged; no secrets exposed.
- No commit, push, or PR.
