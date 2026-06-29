# Research addendum: project-memory folders, skill taxonomies, NotebookLM SKILL.md, multi-agent dashboards

**Type:** research / roadmap addendum only. **No code changed, no dependencies, no third-party code
vendored, no external repos cloned into this repo, no council run.** Extends
[the external-tools / knowledge-graph repo audit](agent-skills-knowledge-graph-repo-audit.md) with
five new references, and aligns with the standing open-core direction (see the
[open-core commercial direction decision](../decisions/2026-06-29-open-core-commercial-direction.md)).
Builds on the standing direction: local-first public core, raw `.council/`
gitignored, curated `docs/decisions/` committed, Obsidian-compatible plain Markdown, context-pack /
agent-brief as the likely moat, vector/hybrid retrieval later, public core + optional private hosted
layer later.

Date: **2026-06-29**. *Not legal advice — license findings are an engineer's reading; borrow concepts,
not code.*

## Summary

The new references converge on one message vibe-council already believes: **durable, file-based,
scoped Markdown context is the unit of value**, and the money is in **curated content + education /
service**, not in running models or building chrome. Concretely:

- The **README/STATUS/PROGRESS/DECISIONS** project-memory folder pattern is a lightweight convention
  vibe-council *mostly already implements* (agent brief + `docs/decisions/`); adopt the **missing
  pieces minimally**, do not duplicate the decision source-of-truth.
- **SkillTree/Altari** and the **NotebookLM→SKILL.md** loop point at a real future direction —
  **source-fed council/review packs** — but with a sharp danger of low-quality skill proliferation;
  gate it behind "skills cite sources, never invent facts."
- **Charlie Automates** supports an **education/service-first validation** path (free education funnel
  → paid install/consulting/community) while keeping the *core open and free*.
- **Octogent** validates the file-based-context moat (its "tentacles" are scoped Markdown folders)
  but is also a clear signal of what **not to build now** — a multi-agent orchestration dashboard.
- **Claude Remote Control** remains an official primitive to **design around, not reimplement**.

## Sources inspected

- **Project-memory folder pattern** — user-provided screenshots (README / STATUS / PROGRESS /
  DECISIONS). Treated as user-supplied reference; no private content reproduced.
- **SkillTree / Altari** — <https://skilltree.altari.ai/waitlist>, <https://altari.ai/guide>
  (pre-launch waitlist; "137 AI skills across 7 departments," department agent networks, function
  skill packs, free audit + consulting).
- **NotebookLM → SKILL.md loop** — public write-ups of the knowledge-distillation workflow and the
  official Claude **Agent Skills** doc (<https://code.claude.com/docs/en/skills>; SKILL.md =
  YAML frontmatter `name`/`description` (+ optional `allowed-tools`) + a Markdown operating manual,
  progressive-disclosure loading, `agentskills.io` open standard).
- **Charlie Automates** — <https://charlieautomates.com> ("Charlie OS," "1-Hour AI Bottleneck
  Protocol," Skool community 3,300+, YouTube/blog, Founder's Toolkit, "work free until it works").
- **Octogent** — <https://github.com/hesamsheikh/octogent> (MIT, TypeScript, ~1.3k stars; thin
  orchestration dashboard over Claude Code; "tentacles," `todo.md`, child-agent spawning, inter-agent
  messaging, worktree isolation, local API + UI).
