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
