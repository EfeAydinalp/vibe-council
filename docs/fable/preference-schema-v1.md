# Preference schema v1 — normative spec (tighten-only, validate-never-apply)

> **Status: normative spec (v0.8.2 PR 7) + read-only validator (v0.8.2 PR 8).** This document defines
> the v1 machine-readable preference schema. A **read-only, fail-closed, findings-only validator** now
> reports on the block — [`backend/preferences.py`](../../backend/preferences.py), folded into
> `vibe project doctor` as an advisory `Preferences (machine-readable, advisory):` section (see
> [`v0.8.x-architecture-plan.md`](v0.8.x-architecture-plan.md) §3 Q3/Q4). The validator **only reports**
> (valid → ok, missing → note, invalid → warn "ignored"); it **applies nothing** and never changes
> `vibe project doctor`'s READY/NOT-READY result. Preference **application** (letting a value influence a
> command) remains deferred to **v0.9.x** behind its own reviewed design. **No preference is applied to
> any behavior; guide/context-export stay pointer-only.**

This is the machine-checkable region of the otherwise prose
[`PREFERENCES.md`](../context/project/PREFERENCES.md). Markdown stays the source of truth; the block is
a small, closed, enumerated island a future validator can check. Its design goal is that **every legal
value can only add friction or checks** — the schema has **no vocabulary for loosening** anything.

## 1. Carrier format

- The machine-readable preferences live in **one optional fenced code block** inside
  `docs/context/project/PREFERENCES.md`, tagged `json`:

  ````
  ```json
  { … }
  ```
  ````

- **At most one** ` ```json ` block is meaningful; a future reader takes the **first** one only.
- The block is **untrusted input** and is size-bounded: **≤ 4096 bytes**. Over budget → the whole block
  is ignored (a future validator warns).
- It is parsed with **stdlib `json.loads` only** — no comments, no YAML/TOML, no anchors, no eval, no
  hooks. (JSON is chosen deliberately: the `>=3.10` floor has no stdlib `tomllib`, the project is
  stdlib-only / no-new-dependency, and JSON's strictness is a feature for untrusted input. Commentary
  lives in the surrounding Markdown, not the block.)
- The top level **must be a JSON object**. The block **must** carry `"schema": 1`.

## 2. The four v1 preference types

v1 has **exactly four** preference keys plus the required `schema` field. Every type is either an
**ordered floor-raise** or an **additive constraint** — the two shapes for which "every legal value can
only add friction/checks" is provable, mechanically, in tests.

| Key | Type | Tighten-only proof shape | Anchored (future v0.9.x) behavior |
|---|---|---|---|
| `schema` | integer, **must be `1`** | version gate; unknown version → whole block ignored | selects this spec |
| `default_review_preset` | enum `"cheap" \| "balanced" \| "full"` | **ordered floor-raise**: names a review floor; **cannot name `premium`** (not in the enum) | review/diff *suggest* this preset as the default |
| `extra_sensitive_paths` | array of relative path prefixes | **additive deny**: can only *add* prefixes to the extra-guarded set, never remove | trust policy treats them as extra-guarded |
| `never_stage_extra` | array of relative paths | **additive no-stage**: can only *grow* the never-stage list | doctor's dangerous-staged check also flags these |
| `require_usage_flag` | boolean where only `true` is meaningful | adds a warning when `--usage` is absent; `false` is identical to unset (disables nothing) | commands warn when `--usage` is missing |

**No type in v1 can name a command to run, a path to *allow*, or a check to *skip*.** There is no
key for widening an allowlist, relaxing a deny, lowering a gate, enabling auto-execution, expanding the
network surface, or altering the Workbench trust/executor boundary. Loosening is **inexpressible by
construction**, not merely discouraged.

**The "anchored behavior" column is a future *suggestion*, never an override.** When application ships
(v0.9.x), a preference may only *raise a default or add a warning* — e.g. `default_review_preset`
suggests a review floor but **never lowers** an explicit stricter user choice and can **never** select
`premium`; `require_usage_flag` only *adds* a warning. A preference never overrides an explicit,
stricter human decision and never removes a gate.

## 3. Validation rules (what a future validator must enforce)

These are the rules the **v0.8.2 PR 8** read-only validator will enforce. They are documented here so
the spec is testable now; **this PR implements none of them in runtime.**

- **Top level is an object**; otherwise the block is invalid → ignored.
- **`schema` present and equal to `1`.** Any other value (including `2`) → **warn + ignore the whole
  block** (a future schema v2 arrives via its own reviewed spec release; no silent coexistence).
- **Key allowlist:** only `schema`, `default_review_preset`, `extra_sensitive_paths`,
  `never_stage_extra`, `require_usage_flag`. Any **unknown key** → validation error.
- **Strict per-key types/values:**
  - `default_review_preset` ∈ `{cheap, balanced, full}` — **`premium` is not accepted**.
  - `extra_sensitive_paths` / `never_stage_extra` — arrays of strings that are **relative paths**
    (relative **to the project root**, `/`-separated): reject **absolute paths**, **drive letters**
    (`C:\…`), and any `..` segment. Also reject **empty / whitespace-only** strings and **duplicate**
    entries (stated-but-inert — a likely mistake). Array length is implicitly bounded by the
    4096-byte block cap (no separate numeric limit in v1).
  - `require_usage_flag` — a **boolean**.
- **Empty arrays warn** (`"extra_sensitive_paths": []` is stated-but-inert — probably a mistake).
- **File-level hardening:** resolve `PREFERENCES.md` to its **real path** and require it to reside
  **inside the project root** (symlink/out-of-root → one generic warn that leaks no content or target
  path); a `UnicodeDecodeError`/unreadable file → a clean warn, never a traceback.
- **Fail-closed:** any anomaly → *"invalid, ignored"* (a warn and no parsed result). A malformed block
  is **never** a crash and **never** a `vibe project doctor` failure — the block is advisory, and its
  validator (PR 8) only emits `[ok ]`/`[warn]` lines with the exit code unchanged.

## 4. Tighten-only semantics (security invariant #17)

**Preferences may tighten rules but never loosen safety/security/no-stage/trust rules.** A preference
is legal only if it **cannot** cause an action, command, or approval to succeed that would have been
rejected without it. The deterministic trust boundary **ignores preferences entirely**; a preference is
advice that can add friction, never authority that removes it. See security invariant #17 in
[`03-security-invariants.md`](03-security-invariants.md) and the tighten-only principle in
[`PREFERENCES.md`](../context/project/PREFERENCES.md) / [`AGENT-ROLES.md`](../context/project/AGENT-ROLES.md).

### What the schema explicitly **cannot** express

The v1 schema has no vocabulary for any of the following, and never will (a v2 that added such a
vocabulary would be a different, separately-reviewed mechanism, not a migration):

- **Loosen** any safety / security / no-stage / trust rule.
- **Change the Workbench executor or trust-boundary** semantics (approval-separate-from-execution,
  deterministic guard, allowlist).
- **Add arbitrary shell, auto-execution, network, LAN, or hosted behavior.**
- **Override the review policy** (e.g. force `premium`, downgrade a security review, skip a gate).
- **Hide, suppress, downrank, or filter dissenting council opinions** — the council is an independent
  multi-model second opinion; a preference can ask for *more* scrutiny, never *less* visibility.
- **Read or write a `.council/profile.*` local store** (deferred; no store exists).

## 5. Examples

### 5.1 Valid (the canonical example — mirrors the block in `PREFERENCES.md`)

```json
{
  "schema": 1,
  "default_review_preset": "balanced",
  "extra_sensitive_paths": ["infra/prod/", "ops/deploy/"],
  "never_stage_extra": ["notes/local-scratch.md"],
  "require_usage_flag": true
}
```

Every field above only *adds* friction: a review floor, two extra-guarded prefixes, one extra
never-stage path, and a warn-when-`--usage`-absent flag. Removing the block entirely is strictly *less*
strict — never more permissive-than-baseline.

### 5.2 Also valid — a minimal block (just the version gate)

```json
{ "schema": 1 }
```

### 5.3 Invalid / forbidden (shown as text, **not** a machine block — a future validator rejects each)

```text
{ "default_review_preset": "balanced" }          # invalid: missing required "schema": 1
{ "schema": 2, ... }                             # ignored: unknown schema version (whole block dropped)
{ "schema": 1, "default_review_preset": "premium" }   # invalid: "premium" not in the enum (a loosening attempt)
{ "schema": 1, "allow_commands": ["rm -rf"] }    # invalid: unknown key + names a command (no such vocabulary)
{ "schema": 1, "extra_sensitive_paths": ["/etc/passwd"] }   # invalid: absolute path
{ "schema": 1, "never_stage_extra": ["../outside.md"] }     # invalid: ".." escapes the project
{ "schema": 1, "extra_sensitive_paths": [] }     # warn: empty array is stated-but-inert
{ "schema": 1, "require_usage_flag": "yes" }     # invalid: must be a boolean
{ "schema": 1, "suppress_dissent": true }        # invalid: unknown key; hiding council views is inexpressible
```

Note the forbidden gallery is intentionally **not** fenced as ` ```json `, so it can never be mistaken
for the single machine-readable block.

