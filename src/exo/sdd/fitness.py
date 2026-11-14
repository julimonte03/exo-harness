"""Clasificación de riesgo de un cambio (tier 1–4), pura y determinista.

Port de §4.8 del reporte (`la referencia privada (§4)`):
siete dimensiones con valores 0–3 y reglas FM-xx. La primera regla que
coincide, en el orden de `RULES`, decide el tier. La evidencia faltante o
ilegible da Tier 4 por la regla `FM-00` (fail-safe de §6.3; definición propia
porque el reporte no le da número).

La tabla también vive en
`content/packs/sdd/skills/risk-tiering/references/classification-rules.md` y un
test de paridad compara ambas.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

DIMENSIONS = (
    "blast_radius",
    "component_criticality",
    "security_data_sensitivity",
    "reversibility",
    "files_modules_footprint",
    "test_maturity_gap",
    "regulatory_compliance_impact",
)
CEREMONIES = {1: "minimal", 2: "light", 3: "full", 4: "full"}
FAILSAFE_RULE = "FM-00"
FAILSAFE_TIER = 4
FAILSAFE_CONDITION = "missing or unreadable evidence"
_MIN, _MAX = 0, 3


@dataclass(frozen=True)
class Rule:
    id: str
    tier: int
    condition: str
    predicate: Callable[[Mapping[str, int]], bool]


def _equals_three(dimension: str) -> Callable[[Mapping[str, int]], bool]:
    return lambda e: e[dimension] == 3


def _at_least(count: int, value: int) -> Callable[[Mapping[str, int]], bool]:
    """Al menos `count` dimensiones con valor >= `value`."""
    return lambda e: sum(v >= value for v in e.values()) >= count


RULES: tuple[Rule, ...] = (
    Rule("FM-01", 4, "security_data_sensitivity == 3", _equals_three("security_data_sensitivity")),
    Rule("FM-02", 4, "reversibility == 3", _equals_three("reversibility")),
    Rule(
        "FM-03",
        4,
        "regulatory_compliance_impact == 3",
        _equals_three("regulatory_compliance_impact"),
    ),
    Rule("FM-10", 3, "component_criticality == 3", _equals_three("component_criticality")),
    Rule("FM-11", 3, "blast_radius == 3", _equals_three("blast_radius")),
    Rule("FM-12", 3, "files_modules_footprint == 3", _equals_three("files_modules_footprint")),
    Rule("FM-13", 3, ">= 3 dimensions with value >= 2", _at_least(3, 2)),
    Rule("FM-20", 2, ">= 1 dimension with value >= 2", _at_least(1, 2)),
    Rule("FM-30", 1, "all dimensions <= 1", lambda e: all(v <= 1 for v in e.values())),
)
RULE_TIERS: dict[str, int] = {FAILSAFE_RULE: FAILSAFE_TIER, **{r.id: r.tier for r in RULES}}


@dataclass(frozen=True)
class FitnessDecision:
    tier: int
    rule: str
    matched_rules: tuple[str, ...]
    ceremony: str
    judgment_day: bool
    evidence: dict[str, int] | None
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "rule": self.rule,
            "matched_rules": list(self.matched_rules),
            "ceremony": self.ceremony,
            "judgment_day": self.judgment_day,
            "evidence": dict(self.evidence) if self.evidence is not None else None,
            "errors": list(self.errors),
        }


def _decision(
    tier: int,
    rule: str,
    matched: tuple[str, ...],
    evidence: dict[str, int] | None,
    errors: tuple[str, ...] = (),
) -> FitnessDecision:
    return FitnessDecision(tier, rule, matched, CEREMONIES[tier], tier == 4, evidence, errors)


def parse_evidence(raw: Any) -> tuple[dict[str, int] | None, list[str]]:
    if raw is None:
        return None, ["missing evidence"]
    if not isinstance(raw, Mapping):
        return None, ["evidence must be an object {dimension: value}"]
    errors = [f"unknown dimension: {key}" for key in raw if key not in DIMENSIONS]
    evidence: dict[str, int] = {}
    for dimension in DIMENSIONS:
        if dimension not in raw:
            errors.append(f"missing {dimension}")
            continue
        value = raw[dimension]
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{dimension} must be an integer, not {value!r}")
        elif not _MIN <= value <= _MAX:
            errors.append(f"{dimension} must be between 0 and 3, not {value}")
        else:
            evidence[dimension] = value
    return (None, errors) if errors else (evidence, [])


def classify(raw: Any) -> FitnessDecision:
    evidence, errors = parse_evidence(raw)
    if evidence is None:
        return _decision(FAILSAFE_TIER, FAILSAFE_RULE, (FAILSAFE_RULE,), None, tuple(errors))
    matched = tuple(rule.id for rule in RULES if rule.predicate(evidence))
    winner = next(rule for rule in RULES if rule.predicate(evidence))
    return _decision(winner.tier, winner.id, matched, evidence)


def classify_json(text: str) -> FitnessDecision:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        error = f"evidence is not valid JSON ({exc.msg}, position {exc.pos})"
        return _decision(FAILSAFE_TIER, FAILSAFE_RULE, (FAILSAFE_RULE,), None, (error,))
    return classify(raw)


def _check_tier(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 4:
        raise ValueError(f"invalid tier: {value!r} (must be 1, 2, 3 or 4)")
    return value


def normalize_tier(value: Any) -> int:
    """Tier desconocido o ilegible es Tier 4 (fail-safe)."""
    try:
        return _check_tier(value)
    except ValueError:
        return FAILSAFE_TIER


def compare_tiers(current: Any, proposed: Any) -> str:
    """`upgrade`, `downgrade` o `same`. El downgrade requiere confirmación humana literal."""
    now, then = _check_tier(current), _check_tier(proposed)
    if then > now:
        return "upgrade"
    if then < now:
        return "downgrade"
    return "same"
