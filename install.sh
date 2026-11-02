#!/bin/sh
# Instala el motor exo desde este clon (Linux y macOS).
#
# Verifica Python 3.10 o más. Con uv usa `uv tool install`; si no, crea un venv
# en la carpeta de datos de usuario y deja `exo` en ~/.local/bin. Agrega ese
# directorio al PATH si falta (avisando), corre `exo doctor` y, con --init,
# adopta un proyecto. Re-ejecutarlo actualiza la instalación.
#
# Uso: ./install.sh [--init DIR] [--with-vector] [--no-path]
# Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1.
set -eu

REPO=$(cd "$(dirname "$0")" && pwd)
DIST=exo-harness
INIT=""
WITH_VECTOR=0
NO_PATH=${EXO_INSTALL_NO_PATH:-0}

while [ $# -gt 0 ]; do
    case "$1" in
        --init) INIT="$2"; shift 2 ;;
        --with-vector) WITH_VECTOR=1; shift ;;
        --no-path) NO_PATH=1; shift ;;
        -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
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

if command -v uv >/dev/null 2>&1 && [ "${EXO_INSTALL_NO_UV:-0}" != 1 ]; then
    echo "Instalando $DIST con uv tool..."
    uv tool install --force --reinstall "$SPEC"
    BIN_DIR=$(uv tool dir --bin)
else
    PY=$(find_python)
    VENV="$(data_dir)/venv"
    echo "Instalando $DIST en $VENV..."
    if ! "$PY" -m venv "$VENV"; then
        echo "No pude crear el venv: instalá el paquete python3-venv o instalá uv." >&2
        exit 1
    fi
    "$VENV/bin/python" -m pip install --upgrade --quiet --disable-pip-version-check "$SPEC"
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
    ln -sf "$VENV/bin/exo" "$BIN_DIR/exo"
fi

EXE="$BIN_DIR/exo"
[ -x "$EXE" ] || { echo "La instalación no dejó $EXE" >&2; exit 1; }

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        if [ "$NO_PATH" != 1 ]; then
            LINE="export PATH=\"$BIN_DIR:\$PATH\""
            if ! grep -qsF "$LINE" "$HOME/.profile"; then
                printf '\n# Agregado por el instalador de %s\n%s\n' "$DIST" "$LINE" >> "$HOME/.profile"
                echo "Agregué $BIN_DIR al PATH en ~/.profile. Abrí una terminal nueva para usar 'exo'."
            fi
        fi
        ;;
esac

"$EXE" doctor
if [ -n "$INIT" ]; then
    "$EXE" init --project "$INIT" --yes
fi
echo "Listo: $EXE"
