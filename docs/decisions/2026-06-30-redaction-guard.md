---
id: DEC-20260630-redaction-guard
status: accepted
date: 2026-06-30
tags: [security, redaction, tooling, v0.3, local-first]
related: [DEC-20260629-operator-control-loop, DEC-20260629-linked-decision-memory, DEC-20260629-track-based-roadmap]
published: true
---

# Redaction guard (`vibe lint --redaction`)

## Context

The compact council roadmap review identified the redaction guard as the **first implementation
blocker** before generated docs, extract/promote, context packs, or MCP export: those features all
write/share docs derived from raw runs, and there was no mechanism to check them. Redaction was
"named, not built." A minimal, deterministic, stdlib-only guard is needed first.

## Decision

Add a minimal **`vibe lint --redaction`** command plus a public **[redaction policy](../redaction-policy.md)**:

- A new `lint` subcommand (CLI shape note below) scans the **tracked public docs** by default, or
  **explicit paths** if given; **no model call, no API key**.
- **Exit `0`** when clean; **non-zero** when a blocking finding exists.
- **Two severities:** `critical` (real leaks — always block) and `warning` (advisory — block only
  with `--strict`). This keeps the guard usable on a repo that legitimately contains public
  third-party pricing or illustrative output samples.
- **Secret and per-user-path matches are masked** in output; the guard never reprints a full secret
  or username.
- Implemented as `backend/redaction.py` (stdlib-only, per-line regex) with unit tests.

**CLI shape note:** the requested `vibe lint --redaction` is implemented as a `lint` subcommand with a
`--redaction` flag (redaction is the only check today; the flag is explicit/forward-compatible) and
optional positional paths — consistent with the existing subcommand-based CLI.

## Rationale

- Unblocks the v0.3 safety story: decision promote, context-pack export, and STATUS/PROGRESS export
  can be checked before commit/share.
- Defense-in-depth: a deterministic pattern scanner catches common leaks cheaply; it complements
  (does not replace) keeping raw `.council/` gitignored and human review.
- The two-severity model avoids noisy failures while still hard-failing on real secrets/paths.

## Alternatives considered

- **Regex-only CI grep (no command)** — rejected; not reusable locally, no masking, no severity model.
- **Fail on every match (no warnings)** — rejected; would false-fail on public third-party pricing and
  documentation output samples.
- **A heavyweight secrets scanner dependency** — rejected; stdlib-only keeps the core dependency-light.
- **Match all `.council/<sub>/` paths** — rejected; only **date-stamped** concrete artifacts are
  flagged, so the many benign convention mentions don't false-positive.

## Consequences

- A reusable safety gate exists for generated/promoted docs (local and, later, CI).
- Redaction remains **defense-in-depth, not a guarantee** — human review still required (documented).
- Warnings (third-party pricing, output samples) are advisory; teams can opt into `--strict`.
- New module + tests; no provider behavior change, no new dependencies.

## Next actions

- Use `vibe lint --redaction` before promoting decisions and before committing generated docs.
- Wire it into the v0.3 decision-promote / context-pack flows; consider a CI check later.

## Related links

- Policy: [redaction policy](../redaction-policy.md)
- Related: [operator control loop](./2026-06-29-operator-control-loop.md),
  [linked decision memory](./2026-06-29-linked-decision-memory.md),
  [track-based roadmap](./2026-06-29-track-based-roadmap.md)
