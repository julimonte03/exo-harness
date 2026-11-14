"""sdd/fitness: clasificación de riesgo FM-00…FM-30, paridad con el Markdown y CLI."""

from __future__ import annotations

import json
import re

import pytest

from exo import content
from exo.cli import main
from exo.sdd import fitness
from exo.sdd.fitness import DIMENSIONS

ZERO = dict.fromkeys(DIMENSIONS, 0)


def _ev(**values: int) -> dict[str, int]:
    return {**ZERO, **values}


@pytest.mark.parametrize(
    ("evidence", "tier", "rule"),
    [
        (_ev(), 1, "FM-30"),
        (dict.fromkeys(DIMENSIONS, 1), 1, "FM-30"),
        (_ev(security_data_sensitivity=3), 4, "FM-01"),
        (_ev(reversibility=3), 4, "FM-02"),
        (_ev(regulatory_compliance_impact=3), 4, "FM-03"),
        (_ev(component_criticality=3), 3, "FM-10"),
        (_ev(blast_radius=3), 3, "FM-11"),
        (_ev(files_modules_footprint=3), 3, "FM-12"),
        (_ev(blast_radius=2, reversibility=2, test_maturity_gap=2), 3, "FM-13"),
        (_ev(test_maturity_gap=3, blast_radius=2, component_criticality=2), 3, "FM-13"),
        (_ev(blast_radius=2, reversibility=2), 2, "FM-20"),
        (_ev(security_data_sensitivity=2), 2, "FM-20"),
        (_ev(test_maturity_gap=3), 2, "FM-20"),
        (_ev(security_data_sensitivity=3, blast_radius=3), 4, "FM-01"),
        (_ev(reversibility=3, regulatory_compliance_impact=3), 4, "FM-02"),
        (_ev(component_criticality=3, blast_radius=2, reversibility=2), 3, "FM-10"),
    ],
)
def test_reglas_tabulares(evidence: dict[str, int], tier: int, rule: str) -> None:
    decision = fitness.classify(evidence)
    assert (decision.tier, decision.rule) == (tier, rule)
    assert decision.ceremony == fitness.CEREMONIES[tier]
    assert decision.judgment_day is (tier == 4)
    assert decision.errors == ()


def test_matched_rules_lista_todas_en_orden() -> None:
    decision = fitness.classify(_ev(security_data_sensitivity=3, blast_radius=3))
    assert decision.matched_rules == ("FM-01", "FM-11", "FM-20")


@pytest.mark.parametrize(
    ("evidence", "fragment"),
    [
        (None, "missing evidence"),
        ([1, 2], "object"),
        ({k: v for k, v in ZERO.items() if k != "reversibility"}, "missing reversibility"),
        ({**ZERO, "blast_radious": 1}, "unknown dimension: blast_radious"),
        ({**ZERO, "blast_radius": True}, "integer"),
        ({**ZERO, "blast_radius": 1.5}, "integer"),
        ({**ZERO, "blast_radius": "2"}, "integer"),
        ({**ZERO, "blast_radius": None}, "integer"),
        ({**ZERO, "blast_radius": -1}, "between 0 and 3"),
        ({**ZERO, "blast_radius": 4}, "between 0 and 3"),
    ],
)
def test_evidencia_faltante_o_ilegible_da_tier_4(evidence: object, fragment: str) -> None:
    decision = fitness.classify(evidence)
    assert (decision.tier, decision.rule) == (4, "FM-00")
    assert decision.judgment_day is True
    assert decision.evidence is None
    assert any(fragment in e for e in decision.errors), decision.errors


def test_json_ilegible() -> None:
    decision = fitness.classify_json("{ no json")
    assert (decision.tier, decision.rule) == (4, "FM-00")
    assert "JSON" in decision.errors[0]
    assert fitness.classify_json(json.dumps(_ev(blast_radius=2))).rule == "FM-20"


def test_to_dict() -> None:
    payload = fitness.classify(_ev(blast_radius=3)).to_dict()
    assert payload == {
        "tier": 3,
        "rule": "FM-11",
        "matched_rules": ["FM-11", "FM-20"],
        "ceremony": "full",
        "judgment_day": False,
        "evidence": _ev(blast_radius=3),
        "errors": [],
    }


@pytest.mark.parametrize(
    ("current", "proposed", "expected"),
    [(1, 3, "upgrade"), (4, 2, "downgrade"), (2, 2, "same"), (3, 4, "upgrade")],
)
def test_compare_tiers(current: int, proposed: int, expected: str) -> None:
    assert fitness.compare_tiers(current, proposed) == expected


@pytest.mark.parametrize("bad", [0, 5, "2", None, True, 2.0])
def test_compare_tiers_invalido(bad: object) -> None:
    with pytest.raises(ValueError, match="tier"):
        fitness.compare_tiers(bad, 2)
    with pytest.raises(ValueError, match="tier"):
        fitness.compare_tiers(2, bad)


@pytest.mark.parametrize(("raw", "tier"), [(1, 1), (4, 4), (0, 4), ("3", 4), (None, 4), (True, 4)])
def test_tier_desconocido_es_4(raw: object, tier: int) -> None:
    assert fitness.normalize_tier(raw) == tier


# -- paridad con la referencia en Markdown ------------------------------------

_ROW = re.compile(r"^\|\s*(FM-\d{2})\s*\|\s*`([^`]+)`\s*\|\s*(\d)\s*\|")


def _markdown_rules() -> list[tuple[str, str, int]]:
    path = (
        content.content_root()
        / "packs" / "sdd" / "skills" / "risk-tiering" / "references" / "classification-rules.md"
    )
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line)
        if match:
            rows.append((match.group(1), match.group(2), int(match.group(3))))
    return rows


def test_paridad_codigo_markdown() -> None:
    expected = [
        (fitness.FAILSAFE_RULE, fitness.FAILSAFE_CONDITION, fitness.FAILSAFE_TIER),
        *((r.id, r.condition, r.tier) for r in fitness.RULES),
    ]
    assert _markdown_rules() == expected


# -- CLI ----------------------------------------------------------------------


def test_cli_criterio_2(capsys: pytest.CaptureFixture[str]) -> None:
    evidence = json.dumps(_ev(security_data_sensitivity=3))
    assert main(["fitness", "classify", "--evidence-json", evidence, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert (payload["tier"], payload["rule"]) == (4, "FM-01")
    assert main(["fitness", "classify", "--evidence-json", evidence]) == 0
    out = capsys.readouterr().out
    assert "Tier 4" in out
    assert "FM-01" in out
    assert "judgment-day" in out


def test_cli_evidencia_rota(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fitness", "classify", "--evidence-json", '{"blast_radius": 9}']) == 0
    out = capsys.readouterr().out
    assert "FM-00" in out
    assert "evidence" in out


def test_cli_fitness_sin_accion(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fitness"]) == 0
    assert "classify" in capsys.readouterr().out
