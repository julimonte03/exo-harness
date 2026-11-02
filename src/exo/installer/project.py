"""Adopción del motor en un proyecto: config, bundle, adaptadores y motor.

`sync` es el núcleo de `exo init`, `exo sync`, `exo add-agent` y
`exo remove-agent`; los comandos solo deciden qué agentes, packs y opciones
pasarle. La config del proyecto es del humano: se crea o actualiza con lo
elegido, pero solo después de aplicar sin conflictos.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo import adapters, content
from exo.adapters.base import Context
from exo.core import config
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
    cfg = loaded.config
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
    cfg["agents"] = list(targets)
    cfg["packs"] = list(bundle.packs)
    ctx = Context(project, bundle, targets, cfg, claude_md="always" if claude_md else "auto")
    result = engine.apply(
        project,
        adapters.plan_all(ctx),
        agents=list(targets),
        packs=list(bundle.packs),
        force=force,
        dry_run=dry_run,
    )
    written = False
    if result.applied:
        written = config.save(project, cfg)
    notes = [*loaded.warnings, *adapters.GENERIC.notes(ctx)]
    return SyncResult(result, list(targets), list(bundle.packs), notes, written)
