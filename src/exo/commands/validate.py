"""`exo validate`: valida el contenido canónico (packs, skills, subagentes, reglas)."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo import content
from exo.commands._output import emit_json, error
from exo.validate import validate


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "validate",
        help="valida el contenido del motor (o el de --root)",
        description="Sale con 1 si hay errores. Las advertencias no cambian el código de salida.",
    )
    parser.add_argument("--root", type=Path, help="raíz de un contenido (con packs/ y rules/)")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        root = args.root if args.root is not None else content.content_root()
    except content.ContentError as exc:
        return error(str(exc))
    report = validate(root)
    if args.json:
        emit_json(
            {
                "ok": report.ok,
                "root": str(root),
                "counts": report.counts,
                "errors": [vars(f) for f in report.errors],
                "warnings": [vars(f) for f in report.warnings],
            }
        )
        return 0 if report.ok else 1
    for finding in report.errors:
        print(f"{finding.path}:{finding.line}: error: {finding.message}")
    for finding in report.warnings:
        print(f"{finding.path}:{finding.line}: aviso: {finding.message}")
    counts = report.counts
    summary = (
        f"contenido: {counts['packs']} packs, {counts['skills']} skills, "
        f"{counts['subagents']} subagentes"
    )
    if report.ok:
        print(f"{summary}: todo válido")
        return 0
    print(f"{summary}: {len(report.errors)} errores")
    return 1
