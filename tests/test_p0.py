"""`exo p0` (D-32) y `exo codeowners` (F5)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from exo.cli import main
from exo.core import config
from exo.governance import p0
from exo.installer import project

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")


def _repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    return path


def test_el_dataset_del_escaner_pasa() -> None:
    result = p0.scanner_regression()
    assert result.ok, result.detail
    assert result.cases >= 20


def test_la_validacion_de_entradas_pasa() -> None:
    result = p0.input_regression()
    assert result.ok, result.detail


@needs_git
def test_criterio_6_p0_pasa_con_los_hooks_activos(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path / "app")
    project.sync(root, agents=["generic"])
    assert main(["p0", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    assert "P0 GATE: PASSED (3/3)" in out


@needs_git
def test_p0_falla_sin_hooks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _repo(tmp_path / "app")
    project.sync(root, agents=["generic"])
    subprocess.run(["git", "-C", str(root), "config", "--unset", "core.hooksPath"], check=True)
    assert main(["p0", "--project", str(root), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] == 2 and payload["total"] == 3
    assert [c["ok"] for c in payload["checks"]] == [True, True, False]


def test_p0_fuera_de_un_proyecto(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["p0", "--project", str(tmp_path)]) == 1
    assert "P0 GATE: FAILED (2/3)" in capsys.readouterr().out


def test_codeowners(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["codeowners", "--project", str(tmp_path)]) == 1
    assert "tech_lead" in capsys.readouterr().err
    cfg = config.defaults()
    cfg["governance"]["roles"]["tech_lead"] = ["@ana", "bob@example.com"]
    cfg["specs_dir"] = "docs/specs"
    config.save(tmp_path, cfg)
    assert main(["codeowners", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "/docs/specs/ @ana bob@example.com" in out
    assert "/.exo/ @ana bob@example.com" in out
    assert out.lstrip().startswith("#")
