# 13 — Fable implementation playbook

How to actually run Fable (or Opus / Claude Code) against this repo, safely, phase by phase.

## Ground rules

- **Human remains the final authority.** Fable implements and reviews; it does **not** merge, tag, or
  release autonomously. A maintainer approves and merges.
- **Phase-based.** One roadmap phase at a time ([04-roadmap.md](04-roadmap.md)); usually several small
  PRs per phase. Never batch phases.
- **Each phase reads only its relevant docs.** Don't dump the whole pack into one prompt — it wastes
  context and blurs scope. Minimum reading set per phase is listed in
  [14-fable-prompt-templates.md](14-fable-prompt-templates.md).

## Per-PR loop

1. Read: [01-operating-rules.md](01-operating-rules.md), [03-security-invariants.md](03-security-invariants.md),
   and the phase doc.
2. `vibe status`. For non-trivial work, write and review a short `plan.md`.
3. Implement a **small** diff. Match surrounding style.
4. Verify (all of these, every PR):
   - `python -m unittest discover -s tests -t .` (use the synced `.venv` interpreter)
   - `vibe diff --preset <cheap|balanced> --usage` (balanced for security/architecture diffs)
   - `vibe lint --redaction` → 0 critical
   - `vibe decisions lint` → passes
   - `vibe context build` → no traceback (budget-trim warnings OK)
   - `vibe context check` → 21/21
   - `vibe mcp inspect --context --health` → 21/21
   - `git status --short` → no private/runtime/generated artifacts staged
5. Re-verify the security invariants against the diff ([03](03-security-invariants.md)).
6. Stage only intended files; show `git diff --cached --stat` and `--name-only`; commit; push; open PR
   with a final report.

## Scratch notes

- Fable may keep a working `notes.md` / local progress note **locally**, but **do not commit raw
  scratch notes.** If a note becomes durable project knowledge, curate it into the vault
  ([08-obsidian-project-vault.md](08-obsidian-project-vault.md)) or a decision record — don't dump the
  raw scratch into the repo.

## When to use which model

- **Fable** — larger, long-running phase implementation where sustained context matters (e.g. the
  v0.6 bridge across several PRs). Still small PRs; still human-merged.
- **Sonnet / Opus** — focused implementation, reviews, and tighter single-PR work.
- **The council (`vibe review`/`diff`)** — an independent second opinion on plans/diffs, especially
  security-relevant ones. Use balanced for those; full only for major architecture/security calls.

Fable can implement larger phases, but the "human is final authority," "small PRs," and "verify every
PR" rules do not relax for it.

## Stop conditions (halt and ask)

Stop immediately and surface the issue — do not push through — if you hit any of:

- a **security-invariant conflict** (the change would weaken anything in [03](03-security-invariants.md))
- an **unexpectedly broad diff** (the change sprawled beyond the phase's scope)
- **dependency churn** you didn't intend (new runtime dep, `uv.lock` graph change)
- a request that implies a **version bump, tag, or release** not explicitly instructed
- any **private artifact touched** (`.council/`, payloads, `.env`, private plans, secrets)
- tests that fail for reasons you don't understand (report the output; don't paper over it)

## Reporting

Report faithfully. If tests fail, say so with the output. If a step was skipped, say that. When
something is done and verified, state it plainly. Every PR ends with the final report shape defined in
the phase's prompt template.
