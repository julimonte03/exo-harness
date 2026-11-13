"""Backend sqlite-vec (extra `[vector]`): `vec_distance_cosine` en C, en la misma base.

Algunos Python (por ejemplo builds de sistema en macOS) no permiten cargar
extensiones de SQLite; entonces `available()` es falso y se usa el backend de
Python. `exo doctor` lo explica.
"""

from __future__ import annotations

import importlib.util
import sqlite3

from exo.memory.model import MemoryStoreError


def installed() -> bool:
    return importlib.util.find_spec("sqlite_vec") is not None


def can_load_extensions() -> bool:
    return hasattr(sqlite3.Connection, "enable_load_extension")


def available() -> bool:
    return installed() and can_load_extensions()


class SqliteVecBackend:
    name = "sqlite-vec"
    distance = "vec_distance_cosine"

    def prepare(self, conn: sqlite3.Connection) -> None:
        import sqlite_vec

        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except (AttributeError, sqlite3.Error) as exc:
            raise MemoryStoreError(f"no se pudo cargar sqlite-vec ({exc})") from exc
