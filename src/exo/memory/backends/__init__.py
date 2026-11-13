"""Backends del índice vectorial derivado (ADR-0009: solo SQLite).

Los vectores viven en la misma base, en `observation_vectors`, como blobs
float32. Un backend solo aporta la función SQL de distancia coseno; así la
búsqueda semántica filtra por proyecto, scope y tipo **antes** de rankear,
con el mismo SQL para los dos:

- `sqlite-vec`: la extensión (extra `[vector]`), `vec_distance_cosine` en C.
- `python`: la misma función en Python puro. Sirve para los tests y para bases
  chicas cuando falta la extensión; `exo doctor` avisa que es lenta.
"""

from __future__ import annotations

import sqlite3
from typing import Protocol


class VectorBackend(Protocol):
    name: str
    distance: str  # nombre de la función SQL: distancia coseno entre dos blobs float32

    def prepare(self, conn: sqlite3.Connection) -> None: ...


def create(prefer: str = "sqlite-vec") -> VectorBackend:
    """El backend pedido si se puede cargar; si no, el de Python."""
    from exo.memory.backends.python import PythonBackend

    if prefer == "sqlite-vec":
        from exo.memory.backends.sqlite_vec import SqliteVecBackend, available

        if available():
            return SqliteVecBackend()
    return PythonBackend()
