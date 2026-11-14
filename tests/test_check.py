"""sdd/check: `exo check` v1 (speclint, AI Usage Record y artefactos por tier, D-27)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from exo.cli import main
from exo.core import config
from exo.sdd import changes, check, fitness, record
from test_speclint import CAPABILITY, DESIGN, PROPOSAL, SPEC, TEST_SPEC

LOW = {dimension: 0 for dimension in fitness.DIMENSIONS}
MEDIUM = {**LOW, "blast_radius": 2}  # FM-20: Tier 2
HIGH = {**LOW, "blast_radius": 3}  # FM-11: Tier 3
TASKS = "# Tasks: demo\n\n- [ ] 1. Do A\n"


def _change(project: Path, slug: str, evidence: dict | None, files: dict[str, str]) -> Path:
    created = changes.new_change(project, slug)
    if evidence is not None:
        changes.record_assessment(project, slug, evidence)
    folder = project / created.path
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    return folder


def _findings(result: check.CheckResult, severity: str = "error") -> list[str]:
    return [f.message for c in result.changes for f in c.findings if f.severity == severity] + [
        f.message for _, findings in result.capabilities for f in findings if f.severity == severity
    ]


def test_tier_1_con_proposal_alcanza_y_avisa_sin_delta(tmp_path: Path) -> None:
    _change(tmp_path, "fix-typo", LOW, {"proposal.md": PROPOSAL})
    result = check.check(tmp_path)
    assert result.ok, _findings(result)
    [item] = result.changes
    assert (item.name, item.tier, item.tier_source) == ("fix-typo", 1, "assessment")
    assert any("must not alter behavior" in m for m in _findings(result, "warning"))


def test_tier_2_exige_spec_y_test_spec(tmp_path: Path) -> None:
    _change(tmp_path, "medio", MEDIUM, {"proposal.md": PROPOSAL})
    messages = _findings(check.check(tmp_path))
    assert "Tier 2 requires spec.md" in messages
    assert "Tier 2 requires test-spec.md" in messages
    assert not any("design.md" in m for m in messages)


def test_tier_3_completo_pasa(tmp_path: Path) -> None:
    files = {"proposal.md": PROPOSAL, "spec.md": SPEC, "design.md": DESIGN, "test-spec.md": TEST_SPEC, "tasks.md": TASKS}
    (tmp_path / "specs" / "capabilities" / "demo").mkdir(parents=True)
    (tmp_path / "specs" / "capabilities" / "demo" / "spec.md").write_text(CAPABILITY, encoding="utf-8")
    _change(tmp_path, "grande", HIGH, files)
    result = check.check(tmp_path)
    assert result.ok, _findings(result)
    assert result.changes[0].tier == 3


def test_tier_3_incompleto(tmp_path: Path) -> None:
    _change(tmp_path, "grande", HIGH, {"proposal.md": PROPOSAL, "spec.md": SPEC})
    messages = _findings(check.check(tmp_path))
    for name in ("design.md", "tasks.md", "test-spec.md"):
        assert f"Tier 3 requires {name}" in messages


def test_sin_clasificacion_es_error_y_aplica_tier_4(tmp_path: Path) -> None:
    _change(tmp_path, "sin-tier", None, {"proposal.md": PROPOSAL})
    result = check.check(tmp_path)
    assert not result.ok
    item = result.changes[0]
    assert (item.tier, item.tier_source) == (4, "missing")
    messages = _findings(result)
    assert any("no fitness-assessment.json" in m and "Tier 4" in m for m in messages)
    assert "Tier 4 requires design.md" in messages


def test_clasificacion_ilegible(tmp_path: Path) -> None:
    folder = _change(tmp_path, "roto", LOW, {"proposal.md": PROPOSAL})
    (folder / changes.ASSESSMENT).write_text("{ roto", encoding="utf-8")
    item = check.check(tmp_path).changes[0]
    assert (item.tier, item.tier_source) == (4, "unreadable")


def test_registro_faltante_o_invalido(tmp_path: Path) -> None:
    folder = _change(tmp_path, "a", LOW, {"proposal.md": PROPOSAL})
    data = json.loads((folder / record.FILENAME).read_text(encoding="utf-8"))
    data["capabilities_used"] = []
    data["change_name"] = "otro"
    (folder / record.FILENAME).write_text(json.dumps(data), encoding="utf-8")
    messages = _findings(check.check(tmp_path))
    assert any("capabilities_used: must have at least 1 item" in m for m in messages)
    assert any("change_name is otro" in m for m in messages)
    (folder / record.FILENAME).unlink()
    assert any("no ai-usage-record.json" in m for m in _findings(check.check(tmp_path)))
    (folder / record.FILENAME).write_text("{ roto", encoding="utf-8")
    assert any("not valid JSON" in m for m in _findings(check.check(tmp_path)))


def test_errores_de_speclint_con_ruta_y_linea(tmp_path: Path) -> None:
    _change(tmp_path, "a", LOW, {"proposal.md": PROPOSAL.replace("## Scope\n- A\n", "")})
    result = check.check(tmp_path)
    finding = next(f for f in result.changes[0].findings if "Scope" in f.message)
    assert finding.path == "specs/a/proposal.md"
    assert finding.severity == "error"


def test_capacidad_invalida(tmp_path: Path) -> None:
    folder = tmp_path / "specs" / "capabilities" / "demo"
    folder.mkdir(parents=True)
    (folder / "spec.md").write_text(CAPABILITY.replace("CAP-demo-FR-3", "CAP-otra-FR-3"), encoding="utf-8")
    result = check.check(tmp_path)
    assert not result.ok
    [(path, _)] = result.capabilities
    assert path == "specs/capabilities/demo/spec.md"


def test_seleccion_por_nombre(tmp_path: Path) -> None:
    _change(tmp_path, "a", LOW, {"proposal.md": PROPOSAL})
    _change(tmp_path, "b", None, {})
    result = check.check(tmp_path, names=["a"])
    assert [c.name for c in result.changes] == ["a"]
    assert result.ok
    with pytest.raises(check.CheckError, match="no-existe"):
        check.check(tmp_path, names=["no-existe"])


def test_archivados_no_se_revisan(tmp_path: Path) -> None:
    viejo = tmp_path / "specs" / "archive" / "2026-01-01-viejo"
    viejo.mkdir(parents=True)
    (viejo / "proposal.md").write_text("roto\n", encoding="utf-8")
    assert check.check(tmp_path).changes == []


@pytest.mark.parametrize("mode", ["memory", "none"])
def test_persistencia_sin_disco(tmp_path: Path, mode: str) -> None:
    cfg = config.defaults()
    cfg["sdd"]["persistence"] = mode
    config.save(tmp_path, cfg)
    result = check.check(tmp_path)
    assert result.ok and result.changes == []
    assert any(mode in note for note in result.notes)


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
def test_base_revisa_solo_lo_tocado_en_el_diff(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _change(tmp_path, "viejo", None, {})  # ya commiteado: no se revisa
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _change(tmp_path, "nuevo", LOW, {"proposal.md": PROPOSAL})  # sin trackear
    result = check.check(tmp_path, base="HEAD")
    assert [c.name for c in result.changes] == ["nuevo"]
    assert result.ok
    with pytest.raises(check.CheckError, match="git"):
        check.check(tmp_path, base="no-existe-esta-ref")
    with pytest.raises(check.CheckError, match="invalid"):
        check.check(tmp_path, base="--output=x")


def test_base_sin_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "no-hay-repo"))
    with pytest.raises(check.CheckError, match="git"):
        check.check(tmp_path, base="HEAD")


# -- CLI ---------------------------------------------------------------------------------


def test_cli_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _change(tmp_path, "a", LOW, {"proposal.md": PROPOSAL})
    assert main(["check", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "PASS a (Tier 1)" in out and "warning:" in out
    _change(tmp_path, "b", HIGH, {"proposal.md": PROPOSAL})
    assert main(["check", "--project", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL b (Tier 3)" in out and "Tier 3 requires design.md" in out
    assert main(["check", "--project", str(tmp_path), "--change", "a", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["changes"][0]["tier"] == 1
    assert main(["check", "--project", str(tmp_path), "--change", "zz"]) == 1
    assert "zz" in capsys.readouterr().err
