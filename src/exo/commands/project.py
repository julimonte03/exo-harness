"""`exo init`, `sync`, `status`, `add-agent`, `remove-agent` y `uninstall`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from exo import _meta, content, packs
from exo.adapters import detect
from exo.commands._output import emit_json, error, usage_error
from exo.core import config
from exo.installer import engine, project, stack, wizard


def _common(parser: argparse.ArgumentParser, *, writes: bool = True) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="raíz del proyecto")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    if writes:
        parser.add_argument(
            "--dry-run", action="store_true", help="muestra qué haría, sin escribir"
        )
        parser.add_argument(
            "--force", action="store_true", help="pisa lo editado a mano (con snapshot)"
        )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def register(sub: argparse._SubParsersAction) -> None:
    init = sub.add_parser(
        "init",
        help="adopta el motor en un proyecto (detecta los agentes)",
        description=(
            "Detecta los agentes que se usan y genera solo lo que cada uno necesita. "
            "En una terminal interactiva pregunta; con --yes usa lo detectado y los flags."
        ),
    )
    _common(init)
    init.add_argument(
        "--agents", type=_csv, help=f"agentes separados por coma; ver `{_meta.NAME} init --help`"
    )
    init.add_argument(
        "--packs", type=_csv, help="packs separados por coma (por defecto, los sugeridos)"
    )
    init.add_argument("--tracker", choices=config.TRACKERS, help="tracker de tickets")
    init.add_argument("--prefix", help="prefijo de los tickets, por ejemplo PROJ")
    init.add_argument(
        "--mcp", action="store_true", help="habilita el servidor MCP opcional (ADR-0005)"
    )
    init.add_argument(
        "--claude-md", action="store_true", help="crea CLAUDE.md con @AGENTS.md aunque no exista"
    )
    init.add_argument("--yes", action="store_true", help="no pregunta nada")
    init.set_defaults(handler=_init)

    sync = sub.add_parser("sync", help="vuelve a generar lo del motor según la config y el lock")
    _common(sync)
    sync.set_defaults(handler=_sync)

    status = sub.add_parser("status", help="agentes, packs y cambios manuales sobre lo generado")
    _common(status, writes=False)
    status.set_defaults(handler=_status)

    for name, helptext in (("add-agent", "suma un agente"), ("remove-agent", "quita un agente")):
        parser = sub.add_parser(name, help=helptext)
        parser.add_argument("agent")
        _common(parser)
        parser.set_defaults(handler=_add_agent if name == "add-agent" else _remove_agent)

    uninstall = sub.add_parser(
        "uninstall",
        help="quita el motor del proyecto y lo deja como estaba",
        description="Guarda antes un backup de seguridad fuera del proyecto.",
    )
    _common(uninstall)
    uninstall.add_argument("--yes", action="store_true", help="no pide confirmación")
    uninstall.set_defaults(handler=_uninstall)


# -- salida ---------------------------------------------------------------------


def _payload(result: engine.Result) -> dict[str, Any]:
    return {
        "applied": result.applied,
        "changed": result.changed,
        "snapshot": result.snapshot,
        "actions": [vars(a) for a in result.actions],
        "conflicts": [vars(c) for c in result.conflicts],
        "warnings": result.warnings,
    }


def _conflict_label(conflict: engine.Conflict, args: argparse.Namespace) -> str:
    if not conflict.forceable:
        return "sin resolver"
    if not args.force:
        return "conflicto"
    return "se forzaría" if args.dry_run else "forzado"


def _report(result: engine.Result, args: argparse.Namespace, extra: dict[str, Any]) -> int:
    """Imprime el resultado. Sale con 1 si hubo conflictos sin `--force`, o si quedaron
    conflictos que `--force` no resuelve."""
    failed = bool(result.conflicts) and not args.force
    code = 1 if failed or result.unresolved else 0
    if args.json:
        emit_json({**extra, **_payload(result)})
        return code
    for key, value in extra.items():
        if isinstance(value, list) and value and key == "notes":
            for note in value:
                print(f"nota: {note}")
        elif isinstance(value, list):
            print(f"{key}: {', '.join(value) if value else '-'}")
        elif value is not None:
            print(f"{key}: {value}")
    for warning in result.warnings:
        print(f"aviso: {warning}")
    for conflict in result.conflicts:
        label = _conflict_label(conflict, args)
        print(f"{label}: {conflict.path} ({conflict.kind}): {conflict.reason}")
    if failed:
        hint = (
            "Arreglá a mano los marcados «sin resolver»; --force no los pisa."
            if result.unresolved
            else "Revisá los conflictos o repetí con --force (con snapshot)."
        )
        print(f"no se escribió nada. {hint}")
        return 1
    writes = [a for a in result.actions if a.action in engine.WRITES]
    if args.dry_run:
        print("dry-run: no se escribió nada")
    for action in writes if (args.dry_run or len(writes) <= 30) else []:
        print(f"{action.action}\t{action.path}")
    if not result.changed:
        print("sin cambios")
    else:
        counts = {name: sum(a.action == name for a in writes) for name in engine.WRITES}
        summary = ", ".join(f"{n} {name}" for name, n in counts.items() if n)
        print(f"{'se haría' if args.dry_run else 'listo'}: {summary or 'solo el lock'}")
        if result.snapshot:
            print(f"snapshot previo: {result.snapshot}")
    if result.unresolved:
        print("lo demás se aplicó; arreglá a mano los marcados «sin resolver» y repetí.")
    return code


# -- comandos ---------------------------------------------------------------------


def _available_packs() -> list[str]:
    return list(packs.load_packs(content.content_root()))


def _init(args: argparse.Namespace) -> int:
    root = args.project.resolve()
    existing = config.load(root)
    interactive = not args.yes and sys.stdin.isatty()
    agents = args.agents
    chosen_packs = args.packs
    tracker = {"type": args.tracker, "prefix": args.prefix} if args.tracker else None
    try:
        if agents is None and existing.source is not None:
            agents = existing.config["agents"]
        if interactive and agents is None:
            choices = wizard.choose(
                detect.detect(root), stack.detect_stack(root), _available_packs()
            )
            agents, chosen_packs, tracker = (
                choices.agents,
                chosen_packs or choices.packs,
                tracker or choices.tracker,
            )
        elif agents is None:
            agents = detect.preselect(detect.detect(root))
            if not agents:
                print("aviso: no se detectó ningún agente; se instala la base genérica (AGENTS.md)")
        if chosen_packs is None and existing.source is None:
            suggested = stack.detect_stack(root).suggested
            available = _available_packs()
            chosen_packs = [p for p in suggested if p in available]
        kwargs = dict(
            agents=agents,
            packs=chosen_packs,
            mcp=True if args.mcp else None,
            tracker=tracker,
            claude_md=args.claude_md,
            force=args.force,
        )
        if interactive and not args.dry_run:
            preview = project.sync(root, dry_run=True, **kwargs)
            summary = [
                f"{a.action} {a.path}" for a in preview.engine.actions if a.action in engine.WRITES
            ]
            if not wizard.confirm(summary or ["sin cambios"]):
                print("cancelado")
                return 1
        result = project.sync(root, dry_run=args.dry_run, **kwargs)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(
        result.engine,
        args,
        {"agentes": result.agents, "packs": result.packs, "notes": result.notes},
    )


def _installed(root: Path) -> bool:
    return project.status(root).installed or config.load(root).source is not None


def _sync(args: argparse.Namespace) -> int:
    root = args.project.resolve()
    if not _installed(root):
        return error(f"el motor no está instalado en {root}; corré `{_meta.NAME} init`")
    try:
        result = project.sync(root, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(
        result.engine,
        args,
        {"agentes": result.agents, "packs": result.packs, "notes": result.notes},
    )


def _change_agents(args: argparse.Namespace, add: bool) -> int:
    root = args.project.resolve()
    if not _installed(root):
        return error(f"el motor no está instalado en {root}; corré `{_meta.NAME} init`")
    current = [a for a in config.load(root).config["agents"] if a != "generic"]
    if add:
        agents = [*current, args.agent] if args.agent not in current else current
    else:
        if args.agent not in current:
            return error(
                f"{args.agent} no está entre los agentes del proyecto ({', '.join(current) or '-'})"
            )
        agents = [a for a in current if a != args.agent]
    try:
        result = project.sync(root, agents=agents, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(result.engine, args, {"agentes": result.agents, "notes": result.notes})


def _add_agent(args: argparse.Namespace) -> int:
    return _change_agents(args, add=True)


def _remove_agent(args: argparse.Namespace) -> int:
    return _change_agents(args, add=False)


def _status(args: argparse.Namespace) -> int:
    try:
        info = project.status(args.project)
    except (ValueError, OSError) as exc:
        return error(str(exc))
    drift = [{"path": d.entry.path, "kind": d.entry.kind, "status": d.status} for d in info.drift]
    if args.json:
        emit_json(
            {
                "installed": info.installed,
                "agents": info.agents,
                "packs": info.packs,
                "engine_version": _meta.VERSION,
                "lock_version": info.lock_version,
                "files": info.files,
                "drift": drift,
                "warnings": info.warnings,
            }
        )
        return 0
    if not info.installed:
        print(f"el motor no está instalado; corré `{_meta.NAME} init`")
        return 0
    print(f"agentes: {', '.join(info.agents)}")
    print(f"packs: {', '.join(info.packs)}")
    print(f"motor: {_meta.VERSION} (lock generado con {info.lock_version})")
    print(f"archivos gestionados: {info.files}")
    for item in drift:
        print(f"cambio manual: {item['path']} ({item['kind']}): {item['status']}")
    if not drift:
        print("sin cambios manuales sobre lo generado")
    for warning in info.warnings:
        print(f"aviso: {warning}")
    return 0


def _uninstall(args: argparse.Namespace) -> int:
    if not args.yes and not args.dry_run:
        if not sys.stdin.isatty():
            return usage_error("uninstall borra lo generado; en modo no interactivo agregá --yes")
        if not wizard.confirm([f"quitar el motor de {args.project.resolve()}"]):  # pragma: no cover
            print("cancelado")
            return 1
    try:
        result = project.uninstall(args.project, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    backup = str(result.backup) if result.backup else None
    return _report(result.engine, args, {"backup de seguridad": backup})
