#!/usr/bin/env bash
# Install todo-tui.
#   Default: set up .venv and symlink the launcher onto PATH.
#   --binary: build a standalone executable with PyInstaller and copy it onto PATH.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
LAUNCHER="$REPO_DIR/todo"
BIN_DIR="${PREFIX:-$HOME/.local/bin}"
TARGET_PATH="$BIN_DIR/todo"

MODE="symlink"
if [[ "${1:-}" == "--binary" ]]; then
    MODE="binary"
fi

echo "==> Repo:       $REPO_DIR"
echo "==> Install to: $TARGET_PATH"
echo "==> Mode:       $MODE"

# Common: set up venv + deps
if [[ ! -d "$VENV_DIR" ]]; then
    echo "==> Creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi
echo "==> Installing runtime dependencies"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"

echo "==> Installing dev dependencies (ruff, pytest)"
"$VENV_DIR/bin/pip" install --quiet ruff pytest

# Wire up the git pre-commit hook (lint + format check + tests).
HOOK_SRC="$REPO_DIR/scripts/pre-commit"
HOOK_DST="$REPO_DIR/.git/hooks/pre-commit"
if [[ -d "$REPO_DIR/.git" && -f "$HOOK_SRC" ]]; then
    if [[ "$(readlink -f "$HOOK_DST" 2>/dev/null || true)" != "$(readlink -f "$HOOK_SRC")" ]]; then
        echo "==> Linking git pre-commit hook"
        ln -sf "$HOOK_SRC" "$HOOK_DST"
    fi
fi

mkdir -p "$BIN_DIR"

if [[ "$MODE" == "binary" ]]; then
    echo "==> Installing PyInstaller"
    "$VENV_DIR/bin/pip" install --quiet pyinstaller

    echo "==> Building standalone binary (this may take a minute)"
    pushd "$REPO_DIR" > /dev/null
    rm -rf build dist todo.spec
    "$VENV_DIR/bin/pyinstaller" \
        --onefile \
        --name todo \
        --paths src \
        --collect-all textual \
        --collect-all rich \
        src/todo.py > /dev/null
    popd > /dev/null

    echo "==> Copying binary to $TARGET_PATH"
    install -m755 "$REPO_DIR/dist/todo" "$TARGET_PATH"
else
    chmod +x "$LAUNCHER"
    echo "==> Symlinking $LAUNCHER -> $TARGET_PATH"
    if [[ -L "$TARGET_PATH" || -e "$TARGET_PATH" ]]; then
        existing="$(readlink -f "$TARGET_PATH" 2>/dev/null || true)"
        if [[ "$existing" == "$(readlink -f "$LAUNCHER")" ]]; then
            echo "==> Symlink already points here, skipping"
        else
            echo "==> Replacing existing $TARGET_PATH (was: ${existing:-not a symlink})"
            ln -sf "$LAUNCHER" "$TARGET_PATH"
        fi
    else
        ln -s "$LAUNCHER" "$TARGET_PATH"
    fi
fi

# PATH warning
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo
        echo "WARNING: $BIN_DIR is not on your PATH."
        echo "Add this to your shell rc:"
        echo "    export PATH=\"$BIN_DIR:\$PATH\""
        ;;
esac

echo
echo "Done. Run 'todo' from anywhere."
