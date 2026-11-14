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

## ADDED Requirements

### CAP-demo-FR-1: Do A
The system shall do A.

#### Scenario S-1: Happy path
- Given a user
- When it does A
- Then it sees B

### CAP-demo-NFR-1: Fast
It responds in under 1 s.

## MODIFIED Requirements

### CAP-demo-FR-2: Do B
The system shall do B.

#### Scenario S-2: Error
- Given a broken input
- When it does A
- Then it sees an error
"""

CAPABILITY = """# Capability: demo

## Purpose
Do things.

## Requirements

### CAP-demo-FR-2: Do B
The system shall do B, the old way.

#### Scenario: Old
- Given a user
- When it does B
- Then it works

### CAP-demo-FR-3: Do C
The system shall do C.

#### Scenario: C
- Given a user
- When it does C
- Then it works
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
- S-1 -> test_happy (covers CAP-demo-FR-1)
- S-2 -> test_error (covers CAP-demo-FR-2)

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
| T-1 | S-1, CAP-demo-FR-1 | unit | happy | pytest -k happy |

## Traceability
- CAP-demo-FR-1, S-1: T-1
"""

MARKER = f"<!-- {_meta.BLOCK_PREFIX}-gate:contract_check -->"

VERIFY = f"""# Verify Record: demo

## Verdict
ready

## Spec Coverage
CAP-demo-FR-1 -> test_happy

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
        ("spec.md", SPEC, "delta"),
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
    expected = "has no requirements" if name == "spec.md" else "is empty"
    assert any(expected in m for m in _messages(report)), _messages(report)


def test_plantilla_de_capacidad_sin_completar(tmp_path: Path) -> None:
    folder = tmp_path / "specs" / "capabilities" / "demo"
    report = speclint.lint_path(_write(folder, "spec.md", speclint.template_text("capability-spec")))
    assert report.files[0].kind == "capability"
    assert "section 'Purpose' is empty" in _messages(report)


def test_spec_de_capacidad(tmp_path: Path) -> None:
    folder = tmp_path / "specs" / "capabilities" / "demo"
    report = speclint.lint_path(_write(folder, "spec.md", CAPABILITY))
    assert report.ok, _messages(report)
    assert report.files[0].kind == "capability"
    bad = CAPABILITY.replace("### CAP-demo-FR-3:", "### CAP-otra-FR-3:")
    messages = _messages(speclint.lint_path(_write(folder, "spec.md", bad)))
    assert any("belongs to capability otra" in m for m in messages)
    assert speclint.lint_path(folder).files[0].kind == "capability"


def test_tipo_forzado_delta_y_capacidad(tmp_path: Path) -> None:
    assert speclint.lint_path(_write(tmp_path, "cambio.md", SPEC), kind="delta").ok
    folder = tmp_path / "demo"
    assert speclint.lint_path(_write(folder, "cap.md", CAPABILITY), kind="capability").ok


def test_marcador_de_gate_de_la_plantilla_coincide_con_el_codigo() -> None:
    assert speclint.GATE_MARKER.match(MARKER)
    assert MARKER in speclint.template_text("verify-record")


def test_falta_encabezado_y_seccion_vacia(tmp_path: Path) -> None:
    text = PROPOSAL.replace("## Approach\nHacer B.\n", "").replace("- C\n", "<!-- nada -->\n")
    messages = _messages(speclint.lint_path(_write(tmp_path, "proposal.md", text)))
    assert "missing section '## Approach'" in messages
    assert "section 'Out of Scope' is empty" in messages


def test_encabezados_sin_distinguir_mayusculas(tmp_path: Path) -> None:
    text = PROPOSAL.replace("## Out of Scope", "## out OF scope")
    assert speclint.lint_path(_write(tmp_path, "proposal.md", text)).ok


def test_encabezados_dentro_de_bloques_de_codigo_no_cuentan(tmp_path: Path) -> None:
    text = PROPOSAL.replace("## Approach\nHacer B.\n", "```\n## Approach\n```\n")
    messages = _messages(speclint.lint_path(_write(tmp_path, "proposal.md", text)))
    assert "missing section '## Approach'" in messages


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("### CAP-demo-FR-2: Do B", "### CAP-demo-FR-1: Do B", "CAP-demo-FR-1 appears twice"),
        ("### CAP-demo-FR-2: Do B", "### FR-2: Do B", "malformed requirement ID: FR-2"),
        ("#### Scenario S-2: Error", "#### Scenario S-1: Error", "S-1 appears twice"),
        ("- Then it sees an error\n", "", "S-2 has no Then"),
        ("- Given a user\n", "", "S-1 has no Given"),
    ],
)
def test_reglas_del_delta_en_speclint(tmp_path: Path, old: str, new: str, fragment: str) -> None:
    """Las reglas del formato están en test_specs.py; acá, que speclint las reporta."""
    report = speclint.lint_path(_write(tmp_path, "spec.md", SPEC.replace(old, new)))
    assert any(fragment in m for m in _messages(report)), _messages(report)


