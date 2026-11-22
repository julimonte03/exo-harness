#!/bin/sh
# Installs the exo engine on Linux and macOS: from this clone, or from GitHub when
# piped:
#
#   curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh | sh
#
# To read it before running it:
#
#   curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh -o install.sh
#   less install.sh
#   sh install.sh
#
# Options and variables: sh install.sh --help
set -eu

# Repo del motor (ADR-0017). EXO_REPO_URL lo cambia para probar contra un remoto
# simulado o para instalar desde un espejo.
EXO_REPO_URL=${EXO_REPO_URL:-https://github.com/julimonte03/exo-harness}
DIST=exo-harness
MARK="# added by $DIST"

usage() {
    cat <<'EOF'
Installs the exo engine (Linux and macOS).

Run from a clone, it installs that clone. Piped from curl, it installs from
GitHub: the latest release, or the tag, branch or commit in EXO_REF. With uv it
runs `uv tool install` from git (needs git). Without uv it creates a venv in the
user data folder and installs the release wheel after checking it against the
SHA256SUMS of the release (a branch or a commit installs from git); that needs
Python 3.10 or later.

It puts `exo` on the PATH if missing and says so: in ~/.profile, in
~/.bash_profile if it exists, in ~/.bashrc with bash and in ~/.zshrc with zsh.
If another `exo` is already installed, it stops without touching it. Then it
runs `exo doctor` and, with --init, adopts a project. Running it again updates
the installation.

Usage:
  sh install.sh [--init DIR] [--with-vector] [--no-path]
  curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh | sh -s -- [options]

Options:
  --init DIR      adopt the project in DIR after installing (exo init --yes)
  --with-vector   also install the semantic memory extra (sqlite-vec, FastEmbed)
  --no-path       leave the PATH alone

Variables:
  EXO_REF                tag, branch or commit to install when piped
                         (default: the latest release; main if there is none)
  EXO_REPO_URL           repository to install from when piped
                         (default: https://github.com/julimonte03/exo-harness)
  EXO_DATA_DIR           data folder (holds the venv when uv is not used)
  EXO_INSTALL_NO_PATH=1  same as --no-path
  EXO_INSTALL_NO_UV=1    do not use uv even if it is installed
EOF
}

die() {
    echo "$*" >&2
    exit 1
}

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

# El clon que contiene este script, o nada. Por pipe (`curl ... | sh`) $0 es el
# shell y no hay archivo; un install.sh bajado suelto no tiene el clon al lado.
clone_dir() {
    case "$0" in
        *.sh) ;;
        *) return 0 ;;
    esac
    [ -f "$0" ] || return 0
    dir=$(cd "$(dirname "$0")" && pwd)
    if [ -f "$dir/pyproject.toml" ] && [ -f "$dir/src/exo/_meta.py" ]; then
        echo "$dir"
    fi
}

# Solo https. file:// y http a 127.0.0.1 o localhost no salen de la máquina: sirven
# para un espejo local y para los tests. Sin @ (credenciales o un host disfrazado),
# ni ? o # que cambien la URL. Deja en SCHEME el protocolo permitido para bajar.
check_repo_url() {
    case "$EXO_REPO_URL" in
        *[!A-Za-z0-9._~:/%+-]*) die "EXO_REPO_URL has characters that are not allowed: $EXO_REPO_URL" ;;
    esac
    case "$EXO_REPO_URL" in
        https://?*) SCHEME=https ;;
        file:///?*) SCHEME=file ;;
        http://127.0.0.1/?* | http://127.0.0.1:[0-9]*/?* | http://localhost/?* | http://localhost:[0-9]*/?*)
            SCHEME=http ;;
        *) die "EXO_REPO_URL must be an https:// URL (got: $EXO_REPO_URL)." ;;
    esac
}

# Un tag, rama o commit que no cambie la URL ni el requisito de pip: sin espacios,
# comillas, @, # ni `..`.
check_ref() {
    case "$1" in
        '' | -* | *..* | *[!A-Za-z0-9._/+-]*)
            die "Not a valid tag, branch or commit: '$1'. Set EXO_REF to a release tag such as v1.0.0, or to a branch." ;;
    esac
}

# Baja $1 a $2. Con curl, solo por el protocolo de EXO_REPO_URL, también en las
# redirecciones; wget no tiene cómo restringirlas (su --https-only es para el modo
# recursivo), pero la URL inicial ya pasó por check_repo_url.
fetch() {
    if command -v curl >/dev/null 2>&1; then
        curl --proto "=$SCHEME" --proto-redir "=$SCHEME" -fsSL -o "$2" "$1"
    else
        wget -q -O "$2" "$1"
    fi
}

# Adónde redirige $1, sin seguir la redirección (con GET, como curl).
redirect_of() {
    if command -v curl >/dev/null 2>&1; then
        curl --proto "=$SCHEME" -fsS -o /dev/null -w '%{redirect_url}' "$1"
    else
        wget -S --max-redirect=0 -O /dev/null "$1" 2>&1 |
            sed -n 's/^ *[Ll]ocation: *\([^ ]*\).*/\1/p' | tr -d '\r' | tail -n 1
    fi
}

