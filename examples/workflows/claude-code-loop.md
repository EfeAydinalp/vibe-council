# Workflow: the Claude Code (agent) loop

How an AI coding agent should use vibe-council as a review gate. The agent runs the
council, **filters** the feedback, and reports cost — it never treats the council as
an authority that auto-applies changes.

> Print this block any time with `vibe guide claude`, or append it to a project's
> `CLAUDE.md` with `vibe guide claude --write CLAUDE.md`. The canonical loop also
> lives in [`docs/agent-integrations.md`](../../docs/agent-integrations.md) — if the
> two ever differ, that file wins.

## The loop

```text
1. vibe status
2. vibe decisions context "<topic>"        # read prior decisions before planning
3. write plan.md
4. vibe review --preset balanced --file plan.md --yes --usage
5. revise plan.md  (apply only useful feedback — see "Filtering" below)
6. implement
7. vibe diff --preset balanced --yes --usage
8. apply only useful feedback
9. vibe extract --preset balanced --file plan.md --save --yes --usage
10. final report: files changed, council commands run, cost/tokens, .council/ paths
```

Agents pass `--yes` (non-interactive); a human at a terminal can drop it to see the
approval prompt first.

## Filtering: council output is advice, not authority

The agent (and the human reviewing the agent) decides what to act on. A good filter:

- **Act on:** correctness bugs, security issues, real cost blow-ups, missing
  constraints/edge cases, and concrete factual errors.
- **Be skeptical of:** style preferences, speculative rewrites, "consider also…"
  expansions, and suggestions that widen the PR's scope.
- **Never** let the agent apply a diff or land a change **without human review** just
  because the council suggested it.

State in the final report *which* findings you applied and which you deliberately
declined, with a one-line reason. That record is more useful than the raw review.

## Preset/cost policy for agents

- **`cheap`** — smoke tests, retries, and changes too small to deserve a full gate
  (e.g. a one-line docs fix).
- **`balanced`** *(default for real work)* — the plan and diff quality gates above.
- **`full`** — only for genuinely big strategic/architecture decisions; it costs more
  and rarely adds signal over `balanced` for routine review.
- **`premium`** — only when the human explicitly requests it; always requires
  `--allow-premium`.

Always pass **`--usage`** so the final report can include provider-reported
tokens/cost when available. Rough anchors from real runs: a `balanced` review is
≈ $0.15–0.30 and an `extract` is ≈ $0.03 — **approximate and provider-dependent**.

## Safety

- Never print or commit the `OPENROUTER_API_KEY`.
- Never commit `.council/`, `data/`, or `.env` — they're local-only and gitignored.
- The council's job is a second opinion. The developer/agent owns the decision.
