---
id: DEC-20260702-workbench-panel-command-results
status: accepted
date: 2026-07-02
tags: [v0.5, workbench, panel, run_command, security, safety]
related: [DEC-20260702-workbench-command-executor, DEC-20260702-workbench-panel-execute, DEC-20260702-workbench-command-preview, DEC-20260701-workbench-trust-boundary]
published: true
---

# The panel exposes command execution only for approved allowlisted run_command actions, action id only

## Context

PR #80 added real `run_command` execution to the executor, but with no panel wiring — the panel's
`executable` flag required a payload artifact, which `run_command` actions never have, so no command
UI existed. This PR extends the panel (PR #77's execute path) to cover approved, resolver-allowlisted
`run_command` actions too, completing the v0.5 guarded-executor track.

## Decision

Extend `backend/workbench_panel.py`'s `_action_view`, `handle_execute`, and `render_html`.

- **Approval and execution remain separate.** Approving a command action still only records a
  decision; execution is still the same distinct, explicit `POST /api/actions/<action_id>/execute`.
- **The browser sends only the action id (and token) — never command data.** `handle_execute` still
  never reads a request body; a command string, argv, cwd, env, or timeout in the body has zero
  effect, verified by a dedicated test that posts a malicious body and asserts only the server-resolved
  argv reaches `subprocess.run`.
- **`Action.command_or_path` is the executor's only input.** The panel never constructs or forwards a
  command — it only asks the executor to run *this action id*, and the executor's own resolver
  (`backend/workbench_commands.py`) maps the label to a fixed argv, exactly as it already does for the
  dry-run preview and for real execution (PR #79/#80). The panel adds no new authority.
- **`executable` for `run_command` no longer requires a payload artifact** — that was always a
  file-action concept. Instead: `action.status == "pending"` and a fresh dry-run preview's
  `would_execute` (which itself requires the resolver **and** trust boundary to both pass). Everything
  that already gated real execution still gates the button.
- **The command preview shown is content-free and path-safe.** Label, fixed argv (with the local
  Python interpreter's absolute path masked to `<python>`, matching the panel's existing no-absolute-
  path convention), timeout, output cap, and `shell=false` — no cwd path is ever rendered (a static
  "runs in the project root" note substitutes for it).
- **Execution results stay bounded/redacted.** `handle_execute`'s response gains `exit_code`,
  `timed_out`, `output_truncated`, `stdout_summary`, `stderr_summary` for `run_command` results — all
  already bounded and redaction-checked by the executor (PR #80); the panel widens nothing.
- **File-action behavior is unchanged.** Payload verification, the "Execute approved file action"
  button, and their tests are untouched — the new logic only branches by `action.kind`.
- **Confirmation dialog differs by kind** — "This will run an exact allowlisted command in the project
  root. Continue?" for commands vs. the existing file-change wording — UX friction only, not a
  security boundary (the real boundary is the executor's invariant, unchanged).

## Rationale

- Reusing the existing `POST /api/actions/<id>/execute` endpoint (rather than adding a second one)
  keeps "the browser only ever sends an action id" a single, easy-to-audit invariant instead of two.
- Dropping the payload-artifact requirement for `run_command` (instead of inventing a fake "command
  payload" concept) matches what the resolver already established: commands don't carry content, they
  carry a label that resolves server-side.
- Masking the interpreter path in the displayed argv (not the executed argv) keeps the UI honest about
  what will run without leaking local filesystem structure, consistent with the panel's existing
  `_project_name` convention.

## Alternatives considered

- **Add a second endpoint for commands** — rejected; unnecessary duplication, and it would double the
  surface that has to be audited for "does the browser ever influence what runs."
- **Show the raw resolved argv including the real interpreter path** — rejected; leaks local path
  structure for no functional benefit (execution is unaffected either way).
- **Require some new "command approved" flag distinct from the existing approval/trust chain** —
  rejected; the resolver + trust boundary re-check at execution time is already the authority; adding
  a parallel flag would only create a second thing that could drift out of sync.

## Consequences

- The v0.5 guarded-executor track (PR #72 plan → PR #81) is complete: task → visible stages → audited
  approval → explicit, guarded execution (file or command) → logged, for the Workbench's first
  vertical slice.
- No dependency/provider/network change; localhost-only and token-gated behavior is unchanged.
- Future work (mobile/LAN/voice, multi-command batches, a new command allowlist entry) is explicitly
  out of scope here and remains deferred.

## Next actions

- None required for the guarded-executor track; future v0.5 work returns to the broader roadmap
  (`docs/plans/v0.5-workbench-mvp.md`).

## Related links

- Decision: [command executor](./2026-07-02-workbench-command-executor.md)
- Decision: [panel execute](./2026-07-02-workbench-panel-execute.md)
- Decision: [command preview](./2026-07-02-workbench-command-preview.md)
- Guard: [deterministic trust boundary](./2026-07-01-workbench-trust-boundary.md)
