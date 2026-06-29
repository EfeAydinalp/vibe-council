# External repo & license-feasibility audit: agent skills, memory, knowledge graphs

**Type:** research / audit only. **No code changed, no dependencies added, no third-party
code copied or vendored, no external repos committed.**

**Date:** 2026-06-29. **vibe-council version at audit time:** 0.2.0 (`scripts\vibe.ps1
--version`). **Tests:** 118 passed (`unittest`), OK.

**Context.** Pairs with [`docs/plans/linked-decision-memory-strategy.md`](../plans/linked-decision-memory-strategy.md):
v0.2.0 is released; the linked decision-memory review is complete; the recommended direction is
(1) dogfood linked decision memory first, (2) curated Markdown decision records, (3) local-first
raw `.council/`, (4) an agent brief / context-pack builder as the likely moat, (5) vector/hybrid
retrieval later, (6) a commercial feasibility review next. This audit surveys eight external
tools — plus **Obsidian** as a product/UX reference model — that already solve parts of that intended
system, to de-risk build-vs-borrow decisions and inform the commercial review.

> **Not legal advice.** License findings below are read from the actual `LICENSE`/package metadata
> in each repo, not just GitHub's UI label, but they are an engineer's reading. **Before copying or
> vendoring any third-party code into a commercial product, get attorney review.** Default posture
> throughout: **borrow concepts, not code**, unless a license is clearly permissive *and* the need
> is strong *and* attribution is preserved.

> **Credibility caution (read first).** Several of these repos advertise implausible star counts
> (200K+ for solo skill repos), API-served "stars" badges, mass machine-translated READMEs, and
> "used by N0,000 skills" claims. Star/▲ social proof in this segment is unreliable and partly
> gamed. Judge these tools on their **code, license, and architecture**, which is what this audit
> does — not on their popularity badges.

---

## Method

- Cloned each repo **shallowly into a temp dir outside this repository** (a sibling
  `vibe-external-research` directory on the Desktop, *not* inside `llm-council`). Nothing external is
  staged or committed. Claude Remote Control (a hosted Anthropic feature, not a repo) was researched
  from the official docs at `code.claude.com/docs/en/remote-control`.
- For each: read `README`, **actual `LICENSE` file**, package metadata (`package.json` /
  `pyproject.toml` / `skill.json`), architecture docs, and the central skill/plugin files. Did not
  exhaustively read every source file. No long third-party source excerpts reproduced here.

---

## Per-tool findings

### 1. ECC — `affaan-m/ecc`
- **URL:** https://github.com/affaan-m/ecc
- **Summary:** A cross-harness "agent operating system" — bundled skills, instincts, hooks, rules,
  agents, memory-optimization, and a security scanner — packaged for Claude Code, Codex, Cursor,
  OpenCode, Gemini, Zed, Copilot.
- **License found:** **MIT** (`LICENSE`, © 2026 Affaan Mustafa). Verified in-file.
- **Commercial-use status:** **Likely allowed** for the MIT-licensed repo content (keep the MIT
  notice). The **hosted "ECC Pro" GitHub App and npm packages** (`ecc-universal`, `ecc-agentshield`)
  are separate products with their own terms — do not assume their service is yours to resell.
- **What it does technically:** A large multi-harness config/skill monorepo (37 dirs: `skills/`,
  `rules/`, `hooks/`, `agents/`, `mcp-configs/`, `contexts/`, `manifests/`, plus per-harness dot
  dirs). Ships a security-scanning angle ("AgentShield") and "memory optimization / continuous
  learning" framing. A Python `ecc_dashboard.py`. Heavy install scripts (`install.ps1/.sh`).
- **Relevant files/patterns inspected:** `README.md`, `SPONSORING.md`, `SPONSORS.md`, top-level
  layout, `the-security-guide.md`/`the-longform-guide.md` (titles only).
- **What vibe-council can learn:** This is the **open-core + hosted-Pro + sponsorship** playbook
  executed end to end: MIT OSS core "free forever," a hosted **GitHub App** (`$19/seat/mo`, private
  repos, PR audits, free tier) as the paid convenience layer, tiered **GitHub Sponsors** ($5 →
  $3,700/mo) and **business sponsors** (CodeRabbit, Greptile, Atlas Cloud) for funding, plus an
  explicit **"Official sources only"** install-safety warning naming every legitimate channel. That
  exact shape — *public MIT tool, monetize the hosted/team/private-repo convenience, never the core*
  — is the most directly transferable monetization template for vibe-council.
- **What we should not copy:** The bloat and breadth (37 top-level dirs, 12-language READMEs, a
  vendored everything-harness layout) — antithetical to vibe-council's "small, local-first CLI."
  Don't copy code; the value here is the **business-shape pattern**, not the artifacts. Treat the
  inflated star/`badge` metrics as marketing, not validation.
- **Disposition:** **Borrow concepts only** (open-core monetization shape, install-safety warning,
  security-scanner-as-feature). Not a dependency. Don't vendor.
- **Risk notes:** MIT core is safe to learn from; the Pro/npm services are not licensed to you.
  Reputation/credibility risk in associating with gamed-metric projects — cite the *pattern*, not
  the project, in any public material.
- **Roadmap impact:** Strongest input to the **open-core vs private-commercial-repo** question and
  the eventual hosted-Pro MVP. Validates that a solo/small maintainer can run MIT-core +
  paid-hosted. See "Impact on roadmap" and "Questions for the commercial review."

### 2. Graphify — `safishamsi/graphify`
- **URL:** https://github.com/safishamsi/graphify
- **Summary:** A Claude-Code skill backed by a standalone Python library that turns a folder
  (code, docs, PDFs, etc.) into a queryable knowledge graph emitting `graph.html` + `GRAPH_REPORT.md`
  + `graph.json`.
