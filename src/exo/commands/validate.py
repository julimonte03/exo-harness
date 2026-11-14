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
        help="validate the engine content (or the content at --root)",
        description="Exits with 1 if there are errors. Warnings do not change the exit code.",
    )
    parser.add_argument("--root", type=Path, help="root of a content tree (with packs/ and rules/)")
    parser.add_argument("--json", action="store_true", help="JSON output")
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
        print(f"{finding.path}:{finding.line}: warning: {finding.message}")
    counts = report.counts
    summary = (
        f"content: {counts['packs']} packs, {counts['skills']} skills, "
        f"{counts['subagents']} subagents, {counts['shared']} shared contracts"
    )
    if report.ok:
        print(f"{summary}: all valid")
        return 0
    print(f"{summary}: {len(report.errors)} errors")
    return 1
