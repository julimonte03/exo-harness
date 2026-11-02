"""Motor de operaciones: compara lo que piden los adaptadores con el lock y lo aplica.

Flujo (`docs/plan/fases/F2-adaptadores-e-instalador.md`):

1. Unifica las operaciones repetidas entre adaptadores.
2. Compara cada unidad con el lock y con el disco: alta, cambio, sin cambios,
   adopción (ya estaba igual y es del humano: no se registra) o conflicto.
3. Lo que está en el lock y ya no se pide, se da de baja.
4. Conflictos (algo editado a mano, o un archivo del humano con otro
   contenido): sin `force` no se escribe **nada** y se informan.
5. Sin cambios: no escribe ni crea snapshot. Con `dry_run`: solo informa.
6. Si no, snapshot de las rutas afectadas, aplicación atómica y lock al final.

Un JSON que no se puede editar sin perder datos (JSONC, claves repetidas) no
es conflicto: se saltea con un aviso y el snippet para pegar a mano.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import filemerge, fsutil, lock, snapshots, structmerge
from exo.installer.ops import (
    MergeBlock,
    MergeKey,
    MergeListItem,
    Op,
    Unit,
    WriteFile,
    expected_hash,
    kind_of,
    merge_duplicates,
    unit_of,
    unit_of_entry,
)

WRITES = ("create", "update", "remove")


@dataclass(frozen=True)
class Action:
    action: str  # create | update | remove | adopt | forget | skip
    path: str
    kind: str
    detail: str = ""


@dataclass(frozen=True)
class Conflict:
    path: str
    kind: str
    reason: str


@dataclass
class Result:
    actions: list[Action] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    snapshot: str | None = None
    applied: bool = False
    lock_changed: bool = False

    @property
    def changed(self) -> bool:
        return self.lock_changed or any(a.action in WRITES for a in self.actions)


# -- estado actual ------------------------------------------------------------


def _current(project: Path, op: Op) -> str | None:
    """Hash actual de la unidad, o None si no existe. Lanza BlockError o StructMergeError."""
    target = fsutil.join_within(project, op.path)
    if not target.exists():
        return None
    if isinstance(op, WriteFile):
        return fsutil.sha256_file(target) if target.is_file() else "<directorio>"
    if isinstance(op, MergeBlock):
        found = next(
            (b for b in filemerge.list_blocks(target, style=op.style) if b.id == op.block_id), None
        )
        return None if found is None else lock.hash_block_content(found.content)
    value = structmerge.get_json_key(target, op.key)
    if value is structmerge.MISSING:
        return None
    if isinstance(op, MergeListItem):
        if not isinstance(value, list):
            raise structmerge.StructMergeError(f"{op.path}: {op.key} no es una lista")
        return lock.hash_json_value(op.item) if op.item in value else None
    return lock.hash_json_value(value)


def _entry(op: Op, created: bool) -> lock.LockEntry:
    common = {"path": op.path, "owner": op.owner, "sha256": expected_hash(op)}
    if isinstance(op, WriteFile):
        return lock.LockEntry(kind=op.kind, **common)
    if isinstance(op, MergeBlock):
        return lock.LockEntry(
            kind="block", block_id=op.block_id, style=op.style, created=created, **common
        )
    if isinstance(op, MergeKey):
        return lock.LockEntry(kind="key", key=op.key, created=created, **common)
    return lock.LockEntry(kind="item", key=op.key, item=op.item, created=created, **common)


def _snippet(op: Op) -> str:
    value: Any = [op.item] if isinstance(op, MergeListItem) else getattr(op, "value", None)
    for part in reversed(getattr(op, "key", "").split(".")):
        value = {part: value}
    return json.dumps(value, indent=2, ensure_ascii=False)


# -- escritura y baja ---------------------------------------------------------


def _prune_dirs(project: Path, path: Path) -> None:
    parent = path.parent
    while parent != project and parent.is_relative_to(project):
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def _write(project: Path, op: Op) -> None:
    target = fsutil.join_within(project, op.path)
    if isinstance(op, WriteFile):
        fsutil.write_atomic(target, op.content)
    elif isinstance(op, MergeBlock):
        filemerge.inject(target, op.block_id, op.content, style=op.style, position=op.position)
    elif isinstance(op, MergeKey):
        structmerge.merge_json_key(target, op.key, op.value)
    else:
        structmerge.add_json_list_item(target, op.key, op.item)


def _is_empty(target: Path, kind: str) -> bool:
    raw = fsutil.read_bytes(target).decode("utf-8", errors="replace").lstrip(chr(0xFEFF)).strip()
    if kind == "block":
        return raw == ""
    try:
        return json.loads(raw or "{}") == {}
    except json.JSONDecodeError:
        return False


def _remove(project: Path, entry: lock.LockEntry) -> None:
    target = fsutil.join_within(project, entry.path)
    if not target.exists():
        return
    if entry.kind in ("file", "mirror"):
        target.unlink()
        _prune_dirs(project, target)
        return
    if entry.kind == "block":
        filemerge.remove(target, entry.block_id or "", style=entry.style)
    elif entry.kind == "key":
        structmerge.remove_json_key(target, entry.key or "", prune_empty=True)
    else:
        structmerge.remove_json_list_item(target, entry.key or "", entry.item, prune_empty=True)
    if entry.created and _is_empty(target, entry.kind):
        target.unlink()
        _prune_dirs(project, target)


# -- plan y aplicación ----------------------------------------------------------


def apply(
    project: Path,
    ops: list[Op],
    *,
    agents: list[str],
    packs: list[str],
    force: bool = False,
    dry_run: bool = False,
) -> Result:
    project = Path(project).resolve()
    ops = merge_duplicates(ops)
    previous = lock.read(project)
    old = {unit_of_entry(e): e for e in (previous.files if previous else [])}
    result = Result()
    writes: list[Op] = []
    removals: list[lock.LockEntry] = []
    entries: dict[Unit, lock.LockEntry] = {}

    for op in ops:
        unit, kind = unit_of(op), kind_of(op)
        entry = old.get(unit)
        expected = expected_hash(op)
        try:
            existed = fsutil.join_within(project, op.path).exists()
            current = _current(project, op)
        except fsutil.UnsafePathError as exc:
            result.conflicts.append(Conflict(op.path, kind, str(exc)))
            continue
        except filemerge.BlockError as exc:
            result.conflicts.append(Conflict(op.path, kind, f"marcadores inválidos ({exc})"))
            continue
        except structmerge.StructMergeError as exc:
            result.warnings.append(
                f"{op.path}: no se modificó ({exc}). Agregá a mano:\n{_snippet(op)}"
            )
            result.actions.append(Action("skip", op.path, kind, "archivo no editable"))
            if entry is not None:
                entries[unit] = entry
            continue
        created = entry.created if entry else (not existed and kind in ("block", "key", "item"))
        new_entry = _entry(op, created)
        if entry is None:
            if current is None:
                writes.append(op)
                result.actions.append(Action("create", op.path, kind))
                entries[unit] = new_entry
            elif current == expected:
                result.actions.append(
                    Action("adopt", op.path, kind, "ya estaba igual; queda del humano")
                )
            else:
                result.conflicts.append(
                    Conflict(op.path, kind, "ya existe con otro contenido y no lo generó el motor")
                )
                if force:
                    writes.append(op)
                    result.actions.append(Action("update", op.path, kind, "forzado"))
                    entries[unit] = new_entry
            continue
        if current is not None and current not in (entry.sha256, expected):
            result.conflicts.append(
                Conflict(op.path, kind, "modificado a mano desde la última instalación")
            )
            if force:
                writes.append(op)
                result.actions.append(Action("update", op.path, kind, "forzado"))
                entries[unit] = new_entry
            else:
                entries[unit] = entry
        elif current != expected:
            writes.append(op)
            result.actions.append(
                Action("update" if current is not None else "create", op.path, kind)
            )
            entries[unit] = new_entry
        else:
            entries[unit] = new_entry

    planned = {unit_of(op) for op in ops}
    for unit, entry in old.items():
        if unit in planned:
            continue
        try:
            current = lock.current_hash(project, entry)
        except (fsutil.UnsafePathError, OSError) as exc:
            result.conflicts.append(Conflict(entry.path, entry.kind, f"no se puede leer ({exc})"))
            entries[unit] = entry
            continue
        if current is None:
            result.actions.append(Action("forget", entry.path, entry.kind, "ya no existía"))
        elif current != entry.sha256:
            result.conflicts.append(
                Conflict(entry.path, entry.kind, "modificado a mano; no se quita")
            )
            if force:
                removals.append(entry)
                result.actions.append(Action("remove", entry.path, entry.kind, "forzado"))
            else:
                entries[unit] = entry
        else:
            removals.append(entry)
            result.actions.append(Action("remove", entry.path, entry.kind))

    new_lock = lock.Lock(_meta.VERSION, list(agents), list(packs), list(entries.values()))
    result.lock_changed = lock.dumps(new_lock) != _current_lock_bytes(project)
    if (result.conflicts and not force) or dry_run:
        return result
    affected = sorted({op.path for op in writes} | {e.path for e in removals})
    if affected:
        result.snapshot = snapshots.snapshot(project, affected).name
    for entry in removals:
        _remove(project, entry)
    for op in writes:
        _write(project, op)
    if result.lock_changed:
        lock.write(project, new_lock)
    result.applied = True
    return result


def _current_lock_bytes(project: Path) -> bytes | None:
    try:
        return fsutil.read_bytes(lock.lock_path(project))
    except FileNotFoundError:
        return None
