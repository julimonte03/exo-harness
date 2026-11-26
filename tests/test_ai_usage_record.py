"""Esquema del AI Usage Record (ticket_key, sin playbook)."""

from __future__ import annotations

import copy

import pytest

from exo.core import jsonschema
from exo.sdd import record

MINIMAL = {
    "attribution_schema_version": 1,
    "change_name": "AB-123-add-login",
    "capabilities_used": [{"name": "change_new", "type": "tool", "activation": "requested"}],
    "updated_at": "2026-11-14T10:00:00Z",
}


def test_el_esquema_usa_solo_lo_que_el_validador_soporta() -> None:
    jsonschema.check_schema(record.schema())


def test_registro_minimo() -> None:
    assert record.validate(MINIMAL) == []


def test_registro_completo() -> None:
    data = {
        **copy.deepcopy(MINIMAL),
        "ticket_key": "AB#123",
        "epic_key": None,
        "purpose": "Let users sign in.",
        "skills_used": ["sdd-new"],
        "knowledge_used": [{"source": "code", "ref": "src/app.py:10"}],
        "judges_invoked": [{"name": "judge-security", "result": "advisory"}],
        "decisions": [{"summary": "Tier 1", "by": "human"}],
        "dismissed_followups": [{"id": "J1", "judge": "judge-security", "rule": "S-1", "reason": "false positive"}],
        "gates": [{"name": "contract_check", "status": "pass"}],
        "updated_at": "2026-11-14T10:00:00.123+00:00",
    }
    data["capabilities_used"].append(
        {
            "name": "sdd-verify",
            "type": "skill",
            "activation": "auto",
            "resolution": "fallback-registry",
            "note": "quality not installed — applying inline criteria",
        }
    )
    assert record.validate(data) == []


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"capabilities_used": None}, "$.capabilities_used: must be of type array"),
        ({"capabilities_used": []}, "$.capabilities_used: must have at least 1 item"),
        (
            {"capabilities_used": [{"name": "x", "type": "skill", "activation": "explicit"}]},
            "$.capabilities_used[0].activation: must be one of: requested, auto",
        ),
        ({"change_name": "#123-x"}, "$.change_name: must match"),
        ({"updated_at": "14/11/2026"}, "$.updated_at: must match"),
        ({"jira_key": "PROJ-1"}, "$: unexpected property 'jira_key'"),
        ({"playbook": "x"}, "$: unexpected property 'playbook'"),
        ({"attribution_schema_version": 0}, "$.attribution_schema_version: must be ≥ 1"),
    ],
)
def test_registro_invalido(change: dict, error: str) -> None:
    data = {**copy.deepcopy(MINIMAL), **change}
    errors = record.validate(data)
    assert any(e.startswith(error) for e in errors), errors


@pytest.mark.parametrize("field", ["attribution_schema_version", "change_name", "capabilities_used", "updated_at"])
def test_campos_obligatorios(field: str) -> None:
    data = copy.deepcopy(MINIMAL)
    del data[field]
    assert f"$: missing required property {field!r}" in record.validate(data)
