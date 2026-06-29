# Operator control loop / approval inbox (spec)

A **docs-only design spec** for a minimal, local-first **operator inbox**: a tiny coordination layer
so users don't miss when Claude/agents are waiting for them. **No code is implemented in this PR** —
this defines the shape, boundaries, and roadmap fit.

**What this is not:** not a dashboard implementation, not a mobile app, not a custom remote-control
transport. It is a minimal status-event design that can **later** integrate with Claude Code context
export, MCP read-only, and official Claude Remote Control-friendly workflows. Keep it **local-first,
safe, and small**.

## Problem

When running councils/agents, users can **miss when Claude/agents are waiting** for:

- approval,
- a choice between options,
- tests failing,
- PR ready,
- merge ready,
- a blocked state,
- manual review needed.

The tool waits **silently** while the user is elsewhere — wasted time and stalled work.

## Product principle

The operator loop is a **tiny local-first coordination layer**:

- status visibility,
- approval awareness,
- next-action clarity,
- **no secrets in notifications**,
- **no custom phone transport early**,
- **no dashboard until the context/memory layer works**.

It is a thin status/event surface over work that already happens locally — not a new product.

## Early expected shape

A local **event/status model**, possibly later implemented as a **gitignored** local event log. Nothing
here is built yet.

### Example event types

`approval_required` · `choice_required` · `pr_ready` · `tests_failed` · `merge_ready` · `blocked` ·
`done` · `needs_review`

### Possible local storage shape (examples only — do not implement yet)

- `.council/operator/events.jsonl` — an append-only local event log.
- `.council/operator/status.json` — the current rolled-up status.

These would live under the **gitignored `.council/`** workspace and are **never committed**.

### Minimal event fields

Each event should carry only **minimal, public-safe** fields:

- `timestamp`
- `task_id` / `run_id`
- `event_type` (one of the types above)
- `message` — short, public-safe summary
- `choices` — optional allowed choices (for `choice_required`)
- `next_action` — what the user should do next
- `severity` — e.g. info / warn / blocking
- `source` — which run/skill emitted it
- `redaction_safe` — a flag asserting the event was redaction-checked

### Events must **not** include

- API keys,
- full prompts,
- private diffs,
- raw council output,
- private commercial details,
- local absolute paths (unless explicitly safe),
- secrets,
- customer data.

Redaction is **defense-in-depth**, not a guarantee: the safe default is to emit a terse pointer
("approval needed for run X — run `vibe operator status`"), not the underlying content.

## CLI shape (future only — do not implement in this PR)

Possible future commands:

- `vibe operator status` — show current rolled-up status.
- `vibe operator events` — list recent events.
- `vibe operator clear` — clear/acknowledge the local log.
- `vibe operator wait` — block until the next actionable event.
- `vibe operator notify` — emit/route a notification.

Stdout stays machine-readable; diagnostics go to stderr; no model call for status/list.

## Notification shape (future only — do not implement in this PR)

Possible **later** notification targets:

- terminal bell,
- desktop notification,
- file watcher,
- OS notification,
- Claude Remote Control-friendly prompt points.

**Do not implement custom mobile push. Do not build our own remote approval transport now.** Where
phone/remote approval is wanted, **design around official Claude Remote Control** — run inside a
Remote-Control'd Claude Code session and surface clear, push-worthy decision points through the
official primitives.

## Relation to roadmap

Ties into the [track-based roadmap](track-based-roadmap.md):

- **v0.3.x** — operator inbox **design** (this spec; no transport built).
- **v0.4.0** — Claude Code context export + **MCP read-only** + Remote Control-friendly workflow; an
  early local inbox (events log + terminal/desktop notification).
- **v0.7+** — dashboard/orchestration **only after** the memory/context layer works.

## Relation to project memory

**Operator events are not canonical project memory.** They must **not** become public docs
automatically. Only **human-approved/promoted** outcomes may become:

- decision records (`docs/decisions/*.md`),
- `STATUS` updates,
- context-pack inputs,
- rolling summaries.

The event log is ephemeral/local; the curated memory is the [project-memory folder](../context/project/README.md)
and the [decision records](../decisions/) — the source of truth.

## Risks

- **Custom insecure mobile transport** — the biggest trap; design around official Remote Control instead.
- **Leaking private data through notifications** — mitigate with redaction + terse pointers, never content.
- **Event log becoming a raw transcript archive** — keep events minimal; raw outputs stay in gitignored
  `.council/`.
- **Dashboard scope creep** — keep it a thin status surface, not a UI product.
- **Approval fatigue / too many noisy notifications** — severity gating + sensible defaults.
- **Unclear ownership of "who approves"** — a single human owner per run by default.

## Non-goals (explicit)

- **No dashboard now.**
- **No mobile app now.**
- **No hosted sync now.**
- **No custom push infrastructure now.**
- **No write-capable MCP now** (read-only first; writes behind approval later).
- **No automatic committing from operator events.**
- **No raw transcript archival.**

## Later milestones (a possible future path)

1. **docs/spec only** (this PR).
2. local `.council/operator/` event model.
3. CLI status commands (`status` / `events`).
4. desktop/terminal notification.
5. integration with the context-pack builder.
6. MCP read-only visibility.
7. Remote Control-friendly approval flow.
8. a dashboard **only if** real usage justifies it.

Each step is prerequisite-gated: a step starts only when the one before it has proven useful.
