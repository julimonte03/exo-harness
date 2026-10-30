"""`exo backups {list,pin,unpin}` y `exo restore`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exo.commands._output import emit_json, error, usage_error
from exo.core import snapshots


def _project_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project", type=Path, default=Path("."), help="raíz del proyecto (por defecto, .)"
    )


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser("backups", help="lista y fija los snapshots del proyecto")
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="backups_command", metavar="<acción>")

    listing = actions.add_parser("list", help="lista los snapshots")
    _project_arg(listing)
    listing.add_argument("--json", action="store_true", help="salida JSON")
    listing.set_defaults(handler=_list)

    for verb, helptext in (("pin", "fija un snapshot para que no se pode"), ("unpin", "lo libera")):
        parser = actions.add_parser(verb, help=helptext)
        parser.add_argument("name", help="nombre del snapshot")
        _project_arg(parser)
        parser.set_defaults(handler=_pin if verb == "pin" else _unpin)

    restore = sub.add_parser(
        "restore",
        help="restaura un snapshot (antes guarda el estado actual)",
        description="Vuelve las rutas del snapshot a su estado. Pisa archivos del proyecto.",
    )
    restore.add_argument("name", help="nombre del snapshot")
    _project_arg(restore)
    restore.add_argument("--yes", action="store_true", help="no pedir confirmación")
    restore.add_argument("--json", action="store_true", help="salida JSON")
    restore.set_defaults(handler=_restore)


def _list(args: argparse.Namespace) -> int:
    items = snapshots.list_snapshots(args.project)
    if args.json:
        emit_json(
            {"backups": [{"name": s.name, "size": s.size, "pinned": s.pinned} for s in items]}
        )
        return 0
    for item in items:
        print(f"{item.name}\t{item.size} bytes" + ("\tfijado" if item.pinned else ""))
    if not items:
        print("sin backups")
    return 0


def _pin(args: argparse.Namespace) -> int:
    try:
        changed = snapshots.pin(args.project, args.name)
    except snapshots.SnapshotError as exc:
        return error(str(exc))
    print(f"{args.name}: " + ("fijado" if changed else "ya estaba fijado"))
    return 0


def _unpin(args: argparse.Namespace) -> int:
    changed = snapshots.unpin(args.project, args.name)
    print(f"{args.name}: " + ("liberado" if changed else "no estaba fijado"))
    return 0


def _confirm(name: str) -> bool:  # pragma: no cover - interactivo
    answer = input(f"¿Restaurar {name}? Pisa archivos del proyecto [s/N] ")
    return answer.strip().lower() in ("s", "si", "sí", "y", "yes")


def _restore(args: argparse.Namespace) -> int:
    if not args.yes:
        if not sys.stdin.isatty():
            return usage_error("restore pisa archivos; en modo no interactivo agregá --yes")
        if not _confirm(args.name):  # pragma: no cover - interactivo
            print("cancelado")
            return 1
    try:
        result = snapshots.restore(args.project, args.name)
    except (snapshots.SnapshotError, OSError) as exc:
        return error(str(exc))
    before = result.before.name if result.before else None
    if args.json:
        emit_json(
            {
                "name": args.name,
                "before": before,
                "restored": result.restored,
                "removed": result.removed,
            }
        )
        return 0
    print(
        f"restaurado {args.name}: {len(result.restored)} archivos, "
        f"{len(result.removed)} borrados"
    )
    if before:
        print(f"estado anterior guardado en {before}")
    return 0
