# Plan: post-v0.1 roadmap

A **strategic roadmap review**, not an implementation plan. `vibe-council v0.1.0` is
published (tag + GitHub Release, commit `89ed6d3`). This document records what shipped,
the current strengths and limitations, the candidate next items, a proposed sequence,
and the one strategic question we want the council to weigh in on. **No features are
implemented in this PR; no core logic changes.**

Release date of v0.1.0: **2026-06-28**.

## What v0.1.0 shipped

- **Workflow modes** — `extract`, `mini` (default), `review`, `full` (only `full` uses
  anonymized peer ranking; `review` is the everyday plan/diff gate).
- **Presets** — `cheap`, `balanced` (default), `premium` (premium gated).
- **Backend CLI** — `python -m backend.cli` plus the global `vibe` command (`review`,
  `diff`, `extract`, `mini`, `full`, `status`, `models`, `presets`, `last`, `guide`,
  `init`, `projects`, `decisions`, `--version`). Clean stdout, dedicated exit codes
  (`0`–`7`), key never printed.
- **Project-local `.council/` workspace** — `reviews/`, `diffs/`, `decisions/`, `runs/`,
  `stages/`, `usage/`, `locks/`, `config.json`; auto-gitignored.
- **Decision memory** — `vibe extract --save` + `vibe decisions list/search/context`
  (no model, no key required). Search is plain string matching.
- **Guardrails** — premium guard, pre-run token guard, best-effort cost guard, loop
  guard, `--usage`, first-run key guard (exit 7).
- **Tests + CI** — stdlib `unittest`, GitHub Actions on Ubuntu/macOS/Windows.
- **Cross-platform install** — `install-vibe.ps1` / `install-vibe.sh`, repo-`.venv`-aware
  launchers.
- **Docs** — README + quick demo, `examples/`, agent-integration guide, privacy/
  local-first notes, release checklist, changelog, sanitized terminal transcript.

## Current strengths

1. **Honest, agent-friendly CLI surface** — stable exit codes, stdout/stderr split, key
   never leaks. This is the real moat: it's scriptable and safe to embed in agents.
2. **Local-first / privacy posture** — artifacts stay in `.council/`; the only network
   egress is to OpenRouter, and that's documented.
3. **Guardrails already exist** — token/cost/loop/premium/key guards mean cost blowups
   and footguns are contained before adding more surface area.
4. **Decision memory** — a genuinely differentiated feature vs. upstream; turns one-off
   reviews into a searchable record.
5. **Cross-platform + CI green** — credible foundation to build on.

## Current limitations

1. **OpenRouter-only** — single provider, no abstraction. This is the biggest
   architectural lock-in and the most-cited limitation.
2. **No Ollama / local inference** — everything is remote; no zero-cost/offline path.
3. **No MCP server** — can't be consumed as a tool by MCP-speaking agents yet.
4. **No real asciinema/GIF demo** — only a sanitized text transcript.
5. **No pre-flight cost estimate** — users see usage *after* a run, not a rough estimate
   before committing spend.
6. **Decision search is naive** — plain substring match; no ranking/embeddings/SQLite.
7. **No Headroom integration** — no token-compression spike yet.
8. **Web UI not aligned with CLI workflow** — the React/Vite UI predates the modes/
   presets/decision-memory model and drifts from the CLI's mental model.

## Candidate next roadmap items

1. **Provider abstraction** — an internal interface so the council isn't hard-wired to
   OpenRouter. Prerequisite for items 2 and (arguably) much of the future.
2. **Ollama / second provider** — first concrete consumer of the abstraction; unlocks
   local/offline and zero-marginal-cost runs.
3. **Rough pre-flight cost estimate** — show an order-of-magnitude `$`/token estimate
   before a run, gated by the existing cost guard. Cheap, high trust-per-effort.
4. **MCP server** — expose modes as MCP tools so agents can call the council natively.
5. **Real asciinema/GIF demo** — replace the text transcript with an actual recording.
6. **Headroom token-compression spike** — investigate compressing context before
   sending to models to cut cost/latency. Research spike, not a committed feature.
7. **Decision search improvement** — ranking, fuzzy/semantic search, or SQLite index.
8. **Web UI alignment** — bring the UI in line with modes/presets/decision memory.
9. **Model validation / retry-backoff** — validate model IDs up front; retry transient
   provider failures with backoff. Reliability hardening.
10. **Package distribution** — `pipx` / `uvx` / PyPI publication so install isn't
    git-clone-only. A later, low-risk distribution win.

## Proposed initial sequence (for council critique)

| Milestone | Theme | Contents |
|-----------|-------|----------|
| **v0.1.1** | Post-release polish | Bug fixes surfaced post-release; real asciinema/GIF demo if it's cheap; model validation / retry-backoff if low-risk. |
| **v0.2.0** | Break the single-provider lock-in | Provider abstraction + Ollama/local provider as the first second-provider. |
| **v0.2.x** | Spend transparency | Rough pre-flight cost estimate, riding on the existing cost guard. |
| **v0.3.0** | Agent-native | MCP server, built on a now-stable provider abstraction. |
| **later** | Depth | Headroom token-compression spike, web UI alignment, decision search improvement, packaging (pipx/uvx/PyPI). |

Rationale we want challenged: provider abstraction is sequenced first because it (a)
removes the most-cited limitation, (b) is a prerequisite for Ollama, and (c) is cheaper
to do *before* MCP hard-codes more assumptions. Pre-flight cost estimate is slotted as a
small, high-value follow-on. Headroom is deferred to "later" as a spike because its
payoff is uncertain.

