"""`exo doctor`: diagnóstico del entorno, del contenido y de la config del proyecto."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo import doctor
from exo.commands._output import emit_json

_LABEL = {"ok": "ok", "info": "info", "warn": "warning", "error": "error"}


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "doctor",
        help="diagnose the environment and the project",
        description="Exits with 1 if any check reports an error; warnings do not change "
        "the exit code.",
    )
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    checks = doctor.run_checks(args.project)
    ok = all(c.status != "error" for c in checks)
    if args.json:
        emit_json({"ok": ok, "checks": [vars(c) for c in checks]})
        return 0 if ok else 1
    width = max(len(c.name) for c in checks)
    for check in checks:
        print(f"{_LABEL[check.status]:<7}  {check.name:<{width}}  {check.detail}")
    return 0 if ok else 1
