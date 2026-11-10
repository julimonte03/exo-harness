#!/bin/sh
# Desinstala el motor exo de esta máquina (Linux y macOS). No toca los proyectos:
# para quitarlo de un proyecto, corré `exo uninstall` dentro de ese proyecto.
#
# Quita las líneas del PATH que agregó install.sh, solo si ese directorio quedó
# vacío (~/.local/bin o el de uv pueden tener otras herramientas).
# Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1 (las mismas
# que install.sh).
set -eu

DIST=exo-harness
REMOVED=0
NO_PATH=${EXO_INSTALL_NO_PATH:-0}
MARK="# agregado por $DIST"

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
        echo "Quité $ADDED del PATH."
    else
        echo "Dejo $ADDED en el PATH: tiene otras herramientas."
    fi
    rm -f "$MARKER" "$CREATED"
fi

if [ "$REMOVED" = 1 ]; then
    echo "Desinstalado $DIST. Los backups de desinstalación de proyectos quedan en $DATA_DIR."
else
    echo "$DIST no estaba instalado."
fi
