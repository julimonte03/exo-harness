"""Store de la memoria: SQLite como fuente de verdad (invariante 8).

- `save` hace upsert por `(proyecto, topic_key)`; sin `topic_key`, no duplica
  un contenido idéntico del mismo proyecto.
- Las observaciones `personal` no tienen proyecto (`""`) y se ven desde todos.
- `search` aplica los filtros antes de rankear y devuelve previews; `get`
  devuelve el contenido completo (recuperación en dos pasos, §5.6 del reporte).
- Búsqueda léxica: FTS5 con BM25. Sin FTS5 (algunos Python lo traen
  deshabilitado) se rankea en Python, con la misma tokenización.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exo import _meta, paths
from exo.memory import db
from exo.memory.model import (
    MAX_CONTENT,
    MAX_TITLE,
    Hit,
    MemoryStoreError,
    NotFoundError,
    Observation,
    SaveResult,
    check_project,
    check_scope,
    check_text,
    check_topic_key,
    check_type,
    preview,
)

__all__ = ["MemoryStore", "MemoryStoreError", "NotFoundError"]

MAX_LIMIT = 100
CONTEXT_CHARS = 8000
_WORD = re.compile(r"[^\W_]+")
# Pesos de BM25 por columna: título, contenido, topic_key.
_BM25 = "bm25(observations_fts, 4.0, 1.0, 2.0)"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def tokens(text: str) -> list[str]:
    """Tokens como los de FTS5 `unicode61 remove_diacritics 2`: alfanuméricos, sin acentos."""
    return _WORD.findall(_fold(text))


def terms(query: str) -> list[tuple[str, ...]]:
    """Términos de una consulta: cada palabra es un término; si tiene separadores
    internos (`PROJ-1234`, `UserService.save`), es una frase."""
    found = []
    for word in query.split():
        parts = tuple(tokens(word))
        if parts and parts not in found:
            found.append(parts)
    return found


def _fts_query(found: list[tuple[str, ...]]) -> str:
    return " OR ".join('"' + " ".join(parts) + '"' for parts in found)


def _contains(haystack: list[str], phrase: tuple[str, ...]) -> bool:
    n = len(phrase)
    return any(tuple(haystack[i : i + n]) == phrase for i in range(len(haystack) - n + 1))


def _hash(kind: str, title: str, content: str) -> str:
    return hashlib.sha256(f"{kind}\n{title}\n{content}".encode()).hexdigest()


_FIELDS = tuple(Observation.__dataclass_fields__)


def _observation(row: sqlite3.Row) -> Observation:
    return Observation(**{name: row[name] for name in _FIELDS})


def _hit(row: sqlite3.Row, score: float) -> Hit:
    return Hit(
        id=row["id"],
        project=row["project"],
        scope=row["scope"],
        type=row["type"],
        title=row["title"],
        topic_key=row["topic_key"],
        preview=preview(row["content"]),
        updated_at=row["updated_at"],
        score=score,
    )


class MemoryStore:
    """Abre (y crea o migra) la base. `fts=None` detecta FTS5; `False` lo fuerza apagado."""

    def __init__(self, path: Path | None = None, *, fts: bool | None = None) -> None:
        self.path = Path(path) if path is not None else paths.memory_db_path()
        self.conn = db.connect(self.path)
        available = db.fts5_available(self.conn)
        if fts and not available:
            self.conn.close()
            raise MemoryStoreError("este Python no trae FTS5; usá otro o fts=False")
        self.fts = available if fts is None else fts
        try:
            had_index = self._has_fts_table()
            db.migrate(self.conn, fts=self.fts)
            if self.fts and (not had_index or db.get_meta(self.conn, "fts_stale") == "1"):
                self.rebuild_fts()
        except BaseException:
            self.conn.close()
            raise

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    # -- índice léxico (derivado) -------------------------------------------------------

    def _has_fts_table(self) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'observations_fts'"
        ).fetchone()
        return row is not None

    def rebuild_fts(self) -> int:
        """Reconstruye el índice FTS5 desde las observaciones. Devuelve cuántas indexó."""
        if not self.fts:
            raise MemoryStoreError("FTS5 no está disponible en este Python")
        with db.write(self.conn):
            self.conn.execute("DELETE FROM observations_fts")
            self.conn.execute(
                "INSERT INTO observations_fts (rowid, title, content, topic_key) "
                "SELECT id, title, content, coalesce(topic_key, '') FROM observations"
            )
            db.set_meta(self.conn, "fts_stale", "0")
        return int(self.conn.execute("SELECT count(*) FROM observations").fetchone()[0])

    def _index(self, obs_id: int, title: str, content: str, topic_key: str | None) -> None:
        if not self.fts:
            db.set_meta(self.conn, "fts_stale", "1")
            return
        self.conn.execute("DELETE FROM observations_fts WHERE rowid = ?", (obs_id,))
        self.conn.execute(
            "INSERT INTO observations_fts (rowid, title, content, topic_key) VALUES (?, ?, ?, ?)",
            (obs_id, title, content, topic_key or ""),
        )

    def _unindex(self, obs_id: int) -> None:
        if not self.fts:
            db.set_meta(self.conn, "fts_stale", "1")
            return
        self.conn.execute("DELETE FROM observations_fts WHERE rowid = ?", (obs_id,))

    # -- escritura ------------------------------------------------------------------------

    def save(
        self,
        *,
        project: str,
        title: str,
        content: str,
        type: str = "note",
        topic_key: str | None = None,
        scope: str = "project",
        session_id: int | None = None,
    ) -> SaveResult:
        scope = check_scope(scope)
        project = "" if scope == "personal" else check_project(project)
        title = check_text("title", title.strip(), MAX_TITLE)
        content = check_text("content", content, MAX_CONTENT)
        kind = check_type(type)
        topic_key = check_topic_key(topic_key)
        digest = _hash(kind, title, content)
        stamp = now()
        with db.write(self.conn):
            if topic_key is not None:
                row = self.conn.execute(
                    "SELECT id, content_hash FROM observations WHERE project = ? AND topic_key = ?",
                    (project, topic_key),
                ).fetchone()
            else:
                row = self.conn.execute(
                    "SELECT id, content_hash FROM observations "
                    "WHERE project = ? AND topic_key IS NULL AND content_hash = ?",
                    (project, digest),
                ).fetchone()
            if row is not None and row["content_hash"] == digest:
                return SaveResult(row["id"], "unchanged")
            if row is not None:
                self.conn.execute(
                    "UPDATE observations SET type = ?, title = ?, content = ?, scope = ?, "
                    "session_id = coalesce(?, session_id), content_hash = ?, "
                    "revision = revision + 1, updated_at = ? WHERE id = ?",
                    (kind, title, content, scope, session_id, digest, stamp, row["id"]),
                )
                self._index(row["id"], title, content, topic_key)
                return SaveResult(row["id"], "updated")
            cursor = self.conn.execute(
                "INSERT INTO observations (project, scope, type, title, content, topic_key, "
                "session_id, content_hash, revision, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                (project, scope, kind, title, content, topic_key, session_id, digest, stamp, stamp),
            )
            obs_id = int(cursor.lastrowid or 0)
            self._index(obs_id, title, content, topic_key)
        return SaveResult(obs_id, "created")

    def delete(self, obs_id: int) -> bool:
        with db.write(self.conn):
            cursor = self.conn.execute("DELETE FROM observations WHERE id = ?", (obs_id,))
            if cursor.rowcount:
                self._unindex(obs_id)
        return bool(cursor.rowcount)

    # -- lectura --------------------------------------------------------------------------

    def get(self, obs_id: int) -> Observation:
        row = self.conn.execute("SELECT * FROM observations WHERE id = ?", (obs_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"no existe la observación {obs_id}")
        return _observation(row)

    @staticmethod
    def _filters(
        project: str | None, kind: str | None, scope: str | None, alias: str = ""
    ) -> tuple[str, list[Any]]:
        """WHERE de los filtros. Con proyecto, también entran las personales (salvo scope)."""
        prefix = f"{alias}." if alias else ""
        clauses: list[str] = []
        args: list[Any] = []
        if project is not None:
            clauses.append(f"{prefix}project IN (?, '')")
            args.append(project)
        if scope is not None:
            clauses.append(f"{prefix}scope = ?")
            args.append(check_scope(scope))
        if kind is not None:
            clauses.append(f"{prefix}type = ?")
            args.append(kind)
        return (" AND ".join(clauses) or "1"), args

    @staticmethod
    def _limit(limit: int) -> int:
        if not 1 <= limit <= MAX_LIMIT:
            raise MemoryStoreError(f"limit tiene que estar entre 1 y {MAX_LIMIT}")
        return limit

    def list(
        self,
        project: str | None = None,
        *,
        type: str | None = None,
        scope: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Observation]:
        where, args = self._filters(project, type, scope)
        rows = self.conn.execute(
            f"SELECT * FROM observations WHERE {where} "
            "ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
            (*args, self._limit(limit), max(offset, 0)),
        ).fetchall()
        return [_observation(row) for row in rows]

    def search(
        self,
        query: str,
        *,
        project: str | None = None,
        type: str | None = None,
        scope: str | None = None,
        limit: int = 10,
    ) -> list[Hit]:
        """Búsqueda léxica. Cada palabra suma (OR); BM25 premia las raras y las del título."""
        limit = self._limit(limit)
        found = terms(query)
        if not found:
            return []
        if self.fts:
            where, args = self._filters(project, type, scope, alias="o")
            rows = self.conn.execute(
                f"SELECT o.*, {_BM25} AS rank FROM observations_fts "
                "JOIN observations o ON o.id = observations_fts.rowid "
                f"WHERE observations_fts MATCH ? AND {where} "
                "ORDER BY rank, o.updated_at DESC, o.id DESC LIMIT ?",
                (_fts_query(found), *args, limit),
            ).fetchall()
            return [_hit(row, -float(row["rank"])) for row in rows]
        return self._search_python(found, project, type, scope, limit)

    def _search_python(
        self,
        found: list[tuple[str, ...]],
        project: str | None,
        kind: str | None,
        scope: str | None,
        limit: int,
    ) -> list[Hit]:
        where, args = self._filters(project, kind, scope)
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in self.conn.execute(f"SELECT * FROM observations WHERE {where}", args):
            fields = (
                (4.0, tokens(row["title"])),
                (1.0, tokens(row["content"])),
                (2.0, tokens(row["topic_key"] or "")),
            )
            score = sum(
                weight for phrase in found for weight, toks in fields if _contains(toks, phrase)
            )
            if score:
                scored.append((score, row))
        scored.sort(key=lambda item: (item[0], item[1]["updated_at"], item[1]["id"]), reverse=True)
        return [_hit(row, score) for score, row in scored[:limit]]

    # -- contexto -------------------------------------------------------------------------

    def context(self, project: str, *, limit: int = 10, max_chars: int = CONTEXT_CHARS) -> str:
        """Contexto reciente del proyecto, para el inicio de una sesión del agente."""
        cli = _meta.NAME
        footer = (
            f"\nDetalle: `{cli} mem get <id>`. Buscá antes de resolver algo de nuevo: "
            f'`{cli} mem search "<texto>"`. Al cerrar la sesión, guardá un resumen: '
            f'`{cli} mem session summary --content "<qué se hizo y qué queda>"`.\n'
        )
        items = self.list(project, limit=self._limit(limit))
        if not items:
            return f"# Memoria de {project}: sin memorias todavía.\n{footer}"
        lines = [f"# Memoria de {project} (más recientes primero)\n"]
        for obs in items:
            key = f" · {obs.topic_key}" if obs.topic_key else ""
            line = f"- #{obs.id} [{obs.type}] {obs.title}{key}: {preview(obs.content, 160)}\n"
            if sum(map(len, lines)) + len(line) + len(footer) > max_chars:
                break
            lines.append(line)
        return "".join(lines) + footer
