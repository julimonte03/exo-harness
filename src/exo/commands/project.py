"""`exo init`, `sync`, `status`, `add-agent`, `remove-agent` y `uninstall`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from exo import _meta, content, packs
from exo.adapters import KNOWN_AGENTS, detect
from exo.commands._output import emit_json, error, usage_error
from exo.core import tickets
from exo.installer import engine, project, stack, wizard


def _common(parser: argparse.ArgumentParser, *, writes: bool = True) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--json", action="store_true", help="JSON output")
    if writes:
        parser.add_argument(
            "--dry-run", action="store_true", help="show what would change, without writing"
        )
        parser.add_argument(
            "--force", action="store_true", help="overwrite manual edits (takes a snapshot first)"
        )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def register(sub: argparse._SubParsersAction) -> None:
    init = sub.add_parser(
        "init",
        help="adopt the engine in a project (detects the agents)",
        description=(
            "Detects the agents in use and generates only what each one needs. "
            "In an interactive terminal it asks; with --yes it uses the detection and the flags."
        ),
    )
    _common(init)
    init.add_argument(
        "--agents", type=_csv, help=f"comma-separated agents: {', '.join(KNOWN_AGENTS)}"
    )
    init.add_argument(
        "--packs", type=_csv, help="comma-separated packs (default: the suggested ones)"
    )
    init.add_argument(
        "--ticket-pattern",
        metavar="REGEX",
        help=(
            "regular expression for the project's ticket IDs (for example "
            "'[A-Z][A-Z0-9]*-\\d+' or '#\\d+'); empty for no tickets"
        ),
    )
    init.add_argument(
        "--ticket-example", metavar="ID", help="example ticket ID shown in messages"
    )
    init.add_argument(
        "--no-tickets",
        action="store_true",
        help="the project has no tickets (same as an empty --ticket-pattern)",
    )
    init.add_argument(
        "--mcp", action="store_true", help="enable the optional MCP server (ADR-0005)"
    )
    init.add_argument(
        "--claude-md",
        action="store_true",
        help="create CLAUDE.md with @AGENTS.md even if it does not exist",
    )
    init.add_argument("--yes", action="store_true", help="never prompt")
    init.set_defaults(handler=_init)

    sync = sub.add_parser("sync", help="regenerate the engine files from the config and the lock")
    _common(sync)
    sync.set_defaults(handler=_sync)

    status = sub.add_parser("status", help="agents, packs and manual changes to generated files")
    _common(status, writes=False)
    status.set_defaults(handler=_status)

    for name, helptext in (("add-agent", "add an agent"), ("remove-agent", "remove an agent")):
        parser = sub.add_parser(name, help=helptext)
        parser.add_argument("agent")
        _common(parser)
        parser.set_defaults(handler=_add_agent if name == "add-agent" else _remove_agent)

    uninstall = sub.add_parser(
        "uninstall",
        help="remove the engine from the project and leave it as it was",
        description="Saves a safety backup outside the project first.",
    )
    _common(uninstall)
    uninstall.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    uninstall.set_defaults(handler=_uninstall)


# -- salida ---------------------------------------------------------------------

# Etiqueta en la salida de texto de las claves del JSON que no se leen tal cual.
_LABELS = {
    "safety_backup": "safety backup",
    "also_removed": "also removed (kept in the backup)",
}


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
        return "unresolved"
    if not args.force:
        return "conflict"
    return "would force" if args.dry_run else "forced"


def _report(result: engine.Result, args: argparse.Namespace, extra: dict[str, Any]) -> int:
    """Imprime el resultado. Sale con 1 si hubo conflictos sin `--force`, o si quedaron
    conflictos que `--force` no resuelve."""
    failed = bool(result.conflicts) and not args.force
    code = 1 if failed or result.unresolved else 0
    if args.json:
        emit_json({**extra, **_payload(result)})
        return code
    for key, value in extra.items():
        if key == "notes":
            for note in value:
                print(f"note: {note}")
        elif isinstance(value, list):
            print(f"{_LABELS.get(key, key)}: {', '.join(value) if value else '-'}")
        elif value is not None:
            print(f"{_LABELS.get(key, key)}: {value}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    for conflict in result.conflicts:
        label = _conflict_label(conflict, args)
        print(f"{label}: {conflict.path} ({conflict.kind}): {conflict.reason}")
    if failed:
        hint = (
            "Fix the ones marked 'unresolved' by hand; --force does not overwrite them."
            if result.unresolved
            else "Review the conflicts or retry with --force (takes a snapshot first)."
        )
        print(f"nothing was written. {hint}")
        return 1
    # Una línea por archivo: varias unidades del mismo archivo (los ítems de una
    # lista, por ejemplo) se informan juntas.
    writes = list(
        dict.fromkeys((a.action, a.path) for a in result.actions if a.action in engine.WRITES)
    )
    if args.dry_run:
        print("dry-run: nothing was written")
    for action, path in writes if (args.dry_run or len(writes) <= 30) else []:
        print(f"{action}\t{path}")
    if not result.changed:
        print("no changes")
    else:
        counts = {name: sum(action == name for action, _ in writes) for name in engine.WRITES}
        summary = ", ".join(f"{n} {name}" for name, n in counts.items() if n)
        print(f"{'would do' if args.dry_run else 'done'}: {summary or 'lock only'}")
        if result.snapshot:
            print(f"snapshot before the changes: {result.snapshot}")
    if result.unresolved:
        done = "would be applied" if args.dry_run else "was applied"
        print(f"the rest {done}; fix the ones marked 'unresolved' by hand and retry.")
    return code


# -- comandos ---------------------------------------------------------------------


def _available_packs() -> list[str]:
    return list(packs.load_packs(content.content_root()))


def _init(args: argparse.Namespace) -> int:
    root = args.project.resolve()
    interactive = not args.yes and sys.stdin.isatty()
    agents = args.agents
    chosen_packs = args.packs
    if args.no_tickets and (args.ticket_pattern is not None or args.ticket_example is not None):
        return usage_error("--no-tickets cannot go with --ticket-pattern or --ticket-example")
    if args.no_tickets:
        args.ticket_pattern = ""
    if args.ticket_example is not None and args.ticket_pattern is None:
        return usage_error("--ticket-example needs --ticket-pattern")
    if args.ticket_pattern:
        try:
            tickets.compile_pattern(args.ticket_pattern)
            if args.ticket_example is not None:
                tickets.check_example(args.ticket_pattern, args.ticket_example)
        except tickets.TicketError as exc:
            return usage_error(str(exc))
    ticket_cfg = (
        wizard.ticket_config(args.ticket_pattern or None, args.ticket_example)
        if args.ticket_pattern is not None
        else None
    )
    try:
        installed = project.current_agents(root)
        if agents is None and installed is not None:
            agents = installed
        if interactive and agents is None:
            choices = wizard.choose(
                detect.detect(root), stack.detect_stack(root), _available_packs()
            )
            agents, chosen_packs, ticket_cfg = (
                choices.agents,
                chosen_packs or choices.packs,
                ticket_cfg or choices.tickets,
            )
        elif agents is None:
            detections = detect.detect(root)
            agents = detect.preselect(detections)
            _print_detections(detections)
            if not agents:
                print("warning: no agent detected; installing the generic base (AGENTS.md)")
        if chosen_packs is None and installed is None:
            suggested = stack.detect_stack(root).suggested
            available = _available_packs()
            chosen_packs = [p for p in suggested if p in available]
        kwargs = dict(
            agents=agents,
            packs=chosen_packs,
            mcp=True if args.mcp else None,
            tickets=ticket_cfg,
            claude_md=args.claude_md,
            force=args.force,
        )
        if interactive and not args.dry_run:
            preview = project.sync(root, dry_run=True, **kwargs)
            summary = [
                f"{a.action} {a.path}" for a in preview.engine.actions if a.action in engine.WRITES
            ]
            if not wizard.confirm(summary or ["no changes"]):
                print("cancelled")
                return 1
        result = project.sync(root, dry_run=args.dry_run, **kwargs)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(
        result.engine,
        args,
        {"agents": result.agents, "packs": result.packs, "notes": result.notes},
    )


def _print_detections(detections: list[detect.Detection]) -> None:
    """ADR-0006: sin preguntar, se instala lo detectado con certeza y se informa el resto."""
    for item in detections:
        evidence = ", ".join(item.evidence)
        if item.strong:
            print(f"detected: {item.agent} ({evidence})")
        else:
            print(
                f"unconfirmed: {item.agent} ({evidence}); if you use it, run "
                f"`{_meta.NAME} add-agent {item.agent}`"
            )


def _not_installed(root: Path) -> int:
    return error(f"the engine is not installed in {root}; run `{_meta.NAME} init`")


def _sync(args: argparse.Namespace) -> int:
    root = args.project.resolve()
    try:
        if project.current_agents(root) is None:
            return _not_installed(root)
        result = project.sync(root, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(
        result.engine,
        args,
        {"agents": result.agents, "packs": result.packs, "notes": result.notes},
    )


def _change_agents(args: argparse.Namespace, add: bool) -> int:
    root = args.project.resolve()
    try:
        installed = project.current_agents(root)
        if installed is None:
            return _not_installed(root)
        current = [a for a in installed if a != "generic"]
        if add:
            agents = [*current, args.agent] if args.agent not in current else current
        elif args.agent not in current:
            return error(
                f"{args.agent} is not one of the project agents ({', '.join(current) or '-'})"
            )
        else:
            agents = [a for a in current if a != args.agent]
        result = project.sync(root, agents=agents, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(result.engine, args, {"agents": result.agents, "notes": result.notes})


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
        print(f"the engine is not installed; run `{_meta.NAME} init`")
        return 0
    print(f"agents: {', '.join(info.agents)}")
    print(f"packs: {', '.join(info.packs)}")
    print(f"engine: {_meta.VERSION} (lock written by {info.lock_version})")
    print(f"managed files: {info.files}")
    for item in drift:
        print(f"manual change: {item['path']} ({item['kind']}): {item['status']}")
    if not drift:
        print("no manual changes to generated files")
    for warning in info.warnings:
        print(f"warning: {warning}")
    return 0


def _uninstall(args: argparse.Namespace) -> int:
    if not args.yes and not args.dry_run:
        if not sys.stdin.isatty():
            return usage_error(
                "uninstall deletes generated files; in non-interactive mode add --yes"
            )
        if not wizard.confirm(  # pragma: no cover
            [f"remove the engine from {args.project.resolve()}"]
        ):
            print("cancelled")
            return 1
    root = args.project.resolve()
    if not (root / _meta.PROJECT_DIR).exists():
        if args.json:
            emit_json({"installed": False, "applied": False, "changed": False})
        else:
            print(f"the engine is not installed in {root}; nothing to do")
        return 0
    try:
        result = project.uninstall(root, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    backup = str(result.backup) if result.backup else None
    extra: dict[str, Any] = {"safety_backup": backup}
    if result.also_removed:
        extra["also_removed"] = result.also_removed
    return _report(result.engine, args, extra)
