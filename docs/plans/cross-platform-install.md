# Plan: cross-platform-install

Make the local `vibe` command usable on macOS/Linux, not just Windows, **without
changing any core council logic** (no changes to `backend/council.py`,
`backend/config.py`, presets, or model behavior). This adds a POSIX shell wrapper
and a user-local installer that mirror the existing Windows wrappers, plus docs and
CI coverage.

## Current Windows install behavior

The repo already ships a Windows-only path:

- **`scripts/vibe.ps1`** — the launcher. It resolves the repo root from
  `VIBE_COUNCIL_HOME` (falling back to deriving it from the script's own location, i.e.
  the parent of `scripts\`),
  records the caller's directory in `VIBE_CALLER_CWD`, prefers the repo's
  `.venv\Scripts\python.exe` (falling back to `python` on PATH), `Push-Location`s
  into the repo, runs `python -m backend.cli @args`, restores the directory, and
  forwards the exit code. Never prints the API key.
- **`scripts/vibe.cmd`** — a CMD shim that forwards all args to `vibe.ps1` using
  `%~dp0` so it works from any directory.
- **`scripts/install-vibe.ps1`** — installs a global command by writing
  `%USERPROFILE%\bin\vibe.cmd` (which calls `vibe.ps1`) and adding
  `%USERPROFILE%\bin` to the **User PATH** (asks first unless `--yes`). Supports
  `--dry-run`. No admin required.

The CLI itself is already cross-platform Python: `backend/project_workspace.caller_cwd()`
reads `VIBE_CALLER_CWD` (falling back to `os.getcwd()`), and the CLI is invoked as
`python -m backend.cli`. **Only the shell entrypoints are Windows-specific.**

### Observed gaps (motivation)

During the last sync, verification showed two install/UX problems on a non-global
setup:

1. `vibe` was not usable as a plain command — it had to be invoked through
   `scripts/vibe.ps1` directly. There is no Unix equivalent at all.
2. A bare `python` resolved to the wrong environment and missed project deps
   (`ModuleNotFoundError: dotenv`); the working interpreter was the repo venv.
   The Windows wrapper already prefers the repo venv; the Unix path must do the
   same and must not assume a bare `python` points at the project environment.

## Proposed Unix/macOS/Linux behavior

Add two POSIX shell scripts that mirror the Windows ones:

- **`scripts/vibe.sh`** — the Unix launcher. It must:
  - **Shell stance (committed):** `#!/bin/sh`, **strict POSIX, no bashisms** (no
    `[[ ]]`, no arrays, no `local`; use `command -v`, not `type`). Rationale: must run
    under dash (Ubuntu's `/bin/sh`) and busybox ash, not just bash. Tested on Ubuntu
    (dash) and macOS in CI.
  - Resolve the repo root **robustly from the script's own real path** (so it works
    when invoked through a symlink in `~/.local/bin`), not from a hardcoded path.
    **Exact algorithm (no `readlink -f`, which is absent on macOS):**
    ```sh
    # Resolve $0 through any chain of symlinks, portably.
    src=$0
    while [ -h "$src" ]; do
      dir=$(cd -P "$(dirname "$src")" && pwd)
      link=$(readlink "$src")
      case $link in
        /*) src=$link ;;        # absolute symlink target
        *)  src=$dir/$link ;;   # relative to the link's directory
      esac
    done
    script_dir=$(cd -P "$(dirname "$src")" && pwd)
    repo=$(cd -P "$script_dir/.." && pwd)   # scripts/ -> repo root
    ```
    Uses only POSIX `readlink` (no `-f`), `cd -P`, `dirname`. Works on BSD/macOS,
    GNU/Linux, and busybox.
  - **`VIBE_COUNCIL_HOME` priority (committed):** if already set and non-empty, it
    **wins** (supports running against a different clone); otherwise it is set to the
    script-resolved `repo`. Documented so the multi-clone case is unambiguous.
  - Set `VIBE_CALLER_CWD` to the caller's current directory **before** changing into
    the repo, so project-local `.council/` artifacts land in the caller's project.
    If `VIBE_CALLER_CWD` is already set by an outer tool, **respect it** (do not
    overwrite) — matches the env-as-override contract `caller_cwd()` already uses.
  - Choose a Python interpreter in this priority order:
    1. `VIBE_PYTHON` if set (escape hatch),
    2. the repo venv at `$repo/.venv/bin/python` if it exists,
    3. an active virtualenv's `python` (`$VIRTUAL_ENV/bin/python`),
    4. `python3`, then `python` on PATH.
    This avoids the "bare python = wrong env" trap and never hardcodes a Windows path.
    `$VIRTUAL_ENV` is the only venv signal checked (Conda's own vars are a documented
    non-goal). Repo `.venv` deliberately beats an active venv: vibe is a tool run
    *against* the caller's project, so it should use its own deps, not the caller's.
  - **Pre-flight dependency check** (turns a raw `ModuleNotFoundError` into a clear
    message): after selecting `$PY`, run
    `"$PY" -c "import backend.cli" >/dev/null 2>&1` from the repo; on failure, print a
    short "dependencies not found — install with `pip install -e .` or create
    `.venv`" message and exit non-zero **before** invoking the CLI.
  - **`exec`** the CLI: `exec "$PY" -m backend.cli "$@"` from the repo root (clean
    signal handling; the process exit code is the CLI's).
  - Never print the API key.

- **`scripts/install-vibe.sh`** — the Unix installer. It must:
  - Install a `vibe` command into a **user-local bin** (`~/.local/bin` preferred),
    as a symlink to `scripts/vibe.sh` (falling back to a small forwarding shim if
    symlinks are unavailable).
  - Make `scripts/vibe.sh` executable (`chmod +x`).
  - Print **clear next steps** if `~/.local/bin` is not on `PATH` (the exact
    `export PATH=...` line and which shell rc file to add it to).
  - **Not require sudo** by default (user-local only).
  - Be **safe/idempotent** with **explicit collision detection** for an existing
    `<bin>/vibe`:
    - if it is a **symlink** that resolves to our `scripts/vibe.sh` → already
      installed, no-op;
    - if it is a **broken symlink** whose target path ends in `scripts/vibe.sh` →
      treat as ours and repair (re-link);
    - if it is **anything else** (a real file, or a symlink elsewhere) → **warn and
      skip** unless `--force` is passed.
  - **Verify `<bin>` is a real, user-owned directory** before writing (`[ -d ]` and
    owned by the current user; create it with `mkdir -p` if absent) — avoids writing
    through a hostile pre-existing symlink.
  - Print **shell-specific** PATH guidance: detect `$SHELL` and name the concrete rc
    file (`~/.zshrc` for zsh, `~/.bashrc`/`~/.bash_profile` for bash, else `~/.profile`)
    with the exact `export PATH="$HOME/.local/bin:$PATH"` line. It **prints**; it does
    **not** edit rc files.
  - Support `--dry-run` (show actions, change nothing) and `--yes` (non-interactive),
    matching the PowerShell installer's flag surface; add `--force` (override a
    non-ours collision) and `--bin-dir DIR`.
  - Honor `VIBE_COUNCIL_HOME`.

