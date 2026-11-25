"""`exo gate publish`: un texto por gate del change, publicado o impreso (D-30)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exo import _meta
from exo.commands._output import emit_json, error, usage_error
from exo.governance import approvals, gates
from exo.sdd import observability

_ENV = _meta.ENV_PREFIX


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser("gate", help="gates of a change as PR comments")
    group.set_defaults(handler=lambda _a: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="gate_command", metavar="<action>")
    publish = actions.add_parser(
        "publish",
        help="one text per gate: run review.publish_command for each, or print them",
        description=(
            "Builds one text per gate of the change, with its marker. If the project set "
            f"review.publish_command, it runs once per gate with {_ENV}GATE, {_ENV}GATE_MARKER, "
            f"{_ENV}GATE_BODY and {_ENV}CHANGE in the environment, and creates or edits the PR "
            "comment that carries the marker. Without a command, or with --dry-run, the texts "
            "are printed."
        ),
    )
    publish.add_argument("--change", help="change name (default: the only active change)")
    publish.add_argument("--dry-run", action="store_true", help="print, never run the command")
    publish.add_argument(
        "--approve-command",
        metavar="COMMAND",
        help=(
            "approve on this machine exactly this command, which must be review.publish_command, "
            "for this project and the current content of the project files it names, and run "
            "it (without the flag, a terminal asks)"
        ),
    )
    publish.add_argument("--project", type=Path, default=Path("."), help="project root")
    publish.add_argument("--json", action="store_true", help="JSON output")
    publish.set_defaults(handler=_publish)


def _confirm(decision: approvals.Decision) -> bool:
    print(f"This project ({decision.project}) runs this command in a shell, once per gate:")
    print(f"  {decision.command}")
    if decision.changed:
        print(f"Changed since you approved it: {', '.join(decision.changed)}")
    print(approvals.coverage(decision))
    answer = input("Approve it on this machine for this project and run it? [y/N] ")
    return answer.strip().lower() in ("y", "yes", "s", "si", "sí")


def _publish(args: argparse.Namespace) -> int:
    name = args.change
    if name is None:
        active = observability.find_changes(args.project, include_archived=False)
        if len(active) != 1:
            names = ", ".join(c.name for c in active) or "none"
            return usage_error(f"pass --change (active changes: {names})")
        name = active[0].name
    # El texto exacto: quien aprueba el pedido del agente ve el comando, y un pipeline fija
    # cuál acepta (un PR que cambia publish_command no coincide). `gates.publish` lo compara
    # con la config que lee para correrlo. Threat model, M-1.
    approve = args.approve_command
    try:
        try:
            results = gates.publish(args.project, name, dry_run=args.dry_run, approve=approve)
        except gates.CommandNotApproved as exc:
            if args.json or not sys.stdin.isatty():
                raise
            if not _confirm(exc.decision):
                print("cancelled: nothing was run")
                return 1
            # Si la config cambió mientras tanto, no coincide y no corre nada.
            results = gates.publish(args.project, name, approve=exc.command)
    except (gates.GateError, ValueError, OSError) as exc:
        return error(str(exc))
    failed = [r for r in results if r.status == "failed"]
    if args.json:
        emit_json(
            {
                "change": name,
                "dry_run": args.dry_run,
                "gates": [
                    {
                        "name": r.name,
                        "status": r.status,
                        "detail": r.detail,
                        "path": r.path,
                        "body": r.body,
                    }
                    for r in results
                ],
            }
        )
        return 1 if failed else 0
    if not results:
        print(f"no gates for {name}")
        return 0
    for item in results:
        if item.status == "printed":
            print(f"--- {item.name} ({item.path}) ---")
            print(item.body.rstrip("\n"))
        elif item.status == "sent":
            print(f"sent {item.name}")
    for item in failed:
        print(f"error: {item.name} was not published: {item.detail}", file=sys.stderr)
    if args.dry_run:
        print("dry-run: nothing was sent")
    return 1 if failed else 0
