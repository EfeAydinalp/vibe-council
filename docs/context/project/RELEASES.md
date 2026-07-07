# Releases (history index)

A concise, newest-first index of shipped releases — an **index / working-memory aid**, not a
replacement for the canonical sources. It keeps [`STATUS.md`](./STATUS.md) focused on the current
state instead of a growing release log.

- **Canonical detailed notes:** [`docs/releases/`](../../releases/) — one file per release.
- **Canonical chronological change list:** [`CHANGELOG.md`](../../../CHANGELOG.md).
- This file **does not** duplicate full release notes; each line points at its canonical notes.

## Cap / collapse policy

- **Hard cap: 30 visible entries.** One line per release, newest first.
- On overflow the **oldest** entries collapse into a single roll-up line (e.g.
  `- **v0.1.0–v0.4.0** — early foundations — see docs/releases/ & CHANGELOG`); history is
  summarized, never endlessly appended.
- Detailed notes are never inlined here — follow the per-line pointer into
  [`docs/releases/`](../../releases/).

## Trimming STATUS history

When [`STATUS.md`](./STATUS.md) accumulates aged "Current state" bullets, move the shipped-release
detail into the canonical release notes and leave a one-line pointer here. The curation is human,
deterministic, and local — see [`WORKFLOWS.md`](./WORKFLOWS.md) → "Trimming STATUS history".

## Releases (newest first)

- **v0.8.2** — Preference schema v1 + read-only doctor validator (findings-only, no application) — [notes](../../releases/v0.8.2.md)
- **v0.8.1** — Vault polish: capped release-history index + STATUS-trimming workflow — [notes](../../releases/v0.8.1.md)
- **v0.8.0** — Agent onboarding launcher (`vibe init-agent` + localhost guard) — [notes](../../releases/v0.8.0.md)
- **v0.7.1** — Personalization hardening (redaction rule, doctor polish, invariant tests) — [notes](../../releases/v0.7.1.md)
- **v0.7.0** — Safe personalization / project-profile scaffold — [notes](../../releases/v0.7.0.md)
- **v0.6.3** — Cross-project agent onboarding (`vibe context export --for`) — [notes](../../releases/v0.6.3.md)
- **v0.6.0** — Agent-to-Workbench proposal bridge — [notes](../../releases/v0.6.0.md)
- **v0.5.2** — Workbench security-hardening patch (Host-header / token) — [notes](../../releases/v0.5.2.md)
- **v0.5.1** — Workbench dogfood & hardening patch — [notes](../../releases/v0.5.1.md)
- **v0.5.0** — AI Council Workbench MVP (guarded execution) — [notes](../../releases/v0.5.0.md)
- **v0.4.0** — Read-only MCP / Claude Code workflow — [notes](../../releases/v0.4.0.md)
- **v0.3.1** — Decision-memory / context dogfood hardening — [notes](../../releases/v0.3.1.md)
- **v0.3.0** — Local-first decision memory + curated project context — [notes](../../releases/v0.3.0.md)
- **v0.2.0** — Multi-provider OpenRouter + local Ollama — [notes](../../releases/v0.2.0.md)
- **v0.1.0** — Initial council CLI — [notes](../../releases/v0.1.0.md)

> Minor releases folded into a bundle (e.g. v0.6.1/v0.6.2 into the v0.6.x onboarding arc) have no
> standalone `docs/releases/` note; see [`CHANGELOG.md`](../../../CHANGELOG.md) and
> [`PROGRESS.md`](./PROGRESS.md) for the full sequence.
