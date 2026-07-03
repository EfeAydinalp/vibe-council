# 02 — Product vision

## What the product is

vibe-council is becoming a **local-first AI Council Workbench**: a control plane on the developer's
own machine where AI agents **propose** code actions, a human **inspects and approves** them, and
only approved actions execute **behind deterministic guards**.

It is **not** merely "ask multiple models." The multi-model council (review, ranking, decision
memory) is one input. The product is the **propose → approve → guarded-execute loop** — the thing
that lets you give an AI agent real leverage without giving it blind write access.

## The core flow

```
agent (Claude / Codex / Fable / a custom worker) proposes an action
        │
        ▼
Workbench stores the proposal                (local runtime state)
        │
        ▼
deterministic trust boundary evaluates it    (the REAL guard: allow / block / needs-approval)
        │
        ▼
advisory approval auditor explains it        (human-readable risk summary; cannot relax the guard)
        │
        ▼
user approves / rejects / holds              (a decision — never itself an execution)
        │
        ▼
guarded executor runs ONLY approved, bounded actions
   • bounded file write/edit behind a verified local payload artifact
   • exact allowlisted command via a fixed argv, shell=False
        │
        ▼
result / status / decision / context is logged   (local, inspectable)
```

Every arrow is a boundary. The agent proposes; it does not act. The user decides; the decision does
not execute. The executor runs; it re-validates everything server-side first.

## The user problem

AI coding agents are getting genuinely capable — and getting write access. Most tooling lets them
**act first and surface it later**: edit files, run commands, open PRs, with the human reduced to
after-the-fact cleanup. The user loses **visibility** (what is it about to do?) and **control**
(can I stop it before it happens?).

vibe-council inverts that. The agent's intent becomes an explicit, inspectable **proposal**. The
human sees exactly what would happen — the file, the bytes, the exact command argv — and decides
before anything runs. A deterministic guard, not the model's judgment, decides what is even
*allowed* to be approved.

## The promise (one line)

**Agents propose. You approve. The Workbench guards execution.**

## Local-first — stated honestly

"Local-first" here means: **runtime state, payloads, decisions, and approvals stay on your machine**
(gitignored `.council/`), the panel binds `127.0.0.1` only, and the executor makes **no** provider/
model/network call. Nothing about the Workbench execution path phones home.

But be precise about the one honest caveat: the **council/review features send prompts, files, and
diffs to whatever model provider you configure** (e.g. OpenRouter) unless you use a **local provider**
(Ollama). So "local-first" is true of the Workbench and artifacts; it is *not* a claim that a
configured cloud review never transmits your code. Say this plainly in docs and on the website
([11-website-and-positioning.md](11-website-and-positioning.md)). Honesty here is a feature — it's
exactly the kind of trust the product is selling.

## Why this ordering matters

The security core (v0.5) had to exist before the bridge (v0.6), because the bridge's whole value is
filling the approval queue with agent proposals — which is only safe if approval, guarding, and
execution are already airtight. Everything downstream (onboarding, vault, personalization, mobile,
hosted) is convenience or reach built *on top of* that core, and must never weaken it. See
[03-security-invariants.md](03-security-invariants.md) and [04-roadmap.md](04-roadmap.md).
