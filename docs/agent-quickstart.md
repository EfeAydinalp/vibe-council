# vibe-council Agent Quickstart

Use vibe-council as a **local-first review and decision-support tool** for AI-assisted
development - from your own project or from an AI coding agent (Claude Code, Codex, etc.).

> **It is not an autonomous authority. It does not implement changes for you.** It produces
> review/advice that a human - or the main coding agent - must **filter and decide on**. You own the
> final decision.

## TL;DR for AI agents

Use vibe-council as a lightweight reviewer, not an implementer.

Before coding:
1. Write a short `plan.md`.
2. Run `vibe status`.
3. Run `vibe review --preset cheap --file plan.md --usage`.
4. Use `--preset balanced` for non-trivial work.

After coding:
1. Run the project tests.
2. Run `vibe diff --preset cheap --usage`.
3. Use `--preset balanced` for important diffs.

Rules:
- Council output is advice, not authority.
- Do not blindly apply every suggestion.
- Do not send secrets, credentials, `.env`, private keys, or unrelated personal files.
- Keep `.council/` gitignored.
- Use `full` only for major roadmap/product/security decisions.
- Use `premium` only with explicit human approval.

The rest of this guide expands each step. If you only read one more section, read
[section 7 Safety rules](#7-safety-rules-for-agents).

---

## 1. What it is + install

vibe-council is a command-line tool: several LLMs review or answer, with cost/safety guardrails and a
project-local `.council/` workspace. Everything runs from the CLI with your own API key.

```sh
git clone https://github.com/EfeAydinalp/vibe-council.git
cd vibe-council
uv sync                       # or: pip install python-dotenv httpx pydantic
cp .env.example .env          # then set OPENROUTER_API_KEY (if using OpenRouter)
sh scripts/install-vibe.sh --yes    # installs the global `vibe` command
vibe doctor                   # checks provider setup (no tokens spent)
vibe status
```

Windows: use `powershell -ExecutionPolicy Bypass -File scripts\install-vibe.ps1 --yes` (see the main
[README](../README.md) for details). Prefer a **local** provider? Set `VIBE_PROVIDER=ollama` +
`VIBE_OLLAMA_MODEL` (no API key, no cloud egress).

`vibe --version`, `vibe doctor`, `vibe presets`, and `vibe models` are all no-cost inspection
commands (no tokens spent).

## 2. Use it in another project

From the **target project's** directory:

```sh
vibe status
```

This creates/checks the local `.council/` workspace for that project. **Keep `.council/`
gitignored** (vibe adds it to the project's `.gitignore` automatically - keep it that way). Raw
council outputs and generated artifacts live there and must never be committed.

## 3. Before coding - review the plan

Write a short plan, then get a lightweight second opinion:

```sh
cat > plan.md <<'EOF'
# Plan
What I intend to change and why.
EOF

vibe review --preset cheap --file plan.md --usage      # routine / small PRs
vibe review --preset balanced --file plan.md --usage   # non-trivial PRs
```

Read the review. **Apply only the useful feedback** - correctness, security, cost, and
missing-constraint findings are worth acting on; style nits and speculative rewrites usually aren't.

## 4. After coding - review the diff

Run the **project's own tests first**. Then review the diff:

```sh
vibe diff --preset cheap --usage        # routine
vibe diff --preset balanced --usage     # important diffs
```

## 5. Durable decisions (optional)

Only when the work creates a **durable** architecture / product / security decision:

```sh
vibe extract --preset cheap --file plan.md --save --usage
```

This writes a **local** draft under `.council/` (gitignored). **Review/redact it, then** promote a
curated record into `docs/decisions/` deliberately (`vibe decisions promote <draft>`) - promotion is
human-reviewed and never automatic. Skip this for routine changes.

## 6. Preset / mode guidance

| Use | When |
|-----|------|
| `--preset cheap` | smoke tests, routine checks, small PRs |
| `mini` | everyday lightweight second opinion |
| `review --preset balanced` | meaningful plans / diffs |
| `full --preset balanced` | major roadmap / product / security decisions, or when a `review` is shallow or conflicted |
| `--preset premium` | **only with explicit human approval** (needs `--allow-premium`) |

Always pass `--usage` on model-spending commands so cost/tokens are visible. `balanced` is the
default for real runs; `full` is multi-model and more expensive - reserve it for big calls.

## 7. Safety rules for agents

- **Council output is advice, not authority.** You own the final decision.
- **Do not let council modify files** or implement changes; it only reviews/advises.
- **Do not blindly apply every suggestion.**
- **Never send secrets or private data:** no `.env`, API keys, credentials, private keys, customer
  data, or unrelated personal files in a prompt/file/diff.
- **Private repo diffs leave your machine** when using a cloud provider - only send them if the user
  intentionally approves that provider call.
- **Keep `.council/` gitignored; never commit `.env`.**
- **Never commit raw `.council/` outputs** unless they've been explicitly curated/redacted into
  public docs. Run `vibe lint --redaction` before committing public docs.
- **Do not use `premium`/`full` unless the user approved the cost/value tradeoff.**

## 8. Local-first privacy note

**"Local-first" does not mean nothing leaves your machine.** When you use OpenRouter (or another
cloud provider), the **prompts, files, and diffs you review are sent to that provider**. What stays
local is the saved `.council/` workspace and generated artifacts. Use **Ollama / a local provider**
(`VIBE_PROVIDER=ollama`) when you need local inference and no cloud egress.

## 9. Using with Claude Code / Codex

Claude Code, Codex, and similar terminal agents have their **own** session commands and
project-instruction files - for example a host agent may support commands such as `/compact`,
`/clear`, `/doctor`, or `/init`, or project files such as `AGENTS.md`. **Those are host-agent
controls**: they manage the live agent session (context, compaction, its own diagnostics). They are
**not** vibe-council commands.

vibe-council is a **separate, complementary layer**: project review, council output, provider
diagnostics, project-local memory, context packs, and decision records:

```sh
vibe doctor                                # vibe's own provider setup check
vibe status                                # project-local .council/ workspace
vibe review --preset cheap --file plan.md --usage    # before implementation
vibe diff --preset cheap --usage                     # after implementation
vibe extract --preset cheap --file plan.md --save --usage   # durable decisions
vibe context build && vibe context check   # compact project memory
vibe context export claude-code            # a Claude Code-friendly local context file
```

Use both layers together:

- use the **host agent's** session commands to keep the live coding session healthy (context,
  compaction, its own diagnostics);
- use **vibe-council** for review signal and durable project memory.

Neither replaces the other, and neither gives "unlimited context" - terminal agents' session tools
and vibe's context packs both just help **manage** long-running context. **Do not confuse
host-agent slash commands (`/compact`, `/clear`, `/doctor`, `/init`, `AGENTS.md`) with `vibe` CLI
commands**, and remember vibe-council output is advice, not authority.

## 10. Proposing actions into the Workbench (agent bridge)

Beyond reviewing, an agent can **propose a bounded code action** into the local Workbench for a human
to approve — instead of editing files or running commands directly. Write a schema-v1 proposal JSON
(one `write_file` / `edit_file` / `run_command` action) and submit it **locally**:

```sh
vibe workbench propose proposal.json     # or:  vibe workbench propose -   (read stdin)
```

This **validates** the proposal, mints ids and the payload hash **server-side**, and records a
**pending** approval — it **does not execute anything**. The human then runs `vibe workbench serve`,
sees a "proposed by agent" card, and approves/rejects/holds; execution is a further, separate,
explicit step through the guarded executor. Never submit a freeform command, `argv`/`env`/`cwd`/
`timeout`/`shell`, a `payload_hash`/`*_id`/`status`, an absolute/`..` path, or a `cloud_call`; never
claim a change was applied until an approved action has actually executed. Full guide + examples:
[`docs/workbench-agent-bridge.md`](workbench-agent-bridge.md).

---

## Copy-paste instruction for AI coding agents

```text
Use vibe-council only as a lightweight reviewer.

Before coding:
1. Write plan.md.
2. Run: vibe status
3. Run: vibe review --preset cheap --file plan.md --usage
4. For non-trivial work, use --preset balanced.
5. Apply only useful feedback.

After coding:
1. Run the project's tests.
2. Run: vibe diff --preset cheap --usage
3. For important diffs, use --preset balanced.

Rules:
- Council gives advice, not commands. You own the final decision.
- Do not let council implement.
- Do not send secrets or private files (.env, keys, credentials, customer data).
- Keep .council/ gitignored; never commit .env or raw .council/ outputs.
- Use `full` only for major roadmap/product/security decisions.
- Use `premium` only with explicit human approval.
```

See also: the full [agent integrations guide](agent-integrations.md), and `vibe guide claude` for a
Claude Code-specific instruction block.
