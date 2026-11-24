"""Adopción del motor en un proyecto: config, bundle, adaptadores y motor.

`sync` es el núcleo de `exo init`, `exo sync`, `exo add-agent` y
`exo remove-agent`; los comandos solo deciden qué agentes, packs y opciones
pasarle. La config del proyecto es del humano: solo se escribe cuando el
comando pide cambiar algo (agentes, packs, MCP o tickets), se valida antes de
tocar nada y va en la misma transacción que el resto, con su snapshot. Si la
config existe pero no se puede usar, se aborta: con los defaults se borraría
lo de los agentes que tiene configurados.

Las huérfanas (skills y subagentes que el contenido ya no trae) no se borran sin
`prune` (F8). Lo que deja de pedirse porque la persona sacó un agente o un pack sí:
son las copias que el contenido actual todavía generaría con los agentes y packs
del lock, es decir, de la última instalación.
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
from exo.installer import engine, renames
from exo.installer.bundle import build_bundle
from exo.installer.ops import Op, Unit, unit_of, unit_of_entry

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
    # Huérfana (o la que se borró con prune) -> su nombre nuevo, si es un renombre conocido.
    renamed: dict[str, str] = field(default_factory=dict)
    # (esquema en disco, esquema actual) si la config se migró al leerla.
    config_migration: tuple[int, int] | None = None


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
    prune: bool = False,
    partial: bool = False,
    save_migrated: bool = False,
) -> SyncResult:
    """`partial` y `save_migrated` son de `exo update`: aplicar lo que no choca con lo
    editado, y guardar la config si se migró al leerla."""
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
    config_rel = f"{_meta.PROJECT_DIR}/{config.FILENAME}"
    migrated = loaded.migrated_from
    asked = explicit and (loaded.source is None or normalized != loaded.config)
    if asked or (save_migrated and migrated is not None):
        extra[config_rel] = config.dumps(normalized)
    ctx = Context(project, bundle, targets, normalized, claude_md="always" if claude_md else "auto")
    ops = adapters.plan_all(ctx)
    previous = lock.read(project)
    result = engine.apply(
        project,
        ops,
        agents=list(targets),
        packs=list(bundle.packs),
        force=force,
        dry_run=dry_run,
        extra=extra,
        prune=prune,
        dropped=_dropped(root, ctx, ops, previous),
        partial=partial,
    )
    gone = [a.path for a in result.actions if a.action in ("orphan", "remove")]
    renamed = renames.find(gone, {op.path for op in ops})
    notes = [*base_notes, *loaded.warnings, *adapters.GENERIC.notes(ctx)]
    if result.applied and not dry_run:
        notes += _githooks(project, normalized, result)
    if host_note and not normalized["review"].get("publish_command"):
        notes.append(
            f"the repo lives on {host_note} (review.host); to publish the gates as PR comments, "
            "set review.publish_command (examples in the ci-and-review contract)"
        )
    if migrated is not None and config_rel not in extra:
        notes.append(
            f"{config_rel} is still on schema {migrated} (read as {config.CURRENT_SCHEMA}); "
            f"`{_meta.NAME} update --apply` saves it migrated"
        )
    written = result.applied and bool(extra)
    migration = (migrated, config.CURRENT_SCHEMA) if migrated is not None else None
    return SyncResult(
        result, list(targets), list(bundle.packs), notes, written, renamed, migration
    )


def _dropped(root: Path, ctx: Context, ops: list[Op], previous: lock.Lock | None) -> set[Unit]:
    """Las copias de contenido que se dejan de pedir porque cambió el pedido, no el contenido.

    Son las que el contenido actual todavía genera con los agentes y packs del lock: si
    ya no se piden, es porque la persona sacó un agente o un pack (por un comando o a mano
    en la config). Las demás son huérfanas y esperan `prune`. Solo se planifica de nuevo
    si hay candidatas y el pedido cambió.
    """
    if previous is None:
        return set()
    planned = {unit_of(op) for op in ops}
    candidates = {
        unit_of_entry(e) for e in previous.files if e.kind in engine.ORPHAN_KINDS
    } - planned
    if not candidates:
        return set()
    available = [p for p in previous.packs if (root / "packs" / p / packs.MANIFEST).is_file()]
    try:
        targets = normalize_agents(previous.agents)
        bundle = build_bundle(root, available) if available else None
    except ValueError:
        return set()
    if bundle is None or (targets == ctx.targets and bundle.packs == ctx.bundle.packs):
        return set()
    before = Context(ctx.project, bundle, targets, ctx.config, claude_md=ctx.claude_md)
    return candidates & {unit_of(op) for op in adapters.plan_all(before)}


def _githooks(project: Path, cfg: dict[str, Any], result: engine.Result) -> list[str]:
    """Activa o desactiva los git hooks en este clon, después de aplicar (D-21).

    Si no hubo nada que aplicar y ya están como deben, no se lanza git (F8).
    """
    if not result.changed and githooks.settled(project, cfg):
        return []
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
    # Lo que produjo la ingeniería inversa, que es conocimiento del proyecto (D-36), y la
    # marca que escribió la persona.
    kept: list[str] = field(default_factory=list)


# Lo del proyecto dentro de la carpeta del motor: `uninstall` no lo borra. `discovery/` y
# `context.md` son conocimiento del proyecto (D-36); `brand.json`, la marca que escribe la
# persona para el estilo ejecutivo (D-12, ADR-0016).
KEEP_ON_UNINSTALL = ("discovery", "context.md", "brand.json")


def uninstall(project: Path, *, force: bool = False, dry_run: bool = False) -> UninstallResult:
    """Revierte todo lo del lock y borra la carpeta del motor.

    Antes guarda un backup de seguridad fuera del proyecto, en la carpeta de datos
    de usuario, para que el proyecto quede idéntico al original. Conserva lo que
    produjo la ingeniería inversa (`discovery/` y `context.md`, D-36) y la marca de la
    persona (`brand.json`), y lo informa.
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
        backup = paths.private_dir(paths.user_data_dir() / "uninstall-backups") / name
        fsutil.write_atomic(backup, archive, mode=paths.PRIVATE_FILE)
    result = engine.apply(
        project, [], agents=[], packs=[], force=force, dry_run=dry_run, prune=True
    )
    if result.applied and not dry_run:
        githooks.deactivate(project)
    also_removed = _human_files_in(project, motor_dir, data)
    kept = [
        f"{_meta.PROJECT_DIR}/{name}" for name in KEEP_ON_UNINSTALL if (motor_dir / name).exists()
    ]
    also_removed = [
        r for r in also_removed if not any(r == k or r.startswith(k + "/") for k in kept)
    ]
    if result.applied and not result.unresolved and motor_dir.is_dir() and not dry_run:
        if fsutil.is_link(motor_dir):
            raise ProjectError(f"{motor_dir} is a link; not deleting it")
        for child in sorted(motor_dir.iterdir()):
            if child.name in KEEP_ON_UNINSTALL:
                continue
            if child.is_dir() and not fsutil.is_link(child):
                shutil.rmtree(child)
            else:
                child.unlink()
        if not any(motor_dir.iterdir()):
            motor_dir.rmdir()
    return UninstallResult(result, backup, also_removed, kept)


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
