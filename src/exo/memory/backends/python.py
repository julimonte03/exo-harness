"""Distancia coseno en Python puro, registrada como función de SQLite."""

from __future__ import annotations

import math
import sqlite3
import struct


def unpack(blob: bytes) -> tuple[float, ...]:
    return struct.unpack(f"<{len(blob) // 4}f", blob)


def pack(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def cosine_distance(a: bytes, b: bytes) -> float | None:
    x, y = unpack(a), unpack(b)
    if len(x) != len(y):
        return None
    dot = sum(p * q for p, q in zip(x, y, strict=True))
    norm = math.sqrt(sum(p * p for p in x)) * math.sqrt(sum(q * q for q in y))
    return 1.0 - dot / norm if norm else 1.0


class PythonBackend:
    name = "python"
    distance = "exo_cosine_distance"

    def prepare(self, conn: sqlite3.Connection) -> None:
        conn.create_function(self.distance, 2, cosine_distance, deterministic=True)