The Python CLI, presets, and council logic are untouched.

## Exact files to add / change

**Add**

- `scripts/vibe.sh` — POSIX launcher (mirror of `vibe.ps1`).
- `scripts/install-vibe.sh` — POSIX user-local installer (mirror of `install-vibe.ps1`).

**Change**

- `README.md` — expand the install section into:
  - Windows PowerShell install (existing),
  - Windows CMD usage (existing wrapper),
  - **macOS/Linux shell install** (new),
  - **manual PATH fallback** (new),
  - quick verification block: `vibe --version`, `vibe status`, `vibe presets`,
    `vibe models`.
  - Update the Roadmap line ("Cross-platform install scripts (macOS/Linux)") since
    it is now delivered.
- `docs/agent-integrations.md` — add a short "cross-platform wrapper" note covering
  `scripts/vibe.sh` / `install-vibe.sh`, document `VIBE_CALLER_CWD`,
  `VIBE_COUNCIL_HOME`, and the interpreter-resolution order (including `VIBE_PYTHON`),
  and add a one-line **security boundary** note: `VIBE_PYTHON` / `VIBE_COUNCIL_HOME`
  select what code runs, so do not run `vibe` where these env vars are
  attacker-controlled.
- `tests/test_install_scripts.py` *(new)* — stdlib `unittest` checks that the
  wrappers exist and contain the expected environment handling (see Test strategy).
- `.gitattributes` *(new)* — `*.sh text eol=lf` so shell scripts are always checked
  out with LF endings (CRLF would break `#!/bin/sh` with `bad interpreter`).
- `.github/workflows/ci.yml` — add **macOS to the OS matrix** (the plan claims macOS
  support, so it must be tested) and add a POSIX-only step that smoke-tests
  `scripts/vibe.sh` (no real model calls, no API key): run `vibe.sh --version`,
  `presets`, `models`; assert `VIBE_CALLER_CWD` is honored; and run an **end-to-end
  install test** (`install-vibe.sh --yes --bin-dir <tmp>`, then invoke the installed
  symlink) so the symlink-resolution path is exercised, not just direct `sh vibe.sh`.

