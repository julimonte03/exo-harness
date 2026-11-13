"""Operaciones que calculan los adaptadores y aplica el motor.

Los adaptadores son puros (invariante 12 de `docs/plan/02-ARQUITECTURA.md`
§2.13): devuelven estas operaciones y nunca escriben. Cada operación describe
el estado deseado de una unidad gestionada, que el lock registra con su hash:

- `WriteFile`: un archivo completo del motor (`file`) o una copia espejo de una
  skill o un subagente (`mirror`).
- `MergeBlock`: un bloque marcado dentro de un archivo que también edita el humano.
- `MergeKey`: una clave dentro de un JSON.
- `MergeListItem`: un ítem dentro de una lista JSON (por ejemplo `permissions.allow`).

Las bajas no son operaciones: el motor las deduce comparando con el lock.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from exo.core import fsutil, lock


@dataclass(frozen=True)
class WriteFile:
    path: str
    content: bytes
    owner: str
    kind: str = "file"  # "file" | "mirror"


@dataclass(frozen=True)
class MergeBlock:
    path: str
    block_id: str
    content: str
    owner: str
    style: str | None = None
    position: str = "end"


@dataclass(frozen=True)
class MergeKey:
    path: str
    key: str
    value: Any
    owner: str


@dataclass(frozen=True)
class MergeListItem:
    path: str
    key: str
    item: str
    owner: str


Op = WriteFile | MergeBlock | MergeKey | MergeListItem
Unit = tuple[str, str, str]  # (ruta, kind, block_id | key | key+item)


def kind_of(op: Op) -> str:
    if isinstance(op, WriteFile):
        return op.kind
    if isinstance(op, MergeBlock):
        return "block"
    if isinstance(op, MergeKey):
        return "key"
    return "item"


def unit_of(op: Op) -> Unit:
    if isinstance(op, WriteFile):
        return (op.path, op.kind, "")
    if isinstance(op, MergeBlock):
        return (op.path, "block", op.block_id)
    if isinstance(op, MergeKey):
        return (op.path, "key", op.key)
    return (op.path, "item", f"{op.key}\n{op.item}")


def unit_of_entry(entry: lock.LockEntry) -> Unit:
    if entry.kind in ("file", "mirror"):
        return (entry.path, entry.kind, "")
    if entry.kind == "block":
        return (entry.path, "block", entry.block_id or "")
    if entry.kind == "key":
        return (entry.path, "key", entry.key or "")
    return (entry.path, "item", f"{entry.key}\n{entry.item}")


def expected_hash(op: Op) -> str:
    if isinstance(op, WriteFile):
        return fsutil.sha256_bytes(op.content)
    if isinstance(op, MergeBlock):
        return lock.hash_block_content(op.content)
    if isinstance(op, MergeKey):
        return lock.hash_json_value(op.value)
    return lock.hash_json_value(op.item)


def _comparable(op: Op) -> Any:
    if isinstance(op, MergeKey):
        return json.dumps(op.value, sort_keys=True)
    return replace(op, owner="")


def combine_owners(owners: list[str]) -> str:
    """`adapter:a` + `adapter:b` -> `adapter:a,b`; otros dueños (`engine`) van aparte."""
    prefix = "adapter:"
    adapters = sorted(
        {p for o in owners if o.startswith(prefix) for p in o[len(prefix) :].split(",")}
    )
    others = sorted({o for o in owners if not o.startswith(prefix)})
    return ";".join([*others, *([prefix + ",".join(adapters)] if adapters else [])])


def merge_duplicates(ops: list[Op]) -> list[Op]:
    """Unifica operaciones iguales de varios adaptadores; el dueño queda combinado.

    Dos operaciones sobre la misma unidad con contenido distinto son un error
    de programación de los adaptadores.
    """
    merged: dict[Unit, Op] = {}
    owners: dict[Unit, list[str]] = {}
    for op in ops:
        unit = unit_of(op)
        if unit in merged and _comparable(merged[unit]) != _comparable(op):
            raise ValueError(f"two adapters request different content for {unit}")
        merged.setdefault(unit, op)
        owners.setdefault(unit, []).append(op.owner)
    return [replace(op, owner=combine_owners(owners[unit])) for unit, op in merged.items()]
