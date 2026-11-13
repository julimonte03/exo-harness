"""Conexión, esquema y migraciones de la base de la memoria.

WAL permite que el CLI y el servidor MCP lean y escriban a la vez; las
escrituras toman el lock al empezar (`BEGIN IMMEDIATE`) para no chocar al
promover una transacción de lectura. El índice FTS5 es derivado: se mantiene
desde Python (sin triggers, para que un Python sin FTS5 pueda escribir igual)
y, si quedó desactualizado, se reconstruye al abrir con FTS5 disponible.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from exo import _meta
from exo.memory.model import MemoryStoreError

SCHEMA_VERSION = 1
BUSY_TIMEOUT_MS = 10_000

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS projects (
    name TEXT PRIMARY KEY,
    remote TEXT,
    path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    agent TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('project', 'personal')),
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    topic_key TEXT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    content_hash TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS observations_topic
    ON observations (project, topic_key) WHERE topic_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS observations_recent ON observations (project, updated_at);
CREATE INDEX IF NOT EXISTS sessions_project ON sessions (project, started_at);
"""

_FTS = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5("
    "title, content, topic_key, tokenize = 'unicode61 remove_diacritics 2')"
)

# MIGRATIONS[n] lleva una base del esquema n al n + 1, dentro de la transacción.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error as exc:
        raise MemoryStoreError(f"could not open the memory at {path} ({exc})") from exc
    return conn


def fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp._exo_probe USING fts5(x)")
    except sqlite3.OperationalError:
        return False
    conn.execute("DROP TABLE temp._exo_probe")
    return True


@contextmanager
def write(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Transacción de escritura: toma el lock al empezar y revierte si algo falla."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row[0])


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def _table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (name,)).fetchone() is not None
    )


def _up_to_date(conn: sqlite3.Connection, *, fts: bool) -> bool:
    """Sin tomar el lock de escritura: abrir para leer no escribe nada."""
    if not _table(conn, "meta"):
        return False
    raw = get_meta(conn, "schema_version")
    version = int(raw) if raw is not None else 0
    if version > SCHEMA_VERSION:
        raise MemoryStoreError(
            f"the memory uses schema {version} and this engine supports up to "
            f"{SCHEMA_VERSION}; upgrade {_meta.NAME}"
        )
    return version == SCHEMA_VERSION and (not fts or _table(conn, "observations_fts"))


def migrate(conn: sqlite3.Connection, *, fts: bool) -> None:
    """Crea o actualiza el esquema. Con `fts`, crea el índice FTS5 si falta."""
    if _up_to_date(conn, fts=fts):
        return
    with write(conn):
        conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        raw = get_meta(conn, "schema_version")
        version = int(raw) if raw is not None else 0
        if version > SCHEMA_VERSION:
            raise MemoryStoreError(
                f"the memory uses schema {version} and this engine supports up to "
                f"{SCHEMA_VERSION}; upgrade {_meta.NAME}"
            )
        if version == 0:
            # Sentencia por sentencia: executescript cerraría la transacción.
            for statement in _SCHEMA_V1.split(";"):
                if statement.strip():
                    conn.execute(statement)
            version = 1
        while version < SCHEMA_VERSION:
            MIGRATIONS[version](conn)
            version += 1
        set_meta(conn, "schema_version", str(version))
        if fts:
            conn.execute(_FTS)
