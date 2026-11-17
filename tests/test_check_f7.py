"""Canvas SPDD y gates condicionales (F7, ADR-0016, D-43).

- `canvas.md` es un artefacto del change con las siete dimensiones REASONS; speclint lo
  lintea y sus referencias a IDs tienen que existir.
- `exo check` revisa todo gate presente, aunque el tier no lo exija, y con `canvas.md`
  exige `prompt_spec_review`.
"""

from __future__ import annotations

from pathlib import Path

from exo.sdd import check, speclint
from test_check_f5 import COMPLETE, MEDIUM, _change, _errors, _warnings, gate

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
