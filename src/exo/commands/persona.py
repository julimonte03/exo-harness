"""`exo persona {set,show,clear}`: el overlay de rol de cada persona (ADR-0018)."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo import _meta, persona
from exo.commands._output import emit_json, error


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser(
        "persona",
        help="choose your role overlay (per person, never in the repo)",
        description=(
            "A role overlay changes what the agent shows you first and how; it never relaxes "
            "a rule, gate or approval. The role is stored in your user data folder."
        ),
    )
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="persona_command", metavar="<action>")

    setter = actions.add_parser("set", help="set your role")
    setter.add_argument("role", choices=persona.ROLES, help="your role")
    setter.set_defaults(handler=_set)

    show = actions.add_parser("show", help="show your role and its overlay")
    show.add_argument("--project", type=Path, default=Path("."), help="project root (default: .)")
    show.add_argument("--json", action="store_true", help="JSON output")
    show.set_defaults(handler=_show)

    clear = actions.add_parser("clear", help="clear your role")
    clear.set_defaults(handler=_clear)


def _set(args: argparse.Namespace) -> int:
    try:
        changed = persona.write(args.role)
    except OSError as exc:
        return error(f"could not save the persona in {persona.file_path()}: {exc}")
    print(f"persona {'set to' if changed else 'is already'} {args.role}")
    return 0


def _show(args: argparse.Namespace) -> int:
    try:
        role = persona.read()
    except persona.PersonaError as exc:
        return error(str(exc))
    overlay = persona.overlay_path(role) if role else None
    installed = bool(overlay) and (args.project / Path(*overlay.parts)).is_file()
    if args.json:
        emit_json(
            {
                "persona": role,
                "overlay": str(overlay) if overlay else None,
                "installed": installed,
            }
        )
        return 0
    if role is None:
        print(f"no persona set (choose one with `{_meta.NAME} persona set <role>`)")
        return 0
    print(f"persona: {role}")
    if installed:
        print(f"overlay: {overlay}")
    else:
        print(f"overlay: {overlay} is not installed in this project; run `{_meta.NAME} sync`")
    return 0


def _clear(_args: argparse.Namespace) -> int:
    try:
        removed = persona.clear()
    except OSError as exc:
        return error(f"could not remove {persona.file_path()}: {exc}")
    print("persona cleared" if removed else "no persona was set")
    return 0