- **License found:** **MIT** (`LICENSE`, © 2026 Safi Shamsi). Verified in-file. PyPI package is
  `graphifyy` (double-y); CLI is `graphify`.
- **Commercial-use status:** **Likely allowed** for the MIT library/skill (keep notice). Commercial
  entity exists (graphifylabs.ai, YC S26, a paid Gumroad book "The Memory Layer", GitHub Sponsors) —
  those are the author's businesses, not licenses you inherit.
- **What it does technically:** Clean staged pipeline, one function per module:
  `detect → extract → build_graph → cluster → analyze → report → export`. Tree-sitter extraction
  per language, NetworkX graph, Leiden community clustering, an analysis pass (god-nodes, surprises,
  suggested questions), Markdown report + `graph.json` + `graph.html` + Obsidian-vault export, an
  optional **MCP stdio server** (`serve.py`), a `watch` mode, and a token-cost **benchmark**
  (corpus vs subgraph). Notably strong **`security.py`**: URL allowlist (`http/https` only, blocks
  `file://` redirects), size/timeout caps on fetch, graph-path containment inside `graphify-out/`,
  label sanitization (strip control chars, cap length, HTML-escape). Extraction carries explicit
  **confidence labels** (`EXTRACTED` / `INFERRED` / `AMBIGUOUS`).
- **Relevant files/patterns inspected:** `README.md`, `ARCHITECTURE.md`, `LICENSE`, `pyproject.toml`,
  module responsibility table, security section.
- **What vibe-council can learn:** Three things. (a) The **three-artifact output shape**
  (`graph.json` machine + `GRAPH_REPORT.md` human + `graph.html` interactive) is an excellent model
  for what a vibe-council "decision graph / context pack" could *render* — without us building any
  graph DB. (b) The **confidence-label convention** maps directly onto decision-memory link quality.
  (c) `security.py` is a near-perfect checklist for our own redaction/sanitization guard
  (path containment, label sanitization, fetch caps) — concepts to re-implement natively, not import.
- **What we should not copy:** Tree-sitter + NetworkX + Leiden is **exactly the heavy graph/vector
  infrastructure the decision-memory review told us to defer.** Adopting it now would invert our
  agreed "frontmatter + backlinks + grep before embeddings" order. Don't take the code; don't take
  the dependency footprint.
- **Disposition:** **Borrow concepts only now** (output triad, confidence labels, security checklist).
  **Possible optional external tool later** — if users ever want a real code-graph, point them at
  `graphify` as an *optional, separately-installed* tool rather than bundling it. Build a **minimal
  native frontmatter+backlink graph first** (per the plan), measure, and only then consider Graphify
  as an opt-in integration. Do **not** take it as a core dependency.
- **Risk notes:** MIT is permissive but the package name collision warning in their own README
  (`graphifyy` vs squatted `graphify*`) is a real supply-chain caution if we ever auto-install it.
- **Roadmap impact:** Directly informs the **context-pack builder** (output shape) and the
  **vector/hybrid-retrieval "later"** decision (validates deferring; gives us a credible "integrate,
  don't rebuild" off-ramp if graph demand materializes).

### 3. Claude Remote Control — official Anthropic feature
- **URL:** https://code.claude.com/docs/en/remote-control (research preview; Claude Code v2.1.51+).
- **Summary:** Drive a **locally-running** Claude Code session from phone/tablet/browser via
  claude.ai/code or the Claude app — including approving permission prompts remotely and receiving
  push notifications.
- **License found:** N/A — a hosted Anthropic product/feature, governed by Anthropic's terms, not an
  open-source license. **Not a repo to borrow from.**
- **Commercial-use status:** **Not applicable / not yours to embed.** It's an Anthropic-account
  feature gated to Pro/Max/Team/Enterprise (no API keys). You cannot resell or reimplement their
  service; you *can* design around its existence.
- **What it does technically:** Local session makes **outbound HTTPS only, opens no inbound ports**,
  registers with the Anthropic API and polls; traffic is TLS; connection uses **multiple short-lived,
  single-purpose, independently-expiring credentials**. **Push notifications**: "push when Claude
  decides" and "push when actions required" (permission prompts/questions). **Trusted Devices** (beta,
  Team/Enterprise): per-device enrolled credential + biometric step-up, sign-in ≤18h, biometrics
  never leave the device. Limitations: one remote session per interactive process (outside server
  mode), the local process must stay running, ~10-min network-outage timeout, some interactive
  commands are local-only.
- **What vibe-council can learn:** The **remote/mobile-approval idea is now an official, well-secured
  Anthropic primitive.** Their security model (outbound-only, short-lived scoped credentials, no
  inbound ports, device trust + biometric step-up, explicit "approve actions" push) is the bar any
  home-grown remote-approval feature would have to clear — and almost certainly shouldn't try to.
- **What we should not do:** **Do not build a competing remote-control / mobile-approval transport.**
  That is undifferentiated, security-heavy, and now table-stakes from the platform owner.
- **Disposition:** **Design around / integrate with, do not compete.** If vibe-council ever wants
  "approve this council run from your phone," the right move is to **run cleanly inside a
  Remote-Control'd Claude Code session** (and emit clear, push-notification-worthy decision points),
  not to ship our own remote transport.
- **Risk notes:** Building our own remote approval would mean owning auth, device trust, and a relay —
  large attack surface, large liability, and redundant with the platform. Security implication for
  *us*: keep council runs safe to approve remotely (clear, bounded, no secret leakage in prompts).
- **Roadmap impact:** **Removes "remote/mobile approval" from our build list.** Reframes it as
  "be a good citizen inside Remote Control" — a small UX/notification-clarity concern, not a feature
  to engineer. Feeds the commercial review's "what's table-stakes vs differentiated" question.

