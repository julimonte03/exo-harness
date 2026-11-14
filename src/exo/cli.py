"""CLI del motor. Solo cablea subcomandos; la lógica vive en los módulos del runtime."""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Sequence

from exo import _meta
from exo.commands import COMMANDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_meta.NAME,
        description=f"{_meta.DISPLAY_NAME}: a governed, per-project development engine.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{_meta.NAME} {_meta.VERSION}",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    for register in COMMANDS:
        register(sub)
    return parser


def _tolerant_streams() -> None:
    # Una consola Windows en cp1252 no debe cortar la salida por un carácter. Si la salida
    # va a un pipe o a un archivo (un agente leyendo `exo mem context`, por ejemplo), sale
    # en UTF-8, como --json: con la página de códigos se perdían acentos y símbolos.
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError, OSError):
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _tolerant_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))
