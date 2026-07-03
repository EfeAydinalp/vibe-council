# Workbench agent proposal bridge

How an AI agent (Claude Code, Codex, Fable, or a custom worker) proposes a code action into the
local **AI Council Workbench**, and how a human reviews and executes it. This is the v0.6 bridge —
built across PR #95 (schema + validation), PR #96 (importer + CLI intake), and PR #97 (panel
proposed-by-agent visibility).

The one-line mental model: **agents propose, you approve, the Workbench guards execution.** An
agent's proposal is a *request*, never an action. Nothing runs until a human explicitly approves it
in the panel and then explicitly executes it.

---

## A. Overview

### What it is

A **local, file/CLI-based** intake that turns a validated proposal JSON into a pending approval the
Workbench panel already knows how to show and gate. There is **no network endpoint** — an agent
writes a JSON file (or pipes JSON on stdin) and runs a CLI command on the same machine.

### Why it exists

AI agents increasingly have write access and tend to *act first, ask later*. The bridge inverts
that: the agent's intent becomes an explicit, inspectable proposal, and a human sees exactly what
would happen — the file, the byte count, the exact allowlisted command — and decides before anything
runs. A deterministic guard, not the model's judgment, decides what is even *allowed* to be approved.

### The flow

```
agent writes proposal JSON
   -> vibe workbench propose <proposal.json | ->
   -> Workbench validates the schema (v1, strict; fail-closed)
   -> importer mints task/approval/action ids and the payload hash SERVER-SIDE
   -> file payload is stored in a local, write-once payload artifact
   -> panel shows the task with a "proposed by agent: <name>" badge + a pending approval
   -> a human approves / rejects / holds in the panel     (a decision only — never execution)
   -> if approved, the human clicks Execute as a SEPARATE explicit step
   -> the existing guarded executor runs it (re-validating the trust boundary at execution time)
```

Every arrow is a boundary. The agent proposes; it does not act. The human decides; the decision does
not execute. The executor runs; it re-validates everything server-side first. The importer,
executor, trust boundary, and auditor are unchanged by the bridge — it only adds an *intake*
upstream of the approval.

---

## B. Safety model

The bridge preserves every Workbench security invariant
([docs/fable/03-security-invariants.md](fable/03-security-invariants.md)). Concretely:

- **No network endpoint.** File/CLI intake only, on the local machine. No HTTP API for agents, no
  CORS, no LAN/mobile/remote surface.
- **No auto-execution.** Importing a proposal creates a *pending* approval and a *pending* action —
  it never writes a file or runs a command. Approval is a separate human step; execution is a
  further separate explicit step.
- **Agents never submit execution parameters.** `argv`, `env`, `cwd`, `timeout`, and `shell` cannot
  appear in a proposal — the schema rejects them outright. For commands, only an exact allowlisted
  `command_label` is accepted; the resolver provides the fixed argv server-side at execution time.
- **Agents never assert identity or verdicts.** `payload_hash`, `action_id`, `approval_id`,
  `task_id`, `status`, `risk`, `verdict`, `blocked`, and `findings` are all hard-rejected if present.
- **The server mints everything.** Task/approval/action ids come from the runtime store; the payload
  hash is computed server-side from the submitted content.
- **Raw payload stays local.** File content lives **only** in the local, gitignored, write-once
  payload artifact (`.council/runtime/payloads/`). It is never stored in the task/approval/action
  JSON, never in the dedup record, and **never rendered** in the panel HTML or the `/api/state` JSON
  (only safe, content-free metadata — agent name/role, `proposal_id`, byte counts — is shown).
- **Commands are exact allowlisted labels only.** No freeform command strings, no shell, ever.
- **The executor re-validates at execution time.** A stored audit or a cached preview cannot
  authorize anything; the deterministic trust boundary is re-run at the moment of execution.
- **The trust boundary is deterministic and authoritative;** the Approval Auditor is **advisory
  only** and can never relax a blocked/high-risk verdict.

