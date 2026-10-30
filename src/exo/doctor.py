"""Diagnóstico del entorno (`exo doctor`). F2 y F3 suman chequeos de agentes y memoria.

Cada chequeo devuelve `ok`, `info`, `warn` o `error`. Solo `error` hace que
`exo doctor` salga con 1. Los autotests (filemerge y determinismo de
snapshots) corren en un directorio temporal y no tocan el proyecto.
"""

from __future__ import annotations

import platform
import shutil
import sys
import sysconfig
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from exo import _meta, content, packs
from exo.core import config, filemerge, snapshots

MIN_PYTHON = (3, 10)
MIN_FREE_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # ok | info | warn | error
    detail: str


def _python(project: Path) -> Check:
    version = ".".join(str(n) for n in sys.version_info[:3])
    if tuple(sys.version_info[:2]) < MIN_PYTHON:
        needed = ".".join(map(str, MIN_PYTHON))
        return Check("python", "error", f"Python {version}; se necesita {needed} o más")
    return Check("python", "ok", f"Python {version} ({sys.executable})")


def _platform(project: Path) -> Check:
    return Check("platform", "info", platform.platform())


def _encoding(project: Path) -> Check:
    encoding = (getattr(sys.stdout, "encoding", None) or "desconocido").lower()
    if encoding.replace("-", "") in ("utf8",):
        return Check("encoding", "ok", encoding)
    return Check(
        "encoding",
        "warn",
        f"la consola usa {encoding}; algunos caracteres pueden verse mal. "
        "La salida --json siempre sale en UTF-8.",
    )


def _version(project: Path) -> Check:
    return Check("version", "ok", f"{_meta.NAME} {_meta.VERSION}")


def _path(project: Path) -> Check:
    found = shutil.which(_meta.NAME)
    if found is None:
        return Check(
            "path",
            "warn",
            f"`{_meta.NAME}` no está en el PATH; activá el entorno o reinstalá el motor",
        )
    expected = Path(sysconfig.get_path("scripts")).resolve()
    if Path(found).resolve().parent != expected:
        return Check(
            "path",
            "warn",
            f"el primer `{_meta.NAME}` del PATH ({found}) no es este motor ({expected}); "
            "puede ser otro proyecto con el mismo nombre (ADR-0001)",
        )
    return Check("path", "ok", found)


def _content(project: Path) -> Check:
    try:
        root = content.content_root()
        collection = packs.load_collection(root)
    except (content.ContentError, packs.PackError) as exc:
        return Check("content", "error", str(exc))
    return Check(
        "content",
        "ok",
        f"{len(collection.packs)} packs y {len(collection.skills)} skills en {root}",
    )


def _disk(project: Path) -> Check:
    free = shutil.disk_usage(Path.home()).free
    megabytes = free // (1024 * 1024)
    if free < MIN_FREE_BYTES:
        return Check("disk", "warn", f"quedan {megabytes} MB libres en el directorio de usuario")
    return Check("disk", "ok", f"{megabytes} MB libres")


def _selftest_filemerge(project: Path) -> Check:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "AGENTS.md"
        target.write_bytes(b"# humano\n")
        first = filemerge.inject(target, "selftest", "x")
        second = filemerge.inject(target, "selftest", "x")
        filemerge.remove(target, "selftest")
        if not first or second or target.read_bytes() != b"# humano\n":
            return Check("filemerge", "error", "inject/remove no es idempotente o no es reversible")
    return Check("filemerge", "ok", "inject idempotente y reversible")


def _selftest_snapshots(project: Path) -> Check:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a").mkdir()
        (root / "a" / "f.txt").write_bytes(b"contenido")
        first = snapshots.build_archive(root, ["a"])
        second = snapshots.build_archive(root, ["a"])
    if first != second:
        return Check("snapshots", "error", "dos snapshots del mismo árbol difieren")
    return Check("snapshots", "ok", "snapshots deterministas")


def _config(project: Path) -> Check:
    result = config.load(project)
    if result.source is None:
        return Check("config", "info", f"sin config del proyecto en {config.config_path(project)}")
    if result.warnings:
        return Check("config", "warn", "; ".join(result.warnings))
    return Check("config", "ok", str(result.source))


CHECKS: tuple[Callable[[Path], Check], ...] = (
    _python,
    _platform,
    _encoding,
    _version,
    _path,
    _content,
    _disk,
    _selftest_filemerge,
    _selftest_snapshots,
    _config,
)
_NAMES = {
    _selftest_filemerge: "filemerge",
    _selftest_snapshots: "snapshots",
}


def run_checks(project: Path) -> list[Check]:
    results: list[Check] = []
    for check in CHECKS:
        try:
            results.append(check(Path(project)))
        except Exception as exc:  # un chequeo roto no corta el diagnóstico
            name = _NAMES.get(check, check.__name__.lstrip("_"))
            results.append(Check(name, "error", f"el chequeo falló: {exc}"))
    return results