## Compatibility risks

- **Repo-root resolution through a symlink.** `~/.local/bin/vibe` will be a symlink;
  `vibe.sh` must resolve **its own real path** before deriving the repo root. Pure
  POSIX `sh` has no `readlink -f` on macOS by default — use a portable resolution
  (a small `cd "$(dirname "$0")" && pwd -P` loop that follows symlinks, or a guarded
  `readlink` fallback). This is the single highest-risk detail.
- **Interpreter selection.** Must not assume bare `python` is the project env (the
  exact bug observed). Prefer repo `.venv`, then active venv, then `python3`. If no
  suitable interpreter and no deps are found, fail with a clear message rather than a
  raw `ModuleNotFoundError`.
- **`~/.local/bin` not on PATH.** Common on fresh macOS/Linux. The installer must
  detect this and print the exact fix; it must not silently edit shell rc files.
- **Line endings.** Shell scripts must be saved **LF**, not CRLF, or they fail with
  `bad interpreter`. Add a `.gitattributes` entry (`*.sh text eol=lf`) if not already
  enforced, and verify in CI (the Ubuntu run executing the script catches CRLF).
- **No bashisms.** Target `/bin/sh` (dash on Debian/Ubuntu) to maximize portability;
  avoid arrays, `[[ ]]`, and `local` where not POSIX.
- **Idempotency / not clobbering files.** If `~/.local/bin/vibe` exists and is **not**
  ours, warn and skip (or require `--force`) rather than overwrite.
- **Windows path untouched.** The PowerShell/CMD wrappers and their behavior must keep
  working exactly as before; no shared file is modified in a way that affects them.

## Test strategy

Stdlib `unittest` only — no new dependencies. Add `tests/test_install_scripts.py`:

- `scripts/vibe.sh` exists and starts with a `#!` shebang.
- `scripts/install-vibe.sh` exists and starts with a `#!` shebang.
- `vibe.sh` references `VIBE_CALLER_CWD`, `VIBE_COUNCIL_HOME`, and
  `backend.cli` (proves the env handling and entrypoint are wired).
- `vibe.sh` does **not** contain a hardcoded Windows path (`C:\\`) — guards against
  copy-paste from `vibe.ps1`.
- `install-vibe.sh` references `.local/bin` and `PATH`.
- These checks are **OS-agnostic** (pure file-content assertions), so they pass on
  Windows CI too and don't require executing the shell script.

Plus, **behavioral** coverage on POSIX CI (`ubuntu-latest` **and** `macos-latest`):

- `sh scripts/vibe.sh --version`, `presets`, `models` → exit 0 + expected output.
- Run from a temp dir with `VIBE_CALLER_CWD` set → `vibe.sh status` reports no
  workspace in that temp dir (caller cwd honored).
- **End-to-end install:** `sh scripts/install-vibe.sh --yes --bin-dir <tmpbin>`, then
  invoke `<tmpbin>/vibe --version` so the **symlink-resolution** path is exercised
  (not just `sh scripts/vibe.sh`). No API key, no model calls.

### Support matrix (committed)

Scripts must work, using only base-system tools (no `realpath`/`greadlink`/GNU-only
`readlink` flags), on:

- **macOS 12+** (`/bin/sh`, bash 3.2),
- **Ubuntu 20.04+** (`/bin/sh` = dash),
- **busybox ash** (Alpine) on a best-effort basis (not in CI, but no feature is used
  that busybox lacks).

Python floor is whatever `pyproject.toml` already requires (`>=3.10`); the wrapper
does not re-validate the Python version — a wrong interpreter surfaces via the
pre-flight `import backend.cli` check, not a cryptic traceback.

Existing tests must keep passing:

- `python -m unittest discover -s tests -t .` (all current `test_cli_smoke.py` tests).

## Out of scope (intentionally)

- **No Ollama / multi-provider abstraction**, no MCP server, no SaaS.
- **No Typer/Click migration** — `argparse` stays.
- **No PyPI publishing**, no `pipx`/`uvx` packaging, no console-script entry point in
  `pyproject.toml` (that is a separate packaging decision).
- **No changes to core council logic**, presets, models, or guard semantics.
- **No automatic editing of the user's shell rc files** — we print instructions, we
  don't mutate `~/.zshrc` / `~/.bashrc`.
- **No Homebrew formula / system package**, no Windows installer changes beyond docs.
- **No `pipx`/`uvx` packaging path** and **no shared `backend/wrapper.py` refactor**
  to unify the PowerShell + sh launchers — both are reasonable future directions
  (council suggested them) but are a packaging/architecture decision out of scope for
  this PR. The four-path maintenance cost (CMD → PS → Python, sh → Python) is accepted
  for now.
