# 14 — Fable prompt templates (copy-paste)

Ready-to-use prompts. Fill the `<…>` placeholders. Every template names the files to read first, the
scope, non-goals, verification, and the required final report. Keep to one phase per prompt.

Common verification block (referenced below as **[VERIFY]**):

```
Verify (run all; report each):
- python -m unittest discover -s tests -t .   (use the synced .venv interpreter)
- vibe diff --preset <cheap|balanced> --usage
- vibe lint --redaction        (expect 0 critical)
- vibe decisions lint          (expect pass)
- vibe context build           (budget-trim warnings OK; no traceback)
- vibe context check           (expect 21/21)
- vibe mcp inspect --context --health   (expect 21/21)
- git status --short           (no .council/, runtime, payloads, private plans, env/venv/data/secrets, uv.lock)
```

Common final-report block (referenced as **[REPORT]**):

```
Final report: branch, commit hash, PR URL, files changed, exactly what changed, whether any security
invariant was touched, whether code/tests/deps changed, all [VERIFY] results, vibe diff cost, and the
exact final git status --short. Confirm no private/runtime/generated artifacts were staged.
```

---

## Project Doctor prompt

```
Read docs/fable/00-current-state.md and docs/fable/01-operating-rules.md.
Task: report the current health of this repo without changing anything. Run vibe status, the test
suite, vibe lint --redaction, vibe decisions lint, vibe context check, and vibe mcp inspect --context
--health. Summarize pass/fail for each and flag anything off. No code changes, no staging, no tokens
beyond what's listed. [REPORT] (omit PR/commit — this is read-only).
```

---

## Phase Implementation prompt (generic)

```
Read docs/fable/01-operating-rules.md, docs/fable/03-security-invariants.md, and the phase doc
docs/fable/<NN-phase>.md. Implement ONLY: <one small slice of the phase>.
Scope: <what to change>. Non-goals: <what NOT to touch> plus everything in 01/03/04's non-goals for
this phase. Small PR. Match surrounding style. Re-verify every invariant in 03 against your diff.
[VERIFY] [REPORT]
Branch: <branch>. Commit: <message>. Open a PR titled <title>.
```

---

## v0.6 Agent Bridge prompt

```
Read docs/fable/03-security-invariants.md, docs/fable/05-v0.6-agent-bridge.md, and
docs/fable/06-proposal-schema.md.
Task: implement <one of: (1) the typed proposal model + envelope schema; (2) the importer with dedup
and SERVER-SIDE payload hashing; (3) the panel "proposed by agent" display; (4) bridge docs>.
Hard rules: file/CLI intake only (NO new network endpoint); server mints all ids and the payload
hash; agents never supply hash/ids/status/verdicts; run_command is exact allowlist label only; no
cloud_call; no allowlist expansion; no auto-execution; the existing trust/auditor/executor path stays
unchanged. Add tests proving a crafted proposal cannot inject argv/content and that disallowed
kinds/fields fail closed. Review level: FULL for the importer PR, balanced otherwise. [VERIFY]
[REPORT]
```

---

## Proposal Schema prompt

```
Read docs/fable/06-proposal-schema.md and docs/fable/03-security-invariants.md.
Task: implement the proposal envelope model + validation (backend/workbench_proposals.py) matching
the schema exactly — required fields, allowed kinds (write_file/edit_file/run_command only),
server-minted fields rejected on input, strict schema_version, payload shapes per kind. Include the
valid AND rejected examples from doc 06 as tests (freeform command rejected; smuggled payload_hash/
status rejected). No importer side effects in this PR — model + validation only. Balanced review.
[VERIFY] [REPORT]
```

---

## Onboarding Launcher prompt

```
Read docs/fable/07-agent-session-launcher.md and docs/fable/01-operating-rules.md.
Task: extend `vibe guide` to <e.g. add codex/fable topics as read-only stdout generators> and/or add
--role <role>. Version 1 prints to stdout and writes NOTHING (no --write in this PR). Reuse the
existing guide-claude machinery. Do NOT introduce a /council shell command. Every generated pack must
include the safety spine (advisor-not-authority, never-stage list, cheap/balanced/full policy,
propose-into-Workbench). Balanced review (safety text must be correct). [VERIFY] [REPORT]
```

---

## Project Vault prompt

```
Read docs/fable/08-obsidian-project-vault.md.
Task: add <one vault file/template under docs/context/project/> and/or wire it into vibe context
build. Extend docs/context/ — do NOT create a competing .vibe/ folder. DECISIONS.md is a pointer into
docs/decisions/, never a restatement. If wiring into context build: keep the pack within budget — do
NOT reopen 21/21; if a file pushes it over, it's too big or belongs behind a pointer. Balanced review
for the context-build change. [VERIFY] [REPORT]
```

---

## Website prompt

```
Read docs/fable/11-website-and-positioning.md and docs/fable/02-product-vision.md.
Task: draft <the requested landing section(s)> as Markdown/HTML copy. Lead with guarded execution,
not "multi-model council." Include the local-first honesty caveat (configured cloud reviews DO send
prompts/diffs unless using a local provider). Do NOT claim autonomous agents, hosted/team, mobile
approvals, "runs on top of your Claude session," or unbreakable security. Docs-only; no code. Cheap
review. [REPORT] (adapt — may be a docs PR).
```

---

## Review / Diff prompt

```
Read docs/fable/03-security-invariants.md.
Task: review the current working diff for correctness and for any weakening of a security invariant.
Run vibe diff --preset <cheap|balanced> --usage (balanced if the diff touches the Workbench/trust/
executor/panel or any security claim). Separate findings into must-fix / strong-rec / optional /
not-now. Apply only the must-fix and clearly-useful items; explain what you declined and why. [VERIFY]
[REPORT]
```
