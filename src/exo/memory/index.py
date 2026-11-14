"""Índice semántico derivado (invariante 8): se puede borrar y reconstruir desde SQLite.

Los vectores viven en `observation_vectors` (float32, con el hash del contenido
que los generó). La configuración (proveedor, modelo, dimensión, permiso
remoto) vive en `meta`. Si el modelo devuelve otra dimensión que la guardada,
el motor exige `reindex` en lugar de mezclar vectores incompatibles.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from exo import _meta
from exo.memory import db
from exo.memory.backends import VectorBackend
from exo.memory.backends.python import pack
from exo.memory.embeddings import EmbeddingProvider, ProviderError
from exo.memory.model import MemoryStoreError

MAX_EMBED_CHARS = 2000
BATCH = 64
_TABLE = (
    "CREATE TABLE IF NOT EXISTS observation_vectors ("
    "id INTEGER PRIMARY KEY REFERENCES observations(id) ON DELETE CASCADE, "
    "content_hash TEXT NOT NULL, embedding BLOB NOT NULL)"
)
_KEYS = ("embedding_provider", "embedding_model", "embedding_dim", "embedding_allow_remote")


@dataclass(frozen=True)
class IndexConfig:
    provider: str
    model: str
    dim: int | None
    allow_remote: bool


def text_for(title: str, content: str) -> str:
    return f"{title}\n{content}"[:MAX_EMBED_CHARS]


def read_config(conn: sqlite3.Connection) -> IndexConfig | None:
    provider = db.get_meta(conn, "embedding_provider")
    if not provider or provider == "none":
        return None
    dim = db.get_meta(conn, "embedding_dim")
    return IndexConfig(
        provider=provider,
        model=db.get_meta(conn, "embedding_model") or "",
        dim=int(dim) if dim else None,
        allow_remote=db.get_meta(conn, "embedding_allow_remote") == "1",
    )


def write_config(conn: sqlite3.Connection, config: IndexConfig | None) -> None:
    """Dentro de una transacción de escritura."""
    if config is None:
        conn.execute(f"DELETE FROM meta WHERE key IN ({', '.join('?' * len(_KEYS))})", _KEYS)
        return
    db.set_meta(conn, "embedding_provider", config.provider)
    db.set_meta(conn, "embedding_model", config.model)
    db.set_meta(conn, "embedding_dim", str(config.dim or ""))
    db.set_meta(conn, "embedding_allow_remote", "1" if config.allow_remote else "0")


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(_TABLE)


class SemanticIndex:
    def __init__(
        self,
        provider: EmbeddingProvider,
        backend: VectorBackend,
        *,
        dim: int | None = None,
        config: IndexConfig | None = None,
    ) -> None:
        self.provider = provider
        self.backend = backend
        self.dim = dim
        # La config de `meta` con la que se abrió; None para un índice armado a mano (tests).
        self.config = config

    def matches(self, conn: sqlite3.Connection) -> bool:
        """El índice de la base sigue siendo este (otro proceso pudo hacer `reindex`)."""
        if self.config is None:
            return True
        current = read_config(conn)
        return (
            current is not None
            and (current.provider, current.model) == (self.config.provider, self.config.model)
            and (current.dim is None or self.dim is None or current.dim == self.dim)
        )

    @property
    def model_id(self) -> str:
        return f"{self.provider.name}:{self.provider.model}"

    def prepare(self, conn: sqlite3.Connection) -> None:
        """Carga el backend; si sqlite-vec no carga en este Python, usa el de Python."""
        try:
            self.backend.prepare(conn)
        except MemoryStoreError:
            from exo.memory.backends.python import PythonBackend

            self.backend = PythonBackend()
            self.backend.prepare(conn)
        ensure_table(conn)

    def vectors(self, texts: list[str]) -> list[bytes]:
        vectors = self.provider.embed(texts)
        dims = {len(v) for v in vectors}
        if len(dims) > 1 or (self.dim is not None and dims and dims != {self.dim}):
            raise ProviderError(
                f"model {self.model_id} returned vectors of dimension {sorted(dims)} but the "
                f"index uses {self.dim}; run `{_meta.NAME} mem reindex`"
            )
        if dims and self.dim is None:
            self.dim = dims.pop()
        return [pack(v) for v in vectors]

    def upsert(self, conn: sqlite3.Connection, obs_id: int, content_hash: str, blob: bytes) -> None:
        conn.execute(
            "INSERT INTO observation_vectors (id, content_hash, embedding) VALUES (?, ?, ?) "
            "ON CONFLICT (id) DO UPDATE SET content_hash = excluded.content_hash, "
            "embedding = excluded.embedding",
            (obs_id, content_hash, blob),
        )

    def nearest(
        self, conn: sqlite3.Connection, blob: bytes, where: str, args: list[Any], k: int
    ) -> list[tuple[int, float]]:
        rows = conn.execute(
            f"SELECT o.id, {self.backend.distance}(v.embedding, ?) AS distance "
            "FROM observation_vectors v JOIN observations o ON o.id = v.id "
            f"WHERE {where} AND v.content_hash = o.content_hash "
            "AND length(v.embedding) = ? "
            "ORDER BY distance, o.id LIMIT ?",
            (blob, *args, len(blob), k),
        ).fetchall()
        return [
            (int(row["id"]), float(row["distance"])) for row in rows if row["distance"] is not None
        ]

    def missing(self, conn: sqlite3.Connection) -> int:
        """Observaciones sin vector, o con un vector de otro contenido."""
        config = read_config(conn)
        size = 4 * (config.dim or self.dim or 0) if config else 4 * (self.dim or 0)
        row = conn.execute(
            "SELECT count(*) FROM observations o LEFT JOIN observation_vectors v ON v.id = o.id "
            "WHERE v.id IS NULL OR v.content_hash != o.content_hash "
            "OR (? > 0 AND length(v.embedding) != ?)",
            (size, size),
        ).fetchone()
        return int(row[0])

    def rebuild(
        self,
        conn: sqlite3.Connection,
        config: IndexConfig,
        *,
        progress: Callable[[int, int], None] | None = None,
    ) -> int:
        """Calcula todos los vectores (fuera del lock) y los escribe en una transacción."""
        rows = conn.execute("SELECT id, title, content, content_hash FROM observations").fetchall()
        computed: list[tuple[int, str, bytes]] = []
        for start in range(0, len(rows), BATCH):
            chunk = rows[start : start + BATCH]
            blobs = self.vectors([text_for(r["title"], r["content"]) for r in chunk])
            computed.extend(
                (r["id"], r["content_hash"], b) for r, b in zip(chunk, blobs, strict=True)
            )
            if progress is not None:
                progress(len(computed), len(rows))
        with db.write(conn):
            ensure_table(conn)
            conn.execute("DELETE FROM observation_vectors")
            conn.executemany(
                "INSERT INTO observation_vectors (id, content_hash, embedding) "
                "SELECT ?, ?, ? WHERE EXISTS (SELECT 1 FROM observations WHERE id = ?)",
                [(obs_id, digest, blob, obs_id) for obs_id, digest, blob in computed],
            )
            self.config = IndexConfig(
                config.provider, config.model, self.dim or config.dim, config.allow_remote
            )
            write_config(conn, self.config)
        return len(computed)
