"""Instaladores de un comando (criterio 1 de F2). Marca `installer`: fuera de la suite normal.

Se corren con `pytest -m installer --no-cov`. Instalan de verdad (necesitan red
para bajar hatchling), pero en carpetas temporales y sin tocar el PATH real:
en Windows el PATH se lee y se escribe en una clave temporal de HKCU
(`EXO_INSTALL_ENV_SUBKEY`); en Linux y macOS, en los archivos de inicio de un
HOME temporal.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from exo import _meta

pytestmark = pytest.mark.installer
REPO = Path(__file__).resolve().parents[1]
TIMEOUT = 900
MARK = f"# agregado por {_meta.DIST_NAME}"


def _env(tmp_path: Path, *, no_uv: bool) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("EXO_INSTALL_NO_PATH", None)
    env.update(
        {
            "EXO_DATA_DIR": str(tmp_path / "datos"),
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
        env["SHELL"] = "/bin/bash"
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


@pytest.fixture
def path_key() -> Iterator[str]:
    """Clave temporal de HKCU con un PATH de usuario REG_EXPAND_SZ, como el de Windows."""
    import winreg

    subkey = rf"Software\{_meta.DIST_NAME}-tests\{uuid.uuid4().hex}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, r"%USERPROFILE%\herramientas;C:\otra")
    try:
        yield subkey
    finally:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)


def _user_path(subkey: str) -> tuple[str, int]:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
        value, kind = winreg.QueryValueEx(key, "Path")
    return value, kind


@pytest.mark.skipif(sys.platform != "win32", reason="install.ps1 es para Windows")
@pytest.mark.parametrize("no_uv", _modes(), ids=lambda v: "venv" if v else "uv")
def test_install_ps1(tmp_path: Path, no_uv: bool, path_key: str) -> None:
    import winreg

    env = {**_env(tmp_path, no_uv=no_uv), "EXO_INSTALL_ENV_SUBKEY": path_key}
    original = _user_path(path_key)
    project = tmp_path / "proyecto"
    project.mkdir()
    shell = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    _run([*shell, str(REPO / "install.ps1"), "-Init", str(project)], env)
    bin_dir = tmp_path / "datos" / "venv" / "Scripts" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / f"{_meta.NAME}.exe"
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    value, kind = _user_path(path_key)
    assert kind == winreg.REG_EXPAND_SZ
    assert value == f"{original[0]};{bin_dir}"
    # Re-ejecutarlo no duplica la entrada.
    _run([*shell, str(REPO / "install.ps1")], env)
    assert _user_path(path_key) == (value, kind)
    assert (project / "AGENTS.md").is_file()
    assert (project / _meta.PROJECT_DIR / "lock.json").is_file()
    _run([str(exe), "uninstall", "--project", str(project), "--yes"], env)
    assert list(project.iterdir()) == []
    _run([*shell, str(REPO / "uninstall.ps1")], env)
    assert not exe.exists()
    assert _user_path(path_key) == original
    # Una segunda desinstalación no falla (uv sin herramientas escribe en stderr).
    assert "no estaba instalado" in _run([*shell, str(REPO / "uninstall.ps1")], env).stdout


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
    home = Path(env["HOME"])
    (home / ".bash_profile").write_text("# mío\n", encoding="utf-8")
    (home / ".bashrc").write_text("", encoding="utf-8")
    project = tmp_path / "proyecto"
    project.mkdir()
    _run(["sh", str(REPO / "install.sh"), "--init", str(project)], env)
    bin_dir = home / ".local" / "bin" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / _meta.NAME
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    line = f'export PATH="{bin_dir}:$PATH" {MARK}\n'
    assert (home / ".profile").read_text(encoding="utf-8") == line
    assert (home / ".bash_profile").read_text(encoding="utf-8") == "# mío\n" + line
    assert (home / ".bashrc").read_text(encoding="utf-8") == line
    assert not (home / ".zshrc").exists()
    _run(["sh", str(REPO / "install.sh")], env)
    assert (home / ".profile").read_text(encoding="utf-8") == line
    assert (project / "AGENTS.md").is_file()
    _run([str(exe), "uninstall", "--project", str(project), "--yes"], env)
    assert list(project.iterdir()) == []
    _run(["sh", str(REPO / "uninstall.sh")], env)
    assert not exe.exists()
    assert not (home / ".profile").exists()
    assert (home / ".bash_profile").read_text(encoding="utf-8") == "# mío\n"
    # Ya existía (vacío): queda, vacío.
    assert (home / ".bashrc").read_text(encoding="utf-8") == ""


@pytest.mark.skipif(sys.platform == "win32", reason="install.sh es para Linux y macOS")
def test_install_sh_no_pisa_otro_exo(tmp_path: Path) -> None:
    env = _env(tmp_path, no_uv=True)
    other = Path(env["HOME"]) / ".local" / "bin" / _meta.NAME
    other.parent.mkdir(parents=True)
    other.write_text("#!/bin/sh\necho otra herramienta\n", encoding="utf-8")
    result = subprocess.run(
        ["sh", str(REPO / "install.sh")], env=env, capture_output=True, text=True, timeout=TIMEOUT
    )
    assert result.returncode == 1
    assert "no es de este motor" in result.stderr
    assert other.read_text(encoding="utf-8") == "#!/bin/sh\necho otra herramienta\n"
    assert not (tmp_path / "datos" / "venv").exists()


@pytest.mark.skipif(sys.platform == "win32" or not shutil.which("uv"), reason="install.sh con uv")
def test_install_sh_con_uv_no_pisa_otro_exo(tmp_path: Path) -> None:
    env = _env(tmp_path, no_uv=False)
    other = tmp_path / "uv-bin" / _meta.NAME
    other.parent.mkdir(parents=True)
    other.write_text("#!/bin/sh\necho otra herramienta\n", encoding="utf-8")
    result = subprocess.run(
        ["sh", str(REPO / "install.sh")], env=env, capture_output=True, text=True, timeout=TIMEOUT
    )
    assert result.returncode != 0
    assert other.read_text(encoding="utf-8") == "#!/bin/sh\necho otra herramienta\n"