## 6. Council personas — future direction (v0.9.x), **not** part of schema v1

In this project "personalization" ultimately points at **council-member / persona behavior models** —
review lenses such as **Cost Skeptic**, **Security Guardian**, **Product Strategist**, **Local-first
Guardian**, **UX / User Advocate**, **Risk Officer**, and **Commercialization Lens**. These are useful
for software review and broader decision-making.

**Personas are explicitly out of scope for schema v1 and for v0.8.x.** The seven lenses named above are
**illustrative and non-binding** — a sketch of intent, not a committed design or a fixed list. They are
recorded here only so v1 is designed toward the future shape:

- When personas arrive (**v0.9.x at the earliest**, with runtime selection/tuning likely behind a
  visual/dashboard/workspace UX), a persona will be a **curated preset of these same tighten-only
  schema values** plus **advisory review-emphasis prose** — an *instance* of this model, not a new,
  broader mechanism. This resolves the "named profiles" question (`v0.8.x-architecture-plan.md` §3 Q7)
  the same way: a selector of tighten-only values, never a policy override.
- A persona's "emphasis / lens" (e.g. Cost Skeptic emphasizes spend, Security Guardian emphasizes
  attack surface) is **advisory framing for a reviewer** — it can ask the council to look *harder* at
  something. It can **never** suppress another persona's dissent, override the review policy, loosen a
  gate, or change trust/executor behavior. The tighten-only envelope in §4 binds personas too.
- **No persona is defined, parsed, selected, or applied in this PR.** Adding persona fields to the v1
  schema, routing a persona into council behavior, or building a persona store/UX are each their own
  future, separately-reviewed work — not this one.

## 7. Non-goals of this PR (PR 7)

No validator/parser runtime · no schema application · no council-behavior change · no persona
definition/selection/application · no `vibe project doctor` / `vibe guide` / `vibe context export`
behavior change (guide/export stay **pointer-only** — they never inline this block) · no
Workbench/proposal/importer/executor/trust change · no `.council/profile.*` local store · no
model/provider/API call · no dependency change · no version bump · no tag/release. The validator is
**PR 8** (`vibe project doctor` advisory section, full review); application is **v0.9.x**.
