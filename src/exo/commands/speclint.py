"""`exo speclint`: valida artefactos SDD (un archivo o una carpeta de change)."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo.commands._output import emit_json, error
from exo.sdd import speclint


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "speclint",
        help="validate SDD artifacts against their templates",
        description=(
            "Takes an artifact (proposal.md, spec.md, design.md, test-spec.md, "
            "verify-record.md, pr.md) or a change folder. Exits with 1 if there are errors."
        ),
    )
    parser.add_argument("path", type=Path, help="file or change folder")
    parser.add_argument("--type", dest="kind", choices=speclint.KINDS, help="force the type")
    parser.add_argument("--json", action="store_true", help="JSON output")
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
        print(f"{total} errors in {len(report.files)} files")
        return 1
    print(f"OK: {len(report.files)} files without errors")
    return 0