- **Claude Remote Control** — official Anthropic feature (facts from
  <https://code.claude.com/docs/en/remote-control>; not re-fetched in depth — see prior audit).

---

## Project-memory folder pattern: README / STATUS / PROGRESS / DECISIONS

The screenshots describe a four-file project-memory folder:

| File | Role (per screenshots) | vibe-council equivalent today |
|------|------------------------|-------------------------------|
| `README.md` | Stable project identity, why it matters, who it's for, links, constraints | The identity sections of [`docs/context/agent-brief.md`](../context/agent-brief.md) + `CLAUDE.md` |
| `STATUS.md` | Current snapshot, next action, blockers, needs-review | **Gap** — no committed "current snapshot / next action" file |
| `PROGRESS.md` | Dated log of what happened/changed/worked/failed | Partly git history + release notes; no curated log |
| `DECISIONS.md` | Decision log, rejected options, rationale, anti-re-litigation | [`docs/decisions/*.md`](../decisions/) (source of truth) + its `README.md` index |

**Analysis.** vibe-council already implements most of this: the **agent brief** is a distilled
README+STATUS, and **`docs/decisions/`** is a richer DECISIONS (ADR-per-file, not one log). The
genuinely missing piece is a **short, current STATUS** ("where are we, what's next, what's blocked").
PROGRESS overlaps heavily with git history and release notes, so a *committed* dated log risks
becoming noise. A second `DECISIONS.md` would **compete with `docs/decisions/` as a source of truth** —
the exact dual-store footgun the strategy plan warned against.

**Recommendation (dogfood a minimal `docs/context/project/` folder):**

- **`docs/context/project/README.md`** — *committed, public.* Stable identity/constraints (can be a
  thin pointer to `CLAUDE.md` + agent brief, not a copy).
- **`docs/context/project/STATUS.md`** — *committed, public, kept short.* The one new high-value file:
  current snapshot, next action, blockers, needs-review. Redacted; updated deliberately, not per-commit.
- **`docs/context/project/PROGRESS.md`** — **default to a generated/local export under `.council/`
  (gitignored)**; commit only by explicit opt-in for a milestone digest. Don't hand-maintain a dated
  log that git already records.
- **`DECISIONS.md`** — **do not create a competing store.** Keep `docs/decisions/*.md` as the source
  of truth; if a single-file rollup is wanted, make it a **generated index/summary** (extending the
  existing `docs/decisions/README.md`), never hand-authored canonical decisions.

All four stay **plain Markdown (Obsidian-openable), no `.obsidian/`**, standard Markdown links
canonical. The agent brief remains the distilled, agent-facing pack that *consumes* README/STATUS.

## SkillTree / business skill taxonomy implications

SkillTree/Altari decompose business operations into a taxonomy of **runnable Claude skills** ("137
skills / 7 departments," department agent networks) distributed as **function packs** ("5 Skills for a
$50K Pipeline," etc.) via a free library + paid consulting. This is the **skill-pack-as-product**
shape, applied to generic business workflows.

**Implication for vibe-council:** it validates a **`vibe packs` / council-pack** direction — but
vibe-council's lane is **decision-quality and review**, not generic sales/marketing agents. The
useful borrow is the *taxonomy + packaging* discipline (named packs, curated content as the asset),
echoing **UI/UX Pro Max** (curated corpus = moat), **Superpowers** (composable skill framework), and
**ECC/gstack** (skill packs). Stay narrow: *security / product / code / persona review packs*, not a
137-skill business OS. Treat Altari as a competitor/market signal in the crowded skill space, not a
template to copy.

## NotebookLM-generated SKILL.md workflow implications

The observed loop: load 3–4 best sources into **NotebookLM**, ask it to write a `SKILL.md` (YAML
frontmatter `name`/`description`/`allowed-tools` + a Markdown operating manual) **strictly from those
sources**, drop it into the Claude skills folder, reuse for repeated jobs. Public write-ups add a QA
discipline: **emit every claim with its source citation, sample-validate several statements against
the originals, and keep a reviewer-checked baseline.**

**Implication for vibe-council:** this is a credible **low-code way to draft council/review packs from
curated sources** — and it maps cleanly onto our own assets (`docs/decisions/`, the research audits)
as the "sources." But two hard requirements:

1. **Skills must cite/point to source docs and must not invent facts** — adopt the NotebookLM QA loop
   (claims carry citations; sample-validate; keep a reviewer-checked version). A council/review pack
   that fabricates is worse than none.
2. **Guard against low-quality skill proliferation** — the ecosystem is already flooded with thin,
   gamed-metric skills (see the prior audit's credibility caution). Quality gate + provenance, not volume.

This points to a **future `vibe packs`/`vibe skills` capability** (v0.4+): generate a *draft* pack from
curated sources, human-curate, attach source citations — never auto-publish. Not now; downstream of the
context-pack builder.

## Charlie Automates / education-service-productization implications

Charlie Automates runs a **free education funnel** (YouTube, blog, "Founder's Toolkit," a 3,300+ Skool
community) into **paid done-for-you install + consulting** ("Charlie OS," the "1-Hour AI Bottleneck
Protocol"), with a "work-free-until-it-works" guarantee. The product (Charlie OS) is the upsell; the
teaching is the top of funnel.

**Implication for vibe-council:** this **supports an education/service-first validation path while
keeping the core open** — vibe-council could offer **training, setup, support, and operator/review
workflow templates** using free docs/content as the funnel, without gating the core. It's a low-infra
way to test willingness-to-pay (no auth/billing/sync needed).
**Caution:** the "100+ skills, AI OS installed in an hour" framing is exactly the **over-broad,
skill-sprawl** direction to avoid — keep the offering narrow (decision-quality + review), and don't
promise a generic business OS.

## Octogent / multi-agent dashboard implications

Octogent (MIT) is "a thin orchestration dashboard over Claude Code": each job gets a **"tentacle"** —
a scoped folder (`CONTEXT.md`, `todo.md`, notes) — agents are spawned per todo item, communicate via
inter-agent messages, and optionally run in isolated git worktrees, all surfaced in a local API + UI.

**Analysis.** Octogent's core insight is **the same file-based, scoped-context pattern** vibe-council,
gstack, and planning-with-files already converge on — strong independent validation that **durable
scoped Markdown context (CONTEXT.md/todo.md ≈ our agent brief + decision records) is the right
foundation**. It is also a clear signal of **what not to build now**:

- **Should vibe-council build a multi-agent dashboard? Not now.** A dashboard/orchestration UI is
  out of scope (CLAUDE.md defers app/TUI), heavy to build and maintain, and undifferentiated.
- **Stay CLI / context-pack foundation first.** The context-pack builder is the moat; orchestration is
  only valuable *after* there's a high-quality shared context to orchestrate against.
- **Later (v0.4+ experiment, after the context-pack builder works):** "orchestrate multiple council /
  Claude sessions over a shared context pack" is a reasonable *exploration* — and Octogent's tentacle
  model is a good **concept reference** (files as shared truth, worktree isolation). **Concept only —
  MIT but do not vendor; do not take a TypeScript/Node dependency into a stdlib-only Python CLI.**

## Claude Remote Control implications

Unchanged from the prior audit: Remote Control is an **official, well-secured Anthropic primitive**
(outbound-only, short-lived scoped credentials, push notifications for "actions required," Trusted
Devices; Pro/Max/Team/Enterprise, no API keys). **Confirm: design around it; do not build our own
remote/mobile-approval transport** — it would be undifferentiated and a large security liability. If
"approve a council run from your phone" is ever wanted, run cleanly *inside* a Remote-Control'd session
and emit clear, push-worthy decision points.

---

## What vibe-council should adopt

1. **A minimal `docs/context/project/` convention** — committed `README.md` + a short `STATUS.md`;
   `PROGRESS.md` generated/local by default; **no competing `DECISIONS.md`** (decisions stay in
   `docs/decisions/`, rolled up via a generated index). Plain Markdown, Obsidian-openable, no `.obsidian/`.
2. **Source-fed pack generation as a future direction** (`vibe packs`/`vibe skills`, v0.4+) with a
   **mandatory citation/QA discipline** (claims cite sources, sample-validate, reviewer-checked
   baseline) — drafts only, human-curated.
3. **Education/service-first validation** (Charlie analogy) — training, setup, support, and curated
   review-workflow templates as an early validation motion, core staying open (aligns with the
   standing open-core direction).
4. **File-based scoped context as the foundation** (Octogent/gstack/planning-with-files validation) —
   keep investing in the context-pack builder before any orchestration or UI.
5. **Design around Claude Remote Control** for any remote/mobile approval need.

## What vibe-council should avoid

1. **Duplicating the decision source-of-truth** with a second `DECISIONS.md` log.
2. **Committing volatile PROGRESS/STATUS noise** — keep PROGRESS generated/local; keep STATUS short and
   deliberate; redact before committing either.
3. **Building a multi-agent dashboard / orchestration UI now** (Octogent's surface) — out of scope.
4. **A 100+-skill "AI OS" / generic-business-agent sprawl** (Altari/Charlie-OS breadth) — stay narrow
   (decision-quality + review).
5. **Auto-generated, uncited, low-quality skills** — the proliferation/credibility trap.
6. **Building our own remote-control transport.**
7. **Vendoring third-party code or taking a JS/Node dependency** (Octogent) into a stdlib-only Python CLI.

## Security / privacy / license cautions

- **Octogent is MIT** (don't vendor; concept-only). **SkillTree/Altari and Charlie Automates are
  commercial closed products** — learn from the model, copy **no content or code**, assume nothing about
  reuse rights. The skill ecosystem at large includes **unlicensed** material — never copy verbatim
  without an explicit license check.
- **Screenshots are user-provided** reference; **do not reproduce private Instagram/Jarrus or other
  private content** beyond the user's own summary in any committed doc.
- **NotebookLM-generated skills:** treat outputs as drafts; run the redaction/secret-guard before any
  commit; require source citations; never let a generated skill assert un-sourced facts.
- **Project-memory files:** STATUS/PROGRESS can concentrate sensitive context — local-by-default for
  PROGRESS, redact STATUS, never paste raw `.council/` output or local absolute paths; keep `.council/`
  gitignored.
- **No `.obsidian/`** committed; Obsidian remains an optional viewer, not a dependency.

---

## Roadmap impact

- **Now:**
  - Record the **public-safe open-core commercial direction** (any detailed strategy stays
    private/local until validated); publish only a public-safe roadmap summary.
  - **Dogfood the project-memory docs** — draft `docs/context/project/README.md` + `STATUS.md` by hand;
    see if STATUS measurably helps.
- **v0.2.x:**
  - Adopt the **project-memory folder convention** (README + short STATUS committed; PROGRESS
    generated/local).
  - Public-safe roadmap update; tighten the **redaction/secrets guard** spec (now also covering STATUS/
    PROGRESS and any generated pack/skill).
- **v0.3:**
  - **Context-pack builder**; `decisions show/new/promote/lint`; **project status/progress export**
    (generate STATUS/PROGRESS from records + git, default local); maybe **Obsidian-compatible export**.
- **v0.4+:**
  - **Skill / council packs**; a **source-fed SKILL.md generator** (cited, human-curated drafts);
    **multi-agent orchestration experiments** (Octogent-style, over the shared context pack);
    **hybrid/vector retrieval** if plain retrieval proves insufficient.
- **Commercial:**
  - **Support/training + a product/code review pack first** (Charlie-style funnel, core open);
    **individual Pro / hosted sync later**; **a private hosted repo only after demand is validated**
    and license/provenance is resolved.

## Questions for later council review

1. Is a `docs/context/project/` folder (README + short STATUS committed; PROGRESS generated/local;
   no competing DECISIONS) the right minimal addition — or does it duplicate the agent brief and
   `docs/decisions/`?
2. Should STATUS/PROGRESS be **committed public**, **generated-local (`.council/`)**, or **opt-in
   export** — and what's the redaction bar for each?
3. Is **source-fed pack/SKILL.md generation** a v0.4+ direction worth committing to, and is the
   "cite-sources / no-invented-facts / human-curated" gate sufficient against quality/credibility risk?
4. Is **education/training/done-for-you** a sensible *early* validation motion (vs a packaged product),
   and how do we keep it from consuming all maintainer time?
5. Does **multi-agent orchestration** ever belong in vibe-council, or should it stay a separate
   experiment that merely *consumes* our context packs?
6. Anything here that changes the standing open-core direction (public local-first core first,
   license/provenance resolved before serious commercialization)?
