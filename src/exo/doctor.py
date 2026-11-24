"""Diagnóstico del entorno (`exo doctor`). F2 y F3 suman chequeos de agentes y memoria.

Cada chequeo devuelve `ok`, `info`, `warn` o `error`. Solo `error` hace que
`exo doctor` salga con 1. Los autotests (filemerge y determinismo de
snapshots) corren en un directorio temporal y no tocan el proyecto.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from exo import _meta, content, packs, paths
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
        return Check("python", "error", f"Python {version}; {needed} or later is required")
    return Check("python", "ok", f"Python {version} ({sys.executable})")


def _platform(project: Path) -> Check:
    return Check("platform", "info", platform.platform())


def _encoding(project: Path) -> Check:
    encoding = (getattr(sys.stdout, "encoding", None) or "unknown").lower()
    if encoding.replace("-", "") in ("utf8",):
        return Check("encoding", "ok", encoding)
    return Check(
        "encoding",
        "warn",
        f"the console uses {encoding}; some characters may display incorrectly. "
        "--json output is always UTF-8.",
    )


def _version(project: Path) -> Check:
    return Check("version", "ok", f"{_meta.NAME} {_meta.VERSION}")


def _path(project: Path) -> Check:
    found = shutil.which(_meta.NAME)
    if found is None:
        return Check(
            "path",
            "warn",
            f"`{_meta.NAME}` is not on the PATH; activate the environment or reinstall the engine",
        )
    expected = Path(sysconfig.get_path("scripts")).resolve()
    if Path(found).resolve().parent != expected:
        return Check(
            "path",
            "warn",
            f"the first `{_meta.NAME}` on the PATH ({found}) is not this engine ({expected}); "
            "it may be another project with the same name (ADR-0001)",
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
        f"{len(collection.packs)} packs and {len(collection.skills)} skills in {root}",
    )


def _disk(project: Path) -> Check:
    free = shutil.disk_usage(Path.home()).free
    megabytes = free // (1024 * 1024)
    if free < MIN_FREE_BYTES:
        return Check("disk", "warn", f"only {megabytes} MB free in the home directory")
    return Check("disk", "ok", f"{megabytes} MB free")


def _selftest_filemerge(project: Path) -> Check:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "AGENTS.md"
        target.write_bytes(b"# humano\n")
        first = filemerge.inject(target, "selftest", "x")
        second = filemerge.inject(target, "selftest", "x")
        filemerge.remove(target, "selftest")
        if not first or second or target.read_bytes() != b"# humano\n":
            return Check("filemerge", "error", "inject/remove is not idempotent or not reversible")
    return Check("filemerge", "ok", "inject is idempotent and reversible")


def _selftest_snapshots(project: Path) -> Check:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a").mkdir()
        (root / "a" / "f.txt").write_bytes(b"contenido")
        first = snapshots.build_archive(root, ["a"])
        second = snapshots.build_archive(root, ["a"])
    if first != second:
        return Check("snapshots", "error", "two snapshots of the same tree differ")
    return Check("snapshots", "ok", "snapshots are deterministic")


def _config(project: Path) -> Check:
    result = config.load(project)
    if result.source is None:
        return Check("config", "info", f"no project config at {config.config_path(project)}")
    if result.warnings:
        return Check("config", "warn", "; ".join(result.warnings))
    return Check("config", "ok", str(result.source))


# Claude Code lee AGENTS.md sin CLAUDE.md desde 2.1.281 en todas las sesiones (agent-matrix).
CLAUDE_AGENTS_MD = (2, 1, 281)


def _lock_version(data: lock.Lock) -> str | None:
    """Aviso si el lock lo escribió otra versión del motor (F8)."""
    written = data.engine_version or "an unknown version"
    if data.engine_version == _meta.VERSION:
        return None
    if lock.newer_than_engine(data.engine_version):
        return (
            f"the lock was written by {_meta.NAME} {written}, newer than this engine "
            f"({_meta.VERSION}); upgrade {_meta.NAME}"
        )
    return f"the lock was written by {_meta.NAME} {written}; run `{_meta.NAME} update`"


def _install(project: Path) -> Check:
    data = lock.read(project)
    if data is None:
        return Check("install", "info", f"the engine is not installed in {project.resolve()}")
    problems = [p for p in (_lock_version(data),) if p]
    drift = lock.drift(project, data)
    if drift:
        listed = ", ".join(f"{d.entry.path} ({d.status})" for d in drift[:5])
        more = f" and {len(drift) - 5} more" if len(drift) > 5 else ""
        problems.append(
            f"manual changes to generated files: {listed}{more}; see `{_meta.NAME} status`"
        )
    if problems:
        return Check("install", "warn", "; ".join(problems))
    return Check("install", "ok", f"{len(data.files)} managed units, no manual changes")


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
        return Check("claude-code", "info", "not a target agent of the project")
    if (project / "CLAUDE.md").exists():
        return Check("claude-code", "ok", "CLAUDE.md imports AGENTS.md with @AGENTS.md")
    version = _claude_version()
    needed = ".".join(map(str, CLAUDE_AGENTS_MD))
    if version is None:
        return Check(
            "claude-code",
            "info",
            f"could not read the Claude Code version; without CLAUDE.md it needs {needed} or later",
        )
    shown = ".".join(map(str, version))
    if version < CLAUDE_AGENTS_MD:
        return Check(
            "claude-code",
            "warn",
            f"Claude Code {shown} may not read AGENTS.md without CLAUDE.md: update it to {needed} "
            f"or run `{_meta.NAME} init --claude-md --yes`",
        )
    return Check("claude-code", "ok", f"Claude Code {shown} reads AGENTS.md without CLAUDE.md")


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
        return Check("claude-trust", "info", "not a target agent of the project")
    trusted = _claude_trusted(project)
    if trusted:
        return Check("claude-trust", "ok", "workspace trusted: the project permissions apply")
    return Check(
        "claude-trust",
        "info",
        "open Claude Code once in the project and accept the workspace trust dialog: until "
        f"then it ignores the `{_meta.NAME}` permission in .claude/settings.json",
    )


# -- memoria (F3, ADR-0009 y ADR-0010) --------------------------------------------------


def _memory_fts5(project: Path) -> Check:
    from exo.memory import db

    conn = sqlite3.connect(":memory:")
    try:
        available = db.fts5_available(conn)
    finally:
        conn.close()
    if available:
        return Check("memory-fts5", "ok", f"FTS5 available (SQLite {sqlite3.sqlite_version})")
    return Check(
        "memory-fts5",
        "warn",
        "this Python lacks FTS5: lexical search ranks results in Python and is slower. "
        "Use a Python from python.org or uv",
    )


def _memory(project: Path) -> Check:
    from exo.memory.store import MemoryStore, MemoryStoreError

    path = paths.memory_db_path()
    if not path.exists():
        return Check("memory", "info", f"no memory at {path} yet; the first `mem save` creates it")
    try:
        with MemoryStore(path, semantic=None) as store:
            stats = store.stats()
    except (MemoryStoreError, sqlite3.Error) as exc:
        return Check("memory", "error", str(exc))
    return Check(
        "memory",
        "ok",
        f"observations: {stats.observations}, projects: {stats.projects}, "
        f"sessions: {stats.sessions} ({path}, schema {stats.schema_version})",
    )


def _memory_semantic(project: Path) -> Check:
    from exo.memory import embeddings, index
    from exo.memory.store import MemoryStore, MemoryStoreError

    how = (
        f"For hybrid search (ADR-0010): pip install {_meta.DIST_NAME}[vector], "
        f"`{_meta.NAME} mem model pull` and `{_meta.NAME} mem reindex --provider local`"
    )
    path = paths.memory_db_path()
    if not path.exists():
        return Check("memory-semantic", "info", f"lexical search only. {how}")
    try:
        with MemoryStore(path) as store:
            config_ = index.read_config(store.conn)
            if config_ is None:
                return Check("memory-semantic", "info", f"lexical search only. {how}")
            name = f"{config_.provider}:{config_.model}"
            if store.semantic is None:
                return Check("memory-semantic", "warn", f"{name}: {store.semantic_note}")
            if config_.provider in embeddings.DEFAULT_MODELS and not embeddings.installed(
                config_.provider
            ):
                extra = "vector" if config_.provider == "onnx" else "static"
                return Check(
                    "memory-semantic",
                    "warn",
                    f"{name}: missing extra; pip install {_meta.DIST_NAME}[{extra}]. "
                    "Until then, searches are lexical",
                )
            if (
                config_.provider in embeddings.DEFAULT_MODELS
                and not embeddings.model_path(config_.provider, config_.model).is_dir()
            ):
                return Check(
                    "memory-semantic",
                    "warn",
                    f"{name}: missing model; `{_meta.NAME} mem model pull {config_.provider}`",
                )
            missing = store.semantic.missing(store.conn)
            backend = store.semantic.backend.name
    except (MemoryStoreError, sqlite3.Error) as exc:
        return Check("memory-semantic", "error", str(exc))
    detail = f"hybrid with {name} (dim {config_.dim}, backend {backend})"
    problems = []
    if backend == "python":
        problems.append(
            "sqlite-vec does not load in this Python (the extra is missing or this Python "
            "does not allow SQLite extensions), so semantic search runs in Python and is slow"
        )
    if missing:
        problems.append(f"{missing} observations without a vector; run `{_meta.NAME} mem reindex`")
    if problems:
        return Check("memory-semantic", "warn", f"{detail}: {'; '.join(problems)}")
    return Check("memory-semantic", "ok", detail)


def _memory_config(project: Path) -> Check:
    loaded = config.load(project)
    if loaded.source is not None and loaded.config.get("memory") != config.defaults()["memory"]:
        return Check(
            "memory-config",
            "info",
            "the memory section of the project config has no effect: memory is per "
            f"user and is configured with `{_meta.NAME} mem reindex` (ADR-0009)",
        )
    return Check("memory-config", "ok", "memory is configured per user")


def _githooks(project: Path) -> Check:
    """Los git hooks del motor (D-21): activos en este clon, o husky / pre-commit con el bloque."""
    from exo.governance import githooks

    if lock.read(project) is None:
        return Check("githooks", "info", "the engine is not installed here")
    found = githooks.status(project)
    return Check("githooks", found.status, found.detail)


def _data_dir(project: Path) -> Check:
    """La carpeta de datos tiene la memoria sin redactar: en POSIX, solo para el dueño (TM-27)."""
    folder = paths.user_data_dir()
    if not folder.is_dir():
        detail = f"{folder} does not exist yet; the engine creates it private"
        return Check("data-dir", "info", detail)
    if os.name == "nt":
        return Check("data-dir", "ok", f"{folder} (per user on Windows)")
    mode = stat.S_IMODE(folder.stat().st_mode)
    if mode & 0o077:
        return Check(
            "data-dir",
            "warn",
            f"{folder} can be read by other users (mode {mode:o}); it holds your memory, "
            f"unredacted: run `chmod 700 {folder}`",
        )
    return Check("data-dir", "ok", f"{folder} (mode {mode:o})")


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
    _githooks,
    _claude_code,
    _claude_trust,
    _memory_fts5,
    _memory,
    _memory_semantic,
    _memory_config,
    _data_dir,
)
_NAMES = {
    _data_dir: "data-dir",
    _selftest_filemerge: "filemerge",
    _selftest_snapshots: "snapshots",
    _memory_fts5: "memory-fts5",
    _memory_semantic: "memory-semantic",
    _memory_config: "memory-config",
}


def run_checks(project: Path) -> list[Check]:
    results: list[Check] = []
    for check in CHECKS:
        try:
            results.append(check(Path(project)))
        except Exception as exc:  # un chequeo roto no corta el diagnóstico
            name = _NAMES.get(check, check.__name__.lstrip("_"))
            results.append(Check(name, "error", f"the check failed: {exc}"))
    return results
