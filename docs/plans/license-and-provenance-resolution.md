# License & provenance resolution (Question 0)

> **Not legal advice.** This is an **engineer's provenance checklist and decision stub**, not a legal
> opinion or a commercial-clearance claim. Where a legal conclusion is needed, an attorney must review.
> Nothing here asserts that vibe-council is cleared for commercial use.

## Purpose

License/provenance is **"Question 0"** — the first blocker to resolve before serious commercialization.
This document records **what must be verified** before any of: paid offerings, hosted work, a private
commercial repo, or relicensing. It exists so the issue has an explicit **owner, status, open
questions, evidence trail, and a go/no-go gate** instead of a vague "must resolve later."

Public, local-first OSS development **continues** while this is being clarified; the gate applies to
*paid/commercial* steps (see "Commercial gate").

## Current known provenance (engineer's reading)

- vibe-council **descends from / was inspired by** [`karpathy/llm-council`](https://github.com/karpathy/llm-council)
  and has diverged substantially. **Attribution to the upstream project is preserved** and must remain
  so (it appears across `README.md`, `CHANGELOG.md`, `CLAUDE.md`, release notes, and decision records).
- Current project identity is **`vibe-council`**.
- **Observed facts (to verify, not conclusions):**
  - The upstream repository currently shows **no detected open-source license** (engineer's check via
    the GitHub API returned no license). An unlicensed upstream is the central risk to clarify.
  - vibe-council has **no `LICENSE` file** committed.
  - `pyproject.toml` declares **no `license` field** and no license classifiers.
- Related existing decisions/plans:
  [repo cleanup & provenance stance](../decisions/2026-06-29-repo-cleanup-and-provenance.md),
  [clean-repo migration manifest](clean-repo-migration-manifest.md),
  [rehome repo identity strategy](rehome-repo-identity-strategy.md).

## What must be checked

- **Upstream repository license status** — licensed, unlicensed, or unclear; and what that implies.
- **What files still substantially derive** from upstream (vs. independently rewritten).
- **Whether any copied snippets or third-party code** exist anywhere in the tree.
- **Dependency licenses** (runtime + dev) — are they all permissive/compatible?
- **Test / demo / example provenance** — any content derived from upstream or third parties?
- **Docs / research provenance** — any copied third-party text (vs. summaries/links)?
- **Package metadata** — does anything imply a license today? (Currently: no.)
- **Whether a `LICENSE` file should exist**, and which license — *only after* provenance is understood.
- **Whether attribution is sufficient** for the chosen path.
- **Whether a clean-room rewrite or further cleanup** is needed for any derived files.
- **Whether commercial use, hosted use, paid support, or a private commercial repo is blocked** by any
  of the above.

## Proposed review checklist

Status legend: `unknown` · `in-progress` · `clear` · `blocked`. Owner is the project maintainer
(`@EfeAydinalp`) unless reassigned. "Target" = before the gate (first paid offering / v0.5), earlier
where noted. **None of the `clear` cells below are asserted yet** — all start `unknown`.

| Item | Status | Evidence | Owner | Target | Notes |
|------|--------|----------|-------|--------|-------|
| Upstream license status | unknown | GitHub API shows no detected license for `karpathy/llm-council` (engineer's check) | @EfeAydinalp | before v0.5 | Unlicensed upstream ⇒ default all-rights-reserved by upstream author; needs careful reading |
| Upstream attribution | in-progress | Attribution present in README/CHANGELOG/CLAUDE/releases/decisions | @EfeAydinalp | ongoing | Must be preserved on any path; confirm it is sufficient for the chosen outcome |
| Derived code inventory | unknown | Not yet inventoried; `CLAUDE.md` notes parts still descend from upstream | @EfeAydinalp | before v0.5 | List files substantially derived vs. independently rewritten (e.g. `main.py`/`storage.py` web-UI lineage) |
| Dependency license inventory | unknown | `pyproject.toml`: `python-dotenv`, `httpx`, `pydantic` (+ stdlib) | @EfeAydinalp | before v0.5 | Confirm each runtime/dev dep is permissive/compatible |
| Docs/research provenance | unknown | Research audits summarize/link external repos; no third-party code copied (by policy) | @EfeAydinalp | before v0.5 | Re-confirm no verbatim third-party text; links/summaries only |
| Examples/demo provenance | unknown | `examples/`, `docs/demo*` exist | @EfeAydinalp | before v0.5 | Confirm not derived from upstream/third parties |
| Package metadata license field | clear (factual) | `pyproject.toml` has no `license` field/classifiers | @EfeAydinalp | n/a | Factual current state; decide intended value with the LICENSE decision |
| Repository `LICENSE` decision | unknown | No `LICENSE` file committed | @EfeAydinalp | before v0.5 | **Do not add a LICENSE until provenance is understood** |
| Commercial use risk | unknown | Depends on the above | @EfeAydinalp | before v0.5 | Gate for paid offerings |
| Hosted/private-repo risk | unknown | Depends on the above | @EfeAydinalp | before v0.5 | Gate for hosted/team/private commercial work |
| Need for attorney review | unknown | TBD after the inventory | @EfeAydinalp | before v0.5 | If derived-code/licensing is unclear, pause commercial steps and get counsel |

## Commercial gate

- **No serious paid commercialization until this is resolved.** Gated items include: support /
  consulting, paid council/skill packs, hosted sync, a private commercial repo, and any public
  **licensing/commercial-clearance claim**.
- **Public, local-first OSS development can continue** while the issue is being clarified.
- **Any public claim stays conservative** — no statement that the project is "commercially cleared,"
  "MIT-licensed," or "safe to resell" until the review supports it.

## Possible outcomes

- **Clear** — provenance understood and compatible: add/confirm a `LICENSE` + attribution, set the
  `pyproject` license field, and lift the gate.
- **Needs cleanup** — remove or rewrite unclear/derived files, then re-evaluate.
- **Needs attorney review** — pause commercial steps until counsel advises.
- **Blocked** — the commercial path requires a new clean repo or a deeper rewrite.

## Next actions

1. Identify upstream license **evidence** (capture what the upstream repo states today).
2. **Inventory derived files** (substantially-from-upstream vs. independently written).
3. **Inventory dependency licenses** (runtime + dev).
4. Decide a **proposed license** (only after 1–3).
5. Decide whether **attorney review** is needed.
6. Create a **final resolution decision record** later, when resolved, and lift the gate if `clear`.

This stub stays open until a final resolution decision supersedes it.
