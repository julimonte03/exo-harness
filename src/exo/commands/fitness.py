"""`exo fitness classify`: clasifica el riesgo de un cambio a partir de la evidencia."""

from __future__ import annotations

import argparse

from exo.commands._output import emit_json
from exo.sdd import fitness


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser("fitness", help="clasificación de riesgo (tier 1–4)")
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="fitness_command", metavar="<acción>")
    classify = actions.add_parser(
        "classify",
        help="calcula el tier a partir de las 7 dimensiones",
        description="Evidencia faltante o ilegible da Tier 4 (regla FM-00).",
    )
    classify.add_argument(
        "--evidence-json",
        required=True,
        help='objeto JSON con las 7 dimensiones 0–3, por ejemplo {"blast_radius": 1, ...}',
    )
    classify.add_argument("--json", action="store_true", help="salida JSON")
    classify.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    decision = fitness.classify_json(args.evidence_json)
    if args.json:
        emit_json(decision.to_dict())
        return 0
    jd = "judgment-day obligatorio" if decision.judgment_day else "sin judgment-day"
    print(f"Tier {decision.tier} ({decision.rule}): ceremonia {decision.ceremony}, {jd}")
    for problem in decision.errors:
        print(f"  evidencia inválida: {problem}")
    return 0
