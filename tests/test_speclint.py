"""sdd/speclint: encabezados obligatorios, IDs y referencias cruzadas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import _meta
from exo.cli import main
from exo.sdd import speclint

PROPOSAL = """# Proposal: demo

## Intent
Resolver X.

## Scope
- A

## Approach
Hacer B.

## Out of Scope
- C
"""

SPEC = """# Spec: demo

## Requirements
- **FR-1** The system shall do A.
- **FR-2** The system shall do B.
- **NFR-1** It responds in under 1 s.

## Scenarios

### S-1 Happy path
- Given a user
- When it does A
- Then it sees B

### S-2 Error
- Given a broken input
- When it does A
- Then it sees an error
"""

DESIGN = """# Design: demo

## Architecture Overview
One module.

## Modules / Files
- src/x.py

## Data Shapes
None.

## Sequence Of Operations
1. Read. 2. Write.

## Error Handling
Raise ValueError.

## Test Plan
- S-1 -> test_happy (covers FR-1)
- S-2 -> test_error (covers FR-2)

## Migration / Backwards Compatibility
None.

## Risks & Mitigations
Low.
"""

TEST_SPEC = """# Test Spec: demo

## Scope
Unit.

## Test Cases
| ID | Covers | Level | Description | Command |
|---|---|---|---|---|
| T-1 | S-1, FR-1 | unit | happy | pytest -k happy |

## Traceability
- FR-1, S-1: T-1
"""

MARKER = f"<!-- {_meta.BLOCK_PREFIX}-gate:contract_check -->"

VERIFY = f"""# Verify Record: demo

## Verdict
ready

## Spec Coverage
FR-1 -> test_happy

## Scenario Coverage
S-1 -> test_happy

## Issues Found
None.

## Tests
pytest: 10 passed

## Out-of-Scope Drift
None.

## Judgment Day Handoff
N/A

## Gate summary
{MARKER}
Requires tech_lead approval: no
"""

PR = """# feat(x): demo

## Summary
Adds A.

## Ticket
none

## Changes
- A

## Test Plan
pytest

