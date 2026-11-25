"""CLI del motor. Solo cablea subcomandos; la lógica vive en los módulos del runtime."""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Iterable, Sequence

from exo import _meta, commands


def build_parser(modules: Iterable[str] | None = None) -> argparse.ArgumentParser:
    """El parser del CLI con los subcomandos de `modules` (por defecto, todos). `main` le
    pasa solo los que necesita la llamada (`commands.needed`): el resto no se importa."""
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
    commands.register(sub, modules)
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
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser(commands.needed(argv))
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))
