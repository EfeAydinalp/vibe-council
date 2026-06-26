#!/bin/sh
# install-vibe.sh — install a user-local `vibe` command (macOS / Linux).
#
# Mirrors scripts/install-vibe.ps1 for POSIX systems. Symlinks
# <bin>/vibe -> this repo's scripts/vibe.sh (default <bin> = ~/.local/bin).
# User-local only: never requires sudo, never edits your shell rc files.
#
# Flags:
#   --dry-run        show what would happen; make no changes
#   --yes            non-interactive (don't prompt)
#   --force          replace an existing non-ours <bin>/vibe
#   --bin-dir DIR    install into DIR instead of ~/.local/bin
#
# Environment:
#   VIBE_COUNCIL_HOME  override the repo root (else parent of this script's dir)

set -eu

DRY_RUN=0
YES=0
FORCE=0
BIN_DIR=""

while [ $# -gt 0 ]; do
    case $1 in
        --dry-run) DRY_RUN=1 ;;
        --yes|-y)  YES=1 ;;
        --force)   FORCE=1 ;;
        --bin-dir) shift; BIN_DIR=${1:-} ;;
        --bin-dir=*) BIN_DIR=${1#--bin-dir=} ;;
        -h|--help)
            echo "Usage: install-vibe.sh [--dry-run] [--yes] [--force] [--bin-dir DIR]"
            exit 0 ;;
        *) echo "install-vibe.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
    shift
done

# --- Resolve this script's real path (follow symlinks), then the repo root ---
src=$0
while [ -h "$src" ]; do
    dir=$(cd -P "$(dirname "$src")" && pwd)
    link=$(readlink "$src")
    case $link in
        /*) src=$link ;;
        *)  src=$dir/$link ;;
    esac
done
script_dir=$(cd -P "$(dirname "$src")" && pwd)

if [ -n "${VIBE_COUNCIL_HOME:-}" ]; then
    repo=$VIBE_COUNCIL_HOME
else
    repo=$(cd -P "$script_dir/.." && pwd)
fi

launcher="$repo/scripts/vibe.sh"
if [ ! -f "$launcher" ]; then
    echo "install-vibe.sh: launcher not found: $launcher" >&2
    exit 1
fi

# Default bin dir.
if [ -z "$BIN_DIR" ]; then
    BIN_DIR="$HOME/.local/bin"
fi
shim="$BIN_DIR/vibe"

echo "vibe-council repo : $repo"
echo "Launcher script   : $launcher"
echo "Install target    : $shim"

# --- Inspect any existing target ---------------------------------------------
# action: link (create/repair) | skip (already ours) | conflict (not ours)
action="link"
if [ -L "$shim" ]; then
    # Symlink (possibly broken). Compare its target to our launcher.
    target=$(readlink "$shim")
    case $target in
        /*) resolved=$target ;;
        *)  resolved="$BIN_DIR/$target" ;;
    esac
    if [ "$resolved" = "$launcher" ]; then
        action="skip"            # already points exactly at our launcher
    else
        # A symlink whose target path ends in scripts/vibe.sh is treated as a
        # previous vibe install that now points at the wrong place (e.g. the repo
        # moved, or it is a broken/dangling link). We own that name, so re-link it
        # to the current launcher rather than refusing. Any other target is a
        # genuine third-party 'vibe' and is left alone (conflict).
        case $resolved in
            */scripts/vibe.sh) action="link" ;;   # ours -> repair/re-point
            *) action="conflict" ;;
        esac
    fi
elif [ -e "$shim" ]; then
    action="conflict"            # a real file we didn't create
fi

if [ "$action" = "conflict" ] && [ "$FORCE" -ne 1 ]; then
    echo "" >&2
    echo "install-vibe.sh: '$shim' already exists and is not managed by vibe." >&2
    echo "  Re-run with --force to replace it, or use --bin-dir to pick another dir." >&2
    exit 1
fi

# --- Dry run -----------------------------------------------------------------
if [ "$DRY_RUN" -eq 1 ]; then
    echo ""
    echo "[dry-run] Would ensure directory : $BIN_DIR"
    echo "[dry-run] Would chmod +x         : $launcher"
    case $action in
        skip)     echo "[dry-run] Symlink already correct: $shim" ;;
        conflict) echo "[dry-run] Would REPLACE (--force): $shim -> $launcher" ;;
        *)        echo "[dry-run] Would create symlink   : $shim -> $launcher" ;;
    esac
    echo "[dry-run] No changes made."
    exit 0
fi

# --- Confirm (interactive only) ----------------------------------------------
if [ "$YES" -ne 1 ] && [ -t 0 ]; then
    printf "Install 'vibe' to %s? [Y/n] " "$shim"
    read ans || ans=""
    case $ans in
        ""|y|Y|yes|YES) : ;;
        *) echo "Aborted."; exit 0 ;;
    esac
fi

# --- Make the launcher executable --------------------------------------------
chmod +x "$launcher"

# --- Ensure a real, user-owned bin dir (avoid writing through a hostile link) -
if [ -L "$BIN_DIR" ] && [ ! -d "$BIN_DIR" ]; then
    echo "install-vibe.sh: '$BIN_DIR' is a symlink but not a directory; refusing." >&2
    exit 1
fi
if [ ! -d "$BIN_DIR" ]; then
    mkdir -p "$BIN_DIR"
fi

# --- Create / repair the symlink ---------------------------------------------
if [ "$action" = "skip" ]; then
    echo "Already installed: $shim -> $launcher"
else
    ln -sf "$launcher" "$shim"
    echo "Linked: $shim -> $launcher"
fi

# --- PATH guidance (print only; never edit rc files) -------------------------
case ":$PATH:" in
    *":$BIN_DIR:"*)
        on_path=1 ;;
    *)
        on_path=0 ;;
esac

if [ "$on_path" -eq 1 ]; then
    echo ""
    echo "Done. '$BIN_DIR' is already on PATH. Try:  vibe --version"
else
    # Name the concrete rc file for the user's shell.
    rc="$HOME/.profile"
    case "${SHELL:-}" in
        *zsh)  rc="$HOME/.zshrc" ;;
        *bash) if [ "$(uname -s)" = "Darwin" ]; then rc="$HOME/.bash_profile"; else rc="$HOME/.bashrc"; fi ;;
    esac
    echo ""
    echo "NOTE: '$BIN_DIR' is not on your PATH yet."
    echo "Add it by appending this line to $rc, then restart your shell:"
    echo ""
    echo "    export PATH=\"$BIN_DIR:\$PATH\""
    echo ""
    echo "After that:  vibe --version"
fi
