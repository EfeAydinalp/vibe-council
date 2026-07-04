# Decisions (index)

An **append-only index/summary** of high-level project decisions — **not** a canonical store. The
source of truth is [`docs/decisions/*.md`](../../decisions/); this file is a short, agent-readable
pointer so a reader can find the shape of the project's decisions quickly. **Never restate or
compete with `docs/decisions/`** — link to it. Add new entries at the bottom; do not rewrite history.

Format per entry: `- **<decision>** — <one line>. (source: <pointer, if a curated record exists>)`

## High-level decisions (summary)

- **Local-first AI Council Workbench.** The product runs on the user's machine with their own API
  key; runtime state, payloads, decisions, and approvals stay local (gitignored `.council/`). Only
  the model calls the user explicitly triggers leave the machine.
- **Approval is separate from execution.** Approving a Workbench action records a decision only; it
  never writes a file or runs a command. Execution is a separate, explicit step through the guarded
  executor, which re-validates the deterministic trust boundary at execution time. (source:
  [`docs/fable/03-security-invariants.md`](../../fable/03-security-invariants.md))
- **Deterministic trust boundary is the real guard; the Approval Auditor is advisory only.** The
  auditor can never relax a blocked/high-risk verdict.
- **Agent proposals are file/CLI intake only — no network endpoint.** `vibe workbench propose`
  validates a schema-v1 proposal and mints ids + payload hash server-side; agents never submit
  argv/hash/ids/status. (source:
  [`docs/workbench-agent-bridge.md`](../../workbench-agent-bridge.md))
- **`docs/context/project/` is the project-vault root.** Curated, committed, public-safe Markdown
  project memory (this folder). Not a database, not an Obsidian dependency. (source:
  [`docs/fable/08-obsidian-project-vault.md`](../../fable/08-obsidian-project-vault.md))
- **Fable is architect / technical lead; Opus/Sonnet implement routine PRs.** Fable is reserved for
  major phase planning, critical architecture/security blockers, and high-leverage reviews — not
  routine implementation or docs-only work. (source:
  [`docs/fable/v0.6-followup-implementation-plan.md`](../../fable/v0.6-followup-implementation-plan.md))
- **License/provenance remains an unresolved "Question 0."** No commercial-clearance claim; no
  `LICENSE` is added; upstream attribution to `karpathy/llm-council` is preserved.

## What must NOT go here

- No secrets, API keys, tokens, or private local paths.
- No raw model/council outputs or runtime payloads.
- No restatement of a decision's full body — link to the `docs/decisions/*.md` record instead.
- No private commercial/feasibility detail (that stays private/local).
