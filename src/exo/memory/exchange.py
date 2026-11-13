"""Export e import de la memoria en JSON (ADR-0009: sin redactar).

- `export` de un proyecto no incluye las observaciones personales: esas salen
  con `scope="personal"` o con el export completo.
- `import_` valida todo antes de escribir, en una sola transacción. Hace upsert
  como `save`, pero no pisa una versión local más nueva (cuenta como `skipped`)
  y conserva las fechas originales.
- Las sesiones no se exportan; sus resúmenes sí, como observaciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from exo import _meta
from exo.memory.model import MemoryStoreError
from exo.memory.store import MemoryStore, _fields, now

FORMAT = f"{_meta.NAME}-memory"
SCHEMA = 1
_FIELDS = ("project", "scope", "type", "title", "content", "topic_key", "created_at", "updated_at")


@dataclass(frozen=True)
class ImportResult:
    created: int
    updated: int
    unchanged: int
    skipped: int


def export(
    store: MemoryStore, *, project: str | None = None, scope: str | None = None
) -> dict[str, Any]:
    if project is not None and scope is None:
        scope = "project"
    observations = store.observations(project=project, scope=scope)
    return {
        "format": FORMAT,
        "schema": SCHEMA,
        "exported_at": now(),
        "engine_version": _meta.VERSION,
        "observations": [
            {
                "project": obs.project,
                "scope": obs.scope,
                "type": obs.type,
                "title": obs.title,
                "content": obs.content,
                "topic_key": obs.topic_key,
                "revision": obs.revision,
                "created_at": obs.created_at,
                "updated_at": obs.updated_at,
            }
            for obs in observations
        ],
    }


def _timestamp(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise MemoryStoreError(f"{where}: falta la fecha o no es texto")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise MemoryStoreError(f"{where}: fecha inválida {value!r}") from exc
    return value


def _row(raw: Any, index: int, project: str | None) -> tuple[Any, ...]:
    where = f"observations[{index}]"
    if not isinstance(raw, dict):
        raise MemoryStoreError(f"{where}: tiene que ser un objeto")
    missing = [name for name in ("title", "content") if not isinstance(raw.get(name), str)]
    scope = raw.get("scope", "project")
    target = project if project is not None else raw.get("project")
    if scope == "project" and not isinstance(target, str):
        missing.append("project")
    if missing:
        raise MemoryStoreError(f"{where}: faltan {', '.join(missing)} o no son texto")
    try:
        fields = _fields(
            target or "",
            scope,
            raw.get("type", "note"),
            raw["title"],
            raw["content"],
            raw.get("topic_key"),
        )
    except MemoryStoreError as exc:
        raise MemoryStoreError(f"{where}: {exc}") from exc
    stamp = now()
    created = _timestamp(raw.get("created_at", stamp), f"{where}.created_at")
    updated = _timestamp(raw.get("updated_at", created), f"{where}.updated_at")
    return (*fields, created, updated)


def import_(store: MemoryStore, data: Any, *, project: str | None = None) -> ImportResult:
    """Importa un export. Con `project`, todo lo de scope `project` va a ese proyecto."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise MemoryStoreError(f"no es un export de memoria (se espera format {FORMAT!r})")
    if data.get("schema") != SCHEMA:
        raise MemoryStoreError(
            f"export del schema {data.get('schema')!r}; este motor entiende el {SCHEMA}"
        )
    items = data.get("observations")
    if not isinstance(items, list):
        raise MemoryStoreError("observations tiene que ser una lista")
    rows = [_row(raw, i, project) for i, raw in enumerate(items)]
    counts = store.import_rows(rows)
    return ImportResult(**counts)
