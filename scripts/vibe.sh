#!/bin/sh
# vibe.sh — POSIX launcher for the vibe-council CLI (macOS / Linux).
#
# Mirrors scripts/vibe.ps1: runs `python -m backend.cli` inside the vibe-council
# repo while remembering the caller's working directory (exposed via
# VIBE_CALLER_CWD) so project-local .council/ artifacts are written in the
# caller's project.
#
# Strict POSIX sh: no bashisms (no [[ ]], arrays, or `local`). Runs under dash,
# bash, zsh, and busybox ash. Never prints the API key.
#
# Environment:
#   VIBE_COUNCIL_HOME  if set, overrides the repo root (supports multiple clones)
#   VIBE_CALLER_CWD    if set, respected; else set to the current directory
#   VIBE_PYTHON        if set, the exact Python interpreter to use (escape hatch)

set -eu

# --- Resolve this script's real path through any chain of symlinks -----------
# ~/.local/bin/vibe is a symlink to this file, so $0 may be a symlink. POSIX
# only (no `readlink -f`, which BSD/macOS lacks).
src=$0
while [ -h "$src" ]; do
    dir=$(cd -P "$(dirname "$src")" && pwd)
    link=$(readlink "$src")
    case $link in
        /*) src=$link ;;        # absolute symlink target
        *)  src=$dir/$link ;;   # relative to the link's own directory
    esac
done
script_dir=$(cd -P "$(dirname "$src")" && pwd)

# --- Repo root: VIBE_COUNCIL_HOME wins; else parent of scripts/ --------------
if [ -n "${VIBE_COUNCIL_HOME:-}" ]; then
    repo=$VIBE_COUNCIL_HOME
else
    repo=$(cd -P "$script_dir/.." && pwd)
fi

# Sanity-check the repo root: it must actually look like vibe-council. This also
# hardens the VIBE_COUNCIL_HOME trust boundary (don't run a fake backend/cli.py).
if [ ! -f "$repo/backend/cli.py" ]; then
    echo "vibe: '$repo' does not look like a vibe-council repo (no backend/cli.py)." >&2
    echo "      Set VIBE_COUNCIL_HOME to the repo root." >&2
    exit 1
fi

# Export so the Python CLI (config / project_workspace) sees them.
export VIBE_COUNCIL_HOME="$repo"

# Remember where the user invoked vibe from; respect an outer tool's value.
if [ -z "${VIBE_CALLER_CWD:-}" ]; then
    VIBE_CALLER_CWD=$(pwd)
fi
export VIBE_CALLER_CWD

# --- Pick a Python interpreter -----------------------------------------------
# Priority: VIBE_PYTHON > repo .venv > active virtualenv > python3 > python.
# Never assume a bare `python` is the project environment.
PY=""
if [ -n "${VIBE_PYTHON:-}" ]; then
    PY=$VIBE_PYTHON
    # Validate the escape hatch: must resolve to a runnable interpreter.
    if ! command -v "$PY" >/dev/null 2>&1; then
        echo "vibe: VIBE_PYTHON='$PY' is not an executable on PATH or a valid path." >&2
        exit 1
    fi
elif [ -x "$repo/.venv/bin/python" ]; then
    PY="$repo/.venv/bin/python"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PY="$VIRTUAL_ENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "vibe: no Python interpreter found (tried VIBE_PYTHON, $repo/.venv, \$VIRTUAL_ENV, python3, python)." >&2
    exit 1
fi

# --- Pre-flight: deps importable? Turn ModuleNotFoundError into a clear msg ---
cd "$repo"
if ! "$PY" -c "import backend.cli" >/dev/null 2>&1; then
    echo "vibe: Python dependencies not found for '$PY'." >&2
    echo "      Install them, e.g.:  python -m venv .venv && .venv/bin/pip install -e ." >&2
    echo "      or set VIBE_PYTHON to an interpreter that has the project deps." >&2
    exit 1
fi

# --- Run the CLI -------------------------------------------------------------
# exec: the CLI's exit code becomes ours; clean signal handling, no subshell.
exec "$PY" -m backend.cli "$@"
