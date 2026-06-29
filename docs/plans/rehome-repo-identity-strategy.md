# Plan: re-home / repository-identity strategy

A **strategy/planning review**, not an implementation. `vibe-council v0.1.0` is published at
`EfeAydinalp/vibe-council`. The question: for the official site, sponsor readiness, and
long-term open-source identity, should the project **stay in the current repo** or move to a
**clean public home** — and what license/provenance cleanup must happen first? This is the
right moment to decide because we're still at v0.1.0, before the v0.2 provider-abstraction
work expands the surface further.

**Nothing is transferred, created, deleted, rewritten, or relicensed in this task. No
attribution is removed. No commit/push/PR.** Council runs use **`review --preset balanced`**
only (not `full`, due to a known None-content ranking-parser bug), always `--usage`; raw
`.council/` output stays local.

> **Status update (2026-06-29):** since this review, low-risk cleanup has landed on
> `master`: `.mailmap` identity unify (#17), project-metadata rename + `CLAUDE.md` rewrite
> (#18), and removal of the unused upstream web UI (#20) — so the "all 39 upstream baseline
> files survive" framing below is now partly historical. The `full`-mode parser bug noted
> above has also been fixed (#23). The core recommendation is **unchanged**: stay in the
> current repo, resolve licensing/provenance first, defer any re-home.

Review date: **2026-06-28**.

---

## Current repo state (verified from git history)

- **Home:** `EfeAydinalp/vibe-council` (fork; `upstream` remote = `karpathy/llm-council`).
- **History shape:** **40 commits**, **15 merge commits** (PR-based workflow, ~#1–#16),
  one tag **`v0.1.0`**, one published GitHub Release.
- **Authorship:** the first **5 commits are karpathy's** original `llm-council` baseline
  (2025-11-22, "v0", label maker, etc.); the remaining **35 are the project owner's** — but
  under **two distinct author identities**: `Efe Aydinalp
  <77501077+EfeAydinalp@users.noreply.github.com>` (19) and `aydinalpefe
  <aydinalpefe@gmail.com>` (16). The split identity is part of what reads as "messy."
- **Provenance footprint:** **every one of the 39 upstream baseline files still survives in
  HEAD** — the entire `frontend/` React app, `header.jpg`, `start.sh`, `main.py`,
  `pyproject.toml`, and the original `backend/` modules (`council.py`, `openrouter.py`,
  `storage.py`, `main.py`, `config.py`). The backend files are heavily modified but *descend*
  from karpathy's code; much of `frontend/` appears largely upstream and predates the CLI
  workflow (per `CLAUDE.md`, the React UI is now drifted/legacy).
- **Diff baseline→HEAD:** 56 files changed, ~7,963 insertions / 302 deletions — lots added,
  little removed. The legacy upstream surface is still carried.

## Current license / attribution uncertainty (the crux)

- **The upstream `karpathy/llm-council` baseline shipped with NO LICENSE file** (verified:
  no license/notice in the first commit). Under default copyright, an unlicensed work is
  **all rights reserved** — there is no granted permission to copy, modify, or redistribute.
- **vibe-council currently also has NO LICENSE file** (confirmed in the prior governance
  audit) and is a **derivative of an unlicensed upstream**.
- **Implication:** we cannot simply add `LICENSE: MIT` and call it clean. For the portions
  that still descend from karpathy's code, vibe-council has **no clear redistribution right**
  to relicense. Options to resolve:
  1. **Obtain explicit permission / a license grant** from Andrej Karpathy for the derived
     portions (cleanest if attainable);
  2. **Remove/replace** the upstream-derived code so the project no longer depends on it
     (the "legacy cleanup" + possible clean-room path); or
  3. **Confirm upstream's intended license** (some `karpathy/*` repos are MIT, but *this*
     one carries no license file — intent must be confirmed, not assumed).
- This is the single most important input to the re-home decision: **provenance, not
  cosmetics.** A clean public home built on un-cleared derivative code would *increase* legal
  exposure, not reduce it.

> **This document does not change any license.** It records the uncertainty so the council
> and the maintainer can decide the cleanup sequence. Resolving licensing is a prerequisite
> step, handled separately and explicitly.

---

## The four options

### Option A — Keep current repo canonical
Continue in `EfeAydinalp/vibe-council`; preserve full PR/release/decision history; clean
README/license/attribution/governance in place; remove unused upstream/legacy code; point
the official site at the current repo.

### Option B — GitHub transfer ownership
Transfer the existing repo to a new account/org. Commit history, issues, PRs, releases,
stars, and `github.com` redirects are **preserved**. New owner/branding, but the **old
history (including the messy parts and the karpathy baseline) remains fully visible**.

### Option C — Clean new repo / curated initial history
Create a new dedicated repo/org later (e.g. `vibecouncil/vibe-council`). Start from a **clean
initial commit** ("vibe-council v0.1.0 baseline") containing only **audited** source/docs/
tests. Do **not** carry the messy early PR history. Keep **professional attribution/
provenance** in README + `THIRD_PARTY_NOTICES.md`. Retain the old repo as archive/reference
(public or private per best practice). Official site points to the new clean repo.

### Option D — Clean-room rewrite before re-home
Write a spec from current observable behavior, then reimplement **without copying upstream-
derived code**. Strongest provenance cleanliness; slowest. Question: overkill before v0.2, or
the only fully-clean path given the unlicensed upstream?

---

## Pros / cons

| Option | Pros | Cons |
|--------|------|------|
| **A — Keep current** | Zero migration risk; preserves stars/links/SEO/history; most transparent (nothing hidden); fastest; honest provenance | Carries "messy" two-identity history + legacy upstream code; does **not** resolve the unlicensed-derivative problem by itself; personal-account (not org) branding |
| **B — Transfer** | Keeps stars/issues/PRs/releases + URL redirects; re-brands owner/org cheaply | **Does not solve the stated concern** — messy history and karpathy baseline stay fully visible; still derivative of unlicensed upstream; one-way-ish, adds confusion if reversed |
| **C — Clean new repo** | Professional first-impression for site/sponsors; drops messy history; ships only audited code; org branding | Loses stars/PR history/community signal; **risky if it ships un-cleared derivative code** (the legal problem moves with the code); can *look* like history-hiding if attribution is weak |
| **D — Clean-room rewrite** | Strongest legal/provenance posture; removes the unlicensed-derivative dependency entirely | Slow; high effort; risks reintroducing bugs; likely **overkill at v0.1.0**; delays v0.2; only the *upstream-derived* parts actually need it |

---

## What GitHub will show after each option

**Question 2 — Clean new repo (Option C):**
- **Commit authors:** only whoever authors the curated initial commit(s) — the karpathy
  baseline commits and the two-identity owner history are **not** carried (unless
  deliberately preserved). Past contributors do **not** appear in the new commit graph.
- **Contributors tab:** reflects only the new repo's commits.
- **Tags/releases:** start fresh (re-create `v0.1.0` as the baseline release).
- **Old-repo relationship:** **not automatic** — only what you state in README/links. This is
  exactly why attribution must be explicit, or it looks like provenance was erased.
- **Attribution text:** whatever you put in README + `THIRD_PARTY_NOTICES.md` / `NOTICE` — the
  *only* place provenance survives.

**Question 3 — GitHub transfer (Option B):**
- **Commit history:** **fully preserved** (including karpathy's baseline and the two-identity
  commits).
- **PRs / issues / releases:** preserved and moved with the repo.
- **Original contributors:** remain visible in history and the contributors graph.
- **Old URL redirects:** GitHub **301-redirects** the old `EfeAydinalp/vibe-council` paths to
  the new location (until/unless the old name is reused). Stars move with the repo.
- **Net:** transfer **re-brands ownership but preserves everything the user finds "messy."**
  If the concern is *visible messy history*, transfer does not address it.

---

## Recommended migration sequence (provenance-first)

1. **License/provenance audit** (no code changes) — determine, file-by-file, what descends
   from karpathy's unlicensed baseline vs. what is original. Resolve the license path:
   seek a grant from Karpathy **and/or** plan removal/replacement of derived code.
2. **Governance/attribution hygiene** — add `LICENSE` (only once the right to do so is
   established), `THIRD_PARTY_NOTICES.md`, a `NOTICE`/credits line, `.github/FUNDING.yml`;
   strengthen the existing README attribution to karpathy.
3. **Upstream/legacy cleanup** — inventory and remove genuinely unused upstream code (the
   drifted `frontend/` React app is the prime candidate), shrinking the derivative footprint
   *in the current repo* (a normal, transparent cleanup — not erasure).
4. **Secret/path scan + artifact exclusion** — run a real scanner (gitleaks/trufflehog) over
   the tree/history; confirm `.council/`, `data/`, `.env`, `.venv/` are excluded; no absolute
   dev paths leak.
5. **Decide A vs. C** — only *after* 1–4. If the derivative footprint is cleared/cleared-by-
   permission and the history is acceptably tidy, **A** wins (cheapest, most honest). If a
   pristine public first-impression genuinely matters for sponsors/site **and** provenance is
   preserved in README/NOTICES **and** the old repo is retained as a public archive, **C** is
   defensible. **B is not recommended** for the stated concern. **D** only if the audit shows
   the derived code can't be cleared and can't be cheaply removed.
6. **(If C)** create the new home, re-tag `v0.1.0` baseline, link old↔new both directions,
   keep the old repo public + archived (read-only) so no one thinks history was buried.

## Risk matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Relicensing un-cleared derivative code | Med | **High** (legal) | Audit first; get grant or remove derived code before any LICENSE |
| Clean repo *looks like* hiding attribution | Med | High (trust) | Loud README provenance + `THIRD_PARTY_NOTICES` + keep old repo public/archived + cross-links |
| Losing stars/community signal (Option C) | High | Med | Weigh signal vs. fresh-start value; only move if it clearly helps sponsors/site |
| Transfer (B) fails to solve the concern | High | Med | Recognize history is preserved; don't pick B for a "messy history" goal |
| Re-home churn delays v0.2 | Med | Med | Sequence after audit/cleanup; don't block provider work on branding |
| Secret/path in history surfaces post-move | Low | High | Scanner over full history *before* publishing any new home |
| Two author identities persist as "messy" | High | Low | Optional `.mailmap` to unify identity (display-only, no history rewrite) |

---

## Proposed stance (before council)

1. **Do not transfer ownership yet.** Transfer (B) preserves the exact history the concern is
   about, so it doesn't solve the problem.
2. **Do not hide attribution** — provenance to `karpathy/llm-council` stays visible and gets
   *stronger*, not weaker, whatever option is chosen.
3. **First do a license/provenance audit** — this is the gating step because the upstream is
   **unlicensed**, so the right to relicense/redistribute the derived parts is unsettled.
4. **Then do upstream/legacy cleanup** — remove genuinely unused upstream code (esp. the
   drifted `frontend/`) transparently, shrinking the derivative footprint.
5. **Then decide current-repo (A) vs. clean-new-repo (C)** — *before* provider implementation,
   so v0.2 lands in the intended home.
6. **A clean new repo (C) before v0.2 can be valid** *iff* attribution/notices are preserved
   and the **old repo is retained as a public archive/reference** (so nothing looks buried).
7. **GitHub transfer (B) is probably not enough** if the concern is visible messy history,
   because transfer preserves history.

## Main question for the council

> **Which re-home option (A keep / B transfer / C clean new repo / D clean-room) best serves
> open-source trust, sponsor readiness, professional branding, and legal/provenance safety —
> given that the upstream is *unlicensed* and the derivative footprint is still large — and is
> v0.1.0 the right time, or should re-home wait until after v0.2?**

Sub-questions:
- Does the unlicensed-upstream fact change the calculus toward removal/clean-room, or is an
  attribution + permission path sufficient?
- Is Option C's loss of stars/history worth the cleaner first impression, or is A's
  transparency the stronger trust signal for an open-source project?
- Minimum cleanup gate before *any* re-home?
- Reserve `vibecouncil.dev` / an org now, or later?

## Council guidance summary

Ran `review --preset balanced` against this doc (2026-06-28). Output is advice to filter,
not authority — the section below is the **human-curated** reading, not a verbatim apply.
Raw output stayed in the gitignored `.council/`. The council's core reframe: **the "messy"
history is not the problem — the unlicensed-derivative code is.** Solve licensing first;
the re-home choice is downstream and mostly answers itself once provenance is clean.

### Recommended option
**Option A (keep the current repo), with a progressive clean-room fallback — not B, not C.**
- **B (transfer)** is "A with a new URL": it preserves the exact history the concern is
  about and solves nothing legal. Drop it.
- **C (clean new repo)** *increases* legal exposure — it moves derivative code into a
  "clean-branding" context (looks original while carrying unlicensed derivatives) and, at
  v0.1.0, reads as history-laundering while throwing away stars/contributor-graph/community
  signal. Only revisit *after* licensing is 100% cleared, and even then transparency should
  outweigh aesthetics.
- **The real decision is binary:** if upstream licensing can be **cleared** → **A** (add
  LICENSE/NOTICES, keep history, ship v0.2 from the current repo; consider an org move later
  once there's traction). If it **can't** → a **progressive clean-room rewrite** (the
  council's Alternative 2): keep the current repo, file a tracking issue per derivative
  module, and replace upstream-derived code incrementally *as part of v0.2+*, adding the
  LICENSE only once derivative code is gone. **D (big-bang rewrite)** is overkill; do it
  incrementally instead.

### Is v0.1.0 the right time?
**Right time to resolve *licensing*; wrong framing to rush *re-homing*.** Legal risk doesn't
scale with code volume (one derivative file ≈ same exposure as 100), so "before the surface
grows" is a weak reason to move. The genuine timing question is: **can licensing be settled
before v0.2 work deepens entanglement with derived code?** Re-home (if ever) waits until
provenance is clean.

### What must happen before any re-home
A strict, ordered gate (the council tightened my sequence):
1. **Secret/history scan first (step 0, not step 4)** — gitleaks/trufflehog over the **full
   40-commit history**; confirm `.council/`/`data/`/`.env` never landed in history.
2. **Resolve upstream licensing** — treat "no LICENSE" as **All Rights Reserved**, not
   "uncertain." Contact Karpathy with a specific, time-boxed (≈30-day) request to clarify
   `llm-council`'s license / grant relicensing permission, **with a no-response fallback
   defined up front** (→ progressive rewrite). Get **qualified open-source IP counsel** —
   this doc is preparation, not a substitute (budget ~$2k–$10k).
3. **Provenance audit** — file-by-file derivative vs. original; note that "heavily modified
   but descends from" backend modules is a *legal* (derivative-vs-transformative) call, not
   just a technical one. The backend is the real liability; the unused `frontend/` is the
   easy win but not the whole story.
4. **Governance/attribution hygiene** — LICENSE *(only once the right exists)*,
   `THIRD_PARTY_NOTICES.md`, `NOTICE`, `FUNDING.yml`; also audit **dependency** licenses
   (`pyproject.toml`/`package.json`) for GPL/AGPL incompatibility before picking a license.
5. **Trivial fixes now, unconditionally** — add a **`.mailmap`** to unify the two author
   identities (display-only, no history rewrite). This alone dissolves the "cosmetic
   messiness" worry.

### How to handle the old repo
If a move ever happens (Option C, post-clearance only): keep the old repo **public + archived
(read-only)** with **bidirectional cross-links**, so nothing looks buried. But the council's
stronger point is to **not move at all** — preserving the real history *is* the trust signal;
the contributor graph and 35 commits of work are an asset, not a liability.

### How to handle attribution
Make it **stronger and unmissable**, never weaker: keep the visible README credit to
`karpathy/llm-council`, add a `NOTICE`/credits line + `THIRD_PARTY_NOTICES.md`. A clean repo's
provenance survives *only* in the text you write, which is exactly why C is risky. Whatever
path: attribution goes up, not down.

### How to handle license uncertainty
**Reclassify it from "uncertainty" to "blocking constraint."** Do **not** assume Karpathy
"probably meant MIT"; do **not** add any LICENSE until the right to do so is established (by
grant or by removing the derived code). This is the single gating input — A, C, and D all
collapse into "depends on licensing," so settle it before anything else.

### Reserve domain / org now?
**Domain: optionally yes (cheap defensive reservation of `vibecouncil.dev`); building the
site: no.** **Org: no** — creating/moving to an org now is premature and entangles with the
re-home question that licensing hasn't unblocked yet. Branding effort is also lower-value to
sponsors than licensing clarity, docs, tests, and governance — don't let it crowd those out.

### Recommended next 3 actions
1. **This week, unconditionally:** run a full-history secret scan; add `.mailmap` to unify
   author identity; (optionally) reserve the domain. Cheap, reversible, removes the cosmetic
   concern outright.
2. **Open the licensing track:** time-boxed permission request to Karpathy *with* a defined
   no-response fallback, plus an IP-counsel consult; in parallel, run the file-by-file
   provenance audit (backend-first).
3. **Pick the branch at day 30:** permission granted → **Option A** (LICENSE + NOTICES, keep
   repo + history, ship v0.2 here; org/site later). No/declined → **progressive clean-room
   rewrite** folded into v0.2 (tracking issue per derivative module; LICENSE once clean).
   **Defer the B/C/D re-home questions until provenance is clean.**

### Where I diverge from the council (curated, not blindly applied)
- **"Make the repo private / freeze all v0.2 development" is too aggressive** for our actual
  situation. The upstream author is Karpathy, whose educational repos are widely forked with
  tacit tolerance; the realistic enforcement posture differs from a generic unknown rights-
  holder. I'd **keep the repo public**, **keep developing**, and prioritize the licensing
  track and the progressive rewrite — rather than going dark, which would itself look alarming
  and isn't warranted by the evidence. (I'm not a lawyer; the "get counsel" point stands.)
- **Adopt wholesale:** licensing-as-gate, scan-first, `.mailmap` now, A-or-progressive-rewrite,
  drop B/C, attribution-up. **Hold lightly:** the exact $ figure and the rigid 30-day calendar
  — they're sensible defaults, not commitments.
- The council is right that the four-option framing over-weights a cosmetic concern; this doc's
  value is mostly in surfacing the **unlicensed-upstream fact**, which reframes the whole
  question.

## Constraints

- Strategy/planning only. **No** repo transfer/creation, no history rewrite, no license change,
  no attribution removal, no code changes, no dependencies.
- Council runs use **`balanced`** only (no premium), always `--usage`; **`review`**, not `full`
  (known None-content ranking-parser bug).
- Raw `.council/` outputs stay local and are **never** committed; `.council/`, `data/`, `.env`,
  `.venv/` untouched. No commit, push, or PR.
