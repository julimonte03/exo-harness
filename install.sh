#!/bin/sh
# Installs the exo engine from this clone (Linux and macOS).
#
# Requires Python 3.10 or later. With uv it uses `uv tool install`; otherwise it
# creates a venv in the user data folder and puts `exo` in ~/.local/bin (if another
# `exo` is already there, it is left alone; uv does the same). Adds that directory
# to the PATH if missing, and says so: in ~/.profile, in ~/.bash_profile if it
# exists, in ~/.bashrc if you use bash and in ~/.zshrc if you use zsh. Runs
# `exo doctor` and, with --init, adopts a project. Running it again updates it.
#
# Usage: ./install.sh [--init DIR] [--with-vector] [--no-path]
# Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1.
set -eu

REPO=$(cd "$(dirname "$0")" && pwd)
DIST=exo-harness
INIT=""
WITH_VECTOR=0
NO_PATH=${EXO_INSTALL_NO_PATH:-0}
MARK="# added by $DIST"

while [ $# -gt 0 ]; do
    case "$1" in
        --init) INIT="$2"; shift 2 ;;
        --with-vector) WITH_VECTOR=1; shift ;;
        --no-path) NO_PATH=1; shift ;;
        -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

SPEC="$REPO"
[ "$WITH_VECTOR" = 1 ] && SPEC="$REPO[vector]"

data_dir() {
    if [ -n "${EXO_DATA_DIR:-}" ]; then echo "$EXO_DATA_DIR"
    elif [ "$(uname -s)" = Darwin ]; then echo "$HOME/Library/Application Support/$DIST"
    else echo "${XDG_DATA_HOME:-$HOME/.local/share}/$DIST"
    fi
}

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
            echo "$candidate"; return 0
        fi
    done
    echo "Python 3.10 or later not found; install it with the system package manager." >&2
    return 1
}

# Agrega la línea del PATH a un archivo de inicio del shell, una sola vez. Anota
# los archivos que crea, para que uninstall.sh borre solo esos si quedan vacíos.
add_path_line() {
    line="export PATH=\"$BIN_DIR:\$PATH\" $MARK"
    if grep -qsF "$line" "$1"; then
        return 0
    fi
    if [ ! -e "$1" ]; then
        printf '%s\n' "$1" >> "$DATA_DIR/path-created.txt"
    fi
    if [ -s "$1" ] && [ -n "$(tail -c 1 "$1")" ]; then
        printf '\n' >> "$1"
    fi
    printf '%s\n' "$line" >> "$1"
    echo "Added $BIN_DIR to the PATH in $1."
}

DATA_DIR=$(data_dir)
if command -v uv >/dev/null 2>&1 && [ "${EXO_INSTALL_NO_UV:-0}" != 1 ]; then
    echo "Installing $DIST with uv tool..."
    # Sin --force: si ya hay otro exo en el directorio de uv, uv no lo pisa (ADR-0001).
    uv tool install --reinstall "$SPEC"
    BIN_DIR=$(uv tool dir --bin)
else
    VENV="$DATA_DIR/venv"
    BIN_DIR="$HOME/.local/bin"
    LINK="$BIN_DIR/exo"
    # ADR-0001: hay otra herramienta que se llama exo. No se pisa nada que no sea nuestro.
    if [ -e "$LINK" ] || [ -L "$LINK" ]; then
        if [ "$(readlink "$LINK" 2>/dev/null || true)" != "$VENV/bin/exo" ]; then
            echo "$LINK already exists and does not belong to this engine (another tool called exo?)." >&2
            echo "Move or delete it and retry." >&2
            exit 1
        fi
    fi
    PY=$(find_python)
    echo "Installing $DIST into $VENV..."
    if ! "$PY" -m venv "$VENV"; then
        echo "Could not create the venv: install the python3-venv package or install uv." >&2
        exit 1
    fi
    "$VENV/bin/python" -m pip install --upgrade --quiet --disable-pip-version-check "$SPEC"
    mkdir -p "$BIN_DIR"
    ln -sf "$VENV/bin/exo" "$LINK"
fi

EXE="$BIN_DIR/exo"
[ -x "$EXE" ] || { echo "The installation did not produce $EXE" >&2; exit 1; }

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        if [ "$NO_PATH" != 1 ]; then
            mkdir -p "$DATA_DIR"
            add_path_line "$HOME/.profile"
            if [ -f "$HOME/.bash_profile" ]; then
                add_path_line "$HOME/.bash_profile"
            fi
            # Las terminales de los escritorios Linux abren bash sin login: leen ~/.bashrc.
            case "${SHELL:-}" in
                *bash) add_path_line "$HOME/.bashrc" ;;
                *) if [ -f "$HOME/.bashrc" ]; then add_path_line "$HOME/.bashrc"; fi ;;
            esac
            case "${SHELL:-}" in
                *zsh) add_path_line "$HOME/.zshrc" ;;
                *) if [ -f "$HOME/.zshrc" ]; then add_path_line "$HOME/.zshrc"; fi ;;
            esac
            printf '%s\n' "$BIN_DIR" > "$DATA_DIR/path-entry.txt"
            echo "Open a new terminal to use 'exo'."
        fi
        ;;
esac

"$EXE" doctor
if [ -n "$INIT" ]; then
    "$EXE" init --project "$INIT" --yes
fi
echo "Done: $EXE"
