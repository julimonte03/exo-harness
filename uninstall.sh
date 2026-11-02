#!/bin/sh
# Desinstala el motor exo de esta máquina (Linux y macOS). No toca los proyectos:
# para quitarlo de un proyecto, corré `exo uninstall` dentro de ese proyecto.
# Variables: EXO_DATA_DIR, EXO_INSTALL_NO_UV=1 (las mismas que install.sh).
set -eu

DIST=exo-harness
REMOVED=0

data_dir() {
    if [ -n "${EXO_DATA_DIR:-}" ]; then echo "$EXO_DATA_DIR"
    elif [ "$(uname -s)" = Darwin ]; then echo "$HOME/Library/Application Support/$DIST"
    else echo "${XDG_DATA_HOME:-$HOME/.local/share}/$DIST"
    fi
}

if command -v uv >/dev/null 2>&1 && [ "${EXO_INSTALL_NO_UV:-0}" != 1 ]; then
    if uv tool list 2>/dev/null | grep -q "^$DIST "; then
        uv tool uninstall "$DIST"
        REMOVED=1
    fi
fi

VENV="$(data_dir)/venv"
if [ -d "$VENV" ]; then
    rm -rf "$VENV"
    REMOVED=1
    LINK="$HOME/.local/bin/exo"
    if [ -L "$LINK" ] && [ "$(readlink "$LINK")" = "$VENV/bin/exo" ]; then
        rm -f "$LINK"
    fi
fi

if [ "$REMOVED" = 1 ]; then
    echo "Desinstalado $DIST. Los backups de desinstalación de proyectos quedan en $(data_dir)."
else
    echo "$DIST no estaba instalado."
fi
