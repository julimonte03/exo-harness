"""`exo skills …`, `exo change …` y `exo mcp`: las tools del motor por CLI o por MCP.

Los subcomandos llaman al mismo registro que el servidor MCP
(`exo.tools.registry`), así que validan y responden igual (ADR-0005).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from exo.commands._output import emit_json, error
from exo.mcp import server
from exo.tools import registry
from exo.tools.validation import InputError


def _project_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="raíz del proyecto")
    parser.add_argument("--json", action="store_true", help="salida JSON")


def _group(sub: argparse._SubParsersAction, name: str, helptext: str) -> argparse._SubParsersAction:
    group = sub.add_parser(name, help=helptext)
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    return group.add_subparsers(dest=f"{name}_command", metavar="<acción>")


def register(sub: argparse._SubParsersAction) -> None:
    skills = _group(sub, "skills", "skills del contenido del motor")
    listing = skills.add_parser("list", help="lista las skills")
    listing.add_argument("--pack", help="solo las de un pack")
    _project_arg(listing)
    listing.set_defaults(handler=_run("skills_list", lambda a: _opt(pack=a.pack)))
    info = skills.add_parser("info", help="detalle de una skill")
    info.add_argument("name")
    _project_arg(info)
    info.set_defaults(handler=_run("skill_info", lambda a: {"name": a.name}))
    diff = skills.add_parser("diff", help="compara con las skills instaladas en el proyecto")
    diff.add_argument("--target", help=f"directorio de skills ({registry.DEFAULT_SKILLS_TARGET})")
    _project_arg(diff)
    diff.set_defaults(handler=_run("skills_diff", lambda a: _opt(target=a.target)))

    change = _group(sub, "change", "estado de los changes SDD (solo lectura)")
    clist = change.add_parser("list", help="lista los changes")
    clist.add_argument("--no-archived", action="store_true", help="omite archive/")
    _project_arg(clist)
    clist.set_defaults(
        handler=_run("list_changes", lambda a: {"include_archived": not a.no_archived})
    )
    for action, tool, helptext in (
        ("status", "get_change_state", "estado de un change"),
        ("ai-usage", "get_ai_usage_record", "AI Usage Record de un change"),
    ):
        parser = change.add_parser(action, help=helptext)
        parser.add_argument("change_name")
        _project_arg(parser)
        parser.set_defaults(handler=_run(tool, lambda a: {"change_name": a.change_name}))
    followups = change.add_parser("followups", help="followups de los jueces")
    followups.add_argument("change_name")
    followups.add_argument("--status", choices=("open", "dismissed", "all"), default="open")
    _project_arg(followups)
    followups.set_defaults(
        handler=_run("get_followups", lambda a: {"change_name": a.change_name, "status": a.status})
    )

    mcp = sub.add_parser(
        "mcp",
        help="servidor MCP por stdio (opcional; ver ADR-0005)",
        description="JSON-RPC 2.0 por stdio. stdout solo lleva el protocolo; logs a stderr.",
    )
    mcp.add_argument("--project", type=Path, default=Path("."), help="raíz del proyecto")
    mcp.add_argument("--verbose", action="store_true", help="logs de depuración en stderr")
    mcp.set_defaults(handler=_serve)


def _opt(**values: Any) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None}


def _run(tool: str, build: Any) -> Any:
    def handler(args: argparse.Namespace) -> int:
        try:
            result = registry.call(tool, build(args), registry.Context(args.project))
        except InputError as exc:
            return error(str(exc))
        if args.json:
            emit_json(result)
        else:
            _print_human(tool, result)
        return 0

    return handler


def _print_human(tool: str, result: dict[str, Any]) -> None:
    if tool == "skills_list":
        for skill in result["skills"]:
            print(f"{skill['name']}\t{skill['pack']}\t{skill['description']}")
    elif tool == "skills_diff":
        for status in ("added", "changed", "removed", "unchanged"):
            for item in result[status]:
                print(f"{status}\t{item['name'] if isinstance(item, dict) else item}")
    elif tool == "list_changes":
        for change in result["changes"]:
            where = "archivado" if change["archived"] else "activo"
            print(f"{change['name']}\t{change['phase']}\t{where}\t{change['path']}")
        if not result["changes"]:
            print("sin changes")
    elif tool == "get_followups":
        for item in result["followups"]:
            print(f"{item.get('id', '-')}\t{item['status']}\t{item.get('summary', '')}")
        if not result["followups"]:
            print("sin followups")
    else:
        for key, value in result.items():
            print(f"{key}: {value}")


def _serve(args: argparse.Namespace) -> int:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return server.serve(args.project)
