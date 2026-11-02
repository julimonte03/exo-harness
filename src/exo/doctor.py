"""Diagnóstico del entorno (`exo doctor`). F2 y F3 suman chequeos de agentes y memoria.

Cada chequeo devuelve `ok`, `info`, `warn` o `error`. Solo `error` hace que
`exo doctor` salga con 1. Los autotests (filemerge y determinismo de
snapshots) corren en un directorio temporal y no tocan el proyecto.
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from exo import _meta, content, packs
from exo.core import config, filemerge, lock, snapshots

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


# Claude Code lee AGENTS.md sin CLAUDE.md desde 2.1.281 en todas las sesiones (agent-matrix).
CLAUDE_AGENTS_MD = (2, 1, 281)


def _install(project: Path) -> Check:
    data = lock.read(project)
    if data is None:
        return Check("install", "info", f"el motor no está instalado en {project.resolve()}")
    drift = lock.drift(project, data)
    if drift:
        listed = ", ".join(f"{d.entry.path} ({d.status})" for d in drift[:5])
        more = f" y {len(drift) - 5} más" if len(drift) > 5 else ""
        return Check(
            "install",
            "warn",
            f"cambios manuales sobre lo generado: {listed}{more}; mirá `{_meta.NAME} status`",
        )
    return Check("install", "ok", f"{len(data.files)} unidades gestionadas, sin cambios manuales")


def _claude_version() -> tuple[int, ...] | None:
    exe = shutil.which("claude")
    if exe is None:
        return None
    try:
        out = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=15, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    return tuple(int(n) for n in match.groups()) if match else None


def _claude_code(project: Path) -> Check:
    agents = config.load(project).config["agents"]
    if "claude-code" not in agents:
        return Check("claude-code", "info", "no es agente destino del proyecto")
    if (project / "CLAUDE.md").exists():
        return Check("claude-code", "ok", "CLAUDE.md importa AGENTS.md con @AGENTS.md")
    version = _claude_version()
    needed = ".".join(map(str, CLAUDE_AGENTS_MD))
    if version is None:
        return Check(
            "claude-code",
            "info",
            f"no se pudo leer la versión de Claude Code; sin CLAUDE.md necesita {needed} o más",
        )
    shown = ".".join(map(str, version))
    if version < CLAUDE_AGENTS_MD:
        return Check(
            "claude-code",
            "warn",
            f"Claude Code {shown} puede no leer AGENTS.md sin CLAUDE.md: actualizalo a {needed} "
            f"o corré `{_meta.NAME} init --claude-md --yes`",
        )
    return Check("claude-code", "ok", f"Claude Code {shown} lee AGENTS.md sin CLAUDE.md")


def _claude_trusted(project: Path) -> bool | None:
    """Si el usuario aceptó la confianza del workspace en Claude Code (lectura de ~/.claude.json).

    Formato interno de Claude Code: puede cambiar, por eso el chequeo es solo informativo.
    """
    try:
        data = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, dict):
        return None
    wanted = Path(project).resolve().as_posix().casefold()
    for key, value in projects.items():
        if Path(key).as_posix().casefold() == wanted and isinstance(value, dict):
            return bool(value.get("hasTrustDialogAccepted"))
    return False


def _claude_trust(project: Path) -> Check:
    if "claude-code" not in config.load(project).config["agents"]:
        return Check("claude-trust", "info", "no es agente destino del proyecto")
    trusted = _claude_trusted(project)
    if trusted:
        return Check(
            "claude-trust", "ok", "workspace confiable: se aplican los permisos del proyecto"
        )
    return Check(
        "claude-trust",
        "info",
        "abrí Claude Code una vez en el proyecto y aceptá la confianza del workspace: hasta "
        f"entonces ignora el permiso para `{_meta.NAME}` de .claude/settings.json",
    )


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
    _install,
    _claude_code,
    _claude_trust,
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
