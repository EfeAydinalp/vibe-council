# 04 — Roadmap (v0.5.2 → v0.9+)

Phase-by-phase. Each phase lists purpose, why now / why later, scope, explicit non-goals, risk, and
the review level to run before merge. **Do one phase at a time.** A phase is usually several small
PRs, not one. Non-goals are as binding as goals.

Review levels: **cheap** (routine), **balanced** (non-trivial / security- or architecture-relevant),
**full** (major roadmap/product/security-architecture decisions only).

---

## v0.5.2 — Workbench Host-header + `/api/state` hardening

- **Status:** implemented in **PR #92 (merged)**; not yet bundled into a tagged `v0.5.2` release.
- **Purpose:** close a DNS-rebinding class gap before the bridge fills the approval queue.
- **Why now:** the bridge (v0.6) makes the runtime store full of approved-pending actions, which is
  exactly what makes a rebinding attack worth an attacker's effort. Fix the surface first.
- **Scope:** `Host`-header validation on all requests; token-gate `GET /api/state`. Done.
- **Non-goals:** configurable allowed hosts, reverse-proxy support, CORS, port-matching, CSRF nonce,
  Origin validation — all out (contrary to localhost-only, or separate later work).
- **Risk:** low. **Review:** balanced (security). Done.
- **Remaining:** optionally cut a tagged `v0.5.2` patch release (maintainer decision).

---

## v0.6.0 — Agent-to-Workbench Bridge

- **Purpose:** let external agents (Claude Code, Codex, Fable, custom workers) **propose** actions
  into the Workbench instead of acting blindly. This is the keystone phase.
- **Why now:** the security core (v0.5) is complete and hardened (v0.5.2). The bridge is the feature
  that turns the guarded executor into a product.
- **Scope:** a **file/CLI-based** proposal intake (`vibe workbench propose < proposal.json`), a
  proposal importer that validates the envelope, mints ids server-side, computes the payload hash
  server-side, and creates task/approval/action so the **existing** trust/auditor/executor path runs
  unchanged. Panel shows "proposed by agent." Dedup via `proposal_id`. See
  [05-v0.6-agent-bridge.md](05-v0.6-agent-bridge.md) and [06-proposal-schema.md](06-proposal-schema.md).
- **Non-goals:** **no new network endpoint** for agents; no auto-execution; no broad shell; no
  command-allowlist expansion; no `cloud_call` proposals; no agent-supplied hash/ids/verdicts.
- **Risk:** medium-high (new trust-relevant intake). **Review:** **full** for the importer PR;
  balanced for schema/panel/docs PRs.

---

## v0.6.1 — Agent Session Launcher / Council Onboarding Layer

- **Purpose:** stop re-explaining vibe-council every new project/session. Generate role-specialized
  instruction packs that teach an agent to use `vibe` and to propose into the Workbench.
- **Why now (after 0.6.0):** the launcher's most valuable output — "propose actions into Workbench"
  — only makes sense once the bridge exists.
- **Scope:** a **read-only stdout generator** first (`vibe guide <agent>`, `vibe guide <agent>
  --role <role>`); `--write` (emit `AGENTS.md`/`CLAUDE.md`) is opt-in and later. `vibe guide claude`
  already exists as the seed. See [07-agent-session-launcher.md](07-agent-session-launcher.md).
- **Non-goals:** no `/council` shell command (future host custom-command idea only); no writing files
  without `--write` + confirmation; no network.
- **Risk:** low-medium (the safety text must be correct). **Review:** balanced.

---

## v0.6.2 — Obsidian-like Project Vault

- **Purpose:** durable, human- and agent-readable local project knowledge so sessions don't start
  from zero and users don't re-explain history.
- **Why now (after 0.6.1):** the launcher and bridge both benefit from a stable knowledge source to
  read from.
- **Scope:** **extend `docs/context/project/`** (do not invent a conflicting `.vibe/`). Add curated
  committed files (STATUS/ROADMAP/RISKS/WORKFLOWS/AGENTS/RELEASES, DECISIONS as a pointer index).
  Wire into `vibe context build` under the **existing budget**. See
  [08-obsidian-project-vault.md](08-obsidian-project-vault.md).
- **Non-goals:** no context-pack bloat (do not reopen 21/21); no duplicating `docs/decisions/`; no
  committing generated packs/exports.
- **Risk:** medium (budget). **Review:** balanced for the `context build` change; cheap for templates.

---

## v0.6.3 — Cross-project Council Onboarding

- **Purpose:** make vibe-council usable in arbitrary projects without re-explaining it.
- **Why now (after 0.6.2):** needs the vault + launcher to have something to export/summarize.
- **Scope:** proposed commands `vibe init-agent`, `vibe guide <agent>`, `vibe context export --for
  <agent>`, `vibe summarize-history`, `vibe project doctor`; safe generated files
  (`AGENTS.md`/`CLAUDE.md`/`.codex/instructions.md`). See
  [09-cross-project-onboarding.md](09-cross-project-onboarding.md).
- **Non-goals:** no overwriting files without confirmation; no raw private artifacts in exported
  context; no network fetches; keep history summaries local by default.
- **Risk:** low-medium. **Review:** balanced.

---

## v0.7 — Personalization Layer

- **Purpose:** a Personal Workbench Profile / project preferences (working style, spending style,
  review strictness, approval prefs, sensitive paths, recurring workflows, release/PR style).
- **Why later:** only meaningful once the safe execution core, bridge, and onboarding exist; it
  personalizes an existing loop, it doesn't create one.
- **Scope:** local profile store; preferences that adjust defaults. See
  [10-personalization-layer.md](10-personalization-layer.md).
- **Non-goals:** **personalization may tighten but never loosen a guardrail** (invariant #17); no
  auto-execute preference; no allowlist-widening preference; profile stays local/gitignored.
- **Risk:** medium. **Review:** balanced.

---

## v0.8 — Mobile / LAN / Voice Approval

- **Purpose:** approve/reject/hold from a phone or by voice.
- **Why later:** it **expands the security surface** (beyond localhost). Do not start before the
  localhost + proposal bridge are solid and dogfooded.
- **Scope (when it starts):** a deliberately narrow, authenticated, auditable remote-approval path —
  design TBD, gated behind its own security review.
- **Non-goals until it starts:** no LAN binding, no remote transport, no mobile client. The panel
  stays `127.0.0.1`-only through v0.7.
- **Risk:** high (surface expansion). **Review:** **full**.

---

## v0.9+ — Hosted / team / commercial layer

- **Purpose:** optional managed convenience on top of an open core.
- **Why later:** needs adoption, a resolved license/provenance "Question 0", and a solid local
  product first. See [12-open-core-commercial-path.md](12-open-core-commercial-path.md).
- **Scope (candidates):** team dashboard, mobile approvals, shared audit logs, org policy packs,
  managed integrations, council packs/templates, BYOK usage dashboard, support/training.
- **Non-goals:** do not hide the whole repo; do not close the core (the auditable guard *is* the
  pitch); do not build hosted infra before adoption; no commercial claim while Question 0 is open.
- **Risk:** high (business + legal + messaging). **Review:** **full**, plus non-engineering (legal).

---

## Sequencing rule

The dependency order is **0.6.0 → 0.6.1 → 0.6.2 → 0.6.3 → 0.7 → 0.8 → 0.9+**. Mobile/hosted stay
behind the local core deliberately. A later phase must not smuggle in an earlier invariant's
weakening (e.g. a "personalization" or "hosted" feature that relaxes the trust boundary is wrong by
construction).
