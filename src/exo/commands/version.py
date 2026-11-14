"""`exo version`."""

from __future__ import annotations

import argparse

from exo import _meta
from exo.commands._output import emit_json


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("version", help="show the engine version")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    if args.json:
        emit_json({"name": _meta.NAME, "version": _meta.VERSION})
    else:
        print(f"{_meta.NAME} {_meta.VERSION}")
    return 0
