"""Adopción del motor en un proyecto: config, bundle, adaptadores y motor.

`sync` es el núcleo de `exo init`, `exo sync`, `exo add-agent` y
`exo remove-agent`; los comandos solo deciden qué agentes, packs y opciones
pasarle. La config del proyecto es del humano: solo se escribe cuando el
comando pide cambiar algo (agentes, packs, MCP o tickets), se valida antes de
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

from exo import _meta, adapters, content, packs, paths
from exo.adapters.base import Context
from exo.core import config, fsutil, lock, snapshots
from exo.governance import githooks, hosts
from exo.installer import engine
from exo.installer.bundle import build_bundle

DEFAULT_PACKS = ("core", "sdd", "quality", "security")


def _default_packs(root: Path) -> list[str]:
    """Los packs por defecto que el contenido trae: un árbol propio puede no tener todos."""
    return [name for name in DEFAULT_PACKS if (root / "packs" / name / packs.MANIFEST).is_file()]


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
            raise ProjectError(f"unknown agent: {agent!r} (known: {known})")
        if agent not in chosen:
            chosen.append(agent)
    if len(chosen) > 1 and "generic" in chosen:
        chosen.remove("generic")
    return tuple(chosen) or ("generic",)


def _base_config(project: Path) -> tuple[config.LoadResult, dict[str, Any], list[str]]:
    """Config de partida. Si existe pero no se puede usar, ProjectError: con los defaults
    se borraría lo de los agentes. Si falta y el motor está instalado, agentes y packs
    salen del lock, por la misma razón."""
    loaded = config.load(project)
    if loaded.fallback or loaded.invalid:
        problems = " | ".join(loaded.invalid or loaded.warnings)
        raise ProjectError(
            f"{_meta.PROJECT_DIR}/{config.FILENAME} cannot be used ({problems}). "
            "Fix it and retry: with the defaults, your agents' files would be removed."
        )
    cfg = copy.deepcopy(loaded.config)
    notes: list[str] = []
    if loaded.source is None:
        previous = lock.read(project)
        if previous is not None:
            cfg["agents"], cfg["packs"] = list(previous.agents), list(previous.packs)
            notes.append(
                f"{_meta.PROJECT_DIR}/{config.FILENAME} is missing: "
                "using the agents and packs from the lock"
            )
    return loaded, cfg, notes


def current_agents(project: Path) -> list[str] | None:
    """Agentes del proyecto (de la config o, si falta, del lock); None si no está instalado."""
    project = Path(project).resolve()
    loaded, cfg, notes = _base_config(project)
    if loaded.source is None and not notes:
        return None
    return list(cfg["agents"])


def sync(
    project: Path,
    *,
    agents: Iterable[str] | None = None,
    packs: Iterable[str] | None = None,
    mcp: bool | None = None,
    tickets: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    detect_host: bool = False,
    claude_md: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> SyncResult:
    project = Path(project).resolve()
    loaded, cfg, base_notes = _base_config(project)
    explicit = agents is not None or packs is not None or mcp is not None or tickets is not None
    if agents is not None:
        cfg["agents"] = list(agents)
    if packs is not None:
        cfg["packs"] = list(packs)
    if mcp is not None:
        cfg["mcp"]["enabled"] = mcp
    if tickets is not None:
        cfg["tickets"] = dict(tickets)
    if review:
        cfg["review"].update(review)
        explicit = True
    host_note = None
    if detect_host and not cfg["review"].get("host"):
        detected = hosts.detect(project)
        if detected:
            cfg["review"]["host"] = detected
            explicit = True
            host_note = detected
    targets = normalize_agents(cfg["agents"])
    try:
        root = content.content_root()
        bundle = build_bundle(root, list(cfg["packs"] or _default_packs(root)))
    except ValueError as exc:
        raise ProjectError(str(exc)) from exc
    if explicit:
        cfg["agents"] = list(targets)
        cfg["packs"] = list(bundle.packs)
    normalized, _, invalid = config.validate(cfg)
    if invalid:
        raise ProjectError("invalid values for the config: " + " | ".join(invalid))
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
    notes = [*base_notes, *loaded.warnings, *adapters.GENERIC.notes(ctx)]
    if result.applied and not dry_run:
        notes += _githooks(project, normalized, result)
    if host_note and not normalized["review"].get("publish_command"):
        notes.append(
            f"the repo lives on {host_note} (review.host); to publish the gates as PR comments, "
            "set review.publish_command (examples in the ci-and-review contract)"
        )
    written = result.applied and bool(extra)
    return SyncResult(result, list(targets), list(bundle.packs), notes, written)


def _githooks(project: Path, cfg: dict[str, Any], result: engine.Result) -> list[str]:
    """Activa o desactiva los git hooks en este clon, después de aplicar (D-21)."""
    if not githooks.enabled(cfg):
        return ["git hooks turned off in this clone"] if githooks.deactivate(project) else []
    if githooks.mechanism(project) == "husky":
        touched = any(
            a.path.startswith(f"{githooks.HUSKY}/") and a.action in ("create", "update")
            for a in result.actions
        )
        return [f"git hooks added to husky ({githooks.HUSKY}/)"] if touched else []
    return githooks.activate(project)


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
    # Archivos de la carpeta del motor que no generó él (notas del humano, etc.): se
    # borran con la carpeta y quedan en el backup de seguridad.
    also_removed: list[str] = field(default_factory=list)


def uninstall(project: Path, *, force: bool = False, dry_run: bool = False) -> UninstallResult:
    """Revierte todo lo del lock y borra la carpeta del motor.

    Antes guarda un backup de seguridad fuera del proyecto, en la carpeta de datos
    de usuario, para que el proyecto quede idéntico al original.
    """
    project = Path(project).resolve()
    data = lock.read(project)
    motor_dir = project / _meta.PROJECT_DIR
    if data is None and not motor_dir.exists():
        raise ProjectError(f"the engine is not installed in {project}")
    # Lo que pasa por un link queda fuera del backup; el motor lo informa sin tocarlo.
    roots = sorted({e.path for e in (data.files if data else []) if _safe(project, e.path)})
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
    if result.applied and not dry_run:
        githooks.deactivate(project)
    also_removed = _human_files_in(project, motor_dir, data)
    if result.applied and not result.unresolved and motor_dir.is_dir():
        if fsutil.is_link(motor_dir):
            raise ProjectError(f"{motor_dir} is a link; not deleting it")
        shutil.rmtree(motor_dir)
    return UninstallResult(result, backup, also_removed)


def _safe(project: Path, rel: str) -> bool:
    try:
        fsutil.join_within(project, rel)
    except fsutil.UnsafePathError:
        return False
    return True


def _human_files_in(project: Path, motor_dir: Path, data: lock.Lock | None) -> list[str]:
    own = {lock.FILENAME, config.FILENAME, snapshots.backups_dir(project).name}
    tracked = {e.path for e in (data.files if data else [])}
    if not motor_dir.is_dir() or fsutil.is_link(motor_dir):
        return []
    found = (path.relative_to(project).as_posix() for path in fsutil.walk_files(motor_dir))
    return sorted(
        rel
        for rel in found
        if rel not in tracked and Path(rel).relative_to(_meta.PROJECT_DIR).parts[0] not in own
    )
