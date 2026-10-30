"""doctor: diagnóstico del entorno, del contenido y de la config del proyecto."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from exo import _meta, content, doctor
from exo.cli import main


def _by_name(checks: list[doctor.Check]) -> dict[str, doctor.Check]:
    return {c.name: c for c in checks}


def test_todo_ok_en_el_entorno_de_desarrollo(tmp_path: Path) -> None:
    checks = _by_name(doctor.run_checks(tmp_path))
    for name in ("python", "version", "content", "filemerge", "snapshots", "disk", "config"):
        assert checks[name].status in ("ok", "info"), (name, checks[name])
    assert checks["version"].detail == f"{_meta.NAME} {_meta.VERSION}"
    assert "packs" in checks["content"].detail
    assert checks["config"].status == "info"


def test_config_con_advertencias(tmp_path: Path) -> None:
    path = tmp_path / _meta.PROJECT_DIR / "config.json"
    path.parent.mkdir()
    path.write_text('{"schema": 1, "specs_dir": "../fuera"}', encoding="utf-8")
    check = _by_name(doctor.run_checks(tmp_path))["config"]
    assert check.status == "warn"
    assert "specs_dir" in check.detail


def test_python_viejo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor.sys, "version_info", (3, 9, 18))
    assert _by_name(doctor.run_checks(tmp_path))["python"].status == "error"


def test_ejecutable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    assert _by_name(doctor.run_checks(tmp_path))["path"].status == "warn"
    other = tmp_path / "otro" / _meta.NAME
    monkeypatch.setattr(doctor.shutil, "which", lambda name: str(other))
    check = _by_name(doctor.run_checks(tmp_path))["path"]
    assert check.status == "warn"
    assert "no es este motor" in check.detail


def test_contenido_ausente(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(content.ENV_VAR, str(tmp_path / "nada"))
    assert _by_name(doctor.run_checks(tmp_path))["content"].status == "error"


def test_disco_lleno(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(doctor.shutil, "disk_usage", lambda path: usage._replace(free=10))
    assert _by_name(doctor.run_checks(tmp_path))["disk"].status == "warn"


def test_autotest_que_falla_se_reporta(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def broken(*args: object, **kwargs: object) -> bytes:
        raise OSError("sin permisos")

    monkeypatch.setattr(doctor.snapshots, "build_archive", broken)
    check = _by_name(doctor.run_checks(tmp_path))["snapshots"]
    assert check.status == "error"
    assert "sin permisos" in check.detail


def test_encoding_no_utf8(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Stream:
        encoding = "cp1252"

    monkeypatch.setattr(doctor.sys, "stdout", Stream())
    check = _by_name(doctor.run_checks(tmp_path))["encoding"]
    assert check.status == "warn"


def test_cli_doctor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "python" in out
    assert "content" in out
    assert main(["doctor", "--project", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert {c["name"] for c in payload["checks"]} >= {"python", "content", "snapshots"}


def test_cli_doctor_con_errores(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv(content.ENV_VAR, str(tmp_path / "nada"))
    assert main(["doctor", "--project", str(tmp_path)]) == 1
    assert "error" in capsys.readouterr().out
