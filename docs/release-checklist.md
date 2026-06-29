# vibe-council release checklist

A practical, auditable checklist for cutting a release. Items are
tiered so you can tell what blocks a release from what's nice to confirm:

- **🔴 Critical** — blocking. The release does not ship until these pass.
- **🟡 Recommended** — should pass; document any exception.
- **⚪ Contextual** — do it if you have the OS/tooling; not every maintainer has all
  three platforms.

> **This is a reusable runbook, not a run-log.** The checkboxes track a single release
> *run*; don't record per-release status (e.g. "in progress", who's tagging) in here, or
> it goes stale for the next version. Track that in the release PR, the dated
> `CHANGELOG.md` section, and `docs/releases/<version>.md`.

> **What a "safe release" means here:** the main release risks for a local-first,
> bring-your-own-key dev tool are (1) leaking secrets or local paths into the repo or
> a published asset, and (2) shipping broken install / inconsistent version state.
> "Safe" = none of those reach the published tag. This checklist is organized around
> catching exactly those.

---

## 1. Pre-release (version & changelog)

- [ ] 🔴 Bump `__version__` in [`backend/__init__.py`](../backend/__init__.py) to the new
      release version (e.g. `0.2.0`).
- [ ] 🔴 Confirm it matches `version` in [`pyproject.toml`](../pyproject.toml). These are
      **two separate strings** — they must agree. Then run `uv lock` to sync the `uv.lock`
      self-version (it should change only the `vibe-council` self-package version).
- [ ] 🔴 `vibe --version` prints the new version (e.g. `vibe-council 0.2.0`).
- [ ] 🔴 In [`CHANGELOG.md`](../CHANGELOG.md), move the `Unreleased` items under a dated
      heading: `## [X.Y.Z] - YYYY-MM-DD`. Leave a fresh empty `Unreleased` above it, and
      update the `> Status:` banner to the new version.

## 2. CI / tests

- [ ] 🔴 `python -m unittest discover -s tests -t .` is green.
      If a system `python` mismatches the environment, use the repo venv interpreter
      (`.venv\Scripts\python.exe` on Windows, `.venv/bin/python` on POSIX) and note it.
- [ ] 🔴 GitHub Actions CI is green on the release commit.
- [ ] ⚪ CI passed on **all three** OS legs (Ubuntu / macOS / Windows), not just one.
- [ ] 🔴 `python -m compileall backend tests` passes (no syntax/import errors).
- [ ] 🟡 `vibe doctor --offline` runs and reports the selected provider (no network, no
      tokens, no key printed).

## 3. README / docs

- [ ] 🔴 All internal doc links resolve: `docs/demo.md`, `docs/release-checklist.md`,
      `CHANGELOG.md`, `examples/`, `docs/agent-integrations.md`.
- [ ] 🟡 README **Quick start** install steps work from a clean clone.
- [ ] 🟡 README **Roadmap** ("Recently shipped" / "Near-term") reflects reality for the
      release (e.g. move shipped items out of "Later").
- [ ] 🟡 README **Demo** section links to `docs/demo.md` and is honest that no recorded
      asset ships yet.
- [ ] 🟡 **Providers documented:** OpenRouter is the default (`VIBE_PROVIDER=openrouter`);
      Ollama env vars (`VIBE_PROVIDER=ollama`, `OLLAMA_HOST`, `VIBE_OLLAMA_MODEL`) are
      documented in README + `.env.example`.
- [ ] 🟡 **Caveats stated:** Ollama users should set `VIBE_OLLAMA_MODEL`, and local Ollama
      reports no cost so `--max-cost` cannot be enforced for Ollama runs.

## 4. Install checks

- [ ] ⚪ **Windows** — `powershell -ExecutionPolicy Bypass -File scripts\install-vibe.ps1 --dry-run`
      then `--yes`; new terminal; `vibe --version` → the release version.
- [ ] ⚪ **macOS / Linux** — `sh scripts/install-vibe.sh --dry-run` then `--yes`;
      `vibe --version` → the release version.
- [ ] 🟡 Direct wrappers run without installing: `scripts/vibe.ps1`, `scripts/vibe.cmd`
      (Windows), `scripts/vibe.sh` (POSIX).
- [ ] 🟡 `vibe status`, `vibe presets`, `vibe models` work (no-model commands, no key).

## 5. Security / safety

