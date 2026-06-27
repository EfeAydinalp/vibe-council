# docs/plans

Committed **plan documents** — the design record for a change, written *before*
implementing and reviewed by the council. These are intentionally version-controlled:
they explain what was decided and why.

| Plan | What it covers |
|------|----------------|
| [`readiness-polish.md`](readiness-polish.md) | First-run key guard, `vibe models`/`presets`, `--version`, tests + CI, privacy docs. |
| [`cross-platform-install.md`](cross-platform-install.md) | POSIX `vibe.sh` launcher + `install-vibe.sh` for macOS/Linux. |
| [`examples-workflow-polish.md`](examples-workflow-polish.md) | README, `examples/`, and agent-workflow docs polish (toward v0.1.0). |
| [`demo-and-release-prep.md`](demo-and-release-prep.md) | Demo recording guide, v0.1.0 release checklist, and changelog draft. |
| [`terminal-demo-asset.md`](terminal-demo-asset.md) | Sanitized terminal-transcript demo artifact (asciinema fallback). |

## Plans vs. raw council output

- **Plan docs (here)** are committed — they're the human-authored design record.
- **Raw council reviews** (the multi-model critique of a plan or diff) are written to
  the local `.council/` workspace and are **gitignored** — they can contain your
  prompts and model outputs and are not part of the repo.

Each plan typically ends with a `## Council feedback applied` section summarizing
which review findings were adopted and which were declined.

For runnable, copy-pasteable samples, see [`../../examples/`](../../examples/README.md).
