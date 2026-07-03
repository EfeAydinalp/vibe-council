# 03 — Security invariants (non-negotiable)

These are the invariants every current and future phase must preserve. A change that weakens any of
them is **rejected by default**, regardless of how useful it seems. If a phase appears to require
weakening one, that is a signal to stop and re-scope — not to relax the invariant.

An implementer should treat this file as a checklist to re-verify after any Workbench-touching PR.

## Approval vs. execution

1. **Approval is separate from execution.** Approving records an `ApprovalDecision` and nothing else
   — it never writes a file, edits a file, or runs a command. Execution is a distinct, explicit step.
2. **No hidden auto-execution.** There is no code path where a decision, a page load, a proposal
   import, or any background process triggers a real action without a separate explicit execute.

## Client trust boundary

3. **The browser/client never sends the payload or argv at execution time.** The execute request
   carries **only an action id** (plus the token). No file content, patch text, command string,
   argv, cwd, env, or timeout comes from the client.
4. **The server resolves action/payload/argv itself**, from local server-side state: the payload
   artifact (`workbench_payloads.py`) for file kinds, the fixed-argv resolver
   (`workbench_commands.py`) for commands. A crafted request body has **zero effect** (proven by
   the PR #89 dogfood and by tests).

## The guard

5. **The deterministic trust boundary (`workbench_trust.py`) is the real guard.** Path allow/deny,
   exact command allowlist, secret patterns, size limits, cloud-egress consent — all deterministic.
6. **The Approval Auditor is advisory only.** It copies risk/blocked/findings verbatim from the
   trust evaluation and adds a human summary; it can **never** lower risk or unblock.
7. **The executor re-validates at execution time.** A stored `AuditResult` or a cached preview
   cannot authorize anything; the trust boundary is re-run at the moment of execution.

## Bounded actions

8. **File writes/edits are bounded** — atomic writes, size and line-delta limits, explicit-overwrite
   requirement, path/symlink guard, no binary, no content in logs.
9. **Payload artifacts are local and gitignored, write-once, and hash/scope-verified** before every
   real execution (hash over `{kind, target, payload}`, plus kind/target/action/approval/task
   agreement). A missing/tampered/mismatched artifact fails closed.
10. **Commands are exact allowlisted labels only**, resolved to a **fixed argv**, run with
    `shell=False`. No shell, ever. No string parsing into argv. No dynamic args, env, cwd, or
    timeout from an agent or the browser. The subprocess env is allowlist-built (no inherited
    secrets); output is bounded and redaction-checked (a critical finding blocks the result).
11. **Two independent gates for commands, both required:** a label must be on *both* the resolver
    allowlist *and* the trust allowlist. The resolver is stricter, never looser.

## Network / surface

12. **Localhost-only by default.** The panel binds `127.0.0.1`; a post-bind check refuses any
    non-loopback bound address.
13. **POST endpoints are token-gated**, and **`GET /api/state` is token-gated** (PR #92) — it exposes
    runtime tasks/approvals/actions. The token is never echoed in JSON.
14. **`Host`-header validation** on every request (PR #92): only literal loopback host names accepted
    (any port); missing/malformed/multiple `Host` fails closed. This is the DNS-rebinding defense —
    localhost binding alone does not stop a rebinding page.
15. **No CORS widening.** No wildcard, no permissive cross-origin headers.

## Scope limits that are security invariants

16. **No `cloud_call` proposals in the v0.6 bridge.** An agent may not propose an action that sends
    data to a provider. (Cloud egress remains a human-driven, consent-gated path, not agent-proposable
    in v0.6.)
17. **No profile/personalization may loosen a guardrail.** Preferences may make review stricter, mark
    more paths sensitive, or narrow what's allowed — never widen the allowlist, relax the trust
    boundary, enable auto-execute, or expand the network surface. Tighten-only. See
    [10-personalization-layer.md](10-personalization-layer.md).
18. **No executor provider/model/network calls.** The execution path stays offline.

## How to verify after a Workbench PR

- Re-read this list against the diff. If any item's guarantee is now weaker, the PR is wrong.
- Run the full suite; the trust/executor/payload/panel tests are the enforcement of most of these.
- `vibe lint --redaction` 0 critical; `vibe context check` 21/21; `vibe mcp inspect --context
  --health` 21/21.
- For a bridge/importer PR, add explicit tests that a crafted proposal cannot inject argv/content and
  that disallowed kinds/fields are rejected.