### 4. Superpowers — `obra/superpowers`
- **URL:** https://github.com/obra/superpowers
- **Summary:** An agentic **skills framework + SDLC methodology** (spec → plan → subagent-driven
  TDD development) distributed as a Claude Code plugin (and other harnesses).
- **License found:** **MIT** (`LICENSE`, © 2025 Jesse Vincent). Verified in-file.
- **Commercial-use status:** **Likely allowed** (MIT, keep notice). Vendor (Prime Radiant) offers
  paid "commercial support / additional tooling / managed spending" — a separate service, not a
  license restriction.
- **What it does technically:** ~14 composable skills with auto-triggering, including
  `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`,
  `systematic-debugging`, `subagent-driven-development`, `requesting-/receiving-code-review`,
  `verification-before-completion`, `using-git-worktrees`, `writing-skills`,
  `dispatching-parallel-agents`. Methodology emphasizes red/green TDD, YAGNI, DRY, and human
  sign-off on spec/plan before code. Installed via the **official Claude plugin marketplace**.
- **Relevant files/patterns inspected:** `README.md`, `skills/` directory listing.
- **What vibe-council can learn:** This is the reference design for a **"council-pack" as a set of
  composable, auto-triggering skills with a methodology spine.** A vibe-council persona/council pack
  could be packaged the same way: small named skills (`review`, `extract`, `decisions`,
  `context-build`) with clear trigger phrases and a documented workflow, distributable through the
  official marketplace rather than a bespoke installer. The **`verification-before-completion`** and
  **`requesting/receiving-code-review`** skills are conceptual cousins of the council itself.
- **What we should not copy:** The methodology prose and skill bodies are the author's voice/IP —
  borrow the *packaging shape*, write our own content. Don't vendor.
- **Disposition:** **Borrow concepts only** (skill-pack packaging, marketplace distribution,
  methodology-as-skills). Not a dependency.
- **Risk notes:** Low. MIT, well-known author, clean repo. Main risk is over-adopting a whole SDLC
  philosophy that's heavier than vibe-council's "one focused review CLI."
- **Roadmap impact:** Shapes the **council/persona-pack** direction and argues for **official
  marketplace distribution** over a hand-rolled plugin path.

### 5. UI/UX Pro Max — `nextlevelbuilder/ui-ux-pro-max-skill`
- **URL:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- **Summary:** A single deep **specialist skill** packaging design intelligence (84 UI styles, 161
  palettes, 73 font pairings, 99 UX guidelines, 25 chart types across 17 stacks) behind one
  `skill.json`.
- **License found:** **MIT** (`LICENSE`, © 2024 Next Level Builder); `skill.json` also declares
  `"license": "MIT"`. Consistent. Homepage `uupm.cc`.
- **Commercial-use status:** **Likely allowed** (MIT). The hosted site/brand may have its own terms;
  the repo content is MIT.
- **What it does technically:** A `skill.json`-declared, multi-platform skill (19 listed harnesses)
  with a `src/`, `cli/`, `preview/`, curated design datasets, and screenshots. The product *is* the
  curated knowledge corpus + a thin skill wrapper.
- **Relevant files/patterns inspected:** `README.md`, `skill.json`, top-level layout.
- **What vibe-council can learn:** What a **commercial-grade specialist pack** looks like as a unit:
  a named skill, a `skill.json` manifest, a curated dataset as the moat, cross-platform install,
  a marketing homepage. A vibe-council "review pack for X" (security review pack, ADR/decision pack,
  Python-CLI pack) could be packaged identically — **the curated content is the defensible asset**,
  the skill wrapper is thin.
- **What we should not copy:** The design datasets are domain-specific and not ours to reuse;
  attribution must be preserved if any MIT content were ever reused (prefer not to). Don't vendor.
- **Disposition:** **Borrow concepts only** (specialist-pack packaging + manifest + curated-corpus-
  as-moat). Not a dependency.
- **Risk notes:** Low licensing risk (consistent MIT). Watch for "Pro Max"-style branding implying a
  paid tier whose terms differ from the MIT repo — verify before reusing anything beyond the concept.
- **Roadmap impact:** Reinforces **council/persona packs** as a productization unit and the
  **"curated content is the moat"** thesis behind the decision-memory/context-pack work.

### 6. Awesome Claude Code Skills — `itgoyo/awesome-claude-code-skills`
- **URL:** https://github.com/itgoyo/awesome-claude-code-skills
- **Summary:** A curated **discovery list** of skills/tools, grouped into ~15 categories.
- **License found:** **NONE.** No `LICENSE` file; GitHub API returns `licenseInfo: null`. **Default
  copyright (all rights reserved)** applies — *not* an open license despite being an "awesome list."
- **Commercial-use status:** **Unclear / risky to reuse content.** Without a license, you have **no
  grant** to copy the list text. You *may* read it and follow links (facts/links aren't
  copyrightable, but the curation/prose is).
- **What it does technically:** A two-file repo (`README.md`, `README_CN.md`). Categories worth
  noting as a market map: Official & Core, Awesome Lists, Agent Frameworks & Harnesses, Orchestration
  & Multi-agent, Skills & Plugins, **Memory & Context**, Workflows & Configuration, MCP Tools,
  Routing & Proxy, UI & Desktop Apps, Developer Tooling, Frameworks & Platforms, Tutorials,
  Specialized & Niche, Other.
- **Relevant files/patterns inspected:** `README.md` overview table + category headers.
- **What vibe-council can learn:** Use it **purely as a market scan** — the "Memory & Context" (only
  3 entries) and "Orchestration & Multi-agent" categories show where vibe-council's decision-memory/
  council angle sits in a crowded-but-thin landscape. The thinness of "Memory & Context" is a mild
  positive signal for our moat thesis.
