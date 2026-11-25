"""`exo fitness classify`: clasifica el riesgo de un cambio a partir de la evidencia.

Con `--change`, además registra el tier en `fitness-assessment.json` del change:
un upgrade es automático y un downgrade exige `--confirm-downgrade` con las
palabras literales de la persona (§6.3).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from exo.commands._output import emit_json, error, usage_error
from exo.core import fsutil
from exo.sdd import changes, fitness


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser("fitness", help="risk classification (tier 1–3)")
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="fitness_command", metavar="<action>")
    classify = actions.add_parser(
        "classify",
        help="compute the tier from the 7 dimensions",
        description=(
            "Missing or unreadable evidence gives Tier 3 (rule FM-00). With --change, the result "
            "is recorded in the change's fitness-assessment.json: raising the tier is automatic, "
            "lowering it needs --confirm-downgrade with the person's exact words."
        ),
    )
    classify.add_argument(
        "--evidence-json",
        help='JSON object with the 7 dimensions (0–3), for example {"blast_radius": 1, ...}',
    )
    classify.add_argument(
        "--evidence-file",
        type=Path,
        help="read the JSON from this file (- for stdin); safer than --evidence-json in "
        "Windows PowerShell, which drops the inner quotes",
    )
    classify.add_argument("--change", help="record the tier in this change")
    classify.add_argument(
        "--confirm-downgrade",
        metavar="WORDS",
        help="the person's literal confirmation, required to lower a recorded tier",
    )
    classify.add_argument("--project", type=Path, default=Path("."), help="project root")
    classify.add_argument("--json", action="store_true", help="JSON output")
    classify.set_defaults(handler=run)


def _read_evidence(args: argparse.Namespace) -> str | None:
    if args.evidence_file is None:
        return args.evidence_json
    if str(args.evidence_file) == "-":
        return sys.stdin.read()
    return fsutil.read_text_auto(args.evidence_file)


def run(args: argparse.Namespace) -> int:
    if (args.evidence_json is None) == (args.evidence_file is None):
        return usage_error(
            "pass the evidence with --evidence-json or --evidence-file (one of them)"
        )
    if args.confirm_downgrade is not None and args.change is None:
        return usage_error("--confirm-downgrade needs --change")
    try:
        text = _read_evidence(args)
    except OSError as exc:
        return usage_error(
            f"cannot read --evidence-file {args.evidence_file}: {exc.strerror or exc}"
        )
    except ValueError as exc:
        return usage_error(str(exc))
    assert text is not None
    args.evidence_json = text
    decision = fitness.classify_json(text)
    assessment = None
    if args.change is not None:
        try:
            evidence = json.loads(text)
        except json.JSONDecodeError as exc:
            return usage_error(
                f"the evidence is not valid JSON ({exc.msg}, position {exc.pos}); nothing was "
                "recorded. In Windows PowerShell 5.1 pass it with --evidence-file"
            )
        try:
            assessment = changes.record_assessment(
                args.project,
                args.change,
                evidence,
                confirm_downgrade=args.confirm_downgrade,
            )
        except (changes.ChangeError, OSError) as exc:
            return error(str(exc))
        decision = assessment.decision
    if args.json:
        payload = decision.to_dict()
        if assessment is not None:
            payload["assessment"] = {
                "path": assessment.path,
                "previous": assessment.previous,
                "comparison": assessment.comparison,
                "written": assessment.written,
            }
        emit_json(payload)
        return 0
    jd = "judgment-day mandatory" if decision.judgment_day else "no judgment-day"
    print(f"Tier {decision.tier} ({decision.rule}): ceremony {decision.ceremony}, {jd}")
    for problem in decision.errors:
        print(f"  invalid evidence: {problem}")
    if assessment is not None:
        if not assessment.written:
            print(f"{assessment.path}: unchanged")
        elif assessment.comparison == "initial":
            print(f"recorded in {assessment.path}")
        else:
            previous = assessment.previous
            print(
                f"recorded in {assessment.path} ({assessment.comparison} from Tier "
                f"{previous if previous is not None else fitness.FAILSAFE_TIER})"
            )
    return 0
