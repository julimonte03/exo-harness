"""`exo --version` y `python -m exo --version` responden con la misma versión (F0, criterio 1)."""

from __future__ import annotations

import runpy
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

from exo import _meta

EXPECTED = f"{_meta.NAME} {_meta.VERSION}"


def test_version_en_proceso(capsys: pytest.CaptureFixture[str]) -> None:
    from exo.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == EXPECTED


def test_sin_argumentos_muestra_ayuda(capsys: pytest.CaptureFixture[str]) -> None:
    from exo.cli import main

    assert main([]) == 0
    assert f"usage: {_meta.NAME}" in capsys.readouterr().out


def test_modulo_main_en_proceso(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["exo", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("exo", run_name="__main__", alter_sys=True)
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == EXPECTED


def test_python_m_exo_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "exo", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == EXPECTED


def _console_script() -> Path | None:
    scripts = Path(sysconfig.get_path("scripts"))
    for name in (_meta.NAME, f"{_meta.NAME}.exe"):
        candidate = scripts / name
        if candidate.is_file():
            return candidate
    return None


def test_console_script_coincide_con_python_m() -> None:
    script = _console_script()
    if script is None:
        pytest.skip("el paquete no está instalado con `pip install -e .`")
    result = subprocess.run([str(script), "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == EXPECTED