- **What we should not copy:** **Do not treat it as a code dependency or copy its text.** Each linked
  repo must have its **own** license checked individually before any reuse. Star figures in the list
  are unreliable.
- **Disposition:** **Ignore as code; use as discovery only.** Not a dependency, no content reuse.
- **Risk notes:** **Unlicensed** — the cleanest example in this audit of "GitHub UI says nothing,
  so assume all-rights-reserved." Good teaching case for our own license-diligence discipline.
- **Roadmap impact:** Minor — a market-positioning input for the commercial review, nothing to build.

### 7. Planning-with-files — `OthmanAdi/planning-with-files`
- **URL:** https://github.com/OthmanAdi/planning-with-files
- **Summary:** A persistent **file-based planning skill** — `task_plan.md` / `findings.md` /
  `progress.md` on disk — so agents survive `/clear`, compaction, and crashes, with an opt-in
  completion gate and multi-agent shared state on disk.
- **License found:** **MIT** (`LICENSE`, © 2026 Ahmad Adi). Verified in-file. Also ships
  `CITATION.cff`, `llms.txt`.
- **Commercial-use status:** **Likely allowed** (MIT, keep notice).
- **What it does technically:** Plan/findings/progress markdown files as the agent's durable memory;
  lifecycle **hooks** (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact)
  across 60+ harnesses via the SKILL.md standard; a **deterministic completion gate** (blocks "done"
  until the plan is actually complete) with opt-in autonomous/gated modes; an **append-only JSONL
  run ledger**; and notable **security hardening**: SHA-256 **plan attestation / tamper-lock**
  (hooks refuse injection if the plan body changed), **prompt-injection delimiters** (`===BEGIN PLAN
  DATA===`), path sanitization, slug-mode isolation for parallel sessions, atomic temp-rename writes.
- **Relevant files/patterns inspected:** `README.md`, `CHANGELOG.md` (release history), top-level
  layout, `skills/`, `templates/`, `docs/` titles.
- **What vibe-council can learn:** This is the closest external analogue to the **agent brief /
  context-pack builder**. Key transferable *concepts*: (a) **durable markdown working-state that
  survives context loss** — exactly the agent-brief value proposition; (b) **append-only JSONL
  ledger** (vibe-council already does this for decisions — validates the pattern); (c)
  **content-injection delimiters + attestation** as a redaction/anti-tamper discipline for any
  generated brief that gets fed back to an agent; (d) **completion-gate** thinking for "did the
  council run actually resolve the question?". Their attestation/delimiter approach is a concrete
  upgrade to the plan's under-specified redaction step.
- **What we should not copy:** The 60+-harness hook sprawl and per-IDE variant maintenance burden
  (their changelog is a parade of "sync the 13 SKILL.md variants" fixes) — a clear warning against
  multi-harness lock-in/maintenance. Don't vendor the hooks; re-implement the *ideas* natively.
- **Disposition:** **Borrow concepts only** (durable-plan-files, completion gate, JSONL ledger,
  attestation/delimiters as redaction hardening). Not a dependency.
- **Risk notes:** MIT is fine. The maintenance-tax lesson is the real takeaway — every harness you
  support is a variant to keep in sync forever.
- **Roadmap impact:** Highest-signal input (with gstack) for the **context-pack/agent-brief** design
  and for the plan's **redaction/secret-guard** hardening. Reinforces "local-first markdown,
  survives context loss" as the core value.

### 8. Gstack — `garrytan/gstack`
- **URL:** https://github.com/garrytan/gstack
- **Summary:** "Garry Tan's Claude Code setup" — 23 opinionated **specialist role** slash-commands
  (CEO, Designer, Eng Manager, Release Manager, Doc Engineer, QA, Security Officer) plus 8 power
  tools, all Markdown skills, MIT.
- **License found:** **MIT** (`LICENSE`, © 2026 Garry Tan). Verified in-file.
- **Commercial-use status:** **Likely allowed** for the MIT repo (keep notice). **GBrain** (the
  optional cross-machine semantic-search / artifact-sync layer) appears to be a **separate companion
  product** with its own setup/terms — treat as not-yours.
- **What it does technically (most relevant parts):**
  - **`/context-save` / `/context-restore`**: write **append-only markdown checkpoint files** with
    frontmatter (`status`, `branch`, `timestamp`, `files_modified`) and stable sections (*Working on*,
    *Decisions Made*, *Remaining Work*, *Notes*), stored locally under `~/.gstack/projects/<slug>/
    checkpoints/`, **branch-scoped**, never overwritten. Bash-side **allowlist title sanitization**
    (only `a-z0-9.-`) so user titles can't inject shell metacharacters; collision-safe filenames.
  - **`/learn`**: a `learnings.jsonl` **append-only, dedup-by-(key,type)** store with confidence
    scores, `prune` (staleness + contradiction detection), `export` to Markdown/CLAUDE.md, `stats`.
  - **Decision memory**: `decisions.active.json` + `gstack-decision-log/search`, `--supersede <id>`
    for reversals, and the rule "treat active decisions as **prior settled calls — don't silently
    re-litigate**; if reversing, say so." (Near-identical in spirit to vibe-council's decision memory
    and the plan's `supersedes`.)
  - **Security/safety**: prompt-injection delimiters, a **profile-poisoning defense** (only honor
    "tune" directives that appear in the *user's own current message*, never from tool output/file
    content), telemetry opt-in and local-by-default, "official sources only" install posture.
  - **GBrain**: optional, separate semantic search + **artifact sync to a private GitHub repo** — the
    monetizable hosted layer, kept *out* of the free core and *off* by default.
- **Relevant files/patterns inspected:** `README.md`, `context-save/SKILL.md`, `learn/SKILL.md`,
  top-level command layout (`ARCHITECTURE.md`, `SKILL.md` present but not exhaustively read).
