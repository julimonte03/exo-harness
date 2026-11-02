"""Instaladores de un comando (criterio 1 de F2). Marca `installer`: fuera de la suite normal.

Se corren con `pytest -m installer --no-cov`. Instalan de verdad (necesitan red
para bajar hatchling), pero en carpetas temporales: no tocan el PATH ni las
herramientas de uv del usuario.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from exo import _meta

pytestmark = pytest.mark.installer
REPO = Path(__file__).resolve().parents[1]
TIMEOUT = 900


def _env(tmp_path: Path, *, no_uv: bool) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "EXO_DATA_DIR": str(tmp_path / "datos"),
            "EXO_INSTALL_NO_PATH": "1",
            "UV_TOOL_DIR": str(tmp_path / "uv-tools"),
            "UV_TOOL_BIN_DIR": str(tmp_path / "uv-bin"),
        }
    )
    if no_uv:
        env["EXO_INSTALL_NO_UV"] = "1"
    if sys.platform != "win32":
        home = tmp_path / "home"
        home.mkdir(exist_ok=True)
        env["HOME"] = str(home)
    return env


def _run(cmd: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=TIMEOUT)
    assert result.returncode == 0, f"{cmd}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result


def _modes() -> list[bool]:
    modes = [True]
    if shutil.which("uv"):
        modes.append(False)
    return modes


@pytest.mark.skipif(sys.platform != "win32", reason="install.ps1 es para Windows")
@pytest.mark.parametrize("no_uv", _modes(), ids=lambda v: "venv" if v else "uv")
def test_install_ps1(tmp_path: Path, no_uv: bool) -> None:
    env = _env(tmp_path, no_uv=no_uv)
    project = tmp_path / "proyecto"
    project.mkdir()
    shell = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    _run([*shell, str(REPO / "install.ps1"), "-Init", str(project)], env)
    bin_dir = tmp_path / "datos" / "venv" / "Scripts" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / f"{_meta.NAME}.exe"
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert (project / "AGENTS.md").is_file()
    assert (project / _meta.PROJECT_DIR / "lock.json").is_file()
    _run([str(exe), "uninstall", "--project", str(project), "--yes"], env)
    assert list(project.iterdir()) == []
    _run([*shell, str(REPO / "uninstall.ps1")], env)
    assert not exe.exists()


def _venv_works() -> bool:
    probe = subprocess.run(
        [sys.executable, "-c", "import ensurepip"], capture_output=True, check=False
    )
    return probe.returncode == 0


@pytest.mark.skipif(sys.platform == "win32", reason="install.sh es para Linux y macOS")
@pytest.mark.parametrize("no_uv", _modes(), ids=lambda v: "venv" if v else "uv")
def test_install_sh(tmp_path: Path, no_uv: bool) -> None:
    if no_uv and not _venv_works():
        pytest.skip("este Python no trae ensurepip (falta python3-venv)")
    env = _env(tmp_path, no_uv=no_uv)
    project = tmp_path / "proyecto"
    project.mkdir()
    _run(["sh", str(REPO / "install.sh"), "--init", str(project)], env)
    bin_dir = Path(env["HOME"]) / ".local" / "bin" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / _meta.NAME
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert (project / "AGENTS.md").is_file()
    _run([str(exe), "uninstall", "--project", str(project), "--yes"], env)
    assert list(project.iterdir()) == []
    _run(["sh", str(REPO / "uninstall.sh")], env)
    assert not exe.exists()
