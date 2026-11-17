"""Command line: run the API, quote an invoice or check a card number."""

from __future__ import annotations

import argparse
import importlib
import sys
from decimal import Decimal

from invoices.billing import LineItem, compute_totals, lookup_discount
from invoices.core.config import load_settings
from invoices.core.errors import InvoiceError
from invoices.payments.cards import mask, validate_card


def load_plugin(name: str):
    """Export plugins are optional modules of `invoices.plugins`, imported by name."""
    if not name.isidentifier():
        raise InvoiceError(f"invalid plugin name: {name!r}")
    return importlib.import_module("invoices.plugins." + name)


def serve(args: argparse.Namespace) -> None:
    import uvicorn  # FastAPI and uvicorn load only for this command

    from invoices.api.app import create_app

    uvicorn.run(create_app(), port=args.port or 8000)


def quote(args: argparse.Namespace) -> None:
    lines = []
    for raw in args.line:
        description, quantity, price, *category = raw.split(":")
        lines.append(LineItem(description, int(quantity), Decimal(price), *category))
    totals = compute_totals(lines, args.region, lookup_discount(args.discount))
    if args.export:
        load_plugin(args.export).export([("QUOTE", totals)], sys.stdout)
    else:
        for name, value in vars(totals).items():
            print(f"{name:>9} {value}")


def check_card(args: argparse.Namespace) -> None:
    digits = validate_card(args.number, sandbox=load_settings().sandbox)
    print(f"{mask(digits)} ok")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="invoices", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="run the HTTP API").add_argument("--port", type=int)
    quoting = commands.add_parser("quote", help="totals of a draft invoice")
    quoting.add_argument("--region", required=True)
    quoting.add_argument("--line", action="append", required=True, metavar="DESC:QTY:PRICE")
    quoting.add_argument("--discount")
    quoting.add_argument("--export", metavar="PLUGIN", help="write the quote with a plugin")
    commands.add_parser("check-card", help="validate a card number").add_argument("number")
    args = parser.parse_args(argv)
    handler = {"serve": serve, "quote": quote, "check-card": check_card}[args.command]
    try:
        handler(args)
    except (InvoiceError, ModuleNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
