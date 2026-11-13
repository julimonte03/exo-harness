"""`exo fitness classify`: clasifica el riesgo de un cambio a partir de la evidencia."""

from __future__ import annotations

import argparse

from exo.commands._output import emit_json
from exo.sdd import fitness


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser("fitness", help="risk classification (tier 1–4)")
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="fitness_command", metavar="<action>")
    classify = actions.add_parser(
        "classify",
        help="compute the tier from the 7 dimensions",
        description="Missing or unreadable evidence gives Tier 4 (rule FM-00).",
    )
    classify.add_argument(
        "--evidence-json",
        required=True,
        help='JSON object with the 7 dimensions (0–3), for example {"blast_radius": 1, ...}',
    )
    classify.add_argument("--json", action="store_true", help="JSON output")
    classify.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    decision = fitness.classify_json(args.evidence_json)
    if args.json:
        emit_json(decision.to_dict())
        return 0
    jd = "judgment-day mandatory" if decision.judgment_day else "no judgment-day"
    print(f"Tier {decision.tier} ({decision.rule}): ceremony {decision.ceremony}, {jd}")
    for problem in decision.errors:
        print(f"  invalid evidence: {problem}")
    return 0
