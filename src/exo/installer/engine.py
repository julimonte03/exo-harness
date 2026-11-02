"""Motor de operaciones: compara lo que piden los adaptadores con el lock y lo aplica.

Flujo (`docs/plan/fases/F2-adaptadores-e-instalador.md`):

1. Unifica las operaciones repetidas entre adaptadores.
2. Compara cada unidad con el lock y con el disco: alta, cambio, sin cambios,
   adopción (ya estaba igual y es del humano: no se registra) o conflicto.
3. Lo que está en el lock y ya no se pide, se da de baja.
4. Conflictos: sin `force` no se escribe **nada** y se informan. Con `force`
   se pisa lo editado a mano sobre lo generado; lo que `force` no resuelve
   (un archivo del humano, marcadores rotos, una ruta que pasa por un link)
   queda como está, con su entrada del lock, y se informa igual.
5. Sin cambios: no escribe ni crea snapshot. Con `dry_run`: solo informa.
6. Si no, snapshot de las rutas afectadas (con el lock), aplicación atómica
   archivo por archivo y lock al final. Si algo falla a mitad de camino, se
   restaura el snapshot: no quedan archivos a medias ni huérfanos.

Un JSON que no se puede editar sin perder datos (JSONC, claves repetidas, un
padre que no es objeto) no es conflicto al agregar: se saltea con un aviso y
el snippet para pegar a mano. Al quitar, sí es conflicto; con `force` se
saltea con el aviso y la entrada se olvida.
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
_LOCK_REL = f"{_meta.PROJECT_DIR}/{lock.FILENAME}"
_HUMAN = (
    "ya existe con otro contenido y no lo generó el motor; movelo o borralo y repetí "
    "(--force no pisa lo del humano)"
)


class ApplyError(ValueError):
    """Falló la escritura a mitad de camino (el mensaje dice si se restauró el snapshot)."""


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
    forceable: bool = True  # --force lo resuelve; si no, hay que arreglarlo a mano


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

    @property
    def unresolved(self) -> list[Conflict]:
        """Conflictos que ni `force` resuelve."""
        return [c for c in self.conflicts if not c.forceable]


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
    value = structmerge.get_json_key(target, op.key, strict=True)
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


def _snippet(key: str, value: Any) -> str:
    for part in reversed(key.split(".")):
        value = {part: value}
    return json.dumps(value, indent=2, ensure_ascii=False)


def _op_snippet(op: Op) -> str:
    if isinstance(op, MergeListItem):
        return _snippet(op.key, [op.item])
    return _snippet(getattr(op, "key", ""), getattr(op, "value", None))


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


def _rollback(project: Path, name: str, error: BaseException) -> ApplyError:
    """Vuelve al snapshot tomado antes de escribir y borra los directorios que quedaron vacíos."""
    try:
        restored = snapshots.restore(project, name)
    except Exception as exc:  # noqa: BLE001 - se informa junto con el error original
        return ApplyError(
            f"falló a mitad de camino ({error}) y no se pudo restaurar el snapshot {name} "
            f"({exc}). Restauralo con `{_meta.NAME} restore {name}`."
        )
    for rel in restored.removed:
        _prune_dirs(project, project / rel)
    return ApplyError(f"falló a mitad de camino ({error}); se restauró el snapshot {name}")


# -- plan y aplicación ----------------------------------------------------------


def apply(
    project: Path,
    ops: list[Op],
    *,
    agents: list[str],
    packs: list[str],
    force: bool = False,
    dry_run: bool = False,
    extra: dict[str, bytes] | None = None,
) -> Result:
    """Aplica `ops` contra el lock. `extra` son archivos fuera del lock (la config del
    proyecto) que se escriben en la misma transacción y entran en el snapshot."""
    project = Path(project).resolve()
    ops = merge_duplicates(ops)
    previous = lock.read(project)
    old = {unit_of_entry(e): e for e in (previous.files if previous else [])}
    result = Result()
    writes: list[Op] = []
    removals: list[lock.LockEntry] = []
    entries: dict[Unit, lock.LockEntry] = {}

    def keep(unit: Unit) -> None:
        if unit in old:
            entries[unit] = old[unit]

    for op in ops:
        unit, kind = unit_of(op), kind_of(op)
        entry = old.get(unit)
        expected = expected_hash(op)
        try:
            existed = fsutil.join_within(project, op.path).exists()
            current = _current(project, op)
        except fsutil.UnsafePathError as exc:
            result.conflicts.append(Conflict(op.path, kind, str(exc), forceable=False))
            keep(unit)
            continue
        except filemerge.BlockError as exc:
            reason = f"marcadores inválidos ({exc})"
            result.conflicts.append(Conflict(op.path, kind, reason, forceable=False))
            keep(unit)
            continue
        except structmerge.StructMergeError as exc:
            result.warnings.append(
                f"{op.path}: no se modificó ({exc}). Agregá a mano:\n{_op_snippet(op)}"
            )
            result.actions.append(Action("skip", op.path, kind, "archivo no editable"))
            keep(unit)
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
                result.conflicts.append(Conflict(op.path, kind, _HUMAN, forceable=False))
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
            current = lock.current_hash(project, entry, strict=True)
        except (fsutil.UnsafePathError, OSError) as exc:
            reason = f"no se puede leer ({exc})"
            result.conflicts.append(Conflict(entry.path, entry.kind, reason, forceable=False))
            keep(unit)
            continue
        except filemerge.BlockError as exc:
            reason = f"marcadores inválidos ({exc}); no se quita"
            result.conflicts.append(Conflict(entry.path, entry.kind, reason, forceable=False))
            keep(unit)
            continue
        except structmerge.StructMergeError as exc:
            result.conflicts.append(
                Conflict(entry.path, entry.kind, f"no se puede editar ({exc}); no se quita")
            )
            if force:
                value: Any = [entry.item] if entry.kind == "item" else "..."
                result.warnings.append(
                    f"{entry.path}: no se quitó ({exc}). Quitá a mano:\n"
                    f"{_snippet(entry.key or '', value)}"
                )
                result.actions.append(Action("skip", entry.path, entry.kind, "quitalo a mano"))
            else:
                keep(unit)
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
                keep(unit)
        else:
            removals.append(entry)
            result.actions.append(Action("remove", entry.path, entry.kind))

    extra_writes: dict[str, bytes] = {}
    for rel, data in (extra or {}).items():
        target = fsutil.join_within(project, rel)
        if not target.exists():
            result.actions.append(Action("create", rel, "file", "fuera del lock"))
        elif fsutil.read_bytes(target) != data:
            result.actions.append(Action("update", rel, "file", "fuera del lock"))
        else:
            continue
        extra_writes[rel] = data

    new_lock = lock.Lock(_meta.VERSION, list(agents), list(packs), list(entries.values()))
    result.lock_changed = lock.dumps(new_lock) != _current_lock_bytes(project)
    if (result.conflicts and not force) or dry_run:
        return result
    affected = {op.path for op in writes} | {e.path for e in removals} | set(extra_writes)
    if affected:
        if result.lock_changed:
            affected.add(_LOCK_REL)
        result.snapshot = snapshots.snapshot(project, sorted(affected)).name
    try:
        for entry in removals:
            _remove(project, entry)
        for op in writes:
            _write(project, op)
        for rel, data in extra_writes.items():
            fsutil.write_atomic(fsutil.join_within(project, rel), data)
        if result.lock_changed:
            lock.write(project, new_lock)
    except Exception as exc:
        if result.snapshot is None:
            raise
        raise _rollback(project, result.snapshot, exc) from exc
    except BaseException as exc:  # Ctrl+C: se restaura y se deja seguir la interrupción
        if result.snapshot is not None:
            _rollback(project, result.snapshot, exc)
        raise
    result.applied = True
    return result


def _current_lock_bytes(project: Path) -> bytes | None:
    try:
        return fsutil.read_bytes(lock.lock_path(project))
    except FileNotFoundError:
        return None
