"""`exo check`: chequeos de los changes SDD antes del PR (v1 de F4)."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo.commands._output import emit_json, error
from exo.sdd import check


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "check",
        help="check the SDD changes before the PR (speclint, AI Usage Record, artifacts per tier)",
        description=(
            "By default checks every active change and every capability spec. With --base, only "
            "what changed against that ref (what CI runs); with --change, only those changes. "
            "Exits with 1 if there are errors."
        ),
    )
    parser.add_argument("--base", help="git ref to compare with, for example origin/main")
    parser.add_argument(
        "--change", dest="names", action="append", help="check only this change (repeatable)"
    )
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        result = check.check(args.project, base=args.base, names=args.names)
    except (check.CheckError, ValueError, OSError) as exc:
        return error(str(exc))
    if args.json:
        emit_json(
            {
                "ok": result.ok,
                "notes": result.notes,
                "changes": [
                    {
                        "name": c.name,
                        "path": c.path,
                        "tier": c.tier,
                        "tier_source": c.tier_source,
                        "ok": c.ok,
                        "findings": [_finding(f) for f in c.findings],
                    }
                    for c in result.changes
                ],
                "capabilities": [
                    {"path": path, "findings": [_finding(f) for f in items]}
                    for path, items in result.capabilities
                ],
            }
        )
        return 0 if result.ok else 1
    for note in result.notes:
        print(f"note: {note}")
    for item in result.changes:
        print(f"{'PASS' if item.ok else 'FAIL'} {item.name} (Tier {item.tier})")
        for f in item.findings:
            print(f"  {f.severity}: {_where(f)}{f.message}")
    for path, items in result.capabilities:
        bad = any(f.severity == "error" for f in items)
        print(f"{'FAIL' if bad else 'PASS'} {path}")
        for f in items:
            print(f"  {f.severity}: {_where(f)}{f.message}")
    if not result.changes and not result.capabilities:
        print("nothing to check")
    errors = sum(
        f.severity == "error"
        for group in [c.findings for c in result.changes] + [i for _, i in result.capabilities]
        for f in group
    )
    print(f"{'OK' if result.ok else 'FAILED'}: {errors} errors")
    return 0 if result.ok else 1


def _finding(f: check.Finding) -> dict[str, object]:
    return {"severity": f.severity, "path": f.path, "line": f.line, "message": f.message}


def _where(f: check.Finding) -> str:
    return f"{f.path}:{f.line}: " if f.line else f"{f.path}: "
