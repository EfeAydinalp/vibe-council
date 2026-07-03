# 06 — Proposal schema (concrete)

The wire contract an agent authors and `vibe workbench propose` imports. **Both layers are
implemented:** validation (`backend/workbench_proposals.py` — schema v1, strict,
pure/side-effect-free) and the importer (`backend/workbench_proposal_importer.py` +
`vibe workbench propose <file | ->` — server-minted ids/hash, dedup by `proposal_id`, conflict on
changed content, no execution). The importer is the authority; anything not listed as
agent-suppliable is server-minted or rejected.

## Envelope

```json
{
  "proposal_schema": 1,
  "proposal_id": "agent-supplied-uuid-or-content-hash",
  "agent": {
    "name": "claude-code",
    "role": "coder",
    "session": "opaque-session-label"
  },
  "title": "Add a null check to parseConfig",
  "summary": "One short human-readable paragraph explaining the intent and why.",
  "action": {
    "kind": "write_file | edit_file | run_command",
    "target": "relative/path/within/project",
    "command_label": "git status --short",
    "payload": { "...": "file kinds only; see below" },
    "scope": { "files_changed": 1, "lines_changed": 8 }
  }
}
```

## Fields

| Field | Who | Notes |
|---|---|---|
| `proposal_schema` | agent | Required. Integer. `1` for v0.6.0. Reject unknown versions. |
| `proposal_id` | agent | Required. Stable per logical proposal; used for **dedup**. |
| `agent.name` | agent | Required. Short label (e.g. `claude-code`, `codex`, `fable`). |
| `agent.role` | agent | Optional. One of the launcher roles (task-shaper/planner/coder/reviewer/release-manager). Display only. |
| `agent.session` | agent | Optional. Opaque; display/audit only. Never a secret. |
| `title` | agent | Required. Short. Escaped before display. |
| `summary` | agent | Required. Human context. Escaped; never treated as payload. |
| `action.kind` | agent | Required. Exactly one of `write_file` / `edit_file` / `run_command`. |
| `action.target` | agent | Required for file kinds. Relative path inside the project root. |
| `action.command_label` | agent | Required for `run_command`. **Exact allowlist label only.** |
| `action.payload` | agent | File kinds only. Content/patch (see below). |
| `action.scope` | agent | Optional hints (`files_changed`, `lines_changed`) — advisory to risk sizing. |
| `task_id`, `action_id`, `approval_id` | **server** | Minted. Reject if present in the proposal. |
| `payload_hash` | **server** | Computed over `{kind,target,payload}`. Reject if agent-supplied. |
| `status`, verdicts, risk, `created_at` | **server** | Never agent-supplied. Reject if present. |

### Payload shapes (file kinds only)

`write_file`:
```json
{ "content": "full new file text", "overwrite": false }
```

`edit_file`:
```json
{ "old_text": "exact existing text", "new_text": "replacement", "max_replacements": 1 }
```

## What agents MAY submit

- `write_file` / `edit_file` with a `target` **inside the project root** and bounded content.
- `run_command` **only as an exact allowlist label** (the resolver's fixed set) — never a freeform
  command string, never argv.
- Metadata: `title`, `summary`, `agent.*`, `proposal_id`, `action.scope`.

## What agents MUST NEVER submit

- Any `command_label` outside the allowlist; any argv, cwd, env, timeout, or shell string.
- `cloud_call` (deferred; not agent-proposable in v0.6).
- Absolute paths, `..` traversal, or paths hitting the deny list (secrets/`.env`/`.git`/`.council`/
  private plans). The trust boundary blocks these, but the importer should reject early with a clear
  message.
- A precomputed `payload_hash`, any `*_id`, any `status`, any risk/verdict/"pre-approved" flag.
- Auditor output or anything asserting the action is already allowed.

## Schema versioning

- `proposal_schema` is a required integer. v0.6.0 accepts `1` only; unknown versions are rejected
  with a clear error (forward-compatibility is a future decision, not an implicit accept).
- Additive fields the importer doesn't recognize should be rejected in v1 (strict), not silently
  dropped — strictness protects the trust boundary from smuggled fields.

## Dedup behavior

- Keyed on `proposal_id`. First import creates the task/approval/action and records the mapping.
- A repeat `proposal_id` returns the existing `{task_id, approval_id, action_id}` and does **not**
  create new records or re-run side effects.
- Missing `proposal_id` → reject (required for safe retries).

## Payload hash behavior

- The server computes `payload_hash` over `{kind, target, payload}` at import (existing
  `canonical_payload_hash`), stores it in the write-once artifact, and re-verifies it at execution.
- The agent never supplies or influences the hash. If content changes, it's a different proposal
  (new `proposal_id`).

## Examples

### Valid `write_file`
```json
{
  "proposal_schema": 1,
  "proposal_id": "c0ffee-write-readme-note",
  "agent": { "name": "fable", "role": "coder" },
  "title": "Add a usage note to docs/example.md",
  "summary": "Documents the new flag so users find it.",
  "action": {
    "kind": "write_file",
    "target": "docs/example.md",
    "payload": { "content": "# Example\n\nUsage note.\n", "overwrite": false }
  }
}
```

### Valid `edit_file`
```json
{
  "proposal_schema": 1,
  "proposal_id": "c0ffee-edit-parse-config",
  "agent": { "name": "claude-code", "role": "coder" },
  "title": "Null-check parseConfig",
  "summary": "Avoids a crash on missing config.",
  "action": {
    "kind": "edit_file",
    "target": "src/config.py",
    "payload": { "old_text": "cfg.value", "new_text": "(cfg.value if cfg else None)", "max_replacements": 1 }
  }
}
```

### Valid `run_command`
```json
{
  "proposal_schema": 1,
  "proposal_id": "c0ffee-run-tests",
  "agent": { "name": "codex", "role": "reviewer" },
  "title": "Run the test suite",
  "summary": "Verify the change before approval.",
  "action": { "kind": "run_command", "command_label": "python -m unittest discover -s tests -t ." }
}
```

### Rejected — freeform/mutated command
```json
{
  "proposal_schema": 1,
  "proposal_id": "bad-freeform",
  "agent": { "name": "unknown" },
  "title": "cleanup",
  "summary": "…",
  "action": { "kind": "run_command", "command_label": "rm -rf / ; git push --force" }
}
```
Rejected: not an exact allowlist label, contains shell metacharacters, and (even if it resolved)
`run_command` never accepts a freeform string. Importer fails closed; nothing is created.

### Rejected — smuggled server field
```json
{
  "proposal_schema": 1,
  "proposal_id": "bad-smuggle",
  "agent": { "name": "x" },
  "title": "…", "summary": "…",
  "action": { "kind": "write_file", "target": "docs/x.md",
              "payload": { "content": "hi" }, "payload_hash": "sha256:deadbeef", "status": "approved" }
}
```
Rejected: `payload_hash` and `status` are server-minted; their presence is an authorship red flag.
