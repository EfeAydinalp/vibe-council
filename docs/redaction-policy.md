# Redaction policy

vibe-council keeps a clean public/local boundary: the public repo holds only **curated, redacted**
docs, while raw model output and runtime state stay local. This page defines what must/should/may be
redacted and how the `vibe lint --redaction` guard helps enforce it.

## Defense-in-depth, not a guarantee

The redaction guard is a **pattern-based scanner**. It catches common, recognizable leaks — it does
**not** prove a document is safe. **Human review is always required.** A scanner can miss novel secret
shapes, and it can occasionally over-flag (false positives). Treat a clean result as "no obvious
leaks found," not "guaranteed safe."

## The boundary

- **Raw `.council/` stays local and gitignored** — reviews, decisions, runs, stages, usage, diffs,
  locks, and any operator events are never committed.
- **The public repo contains only curated/redacted docs** — `docs/`, top-level Markdown, etc.
- The guard is for **public/staged docs safety**, not a promise that local raw outputs are safe. Keep
  `.council/` gitignored as the primary protection.

## What MUST be redacted (critical)

These should never appear in committed/shared docs:

- **API keys** — e.g. OpenRouter keys (`sk-or-v1-<key>`) and any provider key.
- **Private keys** — PEM/OpenSSH private-key blocks (the `PRIVATE KEY` markers).
- **Tokens / passwords / secrets** — `OPENROUTER_API_KEY=<key>`, `ANTHROPIC_API_KEY=<key>`,
  `OPENAI_API_KEY=<key>`, `GEMINI_API_KEY=<key>`, and generic `*_API_KEY=`, `*_SECRET=`, `TOKEN=`,
  `PASSWORD=` assignments with a real value.
- **`.env` contents** pasted into docs.
- **Local absolute paths** that include a real username — `C:\Users\<name>`, `/Users/<name>`,
  `/home/<name>` (generic placeholders like `/home/dev` are fine).
- **Raw `.council/` artifact paths** — concrete, date-stamped files such as
  `.council/reviews/<timestamp>` or `.council/decisions/<timestamp>`.
- **Obsidian workspace state** — the `.obsidian/` config (never committed).
- **Private commercial strategy** — the detailed feasibility/strategy plan stays local; do not link
  to it or quote its internals.
- **Private cost tables** — internal monthly infrastructure / pricing tables.
- **Customer / private-repo details.**

## What SHOULD usually be redacted (warning)

Advisory — review before committing; redact unless clearly public-safe:

- Usernames / local machine names.
- Internal project or customer names.
- Exact private infrastructure details.
- Internal cost/pricing tables (public, third-party pricing in a research doc is usually fine).
- **Local/private profile artifacts** — the machine-local personalization profile lives under
  `.council/` (a gitignored, per-machine store) and must never be committed. The guard flags a
  **concrete** local-profile filename (e.g. the `json`/`toml`/`yaml`/`yml`/`md` form) in a tracked
  doc as an advisory `local-profile-path` warning. Operational and policy text should refer to it by
  the **glob form** `.council/profile.*` (which the rule deliberately does not match); only genuine
  design/plan docs that must name a concrete file trip the warning. **Promotion path:** once a real
  local profile store actually ships, a concrete reference in public docs becomes a live-artifact
  leak — this rule is promoted to **critical** at that point and the remaining design docs move to
  the glob form.

## What is usually OK

- Public docs links and public PR / release links.
- High-level commercial **direction** (public-safe).
- Public-safe decision records and roadmap docs.

## How to use the guard

```sh
vibe lint --redaction                 # scan tracked public docs (default)
vibe lint --redaction docs/decisions  # scan specific paths
vibe lint --redaction --strict        # also fail on advisory warnings
```

- **Before promoting a decision** from a raw run to `docs/decisions/`.
- **Before committing any generated doc** (context pack, agent brief, STATUS/PROGRESS export).
- **Before exporting a context pack** that might be shared.

Behavior:

- **Exit `0`** when no blocking finding; **non-zero** when a blocking finding exists.
- **Critical** findings always block; **warnings** are advisory and block only with `--strict`.
- By default it scans the tracked public docs (so gitignored `.council/`, `data/`, and `.venv/` are
  excluded); pass explicit paths to scan exactly those.
- Secret and per-user-path matches are **masked** in output — the guard never reprints a full secret
  or username.

## Known limitations

- A pattern-based scanner **can miss** secrets it doesn't recognize.
- **Human review remains required** — the guard is one layer, not the whole defense.
- **False positives are possible** (e.g. third-party pricing, illustrative output samples). Warnings
  are advisory for exactly this reason; investigate, then accept or redact.