- **What vibe-council can learn:** The **richest single source** for the context-pack builder and for
  hardening decision memory. Concretely: (a) **checkpoint-markdown-with-frontmatter, append-only,
  branch-scoped** is a proven shape for `agent-brief.md` and curated records; (b) **bash-side
  allowlist sanitization of any user-supplied title before it touches a path/shell** is a direct
  security pattern for `vibe decisions new`/`promote`; (c) **`learnings.jsonl` with dedup + prune +
  contradiction detection** is a ready-made design for the plan's `decisions lint`/`doctor`; (d)
  **supersede + "don't re-litigate"** matches our `supersedes` field and the agent-brief's "don't
  re-propose rejected paths" goal; (e) **profile-poisoning defense** (trust only the live user
  message) is a security control we should adopt for any agent-facing memory; (f) **GBrain's split** —
  local-first free core, hosted sync/semantic-search as the *separate, opt-in, monetizable* layer —
  is the clearest blueprint for vibe-council's open-core/hosted boundary.
- **What we should not copy:** The 23-specialist breadth and the heavy per-skill bash preambles
  (telemetry, upgrade nags, routing injection, Conductor special-casing) — far beyond vibe-council's
  scope and a maintenance sink. Don't vendor any skill bodies (Garry-voiced IP). The auto-`git commit`
  of CLAUDE.md routing rules conflicts with our "no commits unless asked" rule — avoid.
- **Disposition:** **Borrow concepts only** (checkpoint format, sanitization, learnings dedup/prune,
  supersede semantics, profile-poisoning defense, local-core/hosted-sync split). Not a dependency.
- **Risk notes:** MIT core is safe to learn from. GBrain is a separate product — don't assume reuse
  rights. Telemetry-by-prompt and auto-commit behaviors are explicitly *not* patterns we want.
- **Roadmap impact:** Co-highest-signal (with planning-with-files) for **context-pack builder**,
  **decisions lint/doctor**, and the **open-core vs hosted boundary** in the commercial review.

