"""`exo specs`: specs vivas por capacidad e integración de deltas (ADR-0013)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exo.commands._output import emit_json, error
from exo.sdd import specs

_VERBS = {"create": "created", "update": "updated", "unchanged": "unchanged"}
_DRY = {"create": "would create", "update": "would update", "unchanged": "unchanged"}


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser(
        "specs",
        help="living specs per capability (list, merge a change's delta)",
        description=(
            "Living specs live in <specs_dir>/capabilities/<capability>/spec.md. A change's "
            "spec.md is a delta (ADDED/MODIFIED/REMOVED Requirements) that merge applies by ID."
        ),
    )
    group.set_defaults(handler=lambda _a: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="specs_command", metavar="<action>")

    listing = actions.add_parser("list", help="list the capabilities and their requirements")
    _common(listing)
    listing.set_defaults(handler=_list)

    merge = actions.add_parser(
        "merge",
        help="merge a change's delta into the living specs",
        description=(
            "Validates the whole delta first and writes nothing if anything fails: MODIFIED or "
            "REMOVED of an ID that does not exist, ADDED of an ID that exists with other text. "
            "Merging the same delta again changes nothing. Takes a snapshot before writing."
        ),
    )
    merge.add_argument("change", help="change name, such as add-login or PROJ-123-add-login")
    merge.add_argument("--dry-run", action="store_true", help="show what would change")
    _common(merge)
    merge.set_defaults(handler=_merge)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--json", action="store_true", help="JSON output")


def _list(args: argparse.Namespace) -> int:
    try:
        found = specs.list_capabilities(args.project)
    except (ValueError, OSError) as exc:
        return error(str(exc))
    if args.json:
        emit_json(
            {
                "capabilities": [
                    {
                        "name": c.name,
                        "path": c.path,
                        "functional": c.functional,
                        "non_functional": c.non_functional,
                        "removed": c.removed,
                        "problems": c.problems,
                    }
                    for c in found
                ]
            }
        )
        return 0
    if not found:
        print("no capabilities yet (they appear when a change's delta is merged)")
        return 0
    for c in found:
        extra = f", {c.problems} problems (run exo speclint {c.path})" if c.problems else ""
        print(
            f"{c.name}\t{c.functional} FR, {c.non_functional} NFR, {c.removed} removed"
            f"\t{c.path}{extra}"
        )
    return 0


def _merge(args: argparse.Namespace) -> int:
    try:
        result = specs.merge(args.project, args.change, dry_run=args.dry_run)
    except specs.MergeError as exc:
        print(
            f"error: the delta of {exc.change} was not merged; nothing was written:",
            file=sys.stderr,
        )
        for problem in exc.problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        return error(str(exc))
    if args.json:
        emit_json(
            {
                "change": result.change,
                "dry_run": args.dry_run,
                "written": result.written,
                "snapshot": result.snapshot,
                "notes": result.notes,
                "capabilities": [
                    {
                        "name": c.name,
                        "path": c.path,
                        "action": c.action,
                        "ops": [
                            {"id": o.id, "action": o.action, "status": o.status} for o in c.ops
                        ],
                    }
                    for c in result.capabilities
                ],
            }
        )
        return 0
    verbs = _DRY if args.dry_run else _VERBS
    for c in result.capabilities:
        applied = [f"{o.action} {o.id}" for o in c.ops if o.status == "applied"]
        detail = f": {', '.join(applied)}" if applied else ""
        print(f"{verbs[c.action]} {c.path}{detail}")
    for note in result.notes:
        print(f"note: {note}")
    if result.snapshot:
        print(f"snapshot: {result.snapshot}")
    return 0
