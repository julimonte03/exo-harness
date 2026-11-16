"""Specs as-is y severidad de los problemas (F6, ADR-0015)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo.cli import main
from exo.governance import hookrun
from exo.sdd import changes, check, speclint, specs

AS_IS = """# Capability: billing

Status: as-is
Source: exo discover; units: src-billing

## Purpose

Totals, taxes and discounts of invoices, as the code does it today.

## Requirements

### CAP-billing-FR-1: Invoice total

The total is the sum of the lines minus the discount, plus tax. [Code] src/billing/totals.py:12-30

### CAP-billing-FR-2: Discount cap

A discount never goes over 30 % of the subtotal. [Inferred: medium]
"""


def _cap(tmp_path: Path, text: str, name: str = "billing") -> Path:
    path = tmp_path / "specs" / "capabilities" / name / "spec.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _errors(cap: specs.Capability) -> list[str]:
    return [p.message for p in cap.problems if p.severity == "error"]


def _warnings(cap: specs.Capability) -> list[str]:
    return [p.message for p in cap.problems if p.severity == "warning"]


def test_una_spec_as_is_con_evidencia_y_sin_escenarios_no_tiene_errores() -> None:
    cap = specs.parse_capability(AS_IS, "billing")
    assert (cap.status, cap.source) == ("as-is", "exo discover; units: src-billing")
    assert _errors(cap) == []
    assert len(_warnings(cap)) == 2 and all("no scenarios" in w for w in _warnings(cap))


def test_as_is_sin_evidencia_es_error() -> None:
    text = AS_IS.replace(" [Inferred: medium]", "")
    assert any(
        "CAP-billing-FR-2" in e and "evidence" in e
        for e in _errors(specs.parse_capability(text, "billing"))
    )


def test_sin_preambulo_un_fr_sin_escenario_ni_evidencia_sigue_siendo_error() -> None:
    text = AS_IS.replace("Status: as-is\nSource: exo discover; units: src-billing\n\n", "")
    text = text.replace(" [Code] src/billing/totals.py:12-30", "").replace(
        " [Inferred: medium]", ""
    )
    cap = specs.parse_capability(text, "billing")
    assert cap.status is None
    assert sum("no scenarios" in e for e in _errors(cap)) == 2


def test_la_evidencia_relaja_el_escenario_solo_con_status() -> None:
    """M2: sin preámbulo todo es como antes de F6, aunque el FR traiga evidencia."""
    text = AS_IS.replace("Status: as-is\n", "")
    cap = specs.parse_capability(text, "billing")
    assert cap.status is None
    assert sum("no scenarios" in e for e in _errors(cap)) == 2
    validated = specs.parse_capability(AS_IS.replace("as-is\n", "as-is-validated\n", 1), "billing")
    assert validated.status == "as-is-validated" and _errors(validated) == []


LIVING = """# Capability: billing

Status: draft

## Purpose

Totals of invoices.

## Requirements

### CAP-billing-FR-1: Invoice total

The total is the sum of the lines.

#### Scenario: Two lines

- Given two lines of 10
- When the invoice is closed
- Then the total is 20
"""


def test_un_status_desconocido_es_warning_y_no_bloquea_el_pre_commit(tmp_path: Path) -> None:
    """M2: una spec viva que ya tenía `Status: draft` no bloquea nada."""
    import shutil
    import subprocess

    cap = specs.parse_capability(LIVING, "billing")
    assert cap.status is None and _errors(cap) == []
    assert any("Status" in w and "draft" in w for w in _warnings(cap))
    if shutil.which("git") is None:
        pytest.skip("requiere git")
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    path = _cap(tmp_path, LIVING)
    subprocess.run(["git", "-C", str(tmp_path), "add", str(path)], check=True)
    assert hookrun.pre_commit(tmp_path).errors == []


@pytest.mark.parametrize(
    "line",
    ["**Status:** as-is", "**Status**: as-is", "status: as-is", "STATUS: As-Is", "Status: `as-is`"],
)
def test_el_status_se_reconoce_en_negrita_y_sin_distinguir_mayusculas(line: str) -> None:
    text = AS_IS.replace("Status: as-is", line).replace("Source:", "**Source:**")
    cap = specs.parse_capability(text, "billing")
    assert (cap.status, cap.source) == ("as-is", "exo discover; units: src-billing")
    assert _errors(cap) == []


def test_un_status_despues_del_primer_encabezado_es_un_warning() -> None:
    text = AS_IS.replace("Status: as-is\n", "").replace(
        "## Purpose\n\n", "## Purpose\n\nStatus: as-is\n\n"
    )
    cap = specs.parse_capability(text, "billing")
    assert cap.status is None
    assert any("Status goes before ## Purpose" in w for w in _warnings(cap))
    fenced = text.replace("Status: as-is\n", "```\nStatus: as-is\n```\n")
    assert not any("Status goes" in w for w in _warnings(specs.parse_capability(fenced, "billing")))


def test_speclint_check_y_list_respetan_la_severidad(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _cap(tmp_path, AS_IS)
    report = speclint.lint_path(path)
    assert report.ok and len(report.files[0].warnings) == 2
    assert main(["speclint", str(path)]) == 0
    out = capsys.readouterr().out
    assert "warning" in out and "OK" in out
    assert main(["speclint", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"][0]["errors"] == [] and len(payload["files"][0]["warnings"]) == 2
    result = check.check(tmp_path)
    assert result.ok
    assert any(f.severity == "warning" for _, findings in result.capabilities for f in findings)
    [info] = specs.list_capabilities(tmp_path)
    assert (info.status, info.problems) == ("as-is", 0)


def test_no_se_integra_un_delta_en_una_spec_as_is_sin_validar(tmp_path: Path) -> None:
    _cap(tmp_path, AS_IS)
    created = changes.new_change(tmp_path, "cap-discount")
    delta = """# Delta for billing

## ADDED Requirements

### CAP-billing-FR-3: Rounding

Totals round half up to two decimals.

#### Scenario S-1: Half up

- Given a total of 10.005
- When the invoice is closed
- Then the total is 10.01
"""
    (tmp_path / created.path / "spec.md").write_text(delta, encoding="utf-8")
    with pytest.raises(specs.MergeError, match="validate"):
        specs.merge(tmp_path, "cap-discount")
    validated = AS_IS.replace("Status: as-is\n", "Status: as-is-validated\n")
    path = _cap(tmp_path, validated)
    result = specs.merge(tmp_path, "cap-discount")
    assert result.written
    text = path.read_text(encoding="utf-8")
    assert text.startswith(
        "# Capability: billing\n\nStatus: as-is-validated\nSource: exo discover; units: src-billing\n"
    )
    assert "CAP-billing-FR-3" in text


def test_el_pre_commit_no_bloquea_por_warnings(tmp_path: Path) -> None:
    import shutil
    import subprocess

    if shutil.which("git") is None:
        pytest.skip("requiere git")
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    path = _cap(tmp_path, AS_IS)
    subprocess.run(["git", "-C", str(tmp_path), "add", str(path)], check=True)
    assert hookrun.pre_commit(tmp_path).errors == []