## Main strategic question

> **After v0.1.0, should the next priority be provider abstraction/Ollama, pre-flight
> cost estimate, MCP, Headroom, or polish/demo?**

Sub-questions for the council:

- Is **OpenRouter dependency** the right next architectural target, or is it premature
  abstraction for a young project?
- Where does **Headroom** belong — early (cost is the real adoption blocker) or late
  (speculative)?
- Should **MCP** wait until provider abstraction is stable, or ship sooner against the
  current OpenRouter-only core to capture agent users?
- What are we **underestimating** in this sequence?

## Council guidance summary

Ran `full --preset balanced` against this doc (2026-06-28). Output is advice to filter,
not authority — below is the **human-curated** reading, not a verbatim apply. Raw output
stayed in the gitignored `.council/`.

### Strongest agreement
- **Break the OpenRouter lock-in first.** Provider abstraction → Ollama as v0.2.0 was
  unanimously endorsed as the correct first move: it removes the most-cited limitation,
  is a prerequisite for a local/offline path, and gets cheaper the earlier it's done
  (before MCP/UI bake in more OpenRouter assumptions).
- **Scope the abstraction to exactly two providers** (OpenRouter + Ollama). Don't design
  a theoretical N-provider ecosystem; keep the interface minimal (`send_chat`,
  `stream_chat`, error taxonomy, usage reporting).
- **The real demo is not optional polish.** For a CLI tool the demo *is* the marketing;
  elevate it to a v0.1.1 requirement, not "if it's cheap."

### Strongest disagreement (council vs. the original sequence)
- The council **pushed MCP earlier** — from v0.3.0 to right after provider abstraction
  (~v0.2.1) — arguing MCP is a *distribution* unlock (agent ecosystem) rather than a
  feature, and that it's orthogonal to provider abstraction (it can ship OpenRouter-only
  first). The original plan's "MCP waits for architectural purity" was the main point of
  contention.
- The council also **refused to defer Headroom to "later"**, reframing it as a
  hypothesis to test early via a time-boxed spike rather than a speculative backlog item.

### My take (curated, not blindly applied)
- **Adopt** MCP-earlier *in principle* but keep it gated behind an experimental flag and
  explicitly **dependent on the provider interface having landed** (not on it being
  "stable"). I'm wary of the council's optimism that the two are fully orthogonal — MCP
  will surface concurrency/timeout assumptions in the core. That's acceptable (it hardens
  the core) but means v0.2.1 carries real risk, so it stays *experimental*.
- **Adopt** the Headroom-as-spike framing. It's the cheapest way to convert a guess into
  a decision. But I'd **gate the spike on actual cost-pain signal**, not run it
  unconditionally — instrument `--usage` first.
- **Partially adopt** packaging promotion: pipx/uvx/PyPI is a genuine adoption gate, but
  it's low-risk and can slot wherever there's slack; I won't let it crowd out v0.2.0.
- **Note the council's own bias check:** it admits it may overweight *agent* adoption
  because the CLI design makes that the obvious wedge. If the real users turn out to be
  humans doing code review, pre-flight cost estimate outranks MCP. Worth measuring before
  committing to the MCP-first ordering.

### Recommended next 3 PRs
1. **v0.1.1 — real asciinema/GIF demo** (+ any post-release bug fixes, model
   validation/retry-backoff if low-risk). Cheap, high marketing leverage, unblocks
   credibility.
2. **v0.2.0 — provider abstraction (2-provider) + Ollama**, plus a `vibe doctor` health
   check and model-tier guidance to pre-empt the "weak local model → blame the tool"
   perception risk.
3. **v0.2.1 — experimental MCP server** on the OpenRouter-or-Ollama core, behind a flag,
   with cost-feedback instrumentation added to `--usage`.

### What to defer
- **Headroom** → conditional spike in v0.2.x, commit only if signal + spike both pass.
- **Pre-flight cost estimate** → v0.2.x/v0.3.0 follow-on once provider pricing tables
  exist (so it can say "$0.75 on OpenRouter vs. free on Ollama").
- **Decision search improvement** and **packaging** → later, low-risk.
- **Web UI** → force a sunset-or-align decision (don't let it keep drifting), but not
  before v0.3.x.

### Risks we may be underestimating
- **Provider-abstraction scope creep** — normalizing auth, error codes, context windows,
  JSON mode, and rate limits is more than "an interface."
- **Ollama quality perception** — under-spec'd local models produce weak reviews; needs
  explicit tier warnings + `vibe doctor`.
- **Install friction** — git-clone-only blocks mainstream users; packaging matters more
  than "later" implies.
- **Web UI drift as a credibility tax** — every month of divergence makes the surface
  more confusing.
- **MCP support burden** — odd agent behaviors will surface as "vibe-council bugs";
  invest in logging early.

### Direct answers to the strategic sub-questions
- **Is OpenRouter the right next target?** Yes — it's a real, cited limitation and lock-in
  compounds with every new feature. The caveat is scope discipline (two providers).
- **Where does Headroom belong?** Early as a *spike*, conditional for commit — not the
  blind "later" the original plan implied, but not an unconditional early feature either.
- **Should MCP wait for provider abstraction?** It should follow *immediately after* the
  minimal provider interface lands, as experimental — not wait for full multi-provider
  stability, and not ship before the interface exists.

## Constraints

- Planning only. No implementation of Headroom, MCP, Ollama, provider abstraction, or
  cost estimate in this task.
- Council runs use `balanced` preset only (no premium), always with `--usage`.
- Raw `.council/` outputs stay local and are never committed.
