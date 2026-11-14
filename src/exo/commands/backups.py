"""`exo backups {list,pin,unpin}` y `exo restore`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exo.commands._output import emit_json, error, usage_error
from exo.core import snapshots


def _project_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project", type=Path, default=Path("."), help="project root (default: .)"
    )


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser("backups", help="list and pin the project snapshots")
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="backups_command", metavar="<action>")

    listing = actions.add_parser("list", help="list the snapshots")
    _project_arg(listing)
    listing.add_argument("--json", action="store_true", help="JSON output")
    listing.set_defaults(handler=_list)

    for verb, helptext in (
        ("pin", "pin a snapshot so it is never pruned"),
        ("unpin", "unpin a snapshot"),
    ):
        parser = actions.add_parser(verb, help=helptext)
        parser.add_argument("name", help="snapshot name")
        _project_arg(parser)
        parser.set_defaults(handler=_pin if verb == "pin" else _unpin)

    restore = sub.add_parser(
        "restore",
        help="restore a snapshot (saves the current state first)",
        description="Returns the snapshot paths to their saved state. Overwrites project files.",
    )
    restore.add_argument("name", help="snapshot name")
    _project_arg(restore)
    restore.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    restore.add_argument("--json", action="store_true", help="JSON output")
    restore.set_defaults(handler=_restore)


def _list(args: argparse.Namespace) -> int:
    items = snapshots.list_snapshots(args.project)
    if args.json:
        emit_json(
            {"backups": [{"name": s.name, "size": s.size, "pinned": s.pinned} for s in items]}
        )
        return 0
    for item in items:
        print(f"{item.name}\t{item.size} bytes" + ("\tpinned" if item.pinned else ""))
    if not items:
        print("no backups")
    return 0


def _pin(args: argparse.Namespace) -> int:
    try:
        changed = snapshots.pin(args.project, args.name)
    except snapshots.SnapshotError as exc:
        return error(str(exc))
    print(f"{args.name}: " + ("pinned" if changed else "already pinned"))
    return 0


def _unpin(args: argparse.Namespace) -> int:
    changed = snapshots.unpin(args.project, args.name)
    print(f"{args.name}: " + ("unpinned" if changed else "was not pinned"))
    return 0


def _confirm(name: str) -> bool:  # pragma: no cover - interactivo
    answer = input(f"Restore {name}? This overwrites project files [y/N] ")
    return answer.strip().lower() in ("y", "yes", "s", "si", "sí")


def _restore(args: argparse.Namespace) -> int:
    if not args.yes:
        if not sys.stdin.isatty():
            return usage_error("restore overwrites files; in non-interactive mode add --yes")
        if not _confirm(args.name):  # pragma: no cover - interactivo
            print("cancelled")
            return 1
    try:
        result = snapshots.restore(args.project, args.name)
    except (ValueError, OSError) as exc:  # SnapshotError, rutas inseguras, disco
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
        f"restored {args.name}: {len(result.restored)} files, "
        f"{len(result.removed)} removed"
    )
    if before:
        print(f"previous state saved in {before}")
    return 0
