#!/bin/sh
# Uninstalls the exo engine from this machine (Linux and macOS). It does not touch
# projects: to remove it from a project, run `exo uninstall` inside that project.
#
# Removes the PATH lines that install.sh added, only if that directory is empty
# (~/.local/bin or the uv one may hold other tools).
# Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1 (the same as
# install.sh).
set -eu

DIST=exo-harness
REMOVED=0
NO_PATH=${EXO_INSTALL_NO_PATH:-0}
MARK="# added by $DIST"

data_dir() {
    if [ -n "${EXO_DATA_DIR:-}" ]; then echo "$EXO_DATA_DIR"
    elif [ "$(uname -s)" = Darwin ]; then echo "$HOME/Library/Application Support/$DIST"
    else echo "${XDG_DATA_HOME:-$HOME/.local/share}/$DIST"
    fi
}

# Quita las líneas marcadas. Si el archivo queda vacío y lo había creado
# install.sh, lo borra.
strip_marked() {
    if [ ! -f "$1" ] || ! grep -qF "$MARK" "$1"; then
        return 0
    fi
    grep -vF "$MARK" "$1" > "$1.$DIST.tmp" || true
    cat "$1.$DIST.tmp" > "$1"
    rm -f "$1.$DIST.tmp"
    if [ ! -s "$1" ] && grep -qsxF "$1" "$CREATED"; then
        rm -f "$1"
    fi
}

if command -v uv >/dev/null 2>&1 && [ "${EXO_INSTALL_NO_UV:-0}" != 1 ]; then
    if uv tool list 2>/dev/null | grep -q "^$DIST "; then
        uv tool uninstall "$DIST"
        REMOVED=1
    fi
fi

DATA_DIR=$(data_dir)
VENV="$DATA_DIR/venv"
if [ -d "$VENV" ]; then
    rm -rf "$VENV"
    REMOVED=1
    LINK="$HOME/.local/bin/exo"
    if [ -L "$LINK" ] && [ "$(readlink "$LINK")" = "$VENV/bin/exo" ]; then
        rm -f "$LINK"
    fi
fi

MARKER="$DATA_DIR/path-entry.txt"
CREATED="$DATA_DIR/path-created.txt"
if [ "$NO_PATH" != 1 ] && [ -f "$MARKER" ]; then
    ADDED=$(cat "$MARKER")
    if [ ! -d "$ADDED" ] || [ -z "$(ls -A "$ADDED")" ]; then
        for rc in "$HOME/.profile" "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
            strip_marked "$rc"
        done
        echo "Removed $ADDED from the PATH."
    else
        echo "Keeping $ADDED on the PATH: it holds other tools."
    fi
    rm -f "$MARKER" "$CREATED"
fi

if [ "$REMOVED" = 1 ]; then
    echo "Uninstalled $DIST. Project uninstall backups remain in $DATA_DIR."
else
    echo "$DIST was not installed."
fi
