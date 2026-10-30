"""CLI del motor. En F0 solo responde `--version`; F1 suma los subcomandos."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from exo import _meta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_meta.NAME,
        description=f"{_meta.DISPLAY_NAME}: motor de desarrollo gobernado por proyecto.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{_meta.NAME} {_meta.VERSION}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