- [ ] 🔴 No secrets in the diff: `git grep -n "sk-or-v1-"` on the release commit
      returns **nothing committed**. This prefix is **OpenRouter-specific** and the
      grep only covers tracked text — it is a floor, not a guarantee. Prefer running a
      real scanner ([`gitleaks`](https://github.com/gitleaks/gitleaks) /
      [`trufflehog`](https://github.com/trufflesecurity/trufflehog)) over the tree,
      and scan any committed binary asset (e.g. a demo cast/GIF) separately.
- [ ] 🔴 `.env`, `.council/`, `data/`, `.venv/` are **not staged / not committed**.
- [ ] 🟡 First-run key guard still fires: with `OPENROUTER_API_KEY` unset, a model
      command exits **code 7** with a clear message (no traceback, no key echoed).
- [ ] 🟡 No demo asset (`.cast`/`.gif`/`.mp4`) is committed unless it has passed the
      [demo redaction checklist](demo.md#redaction-checklist-do-this-every-time).

## 6. Local runtime artifacts

- [ ] 🔴 `git status --short` shows **no** `.council/`, `data/`, `.env`, `.venv/`,
      `__pycache__/`, `frontend/node_modules/`, or `frontend/dist/` staged.
- [ ] 🟡 `.gitignore` still covers all of the above.

## 7. Tagging

> Performed by a maintainer **after** this prep merges — documented here, not executed
> by the prep PR.

- [ ] 🔴 Create an annotated tag on the release commit:
      `git tag -a vX.Y.Z -m "vibe-council vX.Y.Z"`.
- [ ] 🔴 Push it: `git push origin vX.Y.Z`.
- [ ] 🟡 Confirm the tag points at the intended commit: `git show vX.Y.Z --stat`.

## 8. GitHub release notes

- [ ] 🔴 Create a GitHub Release for `vX.Y.Z`; paste the `CHANGELOG.md` `[X.Y.Z]`
      section (or `docs/releases/vX.Y.Z.md`) as the body.
- [ ] 🟡 State the **known limitations** in the notes for the release. For v0.2.0:
      Ollama users should set `VIBE_OLLAMA_MODEL` (presets still use OpenRouter-style IDs);
      local Ollama reports no cost so `--max-cost` can't be enforced for Ollama; no MCP /
      personas / app yet; no recorded demo asset yet; decision search is plain string
      matching; license/provenance cleanup ongoing.
- [ ] 🟡 Verify release-note links render correctly **from the GitHub Release page**
      (not just the in-repo file): relative links resolve under `/releases/` and break
      (e.g. README "not found"), so prefer **tag-pinned absolute URLs** for links inside
      release bodies — e.g. `https://github.com/<owner>/<repo>/blob/<tag>/README.md`.
- [ ] 🟡 Mark the release as **latest**.

## 9. Post-release verification

- [ ] 🔴 Fresh clone → install → `vibe --version` prints the release version.
- [ ] 🟡 Release page renders; the tag points at the right commit; CHANGELOG link works.
- [ ] ⚪ A `vibe review --preset cheap` smoke run succeeds against the released code.

---

## Rollback / abort procedure

Releases fail. Have the recovery path ready **before** you tag.

**A pre-tag step fails** (CI red, version mismatch, secret found):
- Stop. Do **not** tag. Fix forward on the branch, re-run §2 and §5, then resume.

**A bad tag was already pushed** (e.g. broken install discovered post-tag):
1. Delete the remote tag: `git push origin :refs/tags/vX.Y.Z`.
2. Delete the local tag: `git tag -d vX.Y.Z`.
3. If a GitHub Release was published, delete or mark it as a draft.
4. Fix the issue on `main`, then re-cut — **prefer fixing forward to the next patch
   version** over reusing the same tag if anyone may have already pulled the bad tag
   (a moved tag is a trap for anyone who fetched it).
5. Note what happened in the CHANGELOG / release notes so users aren't confused.

**A secret was committed or leaked into a published asset:**
- Treat the key as **exposed** and **rotate it immediately** at the provider.
- Remove the file from the working tree, then scrub it from history
  (`git filter-repo` / BFG) and force-update the remote.
- If it reached a tag/release, delete that asset (see steps above) and re-cut clean.

**Communicate** any yank/re-cut in the release notes and (if there's one) the project
discussion/issues, so a half-released state doesn't strand early adopters.

---

## Future automation (deferred)

These were raised in review and are deliberately **deferred** — recorded so the intent
isn't lost, not because they're needed to cut a release:

- A `scripts/prepare-release.{sh,ps1}` that bumps the version, dates the changelog, and
  runs the consistency checks in one shot.
- CI that fails on **version-string drift** (a stale `-dev` version left behind) and
  **broken internal doc links**.
- A broader **secrets scanner** (e.g. `gitleaks` / `trufflehog`) in pre-commit / CI,
  instead of a single `sk-or-v1-` grep.
- A `vibe status --sanitize` / `--no-paths` flag so public demos don't have to redact
  the absolute project path by hand (fixes the leak at the source).
- A GitHub **release issue template** so each release is a trackable, tickable artifact.