> **Local-first, honestly.** Runtime state, payloads, decisions, and approvals stay on your machine,
> and the executor makes no network call. **But** the council/review features (`vibe review`,
> `vibe diff`) send prompts, files, and diffs to whatever model provider you configure unless you use
> a local provider (Ollama). "Local-first" describes the Workbench and its artifacts — it is not a
> claim that a configured cloud review never transmits your code.

---

## C. CLI usage

```sh
# import a proposal from a file
vibe workbench propose path/to/proposal.json

# or read the proposal JSON from stdin
vibe workbench propose -
```

(If `vibe` isn't on your PATH, use `uv run python -m backend.cli workbench propose …` or
`python -m backend.cli workbench propose …` from the repo root.)

**Success output.** `propose` prints a JSON result to **stdout** (machine-readable; never any raw
payload content) and a short human summary + next step to **stderr**. On a fresh import:

```json
{
  "ok": true,
  "created": true,
  "duplicate": false,
  "conflict": false,
  "errors": [],
  "kind": "write_file",
  "target": "docs/example.md",
  "task_id": "task-…",
  "approval_id": "appr-…",
  "action_id": "act-…",
  "payload_artifact": true,
  "audit_risk": "medium",
  "audit_blocked": false,
  "agent_name": "claude-code",
  "proposal_id": "add-readme-note-001",
  "next_step": "run 'vibe workbench serve' and review/approve the pending approval in the panel; approving records a decision only — execution is a separate explicit step"
}
```

**Failure behavior.** An invalid proposal (schema violation, denied path, non-allowlisted command,
smuggled server field, malformed JSON) exits **non-zero**, sets `"ok": false` with human-readable
`errors`, and **creates nothing** — no task, approval, action, or `.council/` files.

**Panel next step.** Start the panel with `vibe workbench serve`, open the printed
`http://127.0.0.1:<port>/?token=…` URL, and the imported proposal appears as a task with a
"proposed by agent: `<name>`" badge and a pending approval card.

**No execution happens from `propose`.** It only validates and records a pending approval.

---

## D. Proposal examples (safe)

### write_file

```json
{
  "proposal_schema": 1,
  "proposal_id": "add-readme-note-001",
  "agent": { "name": "claude-code", "role": "coder" },
  "title": "Add a usage note to docs/example.md",
  "summary": "Documents the new flag so users find it.",
  "action": {
    "kind": "write_file",
    "target": "docs/example.md",
    "payload": { "content": "# Example\n\nUsage note.\n", "overwrite": false }
  }
}
```

### edit_file

```json
{
  "proposal_schema": 1,
  "proposal_id": "null-check-parseconfig-001",
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

### run_command

```json
{
  "proposal_schema": 1,
  "proposal_id": "run-tests-001",
  "agent": { "name": "codex", "role": "reviewer" },
  "title": "Run the test suite",
  "summary": "Verify the change before approval.",
  "action": { "kind": "run_command", "command_label": "python -m unittest discover -s tests -t ." }
}
```

`run_command` accepts **only an exact allowlisted label** — the small, fixed set of
verification/status commands the resolver knows (e.g. the test suite, `vibe lint --redaction`,
`vibe context check`, `git status --short`). It never carries a payload, argv, or shell.

---

## E. Rejected examples / common mistakes

All of these **fail closed** — the import exits non-zero and creates nothing.

- **Freeform / mutated command** (inert, clearly-labelled rejection example):
  ```json
  { "kind": "run_command", "command_label": "rm -rf / ; git push --force" }
  ```
  Rejected: not an exact allowlist label, and it contains shell metacharacters. `run_command` never
  accepts a freeform string.
- **Execution parameters** — any of `argv`, `env`, `cwd`, `timeout`, `timeout_seconds`, or `shell`
  on the action → rejected. The resolver owns argv; agents never supply it.
- **Smuggled server-minted field** — e.g. `"payload_hash": "sha256:…"` or `"status": "approved"` on
  the action/payload → rejected. The server computes the hash and mints ids/status.
- **Absolute, traversal, or denylisted path** — e.g. `/etc/passwd`, `C:\…`, `../outside.md`,
  `.env`, `.git/config`, `id_rsa`, a private plan file → rejected. Targets must be **relative and
  inside the project root**, and must pass the deterministic path check.
- **`cloud_call`** (or `read_file`, or any kind other than the three above) → rejected. Cloud egress
  is not agent-proposable in v0.6.
- **Duplicate `proposal_id`, identical content** → **not** an error: the import is idempotent and
  returns the original `task_id`/`approval_id`/`action_id` with `"duplicate": true`, creating nothing
  new. `proposal_id` is the global dedup key.
- **Duplicate `proposal_id`, different content** → **conflict**: exits non-zero with `"conflict":
  true` and creates/updates nothing. Submit the changed content under a **new** `proposal_id`.

See [docs/fable/06-proposal-schema.md](fable/06-proposal-schema.md) for the full field reference.

---

## F. Instructions for agents (copy-paste)

```
To make a code change in a project that uses vibe-council's Workbench, DO NOT edit files or run
commands directly. Instead:

