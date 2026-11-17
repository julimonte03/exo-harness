"""Canvas SPDD y gates condicionales (F7, ADR-0016, D-43).

- `canvas.md` es un artefacto del change con las siete dimensiones REASONS; speclint lo
  lintea y sus referencias a IDs tienen que existir.
- `exo check` revisa todo gate presente, aunque el tier no lo exija, y con `canvas.md`
  exige `prompt_spec_review`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from exo.cli import main
from exo.sdd import check, speclint
from test_check_f5 import COMPLETE, LOW, MEDIUM, _change, _errors, _warnings, gate
from test_speclint import CAPABILITY, PROPOSAL

CANVAS = """# Canvas: demo

## Requirements
CAP-demo-FR-1 and its scenario S-1: do A for a user.

## Entities
User, with an id and a name.

## Approach
Extend the existing handler; no new service.

## Structure
src/app/handler.py gains one function.

## Operations
1. Read the user. 2. Do A. 3. Return B.

## Norms
Type hints everywhere; errors as exceptions, never None.

## Safeguards
Never log the user's name; reject an empty id.
"""

DIMENSIONS = (
    "Requirements",
    "Entities",
    "Approach",
    "Structure",
    "Operations",
    "Norms",
    "Safeguards",
)


def test_la_plantilla_del_canvas_tiene_las_siete_dimensiones() -> None:
    text = speclint.template_text("canvas")
    assert [line[3:] for line in text.splitlines() if line.startswith("## ")] == list(DIMENSIONS)


def test_el_canvas_lleno_pasa_y_la_plantilla_vacia_no(tmp_path: Path) -> None:
    path = tmp_path / "canvas.md"
    path.write_text(CANVAS, encoding="utf-8")
    report = speclint.lint_path(path)
    assert report.ok, [i.message for f in report.files for i in f.errors]
    assert report.files[0].kind == "canvas"
    path.write_text(speclint.template_text("canvas"), encoding="utf-8")
    messages = [i.message for f in speclint.lint_path(path).files for i in f.errors]
    assert "section 'Safeguards' is empty" in messages


def test_el_canvas_de_la_carpeta_se_lintea_y_cruza_ids(tmp_path: Path) -> None:
    folder = _change(tmp_path, "medio", MEDIUM, {**COMPLETE, "canvas.md": CANVAS})
    assert speclint.lint_path(folder).ok
    (folder / "canvas.md").write_text(CANVAS.replace("S-1", "S-9"), encoding="utf-8")
    messages = [i.message for f in speclint.lint_path(folder).files for i in f.errors]
    assert "S-9 is not defined in spec.md" in messages


def test_con_canvas_check_exige_prompt_spec_review(tmp_path: Path) -> None:
    folder = _change(tmp_path, "medio", MEDIUM, {**COMPLETE, "canvas.md": CANVAS})
    result = check.check(tmp_path)
    assert not result.ok
    assert any("canvas.md requires the gate prompt_spec_review" in m for m in _errors(result)), (
        _errors(result)
    )
    (folder / "gates" / "prompt_spec_review.md").write_text(
        gate("prompt_spec_review"), encoding="utf-8"
    )
    result = check.check(tmp_path)
    assert result.ok, _errors(result)


def test_con_canvas_el_gate_se_pide_recien_despues_del_verify(tmp_path: Path) -> None:
    files = {k: v for k, v in COMPLETE.items() if k not in ("verify-record.md",)}
    _change(tmp_path, "medio", MEDIUM, {**files, "canvas.md": CANVAS})
    assert not any("prompt_spec_review" in m for m in _errors(check.check(tmp_path)))


def test_un_gate_condicional_escalado_pide_tech_lead(tmp_path: Path) -> None:
    files = {
        **COMPLETE,
        "gates/accessibility_review.md": gate("accessibility_review", "ESCALATED", "yes"),
    }
    _change(tmp_path, "medio", MEDIUM, files)
    result = check.check(tmp_path)
    assert result.ok, _errors(result)
    assert any("accessibility_review" in w and "tech_lead" in w for w in _warnings(result))


def test_un_gate_condicional_aprobado_no_avisa(tmp_path: Path) -> None:
    files = {**COMPLETE, "gates/accessibility_review.md": gate("accessibility_review")}
    _change(tmp_path, "medio", MEDIUM, files)
    result = check.check(tmp_path)
    assert result.ok, _errors(result)
    assert not any("accessibility_review" in w for w in _warnings(result))


def test_un_gate_condicional_sin_veredicto_es_error(tmp_path: Path) -> None:
    broken = gate("accessibility_review").replace("APPROVED: no blocking finding.", "")
    _change(tmp_path, "medio", MEDIUM, {**COMPLETE, "gates/accessibility_review.md": broken})
    result = check.check(tmp_path)
    assert not result.ok
    assert any("Verdict" in m for m in _errors(result)), _errors(result)


# -- F7R1-6: un gate que no es UTF-8 no aborta `exo check` ----------------------------------


def _error_findings(result: check.CheckResult) -> list[check.Finding]:
    return [f for c in result.changes for f in c.findings if f.severity == "error"]


@pytest.mark.parametrize(
    "rel",
    [
        "gates/accessibility_review.md",  # presente sin que el tier lo exija
        "gates/code_review.md",  # exigido por el tier
        "verify-record.md",
    ],
)
def test_un_artefacto_en_utf16_es_un_error_con_su_ruta(tmp_path: Path, rel: str) -> None:
    """Lo que escribe `Out-File` de Windows PowerShell 5.1: antes abortaba todo `exo check`
    con un `UnicodeDecodeError` sin nombrar el archivo."""
    files = {**COMPLETE, "gates/accessibility_review.md": gate("accessibility_review")}
    folder = _change(tmp_path, "medio", MEDIUM, files)
    other = _change(tmp_path, "otro", MEDIUM, {**COMPLETE, "verify-record.md": "roto"})
    path = folder / rel
    path.write_bytes(path.read_text(encoding="utf-8").encode("utf-16"))
    result = check.check(tmp_path)
    assert not result.ok
    found = [f for f in _error_findings(result) if f.path.startswith(folder.relative_to(tmp_path).as_posix())]
    assert any(rel in f.path + f.message and "UTF-8" in f.message for f in found), found
    assert {c.name for c in result.changes} == {folder.name, other.name}  # el otro también


def test_el_cli_no_aborta_con_un_gate_en_utf16(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _change(tmp_path, "medio", MEDIUM, COMPLETE)
    gate_path = folder / "gates" / "code_review.md"
    gate_path.write_bytes(gate("code_review").encode("utf-16"))
    assert main(["check", "--project", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "gates/code_review.md" in out and "UTF-8" in out


# -- F7R1-14: sin spec.md, el canvas igual se cruza con las specs vivas ----------------------


def test_sin_spec_md_los_ids_del_canvas_se_cruzan_con_las_specs_vivas(tmp_path: Path) -> None:
    """Tier 1 con el overlay SPDD: sin delta, el canvas solo puede nombrar requisitos vigentes."""
    canvas = CANVAS.replace("CAP-demo-FR-1 and its scenario S-1", "CAP-demo-FR-9")
    folder = _change(tmp_path, "chico", LOW, {"proposal.md": PROPOSAL, "canvas.md": canvas})
    messages = [i.message for f in speclint.lint_path(folder).files for i in f.errors]
    assert "CAP-demo-FR-9 is not defined in spec.md nor in the living specs" in messages
    capability = tmp_path / "specs" / "capabilities" / "demo" / "spec.md"
    capability.parent.mkdir(parents=True)
    capability.write_text(CAPABILITY, encoding="utf-8")
    (folder / "canvas.md").write_text(canvas.replace("FR-9", "FR-3"), encoding="utf-8")
    report = speclint.lint_path(folder)
    assert report.ok, [i.message for f in report.files for i in f.errors]
    (folder / "canvas.md").write_text(canvas.replace("FR-9", "FR-3, S-1"), encoding="utf-8")
    messages = [i.message for f in speclint.lint_path(folder).files for i in f.errors]
    assert any(m.startswith("S-1 is not defined in spec.md") for m in messages), messages
