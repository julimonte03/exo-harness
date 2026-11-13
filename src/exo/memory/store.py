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
from exo.memory import db, projects
from exo.memory.model import (
    MAX_CONTENT,
    MAX_TITLE,
    Hit,
    MemoryStoreError,
    MergeResult,
    NotFoundError,
    Observation,
    ProjectInfo,
    SaveResult,
    Session,
    SessionView,
    Stats,
    SummaryResult,
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


def _fields(
    project: str, scope: str, kind: str, title: str, content: str, topic_key: str | None
) -> tuple[str, str, str, str, str, str | None]:
    """Valida y normaliza los campos de una observación."""
    scope = check_scope(scope)
    project = "" if scope == "personal" else check_project(project)
    return (
        project,
        scope,
        check_type(kind),
        check_text("title", title.strip(), MAX_TITLE),
        check_text("content", content, MAX_CONTENT),
        check_topic_key(topic_key),
    )


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
        fields = _fields(project, scope, type, title, content, topic_key)
        with db.write(self.conn):
            obs_id, action = self._upsert(*fields, session_id=session_id)
        return SaveResult(obs_id, action)

    def _upsert(
        self,
        project: str,
        scope: str,
        kind: str,
        title: str,
        content: str,
        topic_key: str | None,
        *,
        session_id: int | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
        keep_newer: bool = False,
    ) -> tuple[int, str]:
        """Upsert dentro de una transacción ya abierta. Con `keep_newer` (import), no pisa
        una versión local más nueva: devuelve "skipped"."""
        digest = _hash(kind, title, content)
        stamp = now()
        if topic_key is not None:
            row = self.conn.execute(
                "SELECT id, content_hash, updated_at FROM observations "
                "WHERE project = ? AND topic_key = ?",
                (project, topic_key),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT id, content_hash, updated_at FROM observations "
                "WHERE project = ? AND topic_key IS NULL AND content_hash = ?",
                (project, digest),
            ).fetchone()
        if row is not None and row["content_hash"] == digest:
            return row["id"], "unchanged"
        if row is not None:
            if keep_newer and updated_at is not None and row["updated_at"] > updated_at:
                return row["id"], "skipped"
            self.conn.execute(
                "UPDATE observations SET type = ?, title = ?, content = ?, scope = ?, "
                "session_id = coalesce(?, session_id), content_hash = ?, "
                "revision = revision + 1, updated_at = ? WHERE id = ?",
                (kind, title, content, scope, session_id, digest, updated_at or stamp, row["id"]),
            )
            self._index(row["id"], title, content, topic_key)
            return row["id"], "updated"
        cursor = self.conn.execute(
            "INSERT INTO observations (project, scope, type, title, content, topic_key, "
            "session_id, content_hash, revision, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                project,
                scope,
                kind,
                title,
                content,
                topic_key,
                session_id,
                digest,
                created_at or stamp,
                updated_at or stamp,
            ),
        )
        obs_id = int(cursor.lastrowid or 0)
        self._index(obs_id, title, content, topic_key)
        return obs_id, "created"

    def import_rows(
        self, rows: list[tuple[str, str, str, str, str, str | None, str, str]]
    ) -> dict[str, int]:
        """Importa filas ya validadas `(proyecto, scope, tipo, título, contenido, topic_key,
        created_at, updated_at)` en una sola transacción. Devuelve cuántas de cada acción."""
        counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        with db.write(self.conn):
            for project, scope, kind, title, content, topic_key, created, updated in rows:
                _, action = self._upsert(
                    project,
                    scope,
                    kind,
                    title,
                    content,
                    topic_key,
                    created_at=created,
                    updated_at=updated,
                    keep_newer=True,
                )
                counts[action] += 1
        return counts

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

    def observations(
        self, *, project: str | None = None, scope: str | None = None
    ) -> list[Observation]:
        """Todas las observaciones, por proyecto exacto (sin sumar las personales) y scope."""
        clauses, args = [], []
        if project is not None:
            clauses.append("project = ?")
            args.append(project)
        if scope is not None:
            clauses.append("scope = ?")
            args.append(check_scope(scope))
        where = " AND ".join(clauses) or "1"
        rows = self.conn.execute(
            f"SELECT * FROM observations WHERE {where} ORDER BY created_at, id", args
        ).fetchall()
        return [_observation(row) for row in rows]

    # -- sesiones -------------------------------------------------------------------------

    def _session(self, session_id: int) -> Session:
        row = self.conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"no existe la sesión {session_id}")
        return Session(**{name: row[name] for name in Session.__dataclass_fields__})

    def session_start(self, project: str, *, agent: str | None = None) -> Session:
        project = check_project(project)
        with db.write(self.conn):
            cursor = self.conn.execute(
                "INSERT INTO sessions (project, agent, started_at) VALUES (?, ?, ?)",
                (project, agent, now()),
            )
        return self._session(int(cursor.lastrowid or 0))

    def session_summary(
        self, project: str, content: str, *, session_id: int | None = None
    ) -> SummaryResult:
        """Guarda el resumen en la sesión (la abierta más reciente del proyecto, o una nueva)
        y como observación `session-summary`, para que se pueda buscar."""
        project = check_project(project)
        content = check_text("content", content, MAX_CONTENT)
        with db.write(self.conn):
            if session_id is None:
                row = self.conn.execute(
                    "SELECT id FROM sessions WHERE project = ? AND ended_at IS NULL "
                    "ORDER BY started_at DESC, id DESC LIMIT 1",
                    (project,),
                ).fetchone()
                if row is not None:
                    session_id = int(row["id"])
                else:
                    cursor = self.conn.execute(
                        "INSERT INTO sessions (project, started_at) VALUES (?, ?)", (project, now())
                    )
                    session_id = int(cursor.lastrowid or 0)
            else:
                project = self._session(session_id).project
            self.conn.execute("UPDATE sessions SET summary = ? WHERE id = ?", (content, session_id))
            obs_id, _ = self._upsert(
                project,
                "project",
                "session-summary",
                f"Resumen de la sesión {session_id}",
                content,
                f"session/{session_id}",
                session_id=session_id,
            )
        return SummaryResult(session_id, obs_id)

    def session_end(self, session_id: int, *, summary: str | None = None) -> Session:
        session = self._session(session_id)
        if summary:
            self.session_summary(session.project, summary, session_id=session_id)
        with db.write(self.conn):
            self.conn.execute(
                "UPDATE sessions SET ended_at = coalesce(ended_at, ?) WHERE id = ?",
                (now(), session_id),
            )
        return self._session(session_id)

    def session_show(
        self, session_id: int | None = None, *, project: str | None = None
    ) -> SessionView:
        """Una sesión con sus observaciones; sin id, la más reciente (del proyecto, si se da)."""
        if session_id is None:
            where, args = ("project = ?", [project]) if project else ("1", [])
            row = self.conn.execute(
                f"SELECT id FROM sessions WHERE {where} ORDER BY started_at DESC, id DESC LIMIT 1",
                args,
            ).fetchone()
            if row is None:
                raise NotFoundError("no hay sesiones" + (f" de {project}" if project else ""))
            session_id = int(row["id"])
        session = self._session(session_id)
        rows = self.conn.execute(
            "SELECT * FROM observations WHERE session_id = ? AND type != 'session-summary' "
            "ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return SessionView(session, [_observation(row) for row in rows])

    # -- proyectos ------------------------------------------------------------------------

    def register_project(
        self, name: str, *, remote: str | None = None, path: Path | str | None = None
    ) -> None:
        name = check_project(name)
        stamp = now()
        with db.write(self.conn):
            self.conn.execute(
                "INSERT INTO projects (name, remote, path, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT (name) DO UPDATE SET "
                "remote = coalesce(excluded.remote, remote), "
                "path = coalesce(excluded.path, path), updated_at = excluded.updated_at",
                (name, remote, str(path) if path is not None else None, stamp, stamp),
            )

    def projects_list(self) -> list[ProjectInfo]:
        rows = self.conn.execute(
            "WITH names AS ("
            "  SELECT name FROM projects"
            "  UNION SELECT project FROM observations WHERE project != ''"
            "  UNION SELECT project FROM sessions)"
            " SELECT n.name, p.remote, p.path,"
            "  (SELECT count(*) FROM observations o WHERE o.project = n.name) AS observations,"
            "  (SELECT count(*) FROM sessions s WHERE s.project = n.name) AS sessions,"
            "  max(coalesce((SELECT max(updated_at) FROM observations o"
            "                WHERE o.project = n.name), ''),"
            "      coalesce((SELECT max(started_at) FROM sessions s"
            "                WHERE s.project = n.name), ''))"
            "   AS last_activity"
            " FROM names n LEFT JOIN projects p ON p.name = n.name"
            " ORDER BY last_activity DESC, n.name"
        ).fetchall()
        return [
            ProjectInfo(
                name=row["name"],
                remote=row["remote"],
                path=row["path"],
                observations=int(row["observations"]),
                sessions=int(row["sessions"]),
                last_activity=row["last_activity"] or None,
            )
            for row in rows
        ]

    def projects_merge(self, source: str, target: str) -> MergeResult:
        """Mueve todo de `source` a `target`. Si un `topic_key` está en los dos, queda la
        versión más reciente."""
        source, target = check_project(source), check_project(target)
        if source == target:
            raise MemoryStoreError("no se puede unir un proyecto consigo mismo")
        if source not in {p.name for p in self.projects_list()}:
            raise NotFoundError(f"no existe el proyecto {source!r}")
        with db.write(self.conn):
            return self._merge(source, target)

    def _merge(self, source: str, target: str) -> MergeResult:
        conflicts = 0
        clashes = self.conn.execute(
            "SELECT s.id AS src, s.updated_at AS src_at, t.id AS dst, t.updated_at AS dst_at "
            "FROM observations s JOIN observations t ON t.topic_key = s.topic_key "
            "WHERE s.project = ? AND t.project = ? AND s.topic_key IS NOT NULL",
            (source, target),
        ).fetchall()
        for clash in clashes:
            loser = clash["dst"] if clash["src_at"] > clash["dst_at"] else clash["src"]
            self.conn.execute("DELETE FROM observations WHERE id = ?", (loser,))
            self._unindex(loser)
            conflicts += 1
        moved = self.conn.execute(
            "UPDATE observations SET project = ? WHERE project = ?", (target, source)
        ).rowcount
        sessions = self.conn.execute(
            "UPDATE sessions SET project = ? WHERE project = ?", (target, source)
        ).rowcount
        self.conn.execute(
            "INSERT OR IGNORE INTO projects (name, remote, path, created_at, updated_at) "
            "SELECT ?, remote, path, created_at, updated_at FROM projects WHERE name = ?",
            (target, source),
        )
        self.conn.execute("DELETE FROM projects WHERE name = ?", (source,))
        return MergeResult(source, target, moved, conflicts, sessions)

    def projects_consolidate(self, *, dry_run: bool = False) -> dict[str, list[str]]:
        """Une los proyectos cuyo nombre es una variante del mismo remoto (mayúsculas, URL
        completa, `.git`). Devuelve `{canónico: [variantes]}`."""
        groups: dict[str, list[str]] = {}
        for info in self.projects_list():
            groups.setdefault(projects.canonical(info.name), []).append(info.name)
        plan = {
            canon: sorted(name for name in names if name != canon)
            for canon, names in sorted(groups.items())
            if any(name != canon for name in names)
        }
        if not dry_run:
            with db.write(self.conn):
                for canon, variants in plan.items():
                    for variant in variants:
                        self._merge(variant, canon)
        return plan

    # -- stats ----------------------------------------------------------------------------

    def stats(self) -> Stats:
        count = self.conn.execute
        by_type = dict(count("SELECT type, count(*) FROM observations GROUP BY type ORDER BY type"))
        by_project = dict(
            count(
                "SELECT project, count(*) FROM observations WHERE project != '' "
                "GROUP BY project ORDER BY count(*) DESC, project"
            )
        )
        size = sum(
            f.stat().st_size
            for f in (self.path, self.path.with_name(self.path.name + "-wal"))
            if f.exists()
        )
        return Stats(
            path=str(self.path),
            schema_version=int(db.get_meta(self.conn, "schema_version") or 0),
            fts=self.fts,
            size_bytes=size,
            observations=int(count("SELECT count(*) FROM observations").fetchone()[0]),
            sessions=int(count("SELECT count(*) FROM sessions").fetchone()[0]),
            projects=len(self.projects_list()),
            by_type=by_type,
            by_project=by_project,
            last_updated=count("SELECT max(updated_at) FROM observations").fetchone()[0],
        )

    # -- contexto -------------------------------------------------------------------------

    def context(self, project: str, *, limit: int = 10, max_chars: int = CONTEXT_CHARS) -> str:
        """Contexto reciente del proyecto, para el inicio de una sesión del agente."""
        cli = _meta.NAME
        footer = (
            f"\nDetalle: `{cli} mem get <id>`. Buscá antes de resolver algo de nuevo: "
            f'`{cli} mem search "<texto>"`. Al cerrar la sesión, guardá un resumen: '
            f'`{cli} mem session summary --content "<qué se hizo y qué queda>"`.\n'
        )
        items = [
            o for o in self.list(project, limit=self._limit(limit)) if o.type != "session-summary"
        ]
        last = self.conn.execute(
            "SELECT id, started_at, summary FROM sessions "
            "WHERE project = ? AND summary IS NOT NULL "
            "ORDER BY started_at DESC, id DESC LIMIT 1",
            (project,),
        ).fetchone()
        if not items and last is None:
            return f"# Memoria de {project}: sin memorias todavía.\n{footer}"
        lines = [f"# Memoria de {project} (más recientes primero)\n"]
        if last is not None:
            lines.append(
                f"\nÚltimo resumen de sesión (#{last['id']}): {preview(last['summary'], 600)}\n\n"
            )
        for obs in items:
            key = f" · {obs.topic_key}" if obs.topic_key else ""
            line = f"- #{obs.id} [{obs.type}] {obs.title}{key}: {preview(obs.content, 160)}\n"
            if sum(map(len, lines)) + len(line) + len(footer) > max_chars:
                break
            lines.append(line)
        return "".join(lines) + footer
