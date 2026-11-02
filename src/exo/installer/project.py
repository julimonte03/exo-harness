"""Adopción del motor en un proyecto: config, bundle, adaptadores y motor.

`sync` es el núcleo de `exo init`, `exo sync`, `exo add-agent` y
`exo remove-agent`; los comandos solo deciden qué agentes, packs y opciones
pasarle. La config del proyecto es del humano: solo se escribe cuando el
comando pide cambiar algo (agentes, packs, MCP o tracker), se valida antes de
tocar nada y va en la misma transacción que el resto, con su snapshot. Si la
config existe pero no se puede usar, se aborta: con los defaults se borraría
lo de los agentes que tiene configurados.
"""

from __future__ import annotations

import copy
import shutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exo import _meta, adapters, content, paths
from exo.adapters.base import Context
from exo.core import config, fsutil, lock, snapshots
from exo.installer import engine
from exo.installer.bundle import build_bundle

DEFAULT_PACKS = ("core", "sdd")


class ProjectError(ValueError):
    """Pedido inválido: agente desconocido, pack inexistente, etc."""


@dataclass
class SyncResult:
    engine: engine.Result
    agents: list[str]
    packs: list[str]
    notes: list[str] = field(default_factory=list)
    config_written: bool = False


def normalize_agents(agents: Iterable[str]) -> tuple[str, ...]:
    """Agentes válidos y sin repetir; sin ninguno, solo la base genérica."""
    chosen: list[str] = []
    for agent in agents:
        if agent not in adapters.KNOWN_AGENTS:
            known = ", ".join(adapters.KNOWN_AGENTS)
            raise ProjectError(f"agente desconocido: {agent!r} (conocidos: {known})")
        if agent not in chosen:
            chosen.append(agent)
    if len(chosen) > 1 and "generic" in chosen:
        chosen.remove("generic")
    return tuple(chosen) or ("generic",)


def sync(
    project: Path,
    *,
    agents: Iterable[str] | None = None,
    packs: Iterable[str] | None = None,
    mcp: bool | None = None,
    tracker: dict[str, Any] | None = None,
    claude_md: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> SyncResult:
    project = Path(project).resolve()
    loaded = config.load(project)
    if loaded.fallback or loaded.invalid:
        problems = " | ".join(loaded.invalid or loaded.warnings)
        raise ProjectError(
            f"{_meta.PROJECT_DIR}/{config.FILENAME} no se puede usar ({problems}). "
            "Corregila y repetí: con los defaults se borraría lo de tus agentes."
        )
    cfg = copy.deepcopy(loaded.config)
    explicit = agents is not None or packs is not None or mcp is not None or bool(tracker)
    if agents is not None:
        cfg["agents"] = list(agents)
    if packs is not None:
        cfg["packs"] = list(packs)
    if mcp is not None:
        cfg["mcp"]["enabled"] = mcp
    if tracker:
        cfg["tracker"].update(tracker)
    targets = normalize_agents(cfg["agents"])
    try:
        bundle = build_bundle(content.content_root(), list(cfg["packs"] or DEFAULT_PACKS))
    except ValueError as exc:
        raise ProjectError(str(exc)) from exc
    if explicit:
        cfg["agents"] = list(targets)
        cfg["packs"] = list(bundle.packs)
    normalized, _, invalid = config.validate(cfg)
    if invalid:
        raise ProjectError("valores inválidos para la config: " + " | ".join(invalid))
    extra: dict[str, bytes] = {}
    if explicit and (loaded.source is None or normalized != loaded.config):
        extra[f"{_meta.PROJECT_DIR}/{config.FILENAME}"] = config.dumps(normalized)
    ctx = Context(project, bundle, targets, normalized, claude_md="always" if claude_md else "auto")
    result = engine.apply(
        project,
        adapters.plan_all(ctx),
        agents=list(targets),
        packs=list(bundle.packs),
        force=force,
        dry_run=dry_run,
        extra=extra,
    )
    notes = [*loaded.warnings, *adapters.GENERIC.notes(ctx)]
    written = result.applied and bool(extra)
    return SyncResult(result, list(targets), list(bundle.packs), notes, written)


# -- estado y desinstalación ----------------------------------------------------


@dataclass
class Status:
    installed: bool
    agents: list[str]
    packs: list[str]
    lock_version: str | None
    files: int
    drift: list[lock.Drift]
    warnings: list[str]


def status(project: Path) -> Status:
    project = Path(project).resolve()
    loaded = config.load(project)
    data = lock.read(project)
    return Status(
        installed=data is not None,
        agents=list(loaded.config["agents"]),
        packs=list(loaded.config["packs"]),
        lock_version=data.engine_version if data else None,
        files=len(data.files) if data else 0,
        drift=lock.drift(project, data) if data else [],
        warnings=loaded.warnings,
    )


@dataclass
class UninstallResult:
    engine: engine.Result
    backup: Path | None


def uninstall(project: Path, *, force: bool = False, dry_run: bool = False) -> UninstallResult:
    """Revierte todo lo del lock y borra la carpeta del motor.

    Antes guarda un backup de seguridad fuera del proyecto, en la carpeta de datos
    de usuario, para que el proyecto quede idéntico al original.
    """
    project = Path(project).resolve()
    data = lock.read(project)
    motor_dir = project / _meta.PROJECT_DIR
    if data is None and not motor_dir.exists():
        raise ProjectError(f"el motor no está instalado en {project}")
    roots = sorted({e.path for e in (data.files if data else [])})
    if motor_dir.is_dir():
        roots.append(_meta.PROJECT_DIR)
    backup = None
    if not dry_run:
        archive = snapshots.build_archive(project, roots)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name = f"{project.name}-{stamp}-{fsutil.sha256_bytes(archive)[:12]}.tar.gz"
        backup = paths.user_data_dir() / "uninstall-backups" / name
        fsutil.write_atomic(backup, archive)
    result = engine.apply(project, [], agents=[], packs=[], force=force, dry_run=dry_run)
    if result.applied and not result.unresolved and motor_dir.is_dir():
        if fsutil.is_link(motor_dir):
            raise ProjectError(f"{motor_dir} es un link; no se borra")
        shutil.rmtree(motor_dir)
    return UninstallResult(result, backup)
