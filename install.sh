#!/bin/sh
# Instala el motor exo desde este clon (Linux y macOS).
#
# Verifica Python 3.10 o más. Con uv usa `uv tool install`; si no, crea un venv
# en la carpeta de datos de usuario y deja `exo` en ~/.local/bin (si ahí ya hay
# otro `exo`, no lo pisa). Agrega ese directorio al PATH si falta, avisando: en
# ~/.profile, en ~/.bash_profile si existe y en ~/.zshrc si usás zsh. Corre
# `exo doctor` y, con --init, adopta un proyecto. Re-ejecutarlo actualiza.
#
# Uso: ./install.sh [--init DIR] [--with-vector] [--no-path]
# Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1.
set -eu

REPO=$(cd "$(dirname "$0")" && pwd)
DIST=exo-harness
INIT=""
WITH_VECTOR=0
NO_PATH=${EXO_INSTALL_NO_PATH:-0}
MARK="# agregado por $DIST"

while [ $# -gt 0 ]; do
    case "$1" in
        --init) INIT="$2"; shift 2 ;;
        --with-vector) WITH_VECTOR=1; shift ;;
        --no-path) NO_PATH=1; shift ;;
        -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
        *) echo "opción desconocida: $1" >&2; exit 2 ;;
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
    echo "No encontré Python 3.10 o más; instalalo con el gestor de paquetes del sistema." >&2
    return 1
}

# Agrega la línea del PATH a un archivo de inicio del shell, una sola vez.
add_path_line() {
    line="export PATH=\"$BIN_DIR:\$PATH\" $MARK"
    if grep -qsF "$line" "$1"; then
        return 0
    fi
    if [ -s "$1" ] && [ -n "$(tail -c 1 "$1")" ]; then
        printf '\n' >> "$1"
    fi
    printf '%s\n' "$line" >> "$1"
    echo "Agregué $BIN_DIR al PATH en $1."
}

DATA_DIR=$(data_dir)
if command -v uv >/dev/null 2>&1 && [ "${EXO_INSTALL_NO_UV:-0}" != 1 ]; then
    echo "Instalando $DIST con uv tool..."
    uv tool install --force --reinstall "$SPEC"
    BIN_DIR=$(uv tool dir --bin)
else
    VENV="$DATA_DIR/venv"
    BIN_DIR="$HOME/.local/bin"
    LINK="$BIN_DIR/exo"
    # ADR-0001: hay otra herramienta que se llama exo. No se pisa nada que no sea nuestro.
    if [ -e "$LINK" ] || [ -L "$LINK" ]; then
        if [ "$(readlink "$LINK" 2>/dev/null || true)" != "$VENV/bin/exo" ]; then
            echo "Ya existe $LINK y no es de este motor (¿otra herramienta llamada exo?)." >&2
            echo "Movelo o borralo y repetí, o instalá uv para usar 'uv tool install'." >&2
            exit 1
        fi
    fi
    PY=$(find_python)
    echo "Instalando $DIST en $VENV..."
    if ! "$PY" -m venv "$VENV"; then
        echo "No pude crear el venv: instalá el paquete python3-venv o instalá uv." >&2
        exit 1
    fi
    "$VENV/bin/python" -m pip install --upgrade --quiet --disable-pip-version-check "$SPEC"
    mkdir -p "$BIN_DIR"
    ln -sf "$VENV/bin/exo" "$LINK"
fi

EXE="$BIN_DIR/exo"
[ -x "$EXE" ] || { echo "La instalación no dejó $EXE" >&2; exit 1; }

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        if [ "$NO_PATH" != 1 ]; then
            add_path_line "$HOME/.profile"
            if [ -f "$HOME/.bash_profile" ]; then
                add_path_line "$HOME/.bash_profile"
            fi
            case "${SHELL:-}" in
                *zsh) add_path_line "$HOME/.zshrc" ;;
                *) if [ -f "$HOME/.zshrc" ]; then add_path_line "$HOME/.zshrc"; fi ;;
            esac
            mkdir -p "$DATA_DIR"
            printf '%s\n' "$BIN_DIR" > "$DATA_DIR/path-entry.txt"
            echo "Abrí una terminal nueva para usar 'exo'."
        fi
        ;;
esac

"$EXE" doctor
if [ -n "$INIT" ]; then
    "$EXE" init --project "$INIT" --yes
fi
echo "Listo: $EXE"