1. Write a proposal JSON (schema v1). Use exactly one action per proposal:
   - write_file / edit_file: a RELATIVE target inside the project + a payload
     (write_file: {content[, overwrite]}; edit_file: {old_text, new_text[, max_replacements]}).
   - run_command: an EXACT allowlisted command_label only (e.g. the test suite) — no argv/shell.
   Include a stable, unique proposal_id (reuse it only to retry the SAME content; new content needs
   a new id), an agent {name[, role]}, a title, and a one-paragraph summary.

2. NEVER include: a freeform command; argv/env/cwd/timeout/shell; payload_hash or any *_id/status/
   risk/verdict; an absolute or "../" path; a cloud_call. The server mints ids and the hash.

3. Submit it locally:  vibe workbench propose path/to/proposal.json   (or: … propose -  for stdin)

4. Read the JSON result on stdout. If ok:true, tell the user:
   "Proposed <kind> <target> to the Workbench (approval <approval_id>). Open the panel with
   'vibe workbench serve' and approve/reject/hold it; nothing has run yet."
   If ok:false, fix the reported errors and resubmit.

5. Do NOT claim the change was applied until an approved action has actually been executed and its
   result exists. Do not bypass the Workbench. Do not stage or commit .council/ or payload artifacts.
```

---

## G. Human operator workflow

1. **Start the panel:** `vibe workbench serve` → open the printed `http://127.0.0.1:<port>/?token=…`
   URL.
2. **Receive the proposal:** run (or let the agent run) `vibe workbench propose <file | ->`. The
   task appears with a **"proposed by agent: `<name>`"** badge and a pending approval card.
3. **Inspect:** read the risk label, the human-readable rewritten prompt, the target/command, and
   the payload's byte-count summary. Raw file content is never shown.
4. **Decide:** **Approve / Reject / Hold**. Approving records a decision only — it never executes.
5. **Execute (optional, explicit):** for an approved bounded file action or an exact allowlisted
   command, click **Execute** and confirm. The guarded executor re-validates the trust boundary and
   then performs the bounded action.
6. **Inspect the result:** a completed/failed/blocked action shows a safe, content-free result
   summary (bytes written, exit code, timeout/truncation flags) — never raw content or unbounded
   output.

---

## H. Non-goals

The bridge is deliberately **not**:

- **Autonomous execution** — a human always approves, and execution is a separate explicit step.
- **A network / HTTP API** — file/CLI intake only; no new endpoint, no CORS, no LAN/mobile/remote.
- **Arbitrary shell** — commands are exact allowlisted labels resolved to a fixed argv, `shell=False`.
- **Personalization** or a **project vault** or a **website** — separate, later, out of scope here.

---

## See also

- [docs/fable/05-v0.6-agent-bridge.md](fable/05-v0.6-agent-bridge.md) — the bridge design.
- [docs/fable/06-proposal-schema.md](fable/06-proposal-schema.md) — the full schema reference.
- [docs/fable/03-security-invariants.md](fable/03-security-invariants.md) — the non-negotiable
  security invariants the bridge preserves.
- [docs/agent-quickstart.md](agent-quickstart.md) — using vibe-council as a reviewer/memory layer.
