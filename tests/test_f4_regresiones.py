"""Regresiones de la revisión con contexto fresco de F4: un test por hallazgo."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pytest

from exo.cli import main
from exo.sdd import changes, check, fitness, observability, record, speclint, specs
from test_speclint import CAPABILITY, DESIGN, PROPOSAL, SPEC, TEST_SPEC
from test_specs import AUTH, DELTA, MergeError, _project

LOW = {dimension: 0 for dimension in fitness.DIMENSIONS}
NOW = datetime(2026, 11, 14, 10, 0, 0, tzinfo=timezone.utc)


def _write(path: Path, data: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


def _repo(project: Path) -> None:
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.email", "test@example.com")
    _git(project, "config", "user.name", "Test")


# -- A1: una épica que queda vacía no es un change ------------------------------------


def test_a1_la_carpeta_vacia_de_una_epica_archivada_no_es_un_change(tmp_path: Path) -> None:
    changes.new_change(tmp_path, "x", now=NOW)
    changes.record_assessment(tmp_path, "x", LOW, now=NOW)
    (tmp_path / "specs" / "x" / "proposal.md").write_text(PROPOSAL, encoding="utf-8")
    epic = tmp_path / "specs" / "PROJ-7"
    (epic / "PROJ-12-y").mkdir(parents=True)
    (epic / "PROJ-12-y").rmdir()  # git mv deja la carpeta de la épica vacía
    assert [c.name for c in observability.find_changes(tmp_path)] == ["x"]
    assert check.check(tmp_path).ok


# -- A2: el JSON de PowerShell 5.1 viene en UTF-16 o en ANSI ----------------------------


def test_a2_evidencia_en_utf16_y_en_ansi(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = str(tmp_path)
    assert main(["change", "new", "x", "--project", project]) == 0
    utf16 = _write(tmp_path / "e16.json", json.dumps(LOW).encode("utf-16"))
    capsys.readouterr()
    assert main(["fitness", "classify", "--evidence-file", str(utf16), "--change", "x", "--project", project, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tier"] == 1
    entry = {"name": "sdd-new", "type": "skill", "activation": "requested", "note": "café"}
    _write(tmp_path / "entry16.json", json.dumps(entry, ensure_ascii=False).encode("utf-16"))
    assert main(["change", "record", "x", "--add", "capabilities_used", f"@{tmp_path / 'entry16.json'}", "--project", project]) == 0
    _write(tmp_path / "ansi.json", json.dumps(entry, ensure_ascii=False).encode("cp1252"))
    capsys.readouterr()
    assert main(["change", "record", "x", "--add", "decisions", f"@{tmp_path / 'ansi.json'}", "--project", project]) == 2
    assert "UTF-8" in capsys.readouterr().err
    assert main(["fitness", "classify", "--evidence-file", str(tmp_path / "ansi.json"), "--change", "x", "--project", project]) == 2


# -- A3: evidencia mal formada no se registra ---------------------------------------------


@pytest.mark.parametrize(
    "evidence",
    [{**LOW, "blast": 1}, {**LOW, "blast_radius": "2"}, {**LOW, "reversibility": 7}, ["no", "es", "objeto"]],
)
def test_a3_evidencia_mal_formada_no_se_registra(tmp_path: Path, evidence: object) -> None:
    changes.new_change(tmp_path, "x", now=NOW)
    with pytest.raises(changes.ChangeError, match="nothing was recorded"):
        changes.record_assessment(tmp_path, "x", evidence, now=NOW)
    assert not (tmp_path / "specs" / "x" / changes.ASSESSMENT).exists()


def test_a3_evidencia_incompleta_si_se_registra_como_tier_4(tmp_path: Path) -> None:
    changes.new_change(tmp_path, "x", now=NOW)
    assert changes.record_assessment(tmp_path, "x", {"blast_radius": 0}, now=NOW).tier == 4


def test_a3_json_roto_por_cli_sale_con_2_sin_registrar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = str(tmp_path)
    assert main(["change", "new", "x", "--project", project]) == 0
    assert main(["fitness", "classify", "--evidence-json", "{blast_radius: 0}", "--change", "x", "--project", project]) == 2
    assert "not valid JSON" in capsys.readouterr().err
    assert not (tmp_path / "specs" / "x" / changes.ASSESSMENT).exists()
    assert main(["fitness", "classify", "--evidence-json", json.dumps(LOW), "--change", "x", "--project", project]) == 0


# -- A4: borrar el último requisito deja una capacidad válida ---------------------------------


def test_a4_borrar_el_ultimo_requisito(tmp_path: Path) -> None:
    one = AUTH.split("### CAP-auth-FR-2:")[0].rstrip("\n") + "\n"
    delta = "# Spec: demo\n\n## REMOVED Requirements\n\n### CAP-auth-FR-1: Sign in with password\nReason: replaced.\n"
    project = _project(tmp_path, delta, auth=one)
    specs.merge(project, "demo")
    path = project / "specs" / "capabilities" / "auth" / "spec.md"
    report = speclint.lint_path(path)
    assert report.ok, [i.message for f in report.files for i in f.errors]


# -- A5: dos secciones Requirements fallan limpio --------------------------------------------


def test_a5_secciones_repetidas_son_un_problema_y_no_un_crash(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doubled = AUTH.replace("## Notes\n", "## Requirements\n\n### CAP-auth-FR-5: Other\nText.\n\n#### Scenario: x\n- Given a\n- When b\n- Then c\n\n## Notes\n")
    assert any("appears twice" in p.message for p in specs.parse_capability(doubled, "auth").problems)
    delta = DELTA.replace("### CAP-auth-FR-1:", "### CAP-auth-FR-5:")
    project = _project(tmp_path, delta, auth=doubled)
    with pytest.raises(MergeError):
        specs.merge(project, "demo")
    assert main(["specs", "merge", "demo", "--project", str(project)]) == 1


# -- A6: un archivo con fines de línea mezclados conserva los que no se tocan -------------------


def test_a6_fines_de_linea_mezclados(tmp_path: Path) -> None:
    lines = AUTH.split("\n")
    mixed = "\r\n".join(lines[:3]) + "\r\n" + "\n".join(lines[3:])  # 3 líneas CRLF, el resto LF
    project = _project(tmp_path, auth=None)
    path = _write(project / "specs" / "capabilities" / "auth" / "spec.md", mixed)
    specs.merge(project, "demo")
    raw = path.read_bytes()
    assert raw.startswith(b"# Capability: auth\r\n\r\n## Purpose\r\n")
    assert b"Free text   that the merge keeps byte for byte.\n" in raw
    assert raw.count(b"\r\n") == 3


# -- A7: un delta con BOM pasa speclint ----------------------------------------------------------


def test_a7_bom(tmp_path: Path) -> None:
    folder = tmp_path / "specs" / "demo"
    _write(folder / "spec.md", "﻿" + SPEC.split("\n", 2)[2])
    _write(folder / "design.md", "﻿" + DESIGN)
    _write(folder / "test-spec.md", TEST_SPEC)
    report = speclint.lint_path(folder)
    assert report.ok, [i.message for f in report.files for i in f.errors]


# -- A8 y C1: --base compara contra la base de la rama, con commits ---------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
def test_a8_base_usa_el_merge_base_y_ve_lo_commiteado(tmp_path: Path) -> None:
    _repo(tmp_path)
    _write(tmp_path / "specs" / "capabilities" / "demo" / "spec.md", CAPABILITY)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feat/x")
    changes.new_change(tmp_path, "x", now=NOW)
    changes.record_assessment(tmp_path, "x", LOW, now=NOW)
    _write(tmp_path / "specs" / "x" / "proposal.md", PROPOSAL)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "change x")
    _git(tmp_path, "checkout", "-q", "main")
    _write(tmp_path / "specs" / "capabilities" / "demo" / "spec.md", CAPABILITY + "\n<!-- moved on -->\n")
    _git(tmp_path, "commit", "-q", "-am", "main moves on")
    _git(tmp_path, "checkout", "-q", "feat/x")
    result = check.check(tmp_path, base="main")
    assert [c.name for c in result.changes] == ["x"]
    assert result.capabilities == []  # la capacidad cambió en main, no en la rama
    assert result.ok


# -- A9 ---------------------------------------------------------------------------------------------


def test_a9_capacidad_que_no_es_utf8_nombra_el_archivo(tmp_path: Path) -> None:
    project = _project(tmp_path, auth=None)
    _write(project / "specs" / "capabilities" / "auth" / "spec.md", AUTH.replace("Who", "Quién").encode("cp1252"))
    with pytest.raises(MergeError) as info:
        specs.merge(project, "demo")
    assert any("capabilities/auth/spec.md" in p and "UTF-8" in p for p in info.value.problems)


def test_a9_el_registro_no_se_escribe_a_traves_de_un_link(
    tmp_path: Path, make_dir_link: Callable[[Path, Path], None]
) -> None:
    outside = tmp_path / "afuera"
    outside.mkdir()
    (outside / record.FILENAME).write_text(json.dumps({"change_name": "linked"}), encoding="utf-8")
    project = tmp_path / "p"
    (project / "specs").mkdir(parents=True)
    make_dir_link(project / "specs" / "linked", outside)
    with pytest.raises(changes.ChangeError, match="link"):
        changes.update_record(project, "linked", add=[("skills_used", "x")])
    with pytest.raises(changes.ChangeError, match="link"):
        changes.record_assessment(project, "linked", LOW)
    assert json.loads((outside / record.FILENAME).read_text(encoding="utf-8")) == {"change_name": "linked"}


@pytest.mark.parametrize(
    "argv",
    [
        ["check", "--base=-x"],
        ["change", "record", "x", "--add", "inventado", "1"],
        ["change", "record", "x", "--set", "change_name", '"y"'],
        ["init", "--agents", "generic", "--yes", "--ticket-pattern", "\\d*"],
        ["init", "--agents", "generic", "--yes", "--ticket-pattern", "#\\d+", "--ticket-example", "PROJ-1"],
    ],
)
def test_a9_errores_de_uso_salen_con_2(tmp_path: Path, argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    changes.new_change(tmp_path, "x", now=NOW)
    assert main([*argv, "--project", str(tmp_path)]) == 2
    assert capsys.readouterr().err.startswith("usage error:")


# -- B1/B2: registro de fases y fase siguiente calculada ----------------------------------------------


def _phase(project: Path, name: str = "x") -> tuple[str, str]:
    state = observability.change_state(project, name)
    return state["next_phase"], state["next_reason"]


def test_b1_fase_siguiente_en_tier_1_y_rework(tmp_path: Path) -> None:
    changes.new_change(tmp_path, "x", now=NOW)
    assert _phase(tmp_path)[0] == "risk"
    changes.record_assessment(tmp_path, "x", LOW, now=NOW)
    assert _phase(tmp_path)[0] == "new"
    _write(tmp_path / "specs" / "x" / "proposal.md", PROPOSAL)
    changes.update_record(tmp_path, "x", phase_done="new")
    assert _phase(tmp_path)[0] == "apply"
    changes.update_record(tmp_path, "x", phase_done="apply")
    assert _phase(tmp_path)[0] == "verify"
    verify = tmp_path / "specs" / "x" / "verify-record.md"
    _write(verify, "# Verify\n\n## Verdict\nneeds-rework: S-1 fails\n")
    changes.update_record(tmp_path, "x", phase_done="verify")
    assert _phase(tmp_path) == ("apply", "the verify said needs-rework: fix what Issues Found lists")
    changes.update_record(tmp_path, "x", phase_done="apply")
    assert _phase(tmp_path)[0] == "verify"
    _write(verify, "# Verify\n\n## Verdict\nready\n")
    changes.update_record(tmp_path, "x", phase_done="verify")
    assert _phase(tmp_path)[0] == "archive"


def test_b1_fase_siguiente_en_tier_3_y_4(tmp_path: Path) -> None:
    changes.new_change(tmp_path, "x", now=NOW)
    changes.record_assessment(tmp_path, "x", {**LOW, "blast_radius": 3}, now=NOW)
    folder = tmp_path / "specs" / "x"
    _write(folder / "proposal.md", PROPOSAL.replace("Hacer B.", "The area is unknown: explore before proposing."))
    assert _phase(tmp_path)[0] == "explore"
    _write(folder / "exploration.md", "# Exploration\n")
    assert _phase(tmp_path)[0] == "propose"
    changes.update_record(tmp_path, "x", phase_done="propose")
    assert _phase(tmp_path)[0] == "spec"
    _write(folder / "spec.md", SPEC)
    assert _phase(tmp_path)[0] == "design"
    _write(folder / "design.md", DESIGN)
    assert _phase(tmp_path)[0] == "tasks"
    _write(folder / "tasks.md", "- [x] 1. a\n- [ ] 2. b\n")
    _write(folder / "test-spec.md", TEST_SPEC)
    assert _phase(tmp_path)[0] == "apply"
    _write(folder / "tasks.md", "- [x] 1. a\n- [x] 2. b\n")
    assert _phase(tmp_path)[0] == "verify"
    _write(folder / "verify-record.md", "# Verify\n\n## Verdict\nready\n")
    assert _phase(tmp_path)[0] == "archive"
    changes.record_assessment(tmp_path, "x", {**LOW, "reversibility": 3}, now=NOW)  # Tier 4
    assert _phase(tmp_path)[0] == "judgment"
    changes.update_record(tmp_path, "x", add=[("judges_invoked", {"name": "judgment-day", "result": "approved"})])
    assert _phase(tmp_path)[0] == "archive"


def test_b2_phase_done_es_un_registro_ordenado_e_idempotente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    changes.new_change(tmp_path, "x", now=NOW)
    assert changes.update_record(tmp_path, "x", phase_done="apply", now=NOW).changed is True
    assert changes.update_record(tmp_path, "x", phase_done="apply", now=NOW).changed is False
    changes.update_record(tmp_path, "x", phase_done="verify", now=NOW)
    changes.update_record(tmp_path, "x", phase_done="apply", now=NOW)
    data = json.loads((tmp_path / "specs" / "x" / record.FILENAME).read_text(encoding="utf-8"))
    assert [p["phase"] for p in data["phases_done"]] == ["apply", "verify", "apply"]
    assert record.validate(data) == []
    assert main(["change", "record", "x", "--phase-done", "spec", "--project", str(tmp_path)]) == 0
    assert main(["change", "record", "x", "--phase-done", "inventada", "--project", str(tmp_path)]) == 2


# -- B6: sin tickets sin un argumento vacío --------------------------------------------------------------


def test_b6_no_tickets(tmp_path: Path) -> None:
    from exo.core import config

    assert main(["init", "--project", str(tmp_path), "--agents", "generic", "--yes", "--ticket-pattern", "#\\d+"]) == 0
    assert main(["init", "--project", str(tmp_path), "--agents", "generic", "--yes", "--no-tickets"]) == 0
    assert config.load(tmp_path).config["tickets"] == {"pattern": None, "example": None}
    assert main(["init", "--project", str(tmp_path), "--yes", "--no-tickets", "--ticket-pattern", "#\\d+"]) == 2


# -- B7: un ID con lápida se puede citar -------------------------------------------------------------------


def test_b7_citar_un_requisito_borrado(tmp_path: Path) -> None:
    folder = tmp_path / "specs" / "demo"
    tomb = CAPABILITY + "\n## Removed Requirements\n\n### CAP-demo-FR-7: Old\nRemoved by change `old`.\n"
    _write(tmp_path / "specs" / "capabilities" / "demo" / "spec.md", tomb)
    for name, text in (("spec.md", SPEC), ("design.md", DESIGN.replace("Low.", "Low. CAP-demo-FR-7 was removed before.")), ("test-spec.md", TEST_SPEC)):
        _write(folder / name, text)
    report = speclint.lint_path(folder)
    assert report.ok, [i.message for f in report.files for i in f.errors]