## Checklist
- [x] Tests
"""


def _write(folder: Path, name: str, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def _messages(result: speclint.LintReport) -> list[str]:
    return [issue.message for f in result.files for issue in f.errors]


@pytest.mark.parametrize(
    ("name", "text", "kind"),
    [
        ("proposal.md", PROPOSAL, "functional"),
        ("spec.md", SPEC, "functional"),
        ("design.md", DESIGN, "technical"),
        ("test-spec.md", TEST_SPEC, "test-spec"),
        ("verify-record.md", VERIFY, "verify-record"),
        ("pr.md", PR, "pr"),
    ],
)
def test_documentos_validos(tmp_path: Path, name: str, text: str, kind: str) -> None:
    report = speclint.lint_path(_write(tmp_path, name, text))
    assert report.ok, _messages(report)
    assert report.files[0].kind == kind


@pytest.mark.parametrize("name", sorted(speclint.ARTIFACTS))
def test_plantillas_sin_completar_no_pasan(tmp_path: Path, name: str) -> None:
    template = speclint.template_text(speclint.ARTIFACTS[name])
    report = speclint.lint_path(_write(tmp_path, name, template))
    assert not report.ok
    assert any("vacía" in m for m in _messages(report))


def test_marcador_de_gate_de_la_plantilla_coincide_con_el_codigo() -> None:
    assert speclint.GATE_MARKER.match(MARKER)
    assert MARKER in speclint.template_text("verify-record")


def test_falta_encabezado_y_seccion_vacia(tmp_path: Path) -> None:
    text = PROPOSAL.replace("## Approach\nHacer B.\n", "").replace("- C\n", "<!-- nada -->\n")
    messages = _messages(speclint.lint_path(_write(tmp_path, "proposal.md", text)))
    assert "falta la sección '## Approach'" in messages
    assert "la sección 'Out of Scope' está vacía" in messages


def test_encabezados_sin_distinguir_mayusculas(tmp_path: Path) -> None:
    text = PROPOSAL.replace("## Out of Scope", "## out OF scope")
    assert speclint.lint_path(_write(tmp_path, "proposal.md", text)).ok


def test_encabezados_dentro_de_bloques_de_codigo_no_cuentan(tmp_path: Path) -> None:
    text = PROPOSAL.replace("## Approach\nHacer B.\n", "```\n## Approach\n```\n")
    messages = _messages(speclint.lint_path(_write(tmp_path, "proposal.md", text)))
    assert "falta la sección '## Approach'" in messages


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("- **FR-2** The system", "- **FR-1** The system", "FR-1 definido dos veces"),
        ("- **FR-2** The system", "- **FR-02** The system", "ID mal formado: FR-02"),
        ("- **FR-2** The system", "- **fr-2** The system", "ID mal formado: fr-2"),
        ("### S-2 Error", "### S-1 Error", "S-1 definido dos veces"),
        ("- Then it sees an error\n", "", "S-2 no tiene Then"),
        ("- Given a user\n", "", "S-1 no tiene Given"),
    ],
)
def test_reglas_de_ids_en_spec(tmp_path: Path, old: str, new: str, fragment: str) -> None:
    report = speclint.lint_path(_write(tmp_path, "spec.md", SPEC.replace(old, new)))
    assert any(fragment in m for m in _messages(report)), _messages(report)


def test_spec_sin_requisitos_ni_escenarios(tmp_path: Path) -> None:
    text = "# Spec\n\n## Requirements\nTexto libre.\n\n## Scenarios\nTexto libre.\n"
    messages = _messages(speclint.lint_path(_write(tmp_path, "spec.md", text)))
    assert "no hay requisitos FR-n en 'Requirements'" in messages
    assert "no hay escenarios S-n en 'Scenarios'" in messages


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("## Verdict\nready", "## Verdict\nmaybe", "Verdict tiene que ser"),
        (MARKER, "sin marcador", "falta el marcador de gate"),
    ],
)
def test_reglas_del_verify_record(tmp_path: Path, old: str, new: str, fragment: str) -> None:
    report = speclint.lint_path(_write(tmp_path, "verify-record.md", VERIFY.replace(old, new)))
    assert any(fragment in m for m in _messages(report)), _messages(report)


def test_errores_llevan_numero_de_linea(tmp_path: Path) -> None:
    report = speclint.lint_path(_write(tmp_path, "spec.md", SPEC.replace("**FR-2**", "**FR-1**")))
    issue = report.files[0].errors[0]
    assert issue.line == 5


# -- carpeta de change --------------------------------------------------------


def _change(tmp_path: Path) -> Path:
    folder = tmp_path / "specs" / "demo"
    for name, text in (("proposal.md", PROPOSAL), ("spec.md", SPEC), ("design.md", DESIGN), ("test-spec.md", TEST_SPEC)):
        _write(folder, name, text)
    return folder


def test_carpeta_completa_valida(tmp_path: Path) -> None:
    report = speclint.lint_path(_change(tmp_path))
    assert report.ok, _messages(report)
    assert [f.path.name for f in report.files] == ["proposal.md", "spec.md", "design.md", "test-spec.md"]


def test_escenario_sin_test_en_el_plan(tmp_path: Path) -> None:
    folder = _change(tmp_path)
    _write(folder, "design.md", DESIGN.replace("- S-2 -> test_error (covers FR-2)\n", ""))
    assert "S-2 de spec.md no aparece en el Test Plan de design.md" in _messages(speclint.lint_path(folder))


def test_referencia_a_id_inexistente(tmp_path: Path) -> None:
    folder = _change(tmp_path)
    _write(folder, "test-spec.md", TEST_SPEC.replace("- FR-1, S-1: T-1", "- FR-9, S-7: T-1"))
    messages = _messages(speclint.lint_path(folder))
    assert "FR-9 no está definido en spec.md" in messages
    assert "S-7 no está definido en spec.md" in messages


def test_carpeta_sin_artefactos(tmp_path: Path) -> None:
    (tmp_path / "vacia").mkdir()
    report = speclint.lint_path(tmp_path / "vacia")
    assert not report.ok
    assert "no hay artefactos" in _messages(report)[0]


def test_tipo_forzado_y_tipo_desconocido(tmp_path: Path) -> None:
    path = _write(tmp_path, "notas.md", DESIGN)
    with pytest.raises(speclint.SpeclintError, match="--type"):
        speclint.lint_path(path)
    assert speclint.lint_path(path, kind="technical").ok
    with pytest.raises(speclint.SpeclintError, match="tipo"):
        speclint.lint_path(path, kind="inventado")


# -- CLI ----------------------------------------------------------------------


def test_cli_speclint(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _change(tmp_path)
    assert main(["speclint", str(folder)]) == 0
    assert "OK" in capsys.readouterr().out
    _write(folder, "design.md", DESIGN.replace("## Error Handling\nRaise ValueError.\n", ""))
    assert main(["speclint", str(folder)]) == 1
    out = capsys.readouterr().out
    assert "design.md:" in out
    assert "Error Handling" in out
    assert main(["speclint", str(folder), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert any(f["errors"] for f in payload["files"])


def test_cli_speclint_errores_de_uso(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["speclint", str(tmp_path / "no-existe.md")]) == 1
    assert "no existe" in capsys.readouterr().err
    path = _write(tmp_path, "notas.md", DESIGN)
    assert main(["speclint", str(path)]) == 1
    assert main(["speclint", str(path), "--type", "technical"]) == 0


def test_ids_dentro_de_codigo_no_cuentan_y_lo_que_sigue_si(tmp_path: Path) -> None:
    text = SPEC.replace(
        "- **FR-2** The system shall do B.\n",
        "```\n- **FR-1** ejemplo dentro de código\n```\n- **FR-2** The system shall do B.\n- **FR-2** repetido\n",
    )
    messages = _messages(speclint.lint_path(_write(tmp_path, "spec.md", text)))
    assert not any("FR-1 definido dos veces" in m for m in messages)
    assert any("FR-2 definido dos veces" in m for m in messages)
