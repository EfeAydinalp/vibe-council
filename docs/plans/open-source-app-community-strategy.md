# Plan: open-source app / community / product-direction strategy

A **strategic direction review**, not an implementation plan. `vibe-council v0.1.0` is
published; v0.2 is already scoped to **provider abstraction + Ollama** (see
[`v0.2-provider-abstraction.md`](v0.2-provider-abstraction.md)), and the
[hosted-service review](hosted-service-strategy.md) already ruled out hosted SaaS / credit
wallets for now. This document asks a longer-horizon question: **could vibe-council grow
into an open-source, sponsor-supported, local-first *app + community ecosystem* — and if
so, what is safe, what crosses the local-first boundary, and what (if anything) should
change about v0.2?**

**No app/TUI/web/cloud/forum/MCP/persona/provider code is written in this task; no core
logic changes; no dependencies added.** Council runs use **`review --preset balanced`**
only (not `full`, due to a known None-content ranking-parser bug), always `--usage`; raw
`.council/` output stays local.

> **Status update (2026-06-29):** two items this review flags as prerequisites have since
> landed on `master` — the `full`-mode ranking-parser fix (#23) and the
> identity/web-UI/dependency cleanup (#17–#22). The strategic recommendations below
> (defer app/community/cloud behind v0.2; keep the local-first boundary) are unchanged.

Review date: **2026-06-28**.

---

## The non-negotiable: the local-first boundary

Everything below is governed by one rule. The **local app owns** execution, project files,
API keys, provider/model calls, `.council/` files, decision memory, agent context, and raw
prompts/results. An **optional** server/cloud layer may *only* handle account/sponsor/
community features, a public role/prompt/model-combo gallery, workflow templates, an
approval-request **relay** (relaying, not executing), approval decisions, and lightweight
metadata.

The optional cloud layer **must NOT, by default**: execute user projects, receive API keys,
receive raw project files, receive raw `.council/` outputs, make provider/model calls on the
user's behalf, or silently automate ChatGPT/Claude/Gemini web UIs. This boundary is the
brand promise; every feature below is evaluated against it.

---

## A. Current position

- **Local-first CLI** — modes (`extract`/`mini`/`review`/`full`) × presets
  (`cheap`/`balanced`/`premium`); clean stdout, dedicated exit codes, key never printed.
- **Project-local `.council/`** — `reviews/`, `decisions/`, `stages/`, `usage/`, `locks/`,
  gitignored; nothing leaves the machine except the model calls the user triggers.
- **BYOK provider calls** — the user's own `OPENROUTER_API_KEY`; we broker nothing.
- **Decision memory** — `vibe extract --save` + `vibe decisions list/search/context`
  (no key, no model, plain string search).
- **Next core work** — **v0.2 provider abstraction + Ollama** (already council-reviewed),
  then v0.2.1 experimental MCP + cost-feedback instrumentation.
- **Governance gaps (verified):** there is **no LICENSE file**, no `THIRD_PARTY_NOTICES.md`,
  no `FUNDING.yml`, and no CONTRIBUTING/governance docs. README attributes
  `karpathy/llm-council` (MIT upstream) and calls this a fork. These gaps matter the moment
  a community/sponsor layer exists (Section G).

---

## B. Product vision (local-first app)

A local app/TUI/desktop/local-web experience wrapped around the existing CLI core — the
core stays the engine, the app is a face:

- **Doctor / setup UI** — a visual `vibe doctor`: provider reachability, key presence
  (never shown), Ollama server/model checks, env/version sanity. (Depends on v0.2 `doctor`.)
- **Provider setup UI** — pick provider (OpenRouter/Ollama), set models, all stored locally.
- **Local `.council` memory browser** — browse/search decisions, reviews, usage; entirely
  local read of existing artifacts.
- **Role/persona management** — named advisors, custom roles, role presets (Section E).
- **Model-combo recommendations** — suggest council/chairman combos per task/budget.
- **Agent / MCP bridge** — call the council from agents via official MCP (Section F).
- **Approval console** — human-in-the-loop approve/reject for agent-triggered actions
  (Section F + the remote-approval vision).

**Sequencing note:** the app is a *v0.3+ track*. It rides on v0.2 primitives (provider
abstraction, `doctor`, MCP) and must not pull UI work forward into v0.2.

---

## C. Optional cloud coordination layer

Strictly optional, **off by default**, and bound by the boundary above. Permitted roles:

- **Approval relay** — relays "approve?" requests + decisions between the local app and a
  user's phone/web; never sees files, keys, or raw outputs (see remote-approval section).
- **Public prompt/template/model-combo gallery** — share *artifacts*, not data.
- **Forum/community metadata** — accounts, votes, tags; no project content.
- **Sponsor/account features** — billing for sponsorship, not for inference.

**May cross the boundary (only with explicit opt-in):** a role prompt the user chooses to
publish, a workflow template, an approval request's *short* human-readable summary + the
decision, anonymous/aggregate metadata. **Must never cross by default:** API keys, raw
project files, raw `.council/` outputs, full prompts/results, anything that lets the cloud
execute or call models for the user.

---

## D. Community / social layer

- **GitHub Discussions first** — zero new infra, native to where the code lives; the
  cheapest way to test whether a community exists before building a forum.
- **Galleries** — role-prompt gallery, model-combo gallery, workflow-recipe sharing, all as
  shareable text artifacts (start as a curated repo folder / Discussions category, not a
  service).
- **Feature requests** — Discussions/Issues.
- **Lightweight "community view" footer on outputs** — an *optional, off-by-default* one-
  liner like "community-recommended combo for this task: …". **Token-impact discipline:**
  it must be a tiny, local-cached, opt-in static hint — never an extra model call, never an
  inline network fetch on each run. If it can't be made near-zero-token and local-cached,
  it doesn't ship.

---

## E. Persona / advisor system (vs. `llm-council-plus`)

`jacob-bd/llm-council-plus`-style ideas worth borrowing: persona-driven debate, named
advisors, customizable roles/personas, multi-provider, web search, temperature controls,
live progress, conversation history, import/export, one-shot API, Docker deploy.

- **Adopt early-ish:** named roles, custom roles, role presets — these are *prompt
  templates*, cheap, and align with the gallery. Multi-provider is already v0.2.
- **Adopt later / carefully:** debate rounds (multi-turn persona argument) — powerful but
  multiplies tokens/latency and stresses the same orchestration the `full`-mode bug lives
  in. Sequence **after** provider abstraction + MCP stabilize.
- **Defer / evaluate:** web search (new egress + provider surface), temperature controls
  (easy, but per-provider semantics — fold into the provider abstraction, not before).
- **Risks:** *prompt bloat* (personas balloon context/cost) and *over-personalization*
  (everyone forks their own roles → unshareable, unsupportable). Mitigate with a small,
  curated default set + a clearly-separated community gallery.
- **Timing:** roles/presets can begin in the **v0.3 app track**; debate rounds wait for a
  stable interface. None of this precedes v0.2.

---

## F. Official API / agent integration stance

- **Acceptable:** official provider APIs and **MCP** (the v0.2.1 experimental server is the
  right native integration point); a **local, dev-only bridge** for agents (Claude Code,
  etc.) running on the user's machine.
- **Not acceptable as default:** scraping/automating consumer **web UIs** of
  ChatGPT/Claude/Gemini — brittle, likely ToS-violating, and a support/headline risk.
- **Human approval is explicit** — any agent-triggered action that has side effects passes
  through an approval step; *approval-only mode* is a supported, optional posture.
- **Approval-only UI** can be optional and is the safe default mental model for agent use.

---

## G. Open-source sustainability

- **Model:** sponsor-supported open-source (GitHub Sponsors / Open Collective), **not**
  inference resale. Add `.github/FUNDING.yml`, a sponsor section in README, and a simple
  sponsor page later.
- **License/attribution hygiene (act on this regardless of the vision):**
  - **Add a `LICENSE`** — currently missing. As a fork of MIT `karpathy/llm-council`,
    preserve the upstream MIT license/copyright and add vibe-council's own. Pick the
    project license deliberately (MIT keeps maximum compatibility and community trust; a
    weak-copyleft option is possible but higher-friction).
  - **Add `THIRD_PARTY_NOTICES.md`** — list upstream + dependency licenses.
  - **Attribution:** keep the visible `karpathy/llm-council` credit; *strengthen* it (a
    `NOTICE`/credits line + retained upstream license) so removing unused upstream code can
    never look like hiding provenance.
  - **Remove unused upstream code safely** — only after license/attribution is in place, in
    a separate, clearly-described PR, so deletion reads as cleanup, not erasure.
  - **Governance:** add `CONTRIBUTING.md` + a light governance/`CODE_OF_CONDUCT` once
    Discussions open.
- **Repo identity:** **continue in `EfeAydinalp/vibe-council` for now.** A dedicated
  org/repo is worth it *only after* the core + governance stabilize and there's real
  community pull (moving early fragments links/SEO and adds maintenance for no gain).
- **Domain/site timing:** defer `vibecouncil.dev` until there's a stable core, governance,
  and an actual audience — a domain is cheap to buy but a site is a maintenance liability;
  buy the name early to reserve it, build the site late.

---

## H. Monetization boundaries

- **Now:** no credit wallet; no selling inference from a central provider key (re-affirming
  the hosted-service decision). Local core stays **free and open**.
- **Possible later, boundary-safe paid/sponsor layers:** curated **role packs**,
  **team/shared role libraries**, **cloud-sync of metadata** (not content), **priority
  support**, a **self-hosted/team edition** later, sponsor recognition.
- **Hard rule:** do **not** gate basic local custom roles or core local features behind
  payment — crippling the local core to upsell would destroy the open-source trust that is
  the entire moat. Paid = convenience/curation/community/scale, never core capability.

---

## I. Roadmap impact

- **Does this change v0.2?** **No.** v0.2 stays provider abstraction + Ollama + the
  `doctor`/MCP prerequisites already planned. This whole vision is a **v0.3+ product/
  community track** that *consumes* v0.2 outputs (provider abstraction → app provider UI;
  `doctor` → doctor panel; MCP → agent bridge & approval).
- **v0.3+ candidates:** local app/TUI shell, memory browser, role/persona system + gallery,
  GitHub Discussions community, approval console, (optional) cloud coordination relay.
- **Prerequisites:** stable provider abstraction; stable MCP; the `full`-mode ranking-parser
  bug fixed (debate rounds depend on that orchestration); license/governance landed *before*
  community opens.
- **Explicitly deferred:** cloud server, forum infra, web-UI automation, debate rounds,
  domain/site, any paid tier, mobile/messaging relays (start with the lowest-risk approval
  flow — see below).

---

## Remote approval / mobile control layer (v0.3+ coordination)

A future local app may support remote **approval** and short prompt-control, **optional and
disabled by default**, strictly within the boundary:

- **Local app** keeps execution, project files, API keys, provider/model calls, `.council/`
  memory, raw prompts/results, and Claude Code/agent actions.
- **Phone/web/message layer is a pure relay:** show pending approval requests; approve /
  reject / split / pause; send short prompt instructions back; show lightweight status;
  support an "approval-only mode."
- **The relay/server must not** receive project files, API keys, or raw `.council/` outputs,
  and must never execute actions itself. **Manual human approval is the default safety
  model.**

**Channel alternatives, by risk (recommended ordering):**

1. **Clipboard / export flow** — lowest risk, no server, no pairing. The natural *first*
   version: export an approval summary, decide, paste back. Ships almost for free.
2. **Purely local LAN approval UI** — local web screen / QR-code pairing to the local app;
   no cloud, data stays on the LAN. Strong second step.
3. **MCP/agent-native approval prompts** — approvals surfaced through the MCP interface to
   the calling agent; rides on v0.2.1 MCP.
4. **Cloud relay with encrypted/pairing-based messages** — only relays summaries +
   decisions, end-to-end paired; more capable, more surface area, needs a real threat model.
5. **Messaging bridge (Poke-like / Telegram/Discord/Slack bot)** — most convenient, **most**
   risk (third-party data handling, spoofed approvals); last, and only if provably safe.

**Stance:** strategically useful as a v0.3+ coordination layer, but start at tier 1–2
(clipboard/export, then LAN UI). It must **not** derail v0.2. Anything cloud/messaging
waits for a threat model and the same boundary guarantees as Section C.

---

## J. Proposed stance (before council)

1. **v0.2 is unchanged** — provider abstraction + Ollama + `doctor`/MCP prerequisites. This
   vision does not reorder it.
2. **This vision is a future product/community track**, not a reason to derail v0.2.
3. **All sensitive execution stays local** — execution, keys, files, `.council/`, raw
   prompts/results never leave the machine by default.
4. **Optional cloud only for** metadata, approvals (relay), templates/gallery, community,
   and sponsor features — never execution, keys, raw content, or model calls.
5. **Continue the current repo** (`EfeAydinalp/vibe-council`) for now; **improve
   attribution/license/governance** (add LICENSE, `THIRD_PARTY_NOTICES.md`, FUNDING,
   CONTRIBUTING) rather than hiding history. Org/repo move only after stabilization.
6. **Consider domain/site after** core + governance stabilize (reserve the name early,
   build the site late).
7. **Monetization** stays sponsor-supported + boundary-safe convenience/curation layers;
   never gate the local core.
8. **Remote approval** starts at the lowest-risk tier (clipboard/export → LAN UI), optional
   and off by default, as a v0.3+ coordination layer.

## Main question for the council

> **Is an open-source, sponsor-supported, local-first *app + community* evolution
> strategically sound — and does it (correctly) leave v0.2 unchanged while deferring the
> app/community/cloud/approval work to a v0.3+ track behind the local-first boundary?**

Sub-questions:
- Is the local-first boundary (Section C) drawn correctly, or does any "optional cloud"
  item leak execution/keys/content?
- Is GitHub-Discussions-first + galleries-as-artifacts the right low-cost community test,
  or premature?
- Is the persona/debate-rounds sequencing (after provider abstraction + MCP) right?
- Is "continue current repo + fix license/governance now" the correct identity call?
- For remote approval, is clipboard/export → LAN UI the right risk-ordered start?
- What are we underestimating (scope, maintenance, community burden, trust risks)?

## Council guidance summary

Ran `review --preset balanced` against this doc (2026-06-28). Output is advice to filter,
not authority — the section below is the **human-curated** reading, not a verbatim apply.
Raw output stayed in the gitignored `.council/`. The council called the *direction* sound
but the *plan as written* over-scoped, and said "do not proceed as written" — which I read
as "right vision, wrong altitude/timing," not "wrong vision."

### Is the vision strategically sound?
**Directionally yes, with a sharp caveat.** Open-source, local-first, sponsor-supported,
community-aware is well-differentiated and the core principles (local-first boundary, v0.2-
before-v0.3+, cautious monetization) were endorsed. The defect is **altitude**: the doc
plans ~2–3 years of ecosystem for a v0.1 tool with a single maintainer, unvalidated
community demand, and a known orchestration bug. Strategy = deciding what *not* to build
until evidence justifies it. Adopt: reframe this as a **conditional, evidence-gated** track,
not a roadmap.

### Does it change v0.2 priorities?
**No — and the council strengthened that.** Keep v0.2 = provider abstraction + Ollama +
`doctor`/MCP prerequisites, **plus two additions it argued belong in v0.2 (not later):**
(1) **fix the `full`-mode ranking-parser bug + add orchestration test coverage** — it's the
foundation every advanced feature (debate rounds, personas) sits on; (2) **land
license/governance basics now** (see below). Neither expands v0.2's feature surface.

### Strongest warning
**Maintainer-capacity vs. scope, and local-first boundary erosion.** The ecosystem is team-
sized work; as a solo personal repo it risks burnout and half-hardened security-critical
surfaces. And "must NOT by default" is *policy*, not *enforcement* — without architectural
controls (key-isolation, no-content-in-logs/telemetry, mandatory security review for
boundary-touching PRs), the boundary erodes one convenient exception at a time. Adopt: the
boundary needs **technical** guarantees, not just a rule.

### Strongest opportunity
**The local-first boundary itself is the moat** — defend it ruthlessly. The highest-
leverage, lowest-risk growth path is **integration-first**: be the best local code-review
*backend* for existing agent/IDE ecosystems (rock-solid MCP, great docs) and let those
communities be the forum — "tool, not platform." This captures most of the upside with a
fraction of the maintenance and without diluting identity.

### Local-first boundary recommendations
- Make the boundary **technically enforced**: key isolation, guaranteed no file
  content/prompts/`.council/` data in crash reports, logs, telemetry, or plugins.
- **Mandatory threat-model + security review** for *any* boundary-crossing code, as a
  written contribution rule — before merge, not after.
- A **Day-1 telemetry/data policy**: what is *never* collected (content, prompts, keys),
  what *might* be with opt-in, how anonymization happens on-device. No telemetry ships
  without it.
- An explicit **"no cloud until X"** gate (LICENSE/CoC/CONTRIBUTING in place; relay threat
  model externally reviewed; ≥1 additional boundary-literate maintainer; capacity budget
  proving cloud won't starve core).

### App / TUI / local-web timing
**v0.3+ at the earliest, and only if evidence warrants.** Adopt the council's narrowing:
**TUI-first (Python Textual), not GUI/desktop/web**; **maximum one UI surface**; local-only
(no sync/gallery backend). Formalize a **stable internal "council engine API"** (inputs:
sources/task/advisors/models/budgets; outputs: decisions/rankings/logs) *before* building
any frontend, so CLI/TUI/MCP can't drift.

### Persona / custom-role timing
Named roles + custom roles + presets are cheap *as templates* but **not free**: they balloon
context/cost (a 5-persona council can push a balanced review from ~$0.50 to $2+; debate
rounds 10–20×). Adopt: ship a **small curated default set with hard token-budget hints/
ceilings**, keep community personas in a clearly-separated gallery, and **defer debate
rounds until the orchestrator bug is fixed and the engine API is stable**. None precedes
v0.2.

### Cloud coordination safety rules
- **Threat model precedes architecture** for the approval relay — a compromised relay can
  DoS, inject, or forge "approved" decisions even without seeing content. E2E encryption +
  device pairing is non-negotiable.
- Even **clipboard/export approval needs a security spec** (signed/tamper-evident token, so
  an agent can't alter the approval before paste-back).
- "Anonymous/aggregate metadata" needs **explicit negative constraints** (no filenames/
  paths/diffs) + on-device redaction, or it leaks project identity.
- Prefer **serverless** designs (council Alternatives 4–5: P2P/WebRTC or stateless one-time-
  code) over a central relay to keep the boundary pure and avoid hosting/compliance cost.

### Community / forum / site timing
**Evidence-gated, not speculative.** Adopt the staged gates: observe 3–6 months post-v0.2
(star velocity, issue engagement, organic mentions, sponsor trickle) **before** opening
Discussions. Discussions-first only if signals appear, with *explicitly scoped categories*
and a stated support boundary (so it doesn't become a general LLM help desk). Galleries stay
**repo folders with manual curation**, never a service, and only after a community exists.
Forum infra separate from GitHub: likely never. Treat the public gallery as a **prompt-
injection / exfiltration attack surface** requiring scanning + curation budget.

### Repo / org / domain / attribution recommendation
- **Continue `EfeAydinalp/vibe-council`** for now; org/repo move only after core + governance
  stabilize and real community pull (early move fragments links/SEO for no gain).
- **Domain:** reserve `vibecouncil.dev` cheaply now if desired, **build the site late.**
- **Attribution/license — do this NOW, not "before community" (council escalated this to a
  blocking, this-week item):** the repo has **no LICENSE at all**, which is live legal
  exposure for current users and any contributor. Add `LICENSE` (MIT, preserving upstream
  `karpathy/llm-council` copyright + adding vibe-council's), `THIRD_PARTY_NOTICES.md`, a
  `NOTICE`/credits line, and `.github/FUNDING.yml`. Account for what's upstream vs. removed
  vs. added so later cleanup can't look like hiding provenance. Defer
  CONTRIBUTING/CODE_OF_CONDUCT until a contributor actually appears.

### Monetization / sponsor recommendation
Sponsor-supported, boundary-safe only; **never gate the local core.** Council flagged the
sustainability *thesis* as unvalidated (what do sponsors get that free users don't, when
curated packs get reshared instantly?) — so treat sponsorship as **opportunistic**
(`FUNDING.yml` now), not a funding *plan*, and don't build paid infrastructure on faith.
Paid tiers beyond sponsor recognition: avoid (no moat, brand risk). Self-hosted/team edition:
far-future, only with capacity.

### Recommended next 3 roadmap actions
1. **Governance/legal hygiene now** — `LICENSE` (MIT + upstream attribution),
   `THIRD_PARTY_NOTICES.md`, `NOTICE`/credits, `.github/FUNDING.yml`. Tiny, unblocks
   everything, removes live exposure. (Its own small PR.)
2. **Finish v0.2 with zero scope adds, and fold in reliability** — provider abstraction +
   Ollama + `doctor`/MCP prerequisites **plus** fixing the `full`-mode ranking-parser bug and
   adding orchestration test coverage. Define a written **"stable core" acceptance bar.**
3. **Observe before building (3–6 mo)** — instrument optional, opt-in usage signal + track
   stars/issues/sponsors; **do not** open Discussions, galleries, app, or cloud during the
   window. Let evidence trigger v0.3, scoped to **one** narrow focus.

### Where I diverge from the council (curated, not blindly applied)
- The "DO NOT PROCEED" headline is about *the plan's altitude*, not the vision — I keep the
  vision as a **conditional future track** and adopt its boundary/sequencing wholesale.
- I **partially** adopt the "license in v0.2" escalation: do the LICENSE/attribution/FUNDING
  immediately (agree it's urgent), but treat full governance (CoC/CONTRIBUTING/threat models)
  as gated on actual contributors/cloud work, not front-loaded.
- I note but **don't commit to** the star-count thresholds (500/2000) as literal gates —
  they're useful order-of-magnitude signals, not a contract; engagement quality matters more
  than a raw number.
- Adopt the **serverless approval** alternatives (P2P / one-time-code) as the preferred shape
  over a central relay; keep clipboard/export → LAN-UI as the risk-ordered start.

## Constraints

- Strategy/planning only. **No** app/TUI/web/cloud/forum/MCP/persona/provider implementation;
  no core logic changes; no new dependencies.
- Council runs use **`balanced`** preset only (no premium), always `--usage`; **`review`**,
  not `full` (known None-content ranking-parser bug).
- Raw `.council/` outputs stay local and are **never** committed.
- No commit, push, or PR from this task. `.council/`, `data/`, `.env`, `.venv/` untouched.