def test_spec_con_el_formato_viejo(tmp_path: Path) -> None:
    text = "# Spec\n\n## Requirements\n- **FR-1** A.\n\n## Scenarios\n### S-1 x\n"
    messages = _messages(speclint.lint_path(_write(tmp_path, "spec.md", text)))
    assert any("unknown section '## Requirements'" in m and "ADR-0013" in m for m in messages)


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("## Verdict\nready", "## Verdict\nmaybe", "Verdict must be"),
        (MARKER, "sin marcador", "missing gate marker"),
    ],
)
def test_reglas_del_verify_record(tmp_path: Path, old: str, new: str, fragment: str) -> None:
    report = speclint.lint_path(_write(tmp_path, "verify-record.md", VERIFY.replace(old, new)))
    assert any(fragment in m for m in _messages(report)), _messages(report)


def test_errores_llevan_numero_de_linea(tmp_path: Path) -> None:
    text = SPEC.replace("### CAP-demo-FR-2: Do B", "### CAP-demo-FR-1: Do B")
    issue = speclint.lint_path(_write(tmp_path, "spec.md", text)).files[0].errors[0]
    assert issue.line == 18


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
    _write(folder, "design.md", DESIGN.replace("- S-2 -> test_error (covers CAP-demo-FR-2)\n", ""))
    assert "S-2 from spec.md does not appear in the Test Plan of design.md" in _messages(speclint.lint_path(folder))


def test_referencia_a_id_inexistente(tmp_path: Path) -> None:
    folder = _change(tmp_path)
    _write(folder, "test-spec.md", TEST_SPEC.replace("- CAP-demo-FR-1, S-1: T-1", "- CAP-demo-FR-9, S-7: T-1"))
    messages = _messages(speclint.lint_path(folder))
    assert "CAP-demo-FR-9 is not defined in spec.md nor in the living specs" in messages
    assert "S-7 is not defined in spec.md" in messages


def test_referencia_a_un_requisito_vigente_que_el_delta_no_toca(tmp_path: Path) -> None:
    folder = _change(tmp_path)
    _write(folder, "design.md", DESIGN.replace("None.\n\n## Sequence", "Keeps CAP-demo-FR-3 as is.\n\n## Sequence", 1))
    assert "CAP-demo-FR-3 is not defined in spec.md nor in the living specs" in _messages(speclint.lint_path(folder))
    _write(tmp_path / "specs" / "capabilities" / "demo", "spec.md", CAPABILITY)
    assert speclint.lint_path(folder).ok, _messages(speclint.lint_path(folder))


def test_el_id_dentro_de_un_cap_no_se_lee_como_otro(tmp_path: Path) -> None:
    """`CAP-demo-FR-12` no es una referencia a `FR-12` ni a `S-…`."""
    folder = _change(tmp_path)
    _write(folder, "design.md", DESIGN.replace("Low.", "Low. See CAP-demo-FR-1 and CAP-demo-NFR-1."))
    assert speclint.lint_path(folder).ok, _messages(speclint.lint_path(folder))


def test_carpeta_sin_artefactos(tmp_path: Path) -> None:
    (tmp_path / "vacia").mkdir()
    report = speclint.lint_path(tmp_path / "vacia")
    assert not report.ok
    assert "no SDD artifacts" in _messages(report)[0]


def test_tipo_forzado_y_tipo_desconocido(tmp_path: Path) -> None:
    path = _write(tmp_path, "notas.md", DESIGN)
    with pytest.raises(speclint.SpeclintError, match="--type"):
        speclint.lint_path(path)
    assert speclint.lint_path(path, kind="technical").ok
    with pytest.raises(speclint.SpeclintError, match="type"):
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
    assert "does not exist" in capsys.readouterr().err
    path = _write(tmp_path, "notas.md", DESIGN)
    assert main(["speclint", str(path)]) == 1
    assert main(["speclint", str(path), "--type", "technical"]) == 0


def test_ids_dentro_de_codigo_no_cuentan(tmp_path: Path) -> None:
    text = SPEC.replace(
        "## MODIFIED Requirements",
        "```\n### CAP-demo-FR-1: inside code\n```\n\n## MODIFIED Requirements",
    )
    assert speclint.lint_path(_write(tmp_path, "spec.md", text)).ok
