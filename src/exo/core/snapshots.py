"""Snapshots tar.gz deterministas de rutas gestionadas, con restore seguro.

Invariantes 1 y 10 de `docs/plan/02-ARQUITECTURA.md` §2.13: snapshot antes de
mutar; snapshots deterministas (entradas ordenadas, metadata normalizada, gzip
con mtime 0) y extracción segura (rechaza traversal, links y devices).

Cada snapshot lleva un manifiesto con las raíces capturadas, cuáles eran
directorios y cuáles no existían, para que `restore` deje cada raíz como estaba:
reescribe los archivos y borra lo que no existía en el momento del snapshot.
Viven en `<PROJECT_DIR>/backups/`; se conservan `DEFAULT_KEEP` sin fijar.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import re
import shutil
import stat
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from exo import _meta
from exo.core import fsutil

DEFAULT_KEEP = 5
MANIFEST_NAME = f".{_meta.NAME}-snapshot.json"
BACKUPS = "backups"
PINS = "pins.json"
_NAME = re.compile(r"^\d{8}T\d{12}Z-([0-9a-f]{12})(?:-\d+)?\.tar\.gz$")
_HASH_LEN = 12


class SnapshotError(ValueError):
    """Operación de backup inválida (nombre, existencia, pins)."""


class UnsafeArchiveError(SnapshotError):
    """El tar.gz tiene entradas peligrosas o no es un snapshot del motor."""


@dataclass(frozen=True)
class Snapshot:
    name: str
    path: Path
    size: int
    pinned: bool = False

    @property
    def content_hash(self) -> str:
        match = _NAME.match(self.name)
        return match.group(1) if match else ""


@dataclass
class Archive:
    manifest: dict
    files: dict[str, tuple[bytes, int]] = field(default_factory=dict)


@dataclass
class RestoreResult:
    before: Snapshot | None
    restored: list[str]
    removed: list[str]


def backups_dir(project: Path) -> Path:
    return Path(project) / _meta.PROJECT_DIR / BACKUPS


# -- armado -------------------------------------------------------------------


def _mode(path: Path) -> int:
    return 0o755 if os.stat(path).st_mode & stat.S_IXUSR and os.name != "nt" else 0o644


def _collect(project: Path, roots: list[str]) -> tuple[dict, dict[str, Path]]:
    excluded = backups_dir(project).resolve()
    files: dict[str, Path] = {}
    dirs: list[str] = []
    absent: list[str] = []
    for root in roots:
        target = fsutil.resolve_within(project, root)
        if target.is_dir():
            dirs.append(root)
            for current, subdirs, names in os.walk(target):
                subdirs.sort()
                here = Path(current)
                if here.resolve().is_relative_to(excluded):
                    subdirs.clear()
                    continue
                for name in sorted(names):
                    item = here / name
                    if item.is_symlink() or not item.is_file():
                        continue
                    files[item.relative_to(project).as_posix()] = item
        elif target.is_file():
            files[root] = target
        else:
            absent.append(root)
    manifest = {"schema": 1, "roots": roots, "dirs": dirs, "absent": absent}
    return manifest, files


def _member(name: str, data: bytes, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.type = tarfile.REGTYPE
    return info


def _tar_bytes(project: Path, paths: list[str]) -> bytes:
    roots = sorted({str(fsutil.safe_relpath(p)) for p in paths})
    manifest, files = _collect(Path(project), roots)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        payload = json.dumps(manifest, sort_keys=True).encode("utf-8")
        tar.addfile(_member(MANIFEST_NAME, payload, 0o644), io.BytesIO(payload))
        for name in sorted(files):
            data = fsutil.read_bytes(files[name])
            tar.addfile(_member(name, data, _mode(files[name])), io.BytesIO(data))
    return raw.getvalue()


def _gzip(data: bytes) -> bytes:
    out = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=out, compresslevel=9, mtime=0) as gz:
        gz.write(data)
    return out.getvalue()


def build_archive(project: Path, paths: list[str]) -> bytes:
    """Tar.gz determinista de las rutas (archivos o directorios) relativas a `project`."""
    return _gzip(_tar_bytes(project, paths))


# -- lectura segura -----------------------------------------------------------


def _read_members(tar: tarfile.TarFile) -> Archive:
    archive = Archive(manifest={})
    for member in tar.getmembers():
        if not member.isreg():
            raise UnsafeArchiveError(
                f"entrada {member.name!r} de tipo no permitido (solo archivos regulares)"
            )
        content = tar.extractfile(member).read()
        if member.name == MANIFEST_NAME:
            try:
                archive.manifest = json.loads(content)
            except json.JSONDecodeError as exc:
                raise UnsafeArchiveError(f"manifiesto ilegible ({exc})") from exc
            continue
        try:
            name = str(fsutil.safe_relpath(member.name))
        except fsutil.UnsafePathError as exc:
            raise UnsafeArchiveError(f"ruta insegura en el backup: {exc}") from exc
        if name in archive.files:
            raise UnsafeArchiveError(f"ruta repetida en el backup: {name!r}")
        archive.files[name] = (content, 0o755 if member.mode & 0o111 else 0o644)
    return archive


def read_archive(data: bytes) -> Archive:
    """Valida todas las entradas antes de devolver nada."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            archive = _read_members(tar)
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise UnsafeArchiveError(f"no es un tar.gz válido ({exc})") from exc
    manifest = archive.manifest
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise UnsafeArchiveError("falta el manifiesto del snapshot o su esquema no es 1")
    try:
        for key in ("roots", "dirs", "absent"):
            manifest[key] = [str(fsutil.safe_relpath(p)) for p in manifest.get(key, [])]
    except fsutil.UnsafePathError as exc:
        raise UnsafeArchiveError(f"ruta insegura en el manifiesto: {exc}") from exc
    return archive


