"""`exo speclint`: valida artefactos SDD (un archivo o una carpeta de change)."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo.commands._output import emit_json, error
from exo.sdd import speclint


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "speclint",
        help="valida artefactos SDD contra sus plantillas",
        description=(
            "Recibe un artefacto (proposal.md, spec.md, design.md, test-spec.md, "
            "verify-record.md, pr.md) o la carpeta de un change. Sale con 1 si hay errores."
        ),
    )
    parser.add_argument("path", type=Path, help="archivo o carpeta de change")
    parser.add_argument("--type", dest="kind", choices=speclint.KINDS, help="fuerza el tipo")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        report = speclint.lint_path(args.path, args.kind)
    except (ValueError, OSError) as exc:  # SpeclintError, UTF-8 inválido, disco
        return error(str(exc))
    if args.json:
        emit_json(
            {
                "ok": report.ok,
                "files": [
                    {
                        "path": str(f.path),
                        "type": f.kind,
                        "errors": [{"line": i.line, "message": i.message} for i in f.errors],
                    }
                    for f in report.files
                ],
            }
        )
        return 0 if report.ok else 1
    total = 0
    for item in report.files:
        for issue in item.errors:
            total += 1
            print(f"{item.path}:{issue.line}: {issue.message}")
    if total:
        print(f"{total} errores en {len(report.files)} archivos")
        return 1
    print(f"OK: {len(report.files)} archivos sin errores")
    return 0
