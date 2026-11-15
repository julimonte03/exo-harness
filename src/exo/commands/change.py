"""`exo change new` y `exo change record`: las acciones que escriben sobre un change.

El resto del grupo (`list`, `status`, `ai-usage`, `followups`) son tools del
registro y viven en `commands/tools.py`. Estas no son tools: escriben, y siguen
el patrón de `speclint` y `fitness` (CLI primero, ADR-0005).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from exo.commands._output import emit_json, error, usage_error
from exo.core import fsutil
from exo.sdd import changes


def register_actions(actions: argparse._SubParsersAction) -> None:
    new = actions.add_parser(
        "new",
        help="create a change: its folder and its AI Usage Record",
        description=(
            "The name is [<ticket>-]<slug>: the ticket must match the project's ticket pattern "
            "(tickets.pattern) and goes in normalized, so AB#123 becomes AB-123. The exact ID "
            "is kept in the record. With --epic, the change goes inside the epic's folder."
        ),
    )
    new.add_argument("slug", help="lowercase kebab-case, for example add-login")
    new.add_argument("--ticket", help="ticket ID, as the person confirmed it")
    new.add_argument("--epic", help="epic ID, as the person confirmed it")
    new.add_argument("--purpose", help="one sentence: what the change is for")
    _common(new)
    new.set_defaults(handler=_new)

    rec = actions.add_parser(
        "record",
        help="add entries to a change's AI Usage Record",
        description=(
            "Adds entries to list fields without duplicating them (a capability is the same "
            "if it has the same name and type) or sets a field, validates the result against "
            "the schema and writes it atomically. If nothing changes, nothing is written."
        ),
    )
    rec.add_argument("change", help="change name")
    rec.add_argument(
        "--add",
        nargs=2,
        action="append",
        default=[],
        metavar=("FIELD", "JSON"),
        help=(
            f"append to a list field ({', '.join(changes.LIST_FIELDS)}); "
            "JSON, or @<file> to read it from a file"
        ),
    )
    rec.add_argument(
        "--set",
        dest="set_",
        nargs=2,
        action="append",
        default=[],
        metavar=("FIELD", "JSON"),
        help=f"set a field ({', '.join(changes.SET_FIELDS)})",
    )
    rec.add_argument(
        "--followup",
        action="append",
        default=[],
        metavar="JSON",
        help="add a judge finding to followups.json (JSON, or @<file>)",
    )
    rec.add_argument(
        "--phase-done",
        metavar="PHASE",
        help=(
            "log that a phase finished with status ok (" + ", ".join(changes.PHASES) + "); "
            "the next phase is derived from this log"
        ),
    )
    _common(rec)
    rec.set_defaults(handler=_record)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--json", action="store_true", help="JSON output")


def _new(args: argparse.Namespace) -> int:
    try:
        created = changes.new_change(
            args.project, args.slug, ticket=args.ticket, epic=args.epic, purpose=args.purpose
        )
    except (changes.ChangeError, OSError) as exc:
        return error(str(exc))
    if args.json:
        emit_json(
            {
                "name": created.name,
                "path": created.path,
                "epic": created.epic,
                "ticket": created.ticket,
                "record": created.record,
            }
        )
    else:
        print(f"created {created.path}")
        print(f"record: {created.record}")
    return 0


def _parse(pairs: list[list[str]], option: str) -> list[tuple[str, Any]] | str:
    parsed: list[tuple[str, Any]] = []
    for field, raw in pairs:
        allowed = {"--add": changes.LIST_FIELDS, "--set": changes.SET_FIELDS}.get(option, (field,))
        if field not in allowed:
            hint = "list fields take --add" if option == "--set" else "a scalar field takes --set"
            return f"{option} {field}: not one of {', '.join(allowed)} ({hint})"
        if raw.startswith("@"):
            try:
                raw = fsutil.read_text_auto(Path(raw[1:]))
            except OSError as exc:
                return f"{option} {field}: cannot read {raw[1:]} ({exc.strerror or exc})"
            except ValueError as exc:
                return f"{option} {field}: {exc}"
        try:
            parsed.append((field, json.loads(raw)))
        except json.JSONDecodeError as exc:
            return (
                f"{option} {field}: the value is not valid JSON ({exc.msg}); quote strings, "
                f"for example {option} {field} '\"text\"'"
            )
    return parsed


def _record(args: argparse.Namespace) -> int:
    add = _parse(args.add, "--add")
    set_ = _parse(args.set_, "--set")
    for parsed in (add, set_):
        if isinstance(parsed, str):
            return usage_error(parsed)
    if args.phase_done is not None and args.phase_done not in changes.PHASES:
        return usage_error(f"--phase-done {args.phase_done}: one of {', '.join(changes.PHASES)}")
    followups = _parse([["followups", raw] for raw in args.followup], "--followup")
    if isinstance(followups, str):
        return usage_error(followups)
    if not add and not set_ and args.phase_done is None and not followups:
        return usage_error("nothing to record: pass --add, --set, --followup or --phase-done")
    assert not isinstance(add, str) and not isinstance(set_, str)
    try:
        for _, value in followups:
            done = changes.add_followup(args.project, args.change, value)
            if not args.json:
                print(f"{done.path}: " + ("updated" if done.changed else "unchanged"))
        if not add and not set_ and args.phase_done is None:
            return 0
        result = changes.update_record(
            args.project, args.change, add=add, set_=set_, phase_done=args.phase_done
        )
    except (changes.ChangeError, OSError) as exc:
        return error(str(exc))
    if args.json:
        emit_json({"changed": result.changed, "path": result.path, "record": result.record})
    else:
        print(f"{result.path}: " + ("updated" if result.changed else "unchanged"))
    return 0