# El tag del último release, sin API ni token: <repo>/releases/latest redirige a
# <repo>/releases/tag/<tag>, o a <repo>/releases si todavía no hay ninguno.
latest_ref() {
    if ! location=$(redirect_of "$EXO_REPO_URL/releases/latest"); then
        die "Could not reach $EXO_REPO_URL to find the latest release. Check the connection, or set EXO_REF to a tag or a branch."
    fi
    case "$location" in
        */releases/tag/?*) echo "${location##*/releases/tag/}" ;;
        */releases | */releases/)
            echo "$EXO_REPO_URL has no releases yet: installing the main branch." >&2
            echo main ;;
        *) die "Unexpected answer from $EXO_REPO_URL/releases/latest. Set EXO_REF to a tag or a branch." ;;
    esac
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d ' ' -f 1
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 -r "$1" | cut -d ' ' -f 1
    else
        die "sha256sum, shasum or openssl is required to verify the download."
    fi
}

# Baja el wheel del release $1 (cuyo SHA256SUMS ya está en $TMP) y lo verifica contra
# ese SHA256SUMS. Deja su ruta en WHEEL. Si no coincide, no instala nada.
verified_wheel() {
    lines=$(tr -d '\r' < "$TMP/SHA256SUMS" |
        grep -E '^[0-9A-Fa-f]{64} [ *][A-Za-z0-9._+-]+\.whl$' || true)
    count=$(printf '%s\n' "$lines" | grep -c . || true)
    if [ "$count" != 1 ]; then
        die "The SHA256SUMS of release $1 should list exactly one wheel; it lists $count."
    fi
    expected=$(printf '%s\n' "$lines" | cut -c 1-64 | tr 'A-F' 'a-f')
    name=$(printf '%s\n' "$lines" | cut -c 67-)
    echo "Downloading $name from release $1..."
    fetch "$EXO_REPO_URL/releases/download/$1/$name" "$TMP/$name" ||
        die "Could not download $EXO_REPO_URL/releases/download/$1/$name."
    actual=$(sha256_of "$TMP/$name" | tr 'A-F' 'a-f')
    if [ "$actual" != "$expected" ]; then
        die "Checksum mismatch for $name: SHA256SUMS says $expected, the download is $actual. Nothing was installed; retry, and report it if it happens again."
    fi
    echo "Verified $name against SHA256SUMS."
    WHEEL="$TMP/$name"
}

# Qué instalar cuando no hay clon (por pipe). Deja el requisito en SPEC.
remote_spec() {
    check_repo_url
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        die "curl or wget is required to install from $EXO_REPO_URL."
    fi
    if [ -n "${EXO_REF:-}" ]; then
        REF=$EXO_REF
    else
        REF=$(latest_ref)
    fi
    check_ref "$REF"
    # Sin uv, el wheel del release, verificado. Una rama o un commit no tienen
    # SHA256SUMS en releases/download: se instalan desde git.
    if [ "$USE_UV" = 0 ]; then
        TMP=$(mktemp -d 2>/dev/null || mktemp -d -t "$DIST")
        if fetch "$EXO_REPO_URL/releases/download/$REF/SHA256SUMS" "$TMP/SHA256SUMS" 2>/dev/null; then
            verified_wheel "$REF"
            SPEC="$WHEEL$EXTRAS"
            return 0
        fi
    fi
    if ! command -v git >/dev/null 2>&1; then
        if [ "$USE_UV" = 1 ]; then
            die "git is required to install $REF with uv. Install git, or set EXO_INSTALL_NO_UV=1 to install the release wheel with pip."
        fi
        die "git is required to install $REF, which is not a release. Install git, or set EXO_REF to a release tag."
    fi
    echo "Installing $DIST from $EXO_REPO_URL at $REF..."
    SPEC="$DIST$EXTRAS @ git+$EXO_REPO_URL@$REF"
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

cleanup() {
    if [ -n "$TMP" ]; then
        rm -rf "$TMP"
        TMP=""
    fi
}

# Todo corre desde main, en la última línea: si la descarga por pipe se corta, el
# shell no llega a ejecutar un script a medias.
main() {
    INIT=""
    WITH_VECTOR=0
    NO_PATH=${EXO_INSTALL_NO_PATH:-0}
    while [ $# -gt 0 ]; do
        case "$1" in
            --init)
                [ $# -ge 2 ] || die "--init needs a directory."
                INIT="$2"; shift 2 ;;
            --with-vector) WITH_VECTOR=1; shift ;;
            --no-path) NO_PATH=1; shift ;;
            -h | --help) usage; exit 0 ;;
            *) echo "unknown option: $1" >&2; exit 2 ;;
        esac
    done

    EXTRAS=""
    if [ "$WITH_VECTOR" = 1 ]; then
        EXTRAS="[vector]"
    fi
    USE_UV=0
    if command -v uv >/dev/null 2>&1 && [ "${EXO_INSTALL_NO_UV:-0}" != 1 ]; then
        USE_UV=1
    fi
    DATA_DIR=$(data_dir)
    TMP=""
    trap cleanup EXIT
    trap 'exit 130' INT TERM

    REPO=$(clone_dir)
    if [ -n "$REPO" ]; then
        if [ -n "${EXO_REF:-}" ]; then
            echo "EXO_REF is ignored: installing the clone in $REPO."
        fi
        SPEC="$REPO$EXTRAS"
    else
        remote_spec
    fi

    if [ "$USE_UV" = 1 ]; then
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
    cleanup

    EXE="$BIN_DIR/exo"
    [ -x "$EXE" ] || die "The installation did not produce $EXE"

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
}

main "$@"