- **No `~/bin` auto-detection** — `~/.local/bin` is the single default, overridable
  via `--bin-dir`. (Keeps installer logic simple and predictable.)
- **No `uninstall-vibe.sh`** in this PR — removal is `rm <bin>/vibe` and is documented
  in the README; a dedicated uninstaller can come later.
- **No Conda interpreter detection** — only `$VIRTUAL_ENV` / repo `.venv` are honored.
- **No `.council/` artifacts committed**; raw outputs stay local and gitignored.

## Council feedback applied

The plan was reviewed by vibe-council (`vibe review --preset balanced` on this plan;
raw output local-only under `.council/reviews/`). The review gave conditional
approval and flagged several concrete gaps. Applied (kept tight, no scope creep):

- **Symlink resolution was underspecified** (the "highest-risk detail"). Now the plan
  pins the **exact POSIX algorithm** (a `readlink` loop with `cd -P`, no `readlink -f`)
  so it works on macOS/BSD, GNU/Linux, and busybox.
- **Interpreter-not-found gave a raw `ModuleNotFoundError`.** Added a **pre-flight
  `import backend.cli` check** that prints a clear "install deps / create .venv"
  message and exits before invoking the CLI.
- **Collision detection was vague.** Now defined concretely (symlink-resolves-to-ours
  → no-op; broken symlink to `…/scripts/vibe.sh` → repair; anything else → warn/skip
  unless `--force`), plus a user-owned-dir check on `<bin>` for safety.
- **`VIBE_COUNCIL_HOME` priority and `VIBE_CALLER_CWD` already-set semantics** are now
  explicit (env wins / respect-if-set).
- **macOS was claimed but untested.** Added **`macos-latest` to the CI matrix** and an
  **end-to-end install + symlink-invocation** smoke test (not just `sh vibe.sh`).
- **Shell stance committed:** strict POSIX `#!/bin/sh`, no bashisms, with an explicit
  **support matrix** (macOS 12+, Ubuntu 20.04+/dash, busybox best-effort) and a
  "base-system tools only" constraint.
- **`.gitattributes` (`*.sh text eol=lf`)** moved from a risk note into the concrete
  **Change** list (CRLF would break the shebang).
- **`exec` the CLI** in `vibe.sh` for clean signal handling/exit codes.
- **Security boundary documented:** `VIBE_PYTHON` / `VIBE_COUNCIL_HOME` choose what
  runs, so don't run `vibe` where they're attacker-controlled (added to the
  agent-integrations note).
- **Shell-specific PATH guidance:** the installer detects `$SHELL` and names the rc
  file, instead of a generic "your shell rc."

**Deliberately not adopted (out of scope / over-engineering for this PR):**

- `pipx`/`uvx` as the primary install path, and a shared `backend/wrapper.py` to
  collapse the PowerShell + sh launchers — sensible, but a packaging/architecture
  change, not this PR.
- `~/bin`-vs-`~/.local/bin` auto-detection, a dedicated `uninstall-vibe.sh`, and Conda
  interpreter detection — kept out to keep the installer small and predictable
  (overridable via `--bin-dir`; removal documented as `rm <bin>/vibe`).
- Switching to `#!/usr/bin/env bash` — declined in favor of committing to POSIX `sh`
  and testing on dash, which is the more portable stance.

### Diff review feedback applied

After implementation, the diff was reviewed by vibe-council (`vibe review --preset
balanced` on a gitignored temp diff under `.council/tmp/`). It gave "approve with
minor hardening" and three required items, all applied:

- **Sanity-check the env-var trust boundaries.** `vibe.sh` now rejects a
  `VIBE_COUNCIL_HOME` that has no `backend/cli.py` and a `VIBE_PYTHON` that is not a
  runnable interpreter — instead of trusting them blindly or failing later with a
  confusing error.
- **Document the repo-`.venv`-over-active-venv precedence in the README**, not just
  the plan (it is surprising behavior). Added an explicit note.
- **Comment the broken-symlink "repair" branch** in `install-vibe.sh` so a future
  maintainer understands why a dangling `…/scripts/vibe.sh` link is re-pointed rather
  than treated as a conflict.

**Deliberately deferred (out of scope, already noted above):** a shared
`backend/wrapper.py` to collapse the two launchers, `pipx`/`uvx` packaging, `~/bin`
auto-detection, negative-path CI cases, WSL-specific docs, and per-script version
metadata. These are reasonable follow-ups but would widen this PR beyond
"cross-platform install."
