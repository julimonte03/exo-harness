"""`exo inject`: inserta, lista o quita bloques marcados en un archivo."""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from exo.commands._output import emit_json, error, usage_error
from exo.core import filemerge


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "inject",
        help="inserta, lista o quita un bloque marcado en un archivo",
        description=(
            "Gestiona bloques BEGIN/END del motor dentro de un archivo, sin tocar el resto. "
            "Idempotente: si nada cambia, no escribe."
        ),
    )
    parser.add_argument("file", type=Path, help="archivo a modificar")
    parser.add_argument("--id", dest="block_id", help="id del bloque (por ejemplo core)")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--content", help="contenido del bloque")
    source.add_argument("--from", dest="source", help="archivo con el contenido, o - para stdin")
    source.add_argument("--remove", action="store_true", help="quita el bloque")
    source.add_argument("--list", action="store_true", help="lista los bloques del archivo")
    parser.add_argument("--position", choices=("end", "start"), default="end")
    parser.add_argument("--style", choices=(filemerge.STYLE_HTML, filemerge.STYLE_HASH))
    parser.add_argument("--backup", action="store_true", help="guarda una copia antes de escribir")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.set_defaults(handler=run)


def _content(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.source == "-":
        return sys.stdin.read()
    return Path(args.source).read_text(encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    if args.list:
        return _list(args)
    if not args.block_id:
        return usage_error("falta --id con el id del bloque")
    if not args.remove and args.content is None and args.source is None:
        return usage_error("indicá el contenido con --content o --from (o usá --remove)")
    try:
        if args.remove:
            changed = filemerge.remove(
                args.file, args.block_id, style=args.style, backup=args.backup
            )
            action, human = "remove", ("quitado" if changed else "no estaba")
        else:
            changed = filemerge.inject(
                args.file,
                args.block_id,
                _content(args),
                style=args.style,
                position=args.position,
                backup=args.backup,
            )
            action, human = "inject", ("actualizado" if changed else "sin cambios")
    except (ValueError, OSError) as exc:  # BlockError, UTF-8 inválido, disco
        return error(str(exc))
    if args.json:
        emit_json(
            {"action": action, "path": str(args.file), "block": args.block_id, "changed": changed}
        )
    else:
        print(f"{args.file}: bloque {args.block_id} {human}")
    return 0


def _list(args: argparse.Namespace) -> int:
    try:
        blocks = filemerge.list_blocks(args.file, style=args.style)
    except (filemerge.BlockError, OSError) as exc:
        return error(str(exc))
    if args.json:
        emit_json({"action": "list", "path": str(args.file), "blocks": [asdict(b) for b in blocks]})
        return 0
    for block in blocks:
        print(f"{block.id}\tlíneas {block.start_line}-{block.end_line}")
    if not blocks:
        print(f"{args.file}: sin bloques")
    return 0
