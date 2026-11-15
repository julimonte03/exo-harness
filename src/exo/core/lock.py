"""Lock del proyecto (`<PROJECT_DIR>/lock.json`): qué generó el motor y con qué hash.

Cada entrada es un archivo completo (`file`), una copia espejo (`mirror`), un
bloque marcado dentro de un archivo del humano (`block`), una clave dentro de
un JSON (`key`) o un ítem dentro de una lista JSON (`item`).

`created` registra, por archivo, lo que el motor creó dentro de archivos que
también son del humano: el archivo mismo y los contenedores JSON (por ejemplo
`permissions.allow`). Al quitar lo del motor, solo eso se borra, y solo si
quedó vacío: así `init` + `uninstall` deja el proyecto como estaba.

`drift()` compara el estado actual con el lock y devuelve lo que alguien
editó a mano: el motor no lo pisa sin `--force` (invariante 13 de
`docs/plan/02-ARQUITECTURA.md` §2.13).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import filemerge, fsutil, structmerge

SCHEMA = 1
FILENAME = "lock.json"
KINDS = ("file", "mirror", "block", "key", "item")


class LockError(ValueError):
    """El lock no se puede leer o tiene entradas inválidas."""


@dataclass(frozen=True, order=True)
class LockEntry:
    path: str
    kind: str
    owner: str
    sha256: str
    block_id: str | None = None
    key: str | None = None
    style: str | None = None  # estilo de comentario del bloque, si no se deduce del nombre
    item: str | None = None  # valor del ítem, para kind "item"
    executable: bool = False  # archivos con bit de ejecución (git hooks)

    def sort_key(self) -> tuple[str, str, str, str, str]:
        return (self.path, self.kind, self.block_id or "", self.key or "", self.item or "")


@dataclass(frozen=True, order=True)
class Created:
    """Lo que el motor creó dentro de `path`: el archivo y/o contenedores JSON."""

    path: str
    file: bool = False
    containers: tuple[str, ...] = ()


@dataclass
class Lock:
    engine_version: str
    agents: list[str] = field(default_factory=list)
    packs: list[str] = field(default_factory=list)
    files: list[LockEntry] = field(default_factory=list)
    created: list[Created] = field(default_factory=list)
    schema: int = SCHEMA


@dataclass(frozen=True)
class Drift:
    entry: LockEntry
    status: str  # "modified" | "missing" | "unreadable"
    actual: str | None


def lock_path(project: Path) -> Path:
    return Path(project) / _meta.PROJECT_DIR / FILENAME


def hash_block_content(content: str) -> str:
    """Hash de un bloque, independiente de CRLF/LF y del salto final."""
    normalized = content.replace("\r\n", "\n").rstrip("\n")
    return fsutil.sha256_bytes(normalized.encode("utf-8"))


def hash_json_value(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return fsutil.sha256_bytes(canonical.encode("utf-8"))


# -- lectura y escritura ----------------------------------------------------


def _entry(raw: Any, index: int) -> LockEntry:
    where = f"files[{index}]"
    if not isinstance(raw, dict):
        raise LockError(f"{where}: must be an object")
    for name in ("path", "kind", "owner", "sha256"):
        if not isinstance(raw.get(name), str) or not raw[name]:
            raise LockError(f"{where}: {name!r} is missing or not a string")
    try:
        path = str(fsutil.safe_relpath(raw["path"]))
    except fsutil.UnsafePathError as exc:
        raise LockError(f"{where}: unsafe path ({exc})") from exc
    kind = raw["kind"]
    if kind not in KINDS:
        raise LockError(f"{where}: unknown kind {kind!r} (one of {', '.join(KINDS)})")
    block_id, key = raw.get("block_id"), raw.get("key")
    if kind == "block" and not isinstance(block_id, str):
        raise LockError(f"{where}: a block entry needs block_id")
    if kind in ("key", "item") and not isinstance(key, str):
        raise LockError(f"{where}: a {kind} entry needs key")
    item = raw.get("item")
    if kind == "item" and not isinstance(item, str):
        raise LockError(f"{where}: an item entry needs item")
    style = raw.get("style")
    if style is not None and style not in (filemerge.STYLE_HTML, filemerge.STYLE_HASH):
        raise LockError(f"{where}: unknown style {style!r}")
    executable = raw.get("executable", False)
    if not isinstance(executable, bool):
        raise LockError(f"{where}: executable must be true or false")
    return LockEntry(
        path, kind, raw["owner"], raw["sha256"], block_id, key, style, item, executable
    )


def _created(raw: Any, index: int) -> Created:
    where = f"created[{index}]"
    if not isinstance(raw, dict) or not isinstance(raw.get("path"), str):
        raise LockError(f"{where}: must be an object with path")
    try:
        path = str(fsutil.safe_relpath(raw["path"]))
    except fsutil.UnsafePathError as exc:
        raise LockError(f"{where}: unsafe path ({exc})") from exc
    file = raw.get("file", False)
    if not isinstance(file, bool):
        raise LockError(f"{where}: file must be true or false")
    containers = raw.get("containers", [])
    if not isinstance(containers, list) or not all(
        isinstance(c, str) and c for c in containers
    ):
        raise LockError(f"{where}: containers must be a list of keys")
    return Created(path, file, tuple(containers))


def read(project: Path) -> Lock | None:
    path = lock_path(project)
    try:
        raw = json.loads(fsutil.read_bytes(path).decode("utf-8"))
    except FileNotFoundError:
        return None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LockError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(raw, dict):
        raise LockError(f"{path}: the root must be an object")
    if raw.get("schema") != SCHEMA:
        raise LockError(f"{path}: unsupported schema {raw.get('schema')!r} (expected {SCHEMA})")
    files = raw.get("files", [])
    if not isinstance(files, list):
        raise LockError(f"{path}: files must be a list")
    created = raw.get("created", [])
    if not isinstance(created, list):
        raise LockError(f"{path}: created must be a list")
    return Lock(
        engine_version=str(raw.get("engine_version", "")),
        agents=[str(a) for a in raw.get("agents", [])],
        packs=[str(p) for p in raw.get("packs", [])],
        files=[_entry(item, i) for i, item in enumerate(files)],
        created=[_created(item, i) for i, item in enumerate(created)],
    )


def _serialize(entry: LockEntry) -> dict[str, Any]:
    out: dict[str, Any] = {
        "path": entry.path,
        "kind": entry.kind,
        "owner": entry.owner,
        "sha256": entry.sha256,
    }
    if entry.block_id is not None:
        out["block_id"] = entry.block_id
    if entry.key is not None:
        out["key"] = entry.key
    if entry.style is not None:
        out["style"] = entry.style
    if entry.item is not None:
        out["item"] = entry.item
    if entry.executable:
        out["executable"] = True
    return out


def _serialize_created(created: Created) -> dict[str, Any]:
    out: dict[str, Any] = {"path": created.path}
    if created.file:
        out["file"] = True
    if created.containers:
        out["containers"] = list(created.containers)
    return out


def write(project: Path, data: Lock) -> bool:
    """Escribe el lock ordenado, de forma atómica. Devuelve si cambió."""
    return fsutil.write_if_changed(lock_path(project), dumps(data))


def dumps(data: Lock) -> bytes:
    """Serialización determinista del lock (entradas ordenadas)."""
    payload = {
        "schema": SCHEMA,
        "engine_version": data.engine_version,
        "agents": list(data.agents),
        "packs": list(data.packs),
        "files": [_serialize(e) for e in sorted(data.files, key=LockEntry.sort_key)],
        "created": [_serialize_created(c) for c in sorted(data.created)],
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# -- drift --------------------------------------------------------------------


def current_hash(project: Path, entry: LockEntry, *, strict: bool = False) -> str | None:
    """Hash actual de lo que registra la entrada, o None si ya no existe.

    Si el archivo no se puede analizar (marcadores rotos, JSON inválido), devuelve el
    hash del archivo entero, que cuenta como cambio manual; con `strict`, lanza el error.
    """
    target = fsutil.resolve_within(project, entry.path)
    if not target.exists():
        return None
    if entry.kind in ("file", "mirror"):
        return fsutil.sha256_file(target)
    if entry.kind == "block":
        try:
            blocks = filemerge.list_blocks(target, style=entry.style)
        except filemerge.BlockError:
            if strict:
                raise
            return fsutil.sha256_file(target)
        found = next((b for b in blocks if b.id == entry.block_id), None)
        return None if found is None else hash_block_content(found.content)
    try:
        value = structmerge.get_json_key(target, entry.key or "", strict=strict)
    except structmerge.StructMergeError:
        if strict:
            raise
        return fsutil.sha256_file(target)
    if value is structmerge.MISSING:
        return None
    if entry.kind == "item":
        present = isinstance(value, list) and entry.item in value
        return hash_json_value(entry.item) if present else None
    return hash_json_value(value)


def drift(project: Path, data: Lock | None = None) -> list[Drift]:
    """Entradas cuyo estado actual no coincide con el hash del lock."""
    data = data if data is not None else read(project)
    if data is None:
        return []
    found: list[Drift] = []
    for entry in sorted(data.files, key=LockEntry.sort_key):
        try:
            actual = current_hash(project, entry)
        except (fsutil.UnsafePathError, OSError):
            found.append(Drift(entry, "unreadable", None))
            continue
        if actual is None:
            found.append(Drift(entry, "missing", None))
        elif actual != entry.sha256:
            found.append(Drift(entry, "modified", actual))
    return found