### 9. Obsidian — local Markdown vault / backlink graph reference
*(Added as a product/UX reference, not a repo to vendor. Researched from official docs:
[help: How Obsidian stores data](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data),
[help: Internal links](https://help.obsidian.md/Linking+notes+and+files/Internal+links),
[help: Graph view](https://help.obsidian.md/Plugins/Graph+view), [obsidian.md/pricing](https://obsidian.md/pricing).)*

- **URL:** https://obsidian.md (app) · docs at help.obsidian.md
- **Summary:** A local-first, **plain-Markdown** knowledge app: a "vault" is just a folder of
  `.md` files that Obsidian renders as a linked, graph-navigable notebook — with paid Sync/Publish
  add-ons layered on top of the free core.
- **License / commercial-use status:** **Not an open-source repo — closed-source desktop app, so
  there is nothing here to vendor or copy code from.** Commercial use of the app itself **appears
  allowed without a mandatory paid license**: the official pricing page states the base app is
  "**free for both personal and commercial use**," and the **Commercial License ($50/user/yr) is
  explicitly *optional*, not required** ("You are not *required* to pay for a commercial license,
  however if you are using Obsidian for work in an organization we encourage you to purchase" one).
  **Sync ($4–5/mo, end-to-end encrypted, version history, vault collaboration)** and **Publish
  ($8–10/mo, web publishing + graph + search)** are the paid add-on services. *(Quoting the pricing
  page as found; their terms can change — verify before relying on it commercially. Not legal advice.)*
- **What it does technically:**
  - **Local Markdown vault:** notes are Markdown-formatted **plain-text files** in a folder (plus
    subfolders) on the local disk — fully editable outside the app; nothing is locked in a database.
  - **`.obsidian/` config folder:** a hidden per-vault folder holding `workspace.json` /
    `workspaces.json` (layout, updates as you open files), hotkeys, themes, and community-plugin
    settings — i.e. **user/machine-specific state, not content**.
  - **Internal links & backlinks:** default is **Wikilinks** `[[Note]]`, but **standard Markdown
    links `[text](Note.md)` are first-class** and can be made the default by turning off
    *Settings → Files and Links → Use [[Wikilinks]]*. Supports heading links `[[Note#Heading]]`,
    block refs `[[Note#^id]]`, aliases, and an automatic **backlinks** pane.
  - **Graph view:** notes as nodes, internal links as edges (node size ∝ connectivity), with a
    **global** and a **local** (per-note, depth-adjustable) graph, plus filters and color groups.
    **Canvas** adds a spatial board over the same files.
  - **Sync / Publish:** optional paid services; the source files stay local either way (third-party
    sync via Dropbox/iCloud/OneDrive/Git is also supported).
  - **Plugin ecosystem:** large community-plugin surface — the extensibility model, not something we
    need to match.
- **What vibe-council can learn:**
  - **Decision records should be plain Markdown** in a plain folder — a `docs/decisions/` directory is
    *already* a valid Obsidian vault with zero added work. This is strong validation of the plan's
    markdown-first store.
  - **Standard Markdown links first, for portability**; treat Wikilinks as an **optional, user-facing**
    convenience (Obsidian itself supports both and lets you choose). Our committed records should use
    portable `[text](path.md)` links so they render in GitHub, editors, and Obsidian alike.
  - **`docs/decisions/` can be opened directly as an Obsidian vault** — giving users backlinks + graph
    view + Canvas **for free**, so we get a "visual knowledge map" without building any UI.
  - The **graph/Canvas view is a user-facing visualization path** we can point users to *instead of*
    building our own graph renderer early (complements Graphify's report-output idea: the human can
    open the same curated records in Obsidian).
- **What we should not do:**
  - **Do not depend on or require Obsidian** — the records and the agent brief must be fully useful
    with plain `grep`, GitHub rendering, and any editor. Obsidian is a *nice-to-have viewer*, never a
    runtime requirement.
  - **Do not commit `.obsidian/` (esp. `workspace.json`) or user-specific vault config** — it's
    machine/user state and noise; gitignore it by default (same discipline as raw `.council/`).
  - **Do not adopt Obsidian-only Wikilinks as the primary/committed link format** — keep portable
    Markdown links canonical; Wikilinks at most as an optional rendering.
  - **Do not build an Obsidian plugin** (or an `obsidian` export target) **before the plain-Markdown
    convention proves useful** in dogfooding.
- **Disposition:** **Borrow concepts only / reference model.** Not a dependency, no code (closed-source
  anyway), no plugin yet. Ensure our records are *Obsidian-openable* by virtue of being plain Markdown.
- **Risk notes:** Low. The only real risks are scope-creep (building Obsidian-specific tooling too
  early) and a **portability trap** if we ever let Wikilinks become the canonical format. Commercial-use
  wording is favorable but vendor-controlled — re-verify if it ever underpins a paid feature.
- **Roadmap impact:** Strengthens the **docs-only dogfood** (records are Obsidian-openable as-is);
  supports "**visual graph later without building our own graph UI**"; and seeds a *later* optional
  `vibe context export --format obsidian` (e.g. a Wikilink-flavored or Canvas-flavored render) — **not
  v0.2.x**.
- **Commercial impact:** Obsidian is a clean, successful example of **local-first free core + paid
  convenience services** (Sync/Publish/optional commercial license) — the *same* open-core-style shape
  ECC and gstack/GBrain show, but from a **closed-source-app** angle. Useful analogy for vibe-council's
  *public core + paid hosted/sync/team layer*: monetize **convenience (sync, team, publish), not the
  core files**. **Learn from the model; do not copy Obsidian's product or assume its license covers us.**

---

## Comparative matrix

| Tool | License | Commercial use likely? | Main pattern | Relevance to vibe-council | Adopt concept? | Use dependency? | Copy code? | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|
| ECC | MIT | Yes (repo); Pro/npm separate | Open-core + hosted Pro + sponsors | High (monetization shape) | Yes | No | No | Med (gamed metrics, bloat) | Cite pattern, not project |
| Graphify | MIT | Yes (lib); company separate | Code→knowledge-graph (3 artifacts) | Med-High (output shape, defer infra) | Partial | No (maybe opt-in later) | No | Low-Med (pkg squatting) | Build minimal native graph first |
| Claude Remote Control | N/A (Anthropic feature) | No (not yours) | Secure remote/mobile session control | High (kills a build item) | n/a (design around) | n/a | No | Low (if we don't compete) | Integrate, don't compete |
| Superpowers | MIT | Yes | Composable skill-pack + SDLC method | Med-High (pack packaging) | Yes | No | No | Low | Marketplace distribution model |
| UI/UX Pro Max | MIT | Yes | Specialist pack, curated-corpus moat | Med (pack productization) | Yes | No | No | Low | Verify "Pro Max" tier terms |
| Awesome CC Skills | **None (ARR)** | **Unclear/risky** | Curated discovery list | Low (market scan only) | No | No | **No** | **Med (unlicensed)** | Links only; check each repo |
| Planning-with-files | MIT | Yes | Durable plan files, completion gate, attestation | High (agent-brief) | Yes | No | No | Low | Multi-harness = maintenance tax |
| Gstack | MIT | Yes (repo); GBrain separate | Specialist roles + context-save/learn/decisions; local-core+hosted-sync | High (context pack + boundary) | Yes | No | No | Low-Med | Richest concept source |
| Obsidian | Closed-source app (not OSS); free for commercial use, Commercial license optional | Yes (app free for commercial; Sync/Publish paid) | Local Markdown vault + backlink graph + paid sync/publish | High (records are Obsidian-openable; local-first free core + paid convenience) | Yes | No | No (closed-source) | Low | Reference model; portable Markdown links first, Wikilinks optional |

---

## Patterns we should adopt

1. **Skills as modular capability packs** (Superpowers, gstack, UI/UX Pro Max). Package
   vibe-council surfaces (`review`, `extract`, `decisions`, future `context build`) as small,
   named, auto-trigger-able skills with a clear methodology — distributable via the **official
   Claude plugin marketplace**, not a bespoke installer.
2. **File-based, local-first planning/memory** (planning-with-files, gstack). Durable Markdown
   that survives context loss/compaction is the core value of the agent brief — confirms the plan's
   "markdown-first, local-first" stance.
3. **Context-save / context-restore as a first-class loop** (gstack). Append-only,
   **branch-scoped**, frontmatter'd checkpoints with stable sections (*Working on / Decisions /
   Remaining / Notes*) — a ready template for `agent-brief.md` and curated records.
4. **Curated graph/report output triad** (Graphify): a machine artifact (`json`), a human report
   (`md`), and an optional interactive view (`html`) — model the context pack's *outputs* this way
   **without** building a graph DB. Carry **confidence labels** on links.
5. **Append-only JSONL ledgers with dedup/prune/contradiction-detection** (gstack `learnings.jsonl`,
   planning-with-files run ledger). vibe-council already uses `index.jsonl`; extend toward a
   `decisions lint/doctor` that flags stale/contradictory/superseded records.
6. **Supersede + "don't re-litigate" semantics** (gstack decisions). Matches the plan's `supersedes`
   field; bake it into the agent brief ("don't re-propose rejected paths").
7. **Local-first default, hosted convenience as a separate opt-in layer** (ECC Pro, gstack GBrain).
   The open-core boundary: free MIT core runs entirely local; **sync / team / semantic-search /
   hosted is the paid, opt-in, separate layer** — never gating the core.
8. **Specialist role / council packs** (gstack 23 roles; Superpowers method skills). A persona/council
   pack is a credible productization unit; the **curated content is the moat** (UI/UX Pro Max).
9. **Official-source / install-safety warnings** (ECC, gstack). A short "install only from these
   channels" note in the README is cheap reputation/security insurance.
10. **Explicit license & attribution discipline** (this audit). Read actual `LICENSE` files; preserve
    notices; keep the `karpathy/llm-council` provenance intact.
11. **Security hardening borrowed as a checklist** (Graphify `security.py`, planning-with-files
    attestation/delimiters, gstack sanitization + profile-poisoning defense): path containment,
    allowlist sanitization of user input before shell/path use, content-injection delimiters,
    SHA-tamper attestation, and **trust only the live user message** for control directives. These
    sharpen the plan's under-specified redaction/secret-guard step.
12. **Obsidian-compatible Markdown vault output** (Obsidian). Keep `docs/decisions/` a plain folder of
    plain `.md` files so it is *already* a valid Obsidian vault — users get backlinks, graph view, and
    Canvas for free, no UI to build on our side.
13. **Standard Markdown links for portability** (Obsidian supports both, defaults to Wikilinks but
    lets you switch). Make portable `[text](path.md)` links the **canonical/committed** format so
    records render in GitHub, any editor, *and* Obsidian; treat Wikilinks as optional/user-facing only.
14. **Optional visual graph via external tools / Obsidian instead of building UI early** (Obsidian
    graph view; Graphify's `graph.html`). Point users at an existing viewer for the "visual knowledge
    map" rather than shipping a graph renderer before the markdown convention proves out.

## Patterns we should avoid

1. **Copying large code chunks** from any of these — even MIT — without attorney review and notice
   preservation. Default to **concepts, not code**.
2. **Vendoring without a license review** — and *never* reuse content from the **unlicensed**
   `awesome-claude-code-skills` (all-rights-reserved by default).
3. **Committing raw outputs / local artifacts** — keep `.council/` gitignored; only curated, redacted
   records are committed (unchanged project rule, reinforced by gstack's local-by-default posture).
4. **Overbuilding graph/vector infrastructure too early** (Graphify's tree-sitter/NetworkX/Leiden
   stack). The decision-memory review already said defer; this audit confirms — build the minimal
   native frontmatter+backlink graph, measure, integrate Graphify *optionally* only if demand proves.
5. **Ambiguous commercial-license assumptions** — GitHub's UI label is not the license; hosted
   companion products (ECC Pro, GBrain, Graphify Labs) are **not** covered by the repo's MIT grant.
6. **Building our own remote-control / mobile-approval transport** — redundant with Claude Remote
   Control and a large security liability. Design around the official feature instead.
7. **Multi-harness / plugin lock-in and per-IDE variant sprawl** (planning-with-files', ECC's, and
   gstack's maintenance tax — endless "sync the N SKILL.md variants" churn). Support few surfaces
   well; don't promise 60 harnesses.
8. **Telemetry-by-default, upgrade-nag preambles, and auto-`git commit` side effects** (gstack
   preambles) — these violate vibe-council's "quiet, no-surprise-commits, local-first" conventions.
9. **A customer-facing self-hosted/uncensored model path without a safety layer** — if any hosted
   offering emerges, it must carry redaction + guardrails, not raw model passthrough.
10. **Relying on Obsidian-only Wikilinks as the primary format** — a portability trap. Wikilinks
    `[[Note]]` render poorly outside Obsidian (e.g. GitHub); keep portable Markdown links canonical.
11. **Committing `.obsidian/` user workspace state** (`workspace.json`, themes, plugin config) — it's
    machine/user-specific noise; gitignore it by default, same as raw `.council/`.
12. **Building an Obsidian plugin (or `--format obsidian` export) too early** — before the plain-
    Markdown convention is dogfooded and proven useful. It's a *later, optional* target, not v0.2.x.
13. **Treating Obsidian as a dependency** — records and the agent brief must be fully usable with
    `grep`, GitHub rendering, and any editor; Obsidian is a nice-to-have viewer, never required.

---

## Impact on vibe-council roadmap

- **Docs-only dogfood PR (next concrete step, unchanged):** Proceed with the decision-memory plan's
  recommendation — hand-author ~6 `docs/decisions/` records + a manual `agent-brief.md` and test
  whether it measurably helps Claude Code. This audit **reinforces** that path and donates concrete
  templates: gstack's checkpoint frontmatter/sections for the brief, planning-with-files' delimiter/
  attestation idea for redaction, Graphify's report-output shape for the pack. Still **no code, no
  PR unless asked.**
- **v0.2.x:** Documentation convention + dogfooded records + manual brief experiment only. Add the
  **install-safety note** and tighten the **redaction/secret-guard** spec using the borrowed security
  checklist (path containment, allowlist sanitization, injection delimiters). No runtime code.
- **v0.3:** *If validation passes*, ship the minimal tooling (`decisions show/new/promote/lint`,
  on-demand index) **plus** the security guard. Adopt **supersede + don't-re-litigate** and
  **learnings-style prune/contradiction detection** for `decisions lint/doctor`. Keep stdlib-only.
- **Commercial feasibility review (next):** This audit is its primary input. ECC and GBrain give a
  concrete, working **open-core + hosted-opt-in** template; Remote Control removes "mobile approval"
  from scope; the thin "Memory & Context" market category is a mild moat signal.
- **Open-source vs private commercial repo:** Lean toward **MIT public core + a separate private repo
  for any hosted/team/billing/sync layer** (the ECC-Pro / GBrain shape). Decide explicitly in the
  commercial review.
- **Context-pack builder:** Confirmed as the likely moat. Design it as durable, local-first,
  branch-scoped Markdown (gstack/planning-with-files), emitting a human report + machine index
  (Graphify shape), built only from curated records, with a real redaction pass.
- **Vector/hybrid retrieval:** Keep deferred. Graphify is the credible **"integrate later, don't
  rebuild"** option if semantic demand appears; a time-boxed local-embeddings prototype remains the
  cheap test.
- **Council / persona packs:** Viable productization unit (Superpowers/gstack/UI-UX). Package as
  marketplace skills with curated content as the asset; revisit after the memory layer proves out.
- **Remote / mobile approval:** **Drop as a build item.** Reframe as "run well inside Claude Remote
  Control" and emit clear, push-worthy decision points.
- **Obsidian compatibility (reference model, no dependency):** The docs-only **dogfood records should
  be Obsidian-openable** — i.e. plain `.md` with portable Markdown links — so `docs/decisions/` can be
  opened as a vault during dogfood for a free **manual visualization layer** (backlinks + graph +
  Canvas). The **agent brief and decision records stay plain Markdown** (no Wikilink lock-in,
  `.obsidian/` gitignored). An **Obsidian plugin or `vibe context export --format obsidian` is a
  later, optional target — not v0.2.x**, and only after the markdown convention proves useful.

---

## Questions for the commercial feasibility review

1. **Can the open-source core stay fully public (MIT) while we monetize hosted convenience?**
   ECC (MIT core + $19/seat Pro GitHub App) and gstack (MIT core + GBrain hosted sync) both say yes —
   does that shape fit vibe-council's local-first, BYO-key ethos without diluting the OSS promise?
2. **Should hosted/billing/team/mobile live in a separate private repo?** The ECC-Pro/GBrain pattern
   keeps the paid layer out of the public tree. What's our public/private boundary, and what stays
   MIT?
3. **Which external patterns actually prove monetizability?** Hosted PR-audit GitHub App (ECC),
   cross-machine artifact sync + semantic search (GBrain), paid support/managed-spend (Superpowers/
   Prime Radiant), curated-corpus specialist packs (UI/UX Pro Max), info products (Graphify's book).
   Which are credible for a council/decision-memory product?
4. **What recurring costs must we model?** Per-user hosting, sync storage, any server-side model
   calls, support load, and the **per-harness maintenance tax** this audit flagged (variant sprawl).
   Note: BYO-key keeps *inference* cost on the user — preserve that.
5. **What credit/balance model is safest?** (Out of scope per CLAUDE.md's "hosted SaaS / credit
   wallet is out of scope" today — but if revisited, prefer BYO-key + a thin hosted convenience fee
   over reselling tokens, to avoid wallet/credit liability.)
6. **What security controls are mandatory for any hosted/team tier?** Borrowing the bar set here:
   outbound-only + short-lived scoped credentials + device trust (Remote Control), redaction +
   path-containment + injection-delimiters + profile-poisoning defense (Graphify/planning-with-files/
   gstack), local-by-default with explicit opt-in sync.
7. **What is the first paid MVP?** Candidate framing: *free MIT CLI (council + local decision memory
   + context pack)*; *paid = hosted/team sync of curated decision records + an org-shared agent brief*,
   kept in a separate private repo, opt-in, never gating the core. Validate against the dogfood result
   first.
8. **Can vibe-council follow an Obsidian-like model — free local-first core + paid Sync/Publish/team
   convenience?** Obsidian monetizes *convenience services* (sync, publish, optional commercial
   license) while the core files stay free and local. Does that map onto a vibe-council "free CLI +
   paid sync/team" split?
9. **Should hosted *team decision-memory* be the paid layer, rather than inference resale?** Sync of
   curated decision records + a shared org agent brief (Obsidian-Sync-style) keeps BYO-key inference
   on the user and avoids credit/wallet liability — is that the safer monetization than reselling tokens?
10. **Should Obsidian-compatible export be part of the first paid/team story?** E.g. a team vault of
    curated decision records that opens cleanly in Obsidian (graph + backlinks) — is "your team's
    decisions, as a synced, graph-navigable vault" a compelling paid hook, or just a free-tier nicety?

---

## License / commercial-use summary

| Tool | License (verified in-file) | Reuse posture |
|---|---|---|
| ECC | MIT | Concepts only; Pro/npm services not licensed to us |
| Graphify | MIT | Concepts only now; possible opt-in external tool later |
| Claude Remote Control | Anthropic product (no OSS license) | Design around; cannot reimplement/resell |
| Superpowers | MIT | Concepts only (packaging/method) |
| UI/UX Pro Max | MIT (repo + skill.json consistent) | Concepts only; verify hosted-tier terms |
| Awesome CC Skills | **None — all rights reserved** | Discovery/links only; **no content reuse** |
| Planning-with-files | MIT | Concepts only |
| Gstack | MIT | Concepts only; GBrain is a separate product |
| Obsidian | Closed-source app (no OSS license); core free for commercial use, Commercial license optional ($50/user/yr); Sync/Publish paid | Reference model only; nothing to copy (closed-source); ensure our records are Obsidian-openable plain Markdown |

**This is not legal advice.** Of the eight code references, six are MIT (permissive, attribution-
preserving); one (`awesome-claude-code-skills`) is **unlicensed** and must be treated as
all-rights-reserved; one (Claude Remote Control) is a hosted Anthropic feature, not a repo. The ninth
reference, **Obsidian**, is a **closed-source app** (no source to copy) whose core is free for
commercial use with an *optional* commercial license — a reference model, not a dependency. For any
move beyond borrowing concepts — i.e., copying or vendoring code — **obtain attorney review first**,
preserve all upstream notices, and keep the `karpathy/llm-council` provenance intact.