# -- pins, listado y poda -----------------------------------------------------


def _pins(project: Path) -> set[str]:
    try:
        raw = json.loads(fsutil.read_bytes(backups_dir(project) / PINS))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()
    return {str(n) for n in raw.get("pinned", [])} if isinstance(raw, dict) else set()


def _write_pins(project: Path, pinned: set[str]) -> None:
    payload = json.dumps({"schema": 1, "pinned": sorted(pinned)}, indent=2) + "\n"
    fsutil.write_if_changed(backups_dir(project) / PINS, payload.encode("utf-8"))


def list_snapshots(project: Path) -> list[Snapshot]:
    folder = backups_dir(project)
    if not folder.is_dir():
        return []
    pinned = _pins(project)
    return [
        Snapshot(p.name, p, p.stat().st_size, p.name in pinned)
        for p in sorted(folder.iterdir())
        if p.is_file() and _NAME.match(p.name)
    ]


def _existing(project: Path, name: str) -> Path:
    if not _NAME.match(name):
        raise SnapshotError(f"nombre de backup inválido: {name!r}")
    path = backups_dir(project) / name
    if not path.is_file():
        raise SnapshotError(f"no existe el backup {name!r}; mirá `{_meta.NAME} backups list`")
    return path


def pin(project: Path, name: str) -> bool:
    _existing(project, name)
    pinned = _pins(project)
    if name in pinned:
        return False
    _write_pins(project, pinned | {name})
    return True


def unpin(project: Path, name: str) -> bool:
    pinned = _pins(project)
    if name not in pinned:
        return False
    _write_pins(project, pinned - {name})
    return True


def prune(project: Path, keep: int = DEFAULT_KEEP) -> list[str]:
    """Borra los snapshots sin fijar más viejos hasta dejar `keep`. Devuelve los borrados."""
    loose = [s for s in list_snapshots(project) if not s.pinned]
    removed = [s.name for s in loose[: max(0, len(loose) - keep)]]
    for name in removed:
        (backups_dir(project) / name).unlink()
    return removed


def snapshot(project: Path, paths: list[str], *, keep: int = DEFAULT_KEEP) -> Snapshot:
    """Crea un snapshot de `paths` o devuelve el último si el contenido es el mismo."""
    tar = _tar_bytes(project, paths)
    digest = fsutil.sha256_bytes(tar)[:_HASH_LEN]
    existing = list_snapshots(project)
    if existing and existing[-1].content_hash == digest:
        return existing[-1]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = backups_dir(project)
    name = f"{stamp}-{digest}.tar.gz"
    counter = 1
    while (folder / name).exists():
        name = f"{stamp}-{digest}-{counter}.tar.gz"
        counter += 1
    data = _gzip(tar)
    fsutil.write_atomic(folder / name, data)
    prune(project, keep)
    pinned = name in _pins(project)
    return Snapshot(name, folder / name, len(data), pinned)


# -- restore ------------------------------------------------------------------


def _remove_tree(project: Path, target: Path, removed: list[str]) -> None:
    if target.is_dir() and not target.is_symlink():
        for item in sorted(target.rglob("*")):
            if item.is_file() or item.is_symlink():
                removed.append(item.relative_to(project).as_posix())
        shutil.rmtree(target)
    elif target.exists() or target.is_symlink():
        removed.append(target.relative_to(project).as_posix())
        target.unlink()


def restore(project: Path, name: str) -> RestoreResult:
    """Vuelve las raíces del snapshot a su estado. Antes snapshotea el estado actual."""
    project = Path(project)
    archive = read_archive(fsutil.read_bytes(_existing(project, name)))
    manifest = archive.manifest
    before = snapshot(project, manifest["roots"]) if manifest["roots"] else None
    removed: list[str] = []
    for root in manifest["absent"]:
        _remove_tree(project, fsutil.resolve_within(project, root), removed)
    for root in manifest["dirs"]:
        target = fsutil.resolve_within(project, root)
        if not target.is_dir():
            continue
        for item in sorted(target.rglob("*")):
            rel = item.relative_to(project).as_posix()
            if (item.is_file() or item.is_symlink()) and rel not in archive.files:
                item.unlink()
                removed.append(rel)
    restored: list[str] = []
    for rel, (data, mode) in sorted(archive.files.items()):
        target = fsutil.resolve_within(project, rel)
        if target.is_dir():
            _remove_tree(project, target, removed)
        if fsutil.write_if_changed(target, data, mode=mode):
            restored.append(rel)
    return RestoreResult(before, restored, sorted(removed))
