"""Tipos de la memoria y sus validaciones.

Definiciones propias: la referencia solo nombra los campos (tipo, título,
contenido, `topic_key`, scope, proyecto); los límites y los patrones son de
este motor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SCOPES = ("project", "personal")
# Tipos habituales; se acepta cualquier slug para no frenar a la skill.
COMMON_TYPES = ("decision", "bugfix", "discovery", "gotcha", "convention", "pattern", "note")
MAX_TITLE = 200
MAX_CONTENT = 100_000
MAX_PROJECT = 300
PREVIEW = 300

_TYPE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_TOPIC_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")


class MemoryStoreError(ValueError):
    """Pedido inválido o base de la memoria inutilizable (el mensaje dice qué hacer)."""


class NotFoundError(MemoryStoreError):
    """No existe la observación, sesión o proyecto pedido."""


@dataclass(frozen=True)
class Observation:
    id: int
    project: str  # "" para scope personal
    scope: str
    type: str
    title: str
    content: str
    topic_key: str | None
    session_id: int | None
    content_hash: str
    revision: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Hit:
    """Resultado de búsqueda: preview truncado; el contenido completo sale de `get`."""

    id: int
    project: str
    scope: str
    type: str
    title: str
    topic_key: str | None
    preview: str
    updated_at: str
    score: float


@dataclass(frozen=True)
class SaveResult:
    id: int
    action: str  # created | updated | unchanged
    similar: list[Hit] = field(default_factory=list)


def preview(text: str, limit: int = PREVIEW) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def check_project(project: str) -> str:
    project = project.strip()
    if not project or len(project) > MAX_PROJECT or "\n" in project:
        raise MemoryStoreError(
            f"invalid project: {project!r} (text of 1 to {MAX_PROJECT} characters)"
        )
    return project


def check_scope(scope: str) -> str:
    if scope not in SCOPES:
        raise MemoryStoreError(f"invalid scope: {scope!r} (one of {', '.join(SCOPES)})")
    return scope


def check_type(kind: str) -> str:
    if not _TYPE.match(kind):
        raise MemoryStoreError(
            f"invalid type: {kind!r} (lowercase letters, digits and hyphens; for example "
            f"{', '.join(COMMON_TYPES[:3])})"
        )
    return kind


def check_topic_key(topic_key: str | None) -> str | None:
    if topic_key is None or topic_key == "":
        return None
    parts = topic_key.split("/")
    if not _TOPIC_KEY.match(topic_key) or any(p in ("", ".", "..") for p in parts):
        raise MemoryStoreError(
            f"invalid topic_key: {topic_key!r} (segments separated by /, for example "
            "sdd/<change>/<phase> or project/profile)"
        )
    return topic_key


def check_text(name: str, value: str, limit: int) -> str:
    if not value.strip():
        raise MemoryStoreError(f"{name} cannot be empty")
    if len(value) > limit:
        raise MemoryStoreError(f"{name} exceeds {limit} characters")
    return value


@dataclass(frozen=True)
class Session:
    id: int
    project: str
    agent: str | None
    started_at: str
    ended_at: str | None
    summary: str | None


@dataclass(frozen=True)
class SessionView:
    session: Session
    observations: list[Observation]


@dataclass(frozen=True)
class SummaryResult:
    session_id: int
    observation_id: int


@dataclass(frozen=True)
class ProjectInfo:
    name: str
    remote: str | None
    path: str | None
    observations: int
    sessions: int
    last_activity: str | None


@dataclass(frozen=True)
class MergeResult:
    source: str
    target: str
    moved: int
    conflicts: int  # topic_key repetidos: queda la versión más reciente
    sessions: int


@dataclass(frozen=True)
class Stats:
    path: str
    schema_version: int
    fts: bool
    size_bytes: int
    observations: int
    sessions: int
    projects: int
    by_type: dict[str, int]
    by_project: dict[str, int]
    last_updated: str | None
    semantic: dict[str, object] | None = None  # proveedor, modelo, dimensión, vectores


SEARCH_MODES = ("auto", "lexical", "semantic", "hybrid")


@dataclass(frozen=True)
class SearchResult:
    hits: list[Hit]
    mode: str  # el que se usó de verdad: lexical, semantic o hybrid
    note: str | None = None


@dataclass(frozen=True)
class ReindexResult:
    fts: int
    vectors: int
    provider: str | None
    model: str | None
    dim: int | None
