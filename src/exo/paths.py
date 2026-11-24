"""Rutas de usuario del motor (ADR-0001).

Nunca la carpeta oculta con el nombre del motor en el home: la usa otro proyecto
con el mismo nombre.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from exo import _meta

ENV_DATA_DIR = f"{_meta.ENV_PREFIX}DATA_DIR"
ENV_MEMORY_DB = f"{_meta.ENV_PREFIX}MEMORY_DB"
MEMORY_DB_NAME = "memory.db"
# Solo el dueño, en POSIX (threat model, TM-27): la memoria va sin redactar (ADR-0009).
PRIVATE_DIR = 0o700
PRIVATE_FILE = 0o600


def private_dir(path: Path) -> Path:
    """Crea `path` y las carpetas que le falten, en `PRIVATE_DIR` en POSIX.

    No cambia los permisos de una carpeta que ya existe: puede no ser del motor (una
    `<ENV_PREFIX>DATA_DIR` elegida por la persona); `exo doctor` avisa si la de datos la
    leen otros. En Windows, `%LOCALAPPDATA%` ya es por usuario.
    """
    path = Path(path)
    if os.name == "nt":
        path.mkdir(parents=True, exist_ok=True)
        return path
    missing: list[Path] = []
    current = path
    while not current.exists() and current != current.parent:
        missing.append(current)
        current = current.parent
    for folder in reversed(missing):
        try:
            os.mkdir(folder, PRIVATE_DIR)
            os.chmod(folder, PRIVATE_DIR)  # el umask no recorta: queda exactamente 0700
        except FileExistsError:
            pass
    return path


def user_data_dir() -> Path:
    """Carpeta de datos del usuario: memoria (F3), backups de desinstalación, venv del instalador.

    - Windows: %LOCALAPPDATA%/<USER_DIR_NAME>
    - macOS: ~/Library/Application Support/<USER_DIR_NAME>
    - Linux y otros: $XDG_DATA_HOME/<USER_DIR_NAME> o ~/.local/share/<USER_DIR_NAME>

    La variable `<ENV_PREFIX>DATA_DIR` la reemplaza (tests, instalaciones portables).
    """
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / _meta.USER_DIR_NAME


def memory_db_path() -> Path:
    """Base de la memoria (F3, ADR-0009): una por usuario, en la carpeta de datos.

    La variable `<ENV_PREFIX>MEMORY_DB` la reemplaza.
    """
    override = os.environ.get(ENV_MEMORY_DB)
    if override:
        return Path(override).expanduser()
    return user_data_dir() / MEMORY_DB_NAME
