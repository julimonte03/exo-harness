"""Instaladores de un comando (criterio 1 de F2 y distribución de F8). Marca `installer`.

Se corren con `pytest -m installer --no-cov`. Instalan de verdad (necesitan red
para bajar hatchling), pero en carpetas temporales y sin tocar el PATH real:
en Windows el PATH se lee y se escribe en una clave temporal de HKCU
(`EXO_INSTALL_ENV_SUBKEY`); en Linux y macOS, en los archivos de inicio de un
HOME temporal.

Desde el clon (`sh install.sh`, `install.ps1 -File`) instalan el árbol de trabajo.
Por pipe (`curl … | sh`, `irm … | iex`) instalan desde un remoto simulado con la
forma de GitHub, servido en 127.0.0.1 (`tests/_remote.py`): nada va a GitHub.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

import _remote
from exo import _meta

pytestmark = pytest.mark.installer
REPO = Path(__file__).resolve().parents[1]
TIMEOUT = 900
MARK = f"# added by {_meta.DIST_NAME}"
PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass"]
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="install.sh es para Linux y macOS")
WINDOWS_ONLY = pytest.mark.skipif(sys.platform != "win32", reason="install.ps1 es para Windows")

# URLs que el instalador remoto rechaza antes de bajar nada: solo https (y file:// o
# http a loopback, que no salen de la máquina), sin credenciales ni hosts disfrazados.
INSECURE_URLS = [
    "http://example.com/owner/exo-harness",
    "git://example.com/owner/exo-harness",
    "ftp://example.com/owner/exo-harness",
    "https://token@example.com/owner/exo-harness",
    "http://127.0.0.1.example.com/owner/exo-harness",
    "http://127.0.0.1:80@example.com/owner/exo-harness",
    "https://example.com/owner/exo-harness?x=1",
]
# Refs que cambiarían la URL o el requisito de pip.
BAD_REFS = ["main;touch pwned", "--upload-pack=touch pwned", "v1..v2", "a b", "x@{1}", "main#egg=other"]


def _env(tmp_path: Path, *, no_uv: bool) -> dict[str, str]:
    env = dict(os.environ)
    for name in ("EXO_INSTALL_NO_PATH", "EXO_REF", "EXO_REPO_URL"):
        env.pop(name, None)
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


def _remote_env(tmp_path: Path, url: str, *, no_uv: bool, ref: str | None = None) -> dict[str, str]:
    env = {**_env(tmp_path, no_uv=no_uv), "EXO_REPO_URL": url}
    if ref is not None:
        env["EXO_REF"] = ref
    return env


def _exec(
    cmd: list[str], env: dict[str, str], stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        env=env,
        input=stdin,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT,
    )


def _run(
    cmd: list[str], env: dict[str, str], stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    result = _exec(cmd, env, stdin)
    assert result.returncode == 0, f"{cmd}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result


def _script(name: str) -> str:
    """El script tal como lo baja `curl`, para pasarlo por stdin a `sh -s`."""
    return (REPO / name).read_text(encoding="utf-8")


def _irm_iex(url: str) -> list[str]:
    """`irm <url> | iex`, como lo corre quien instala en Windows."""
    return [*PS, "-Command", f"irm '{url}' | iex"]


def _dice(result: subprocess.CompletedProcess[str], text: str) -> bool:
    """Si la salida contiene `text`. Sin espacios ni saltos de los dos lados: PowerShell
    corta un error largo al ancho de la consola, entre palabras o en medio de una."""
    def squash(value: str) -> str:
        return "".join(value.split())

    return squash(text) in squash(result.stdout + result.stderr)


def _modes() -> list[bool]:
    modes = [True]
    if shutil.which("uv"):
        modes.append(False)
    return modes


def _mode_id(no_uv: bool) -> str:
    return "venv" if no_uv else "uv"


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


@pytest.fixture(scope="module")
def _remoto_servido(tmp_path_factory: pytest.TempPathFactory) -> Iterator[_remote.Remote]:
    remote = _remote.build(tmp_path_factory.mktemp("remoto"), REPO, _meta.VERSION)
    with _remote.serve(remote) as served:
        yield served


@pytest.fixture
def remoto(_remoto_servido: _remote.Remote) -> _remote.Remote:
    """El remoto simulado, con `v<VERSION>` como último release y sin pedidos anotados."""
    _remoto_servido.latest = _remoto_servido.tag
    _remoto_servido.requests.clear()
    return _remoto_servido


# -- Desde el clon --------------------------------------------------------------------------------


@WINDOWS_ONLY
@pytest.mark.parametrize("no_uv", _modes(), ids=_mode_id)
def test_install_ps1(tmp_path: Path, no_uv: bool, path_key: str) -> None:
    import winreg

    env = {**_env(tmp_path, no_uv=no_uv), "EXO_INSTALL_ENV_SUBKEY": path_key}
    original = _user_path(path_key)
    project = tmp_path / "proyecto"
    project.mkdir()
    shell = [*PS, "-File"]
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
    assert "was not installed" in _run([*shell, str(REPO / "uninstall.ps1")], env).stdout


def _venv_works() -> bool:
    probe = subprocess.run(
        [sys.executable, "-c", "import ensurepip"], capture_output=True, check=False
    )
    return probe.returncode == 0


@POSIX_ONLY
@pytest.mark.parametrize("no_uv", _modes(), ids=_mode_id)
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


@POSIX_ONLY
def test_install_sh_no_pisa_otro_exo(tmp_path: Path) -> None:
    env = _env(tmp_path, no_uv=True)
    other = Path(env["HOME"]) / ".local" / "bin" / _meta.NAME
    other.parent.mkdir(parents=True)
    other.write_text("#!/bin/sh\necho otra herramienta\n", encoding="utf-8")
    result = _exec(["sh", str(REPO / "install.sh")], env)
    assert result.returncode == 1
    assert "does not belong to this engine" in result.stderr
    assert other.read_text(encoding="utf-8") == "#!/bin/sh\necho otra herramienta\n"
    assert not (tmp_path / "datos" / "venv").exists()


@pytest.mark.skipif(sys.platform == "win32" or not shutil.which("uv"), reason="install.sh con uv")
def test_install_sh_con_uv_no_pisa_otro_exo(tmp_path: Path) -> None:
    env = _env(tmp_path, no_uv=False)
    other = tmp_path / "uv-bin" / _meta.NAME
    other.parent.mkdir(parents=True)
    other.write_text("#!/bin/sh\necho otra herramienta\n", encoding="utf-8")
    result = _exec(["sh", str(REPO / "install.sh")], env)
    assert result.returncode != 0
    assert other.read_text(encoding="utf-8") == "#!/bin/sh\necho otra herramienta\n"


# -- Por pipe, desde el remoto simulado (F8) -------------------------------------------------------


@pytest.mark.parametrize("script", ["install.ps1", "uninstall.ps1"])
def test_ps1_en_ascii_sin_bom(script: str) -> None:
    """`irm | iex` no tolera un BOM, y PowerShell 5.1 lee un archivo sin BOM en la página
    de códigos ANSI: los scripts de Windows van en ASCII puro."""
    assert (REPO / script).read_bytes().isascii()


# Funciones (no cmdlets compilados) de Microsoft.PowerShell.Utility en Windows PowerShell 5.1:
# lanzado desde pwsh hereda el PSModulePath de PowerShell 7 y no las encuentra. Pasó en el
# runner de Windows de GitHub Actions con Get-FileHash (F8).
_PS51_FRAGILE = ("Get-FileHash", "New-TemporaryFile", "New-Guid", "Format-Hex")


@pytest.mark.parametrize("script", ["install.ps1", "uninstall.ps1"])
def test_ps1_sin_funciones_que_fallan_desde_pwsh(script: str) -> None:
    lines = (REPO / script).read_text(encoding="ascii").splitlines()
    code = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
    assert [name for name in _PS51_FRAGILE if name in code] == []


@POSIX_ONLY
def test_install_sh_help_por_pipe(tmp_path: Path) -> None:
    result = _run(["sh", "-s", "--", "--help"], _env(tmp_path, no_uv=True), _script("install.sh"))
    assert "Usage:" in result.stdout
    assert "EXO_REF" in result.stdout


@POSIX_ONLY
@pytest.mark.parametrize("no_uv", _modes(), ids=_mode_id)
def test_install_sh_remoto_ultimo_release(tmp_path: Path, no_uv: bool, remoto: _remote.Remote) -> None:
    """Sin EXO_REF, el último release: sin uv, su wheel verificado; con uv, git en el tag."""
    if no_uv and not _venv_works():
        pytest.skip("este Python no trae ensurepip (falta python3-venv)")
    env = _remote_env(tmp_path, remoto.url, no_uv=no_uv)
    home = Path(env["HOME"])
    result = _run(["sh", "-s"], env, _script("install.sh"))
    bin_dir = home / ".local" / "bin" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / _meta.NAME
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert f"{remoto.path}/releases/latest" in remoto.requests
    if no_uv:
        assert f"{remoto.path}/releases/download/{remoto.tag}/{remoto.wheel}" in remoto.requests
        assert f"Verified {remoto.wheel} against SHA256SUMS." in result.stdout
        assert not remoto.git_fetched()
    else:
        assert remoto.git_fetched()
    assert (home / ".profile").read_text(encoding="utf-8") == f'export PATH="{bin_dir}:$PATH" {MARK}\n'
    # El desinstalador también corre por pipe.
    _run(["sh", "-s"], env, _script("uninstall.sh"))
    assert not exe.exists()
    assert not (home / ".profile").exists()


@POSIX_ONLY
def test_install_sh_remoto_carpeta_de_datos_privada(tmp_path: Path, remoto: _remote.Remote) -> None:
    """Sin uv, la carpeta de datos y las que le faltan se crean en 0700 aunque el umask
    sea 022; una que ya existe no se toca (TM-27)."""
    if not _venv_works():
        pytest.skip("este Python no trae ensurepip (falta python3-venv)")
    shared = tmp_path / "compartida"
    shared.mkdir()
    shared.chmod(0o755)
    data = shared / "nueva" / "datos"
    env = {**_remote_env(tmp_path, remoto.url, no_uv=True), "EXO_DATA_DIR": str(data)}
    _run(["sh", "-c", "umask 022 && exec sh -s"], env, _script("install.sh"))
    assert (data / "path-entry.txt").is_file()
    assert stat.S_IMODE(data.stat().st_mode) == 0o700
    assert stat.S_IMODE(data.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(shared.stat().st_mode) == 0o755


@POSIX_ONLY
def test_install_sh_remoto_sin_releases_instala_main(tmp_path: Path, remoto: _remote.Remote) -> None:
    """Sin releases, `main` desde git (con pip: no hay SHA256SUMS para una rama)."""
    if not _venv_works():
        pytest.skip("este Python no trae ensurepip (falta python3-venv)")
    remoto.latest = None
    env = _remote_env(tmp_path, remoto.url, no_uv=True)
    result = _run(["sh", "-s", "--", "--no-path"], env, _script("install.sh"))
    assert "has no releases yet: installing the main branch" in result.stderr
    assert f"{remoto.path}/releases/download/main/SHA256SUMS" in remoto.requests
    assert remoto.git_fetched()
    exe = Path(env["HOME"]) / ".local" / "bin" / _meta.NAME
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert not (Path(env["HOME"]) / ".profile").exists()


@POSIX_ONLY
def test_install_sh_remoto_ref_por_file(tmp_path: Path, remoto: _remote.Remote) -> None:
    """EXO_REF elige la rama, y el repo puede ser un file:// (un espejo local)."""
    no_uv = not shutil.which("uv")
    if no_uv and not _venv_works():
        pytest.skip("este Python no trae ensurepip (falta python3-venv)")
    env = {**_remote_env(tmp_path, remoto.file_url, no_uv=no_uv, ref="main"), "EXO_INSTALL_NO_PATH": "1"}
    result = _run(["sh", "-s"], env, _script("install.sh"))
    assert f"from {remoto.file_url} at main" in result.stdout
    bin_dir = Path(env["HOME"]) / ".local" / "bin" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / _meta.NAME
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert remoto.requests == []


@POSIX_ONLY
def test_install_sh_remoto_checksum_distinto_no_instala(tmp_path: Path, remoto: _remote.Remote) -> None:
    env = _remote_env(tmp_path, remoto.url, no_uv=True, ref=_remote.BAD_TAG)
    result = _exec(["sh", "-s"], env, _script("install.sh"))
    assert result.returncode == 1
    assert f"Checksum mismatch for {remoto.wheel}" in result.stderr
    assert not (tmp_path / "datos" / "venv").exists()
    assert not (Path(env["HOME"]) / ".local" / "bin" / _meta.NAME).exists()


@POSIX_ONLY
def test_install_sh_remoto_release_sin_sha256sums_no_pasa_a_git(
    tmp_path: Path, remoto: _remote.Remote
) -> None:
    """Un release sin `SHA256SUMS` no se instala desde git sin checksum (TM-6)."""
    env = _remote_env(tmp_path, remoto.url, no_uv=True, ref=_remote.NO_SUMS_TAG)
    result = _exec(["sh", "-s"], env, _script("install.sh"))
    assert result.returncode == 1
    assert f"Cannot verify release {_remote.NO_SUMS_TAG}" in result.stderr
    assert f"{remoto.path}/releases/download/{_remote.NO_SUMS_TAG}/SHA256SUMS" in remoto.requests
    assert not remoto.git_fetched()
    assert not (tmp_path / "datos" / "venv").exists()


@POSIX_ONLY
@pytest.mark.skipif(not shutil.which("curl"), reason="sin curl")
def test_install_sh_remoto_redireccion_a_otro_protocolo_no_instala(
    tmp_path: Path, remoto: _remote.Remote
) -> None:
    """El wheel redirige de http a https: curl no sigue un salto a otro protocolo (TM-3)."""
    env = _remote_env(tmp_path, remoto.url, no_uv=True, ref=_remote.REDIRECT_TAG)
    result = _exec(["sh", "-s"], env, _script("install.sh"))
    assert result.returncode == 1
    # El error de curl con --proto-redir; sin él, seguiría el salto y la conexión se rechazaría.
    assert 'Protocol "https"' in result.stderr
    assert f"{remoto.path}/releases/download/{_remote.REDIRECT_TAG}/{remoto.wheel}" in remoto.requests
    assert not remoto.git_fetched()
    assert not (tmp_path / "datos" / "venv").exists()


def _path_sin_curl(tmp_path: Path) -> tuple[str, Path]:
    """Un PATH con los programas del de esta sesión, menos curl, y un wget falso que anota
    cada llamada en el archivo que devuelve y falla."""
    bin_dir = tmp_path / "sin-curl"
    bin_dir.mkdir()
    log = tmp_path / "wget.log"
    wget = bin_dir / "wget"
    wget.write_text(f'#!/bin/sh\necho "$*" >> "{log}"\nexit 1\n', encoding="utf-8")
    wget.chmod(0o755)
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not os.path.isdir(folder):
            continue
        for entry in os.scandir(folder):
            link = bin_dir / entry.name
            if entry.name == "curl" or os.path.lexists(link):
                continue
            try:  # en macOS hay entradas de /usr/sbin que ni se pueden examinar
                executable = entry.is_file() and os.access(entry.path, os.X_OK)
            except OSError:
                continue
            if executable:
                link.symlink_to(entry.path)
    return str(bin_dir), log


@POSIX_ONLY
def test_install_sh_remoto_https_sin_curl_no_baja_con_wget(tmp_path: Path) -> None:
    """wget sigue redirecciones a cualquier protocolo: con https, sin curl no baja nada (TM-3)."""
    path, log = _path_sin_curl(tmp_path)
    url = "https://example.invalid/owner/exo-harness"
    env = {**_remote_env(tmp_path, url, no_uv=True, ref="v1.0.0"), "PATH": path}
    result = _exec(["sh", "-s"], env, _script("install.sh"))
    assert result.returncode == 1
    assert "curl is required" in result.stderr
    assert "Cannot verify release v1.0.0" in result.stderr
    assert not log.exists()


@POSIX_ONLY
@pytest.mark.parametrize("url", INSECURE_URLS)
def test_install_sh_remoto_solo_https(tmp_path: Path, url: str) -> None:
    env = _remote_env(tmp_path, url, no_uv=True)
    result = _exec(["sh", "-s"], env, _script("install.sh"))
    assert result.returncode == 1
    assert "EXO_REPO_URL" in result.stderr
    assert not (tmp_path / "datos").exists()


@POSIX_ONLY
@pytest.mark.parametrize("ref", BAD_REFS)
def test_install_sh_remoto_rechaza_refs_raros(tmp_path: Path, ref: str) -> None:
    # Bajado suelto, fuera de un clon: también instala desde el remoto.
    script = tmp_path / "bajado" / "install.sh"
    script.parent.mkdir()
    shutil.copy2(REPO / "install.sh", script)
    env = _remote_env(tmp_path, "https://example.invalid/owner/exo-harness", no_uv=True, ref=ref)
    result = _exec(["sh", str(script)], env)
    assert result.returncode == 1
    assert "Not a valid tag, branch or commit" in result.stderr


@WINDOWS_ONLY
@pytest.mark.parametrize("no_uv", _modes(), ids=_mode_id)
def test_install_ps1_remoto_ultimo_release(
    tmp_path: Path, no_uv: bool, path_key: str, remoto: _remote.Remote
) -> None:
    """Sin EXO_REF, el último release: sin uv, su wheel verificado; con uv, git en el tag."""
    env = {**_remote_env(tmp_path, remoto.url, no_uv=no_uv), "EXO_INSTALL_ENV_SUBKEY": path_key}
    original = _user_path(path_key)
    result = _run(_irm_iex(remoto.raw("install.ps1")), env)
    bin_dir = tmp_path / "datos" / "venv" / "Scripts" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / f"{_meta.NAME}.exe"
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert f"{remoto.path}/releases/latest" in remoto.requests
    if no_uv:
        assert f"{remoto.path}/releases/download/{remoto.tag}/{remoto.wheel}" in remoto.requests
        assert f"Verified {remoto.wheel} against SHA256SUMS." in result.stdout
        assert not remoto.git_fetched()
    else:
        assert remoto.git_fetched()
    assert _user_path(path_key)[0] == f"{original[0]};{bin_dir}"
    # El desinstalador también corre por pipe.
    _run(_irm_iex(remoto.raw("uninstall.ps1")), env)
    assert not exe.exists()
    assert _user_path(path_key) == original


@WINDOWS_ONLY
@pytest.mark.parametrize("no_uv", _modes(), ids=_mode_id)
def test_install_ps1_con_la_salida_redirigida(
    tmp_path: Path, no_uv: bool, remoto: _remote.Remote
) -> None:
    """`... *> install.log`: con la salida redirigida, PowerShell 5.1 convierte el stderr de
    uv o de pip (su progreso) en errores, y el 'Stop' del script cortaba la instalación
    (lo encontró el checklist cronometrado de F8). Lo mismo con `uv tool uninstall` en el
    desinstalador (F8R2-2)."""
    env = {**_remote_env(tmp_path, remoto.url, no_uv=no_uv), "EXO_INSTALL_NO_PATH": "1"}
    log = tmp_path / "install.log"
    script = f"& ([scriptblock]::Create((irm '{remoto.raw('install.ps1')}'))) *> '{log}'"
    result = _exec([*PS, "-Command", script], env)
    assert result.returncode == 0, log.read_text(encoding="utf-16", errors="replace")
    bin_dir = tmp_path / "datos" / "venv" / "Scripts" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / f"{_meta.NAME}.exe"
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    log = tmp_path / "uninstall.log"
    script = f"& ([scriptblock]::Create((irm '{remoto.raw('uninstall.ps1')}'))) *> '{log}'"
    result = _exec([*PS, "-Command", script], env)
    output = log.read_text(encoding="utf-16", errors="replace")
    assert result.returncode == 0, output
    assert f"Uninstalled {_meta.DIST_NAME}" in output
    assert not exe.exists()


@WINDOWS_ONLY
def test_install_ps1_remoto_sin_releases_instala_main(tmp_path: Path, remoto: _remote.Remote) -> None:
    """Sin releases, `main` desde git (con pip: no hay SHA256SUMS para una rama)."""
    remoto.latest = None
    env = {**_remote_env(tmp_path, remoto.url, no_uv=True), "EXO_INSTALL_NO_PATH": "1"}
    result = _run(_irm_iex(remoto.raw("install.ps1")), env)
    assert "has no releases yet: installing the main branch" in result.stdout
    assert f"{remoto.path}/releases/download/main/SHA256SUMS" in remoto.requests
    assert remoto.git_fetched()
    exe = tmp_path / "datos" / "venv" / "Scripts" / f"{_meta.NAME}.exe"
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"


@WINDOWS_ONLY
def test_install_ps1_remoto_ref_por_file(tmp_path: Path, remoto: _remote.Remote) -> None:
    """EXO_REF elige la rama, y el repo puede ser un file:// (un espejo local)."""
    no_uv = not shutil.which("uv")
    env = {**_remote_env(tmp_path, remoto.file_url, no_uv=no_uv, ref="main"), "EXO_INSTALL_NO_PATH": "1"}
    result = _run(_irm_iex(remoto.raw("install.ps1")), env)
    assert f"from {remoto.file_url} at main" in result.stdout
    bin_dir = tmp_path / "datos" / "venv" / "Scripts" if no_uv else tmp_path / "uv-bin"
    exe = bin_dir / f"{_meta.NAME}.exe"
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert remoto.requests == ["/raw/install.ps1"]


@WINDOWS_ONLY
def test_install_ps1_remoto_checksum_distinto_no_instala(tmp_path: Path, remoto: _remote.Remote) -> None:
    env = {
        **_remote_env(tmp_path, remoto.url, no_uv=True, ref=_remote.BAD_TAG),
        "EXO_INSTALL_NO_PATH": "1",
    }
    result = _exec(_irm_iex(remoto.raw("install.ps1")), env)
    assert result.returncode != 0
    assert f"Checksum mismatch for {remoto.wheel}" in result.stdout + result.stderr
    assert not (tmp_path / "datos" / "venv").exists()


@WINDOWS_ONLY
def test_install_ps1_remoto_release_sin_sha256sums_no_pasa_a_git(
    tmp_path: Path, remoto: _remote.Remote
) -> None:
    """Un release sin `SHA256SUMS` no se instala desde git sin checksum (TM-6)."""
    env = {
        **_remote_env(tmp_path, remoto.url, no_uv=True, ref=_remote.NO_SUMS_TAG),
        "EXO_INSTALL_NO_PATH": "1",
    }
    result = _exec(_irm_iex(remoto.raw("install.ps1")), env)
    assert result.returncode != 0
    assert _dice(result, f"Cannot verify release {_remote.NO_SUMS_TAG}")
    assert f"{remoto.path}/releases/download/{_remote.NO_SUMS_TAG}/SHA256SUMS" in remoto.requests
    assert not remoto.git_fetched()
    assert not (tmp_path / "datos" / "venv").exists()


@WINDOWS_ONLY
def test_install_ps1_remoto_redireccion_a_otro_protocolo_no_instala(
    tmp_path: Path, remoto: _remote.Remote
) -> None:
    """El wheel redirige de http a https: se rechaza el salto antes de pedirlo (TM-3)."""
    env = {
        **_remote_env(tmp_path, remoto.url, no_uv=True, ref=_remote.REDIRECT_TAG),
        "EXO_INSTALL_NO_PATH": "1",
    }
    result = _exec(_irm_iex(remoto.raw("install.ps1")), env)
    assert result.returncode != 0
    wheel = f"{remoto.path}/releases/download/{_remote.REDIRECT_TAG}/{remoto.wheel}"
    target = f"{remoto.redirect_to}{wheel}"
    # El chequeo del instalador; sin él, .NET seguiría el salto y la conexión se rechazaría.
    assert _dice(result, f"redirected to {target}, which is not http; refusing it.")
    assert wheel in remoto.requests
    assert not remoto.git_fetched()
    assert not (tmp_path / "datos" / "venv").exists()


def _carpeta_ajena(tmp_path: Path) -> Path:
    """`datos1\\venv`, de otro dueño: `datos[1]` leído como comodín calza con `datos1` (TM-8)."""
    other = tmp_path / "datos1" / "venv"
    other.mkdir(parents=True)
    (other / "ajeno.txt").write_text("no es del motor\n", encoding="utf-8")
    return other


@WINDOWS_ONLY
def test_uninstall_ps1_carpeta_de_datos_con_corchetes(tmp_path: Path) -> None:
    """Borra el venv de la carpeta de datos tal como está escrita, sin comodines."""
    data = tmp_path / "datos[1]"
    (data / "venv" / "Scripts").mkdir(parents=True)
    (data / "venv" / "Scripts" / "python.exe").write_bytes(b"")
    other = _carpeta_ajena(tmp_path)
    env = {**_env(tmp_path, no_uv=True), "EXO_DATA_DIR": str(data), "EXO_INSTALL_NO_PATH": "1"}
    result = _run([*PS, "-File", str(REPO / "uninstall.ps1")], env)
    assert "Uninstalled" in result.stdout
    assert not (data / "venv").exists()
    assert (other / "ajeno.txt").read_text(encoding="utf-8") == "no es del motor\n"


def _uv_falso(tmp_path: Path) -> tuple[Path, Path]:
    """Una carpeta con un `uv.cmd` cuyo `uv tool list` muestra otra herramienta,
    `exo-harness-x`, y que anota en el log que devuelve cualquier otro comando."""
    folder = tmp_path / "uv-falso"
    folder.mkdir()
    log = tmp_path / "uv.log"
    (folder / "uv.cmd").write_text(
        "@echo off\r\n"
        'if "%1"=="tool" if "%2"=="list" (\r\n'
        "  echo exo-harness-x v1.0.0\r\n"
        "  echo - exo-x.exe\r\n"
        "  exit /b 0\r\n"
        ")\r\n"
        f'echo %*>>"{log}"\r\n'
        "exit /b 0\r\n",
        encoding="ascii",
        newline="",
    )
    return folder, log


@WINDOWS_ONLY
def test_uninstall_ps1_no_desinstala_otra_herramienta_de_uv(tmp_path: Path) -> None:
    """`uv tool list` con `exo-harness-x` no es el motor: no se desinstala (F8R2-18)."""
    folder, log = _uv_falso(tmp_path)
    env = {**_env(tmp_path, no_uv=False), "EXO_INSTALL_NO_PATH": "1"}
    env["PATH"] = f"{folder}{os.pathsep}{env['PATH']}"
    result = _run([*PS, "-File", str(REPO / "uninstall.ps1")], env)
    assert "was not installed" in result.stdout
    assert not log.exists(), log.read_text(encoding="utf-8", errors="replace")


@WINDOWS_ONLY
def test_uninstall_ps1_con_path_entry_vacio(tmp_path: Path, path_key: str) -> None:
    """Un `path-entry.txt` vacío no corta la desinstalación ni toca el PATH (F8R2-18)."""
    data = tmp_path / "datos"
    data.mkdir()
    (data / "path-entry.txt").write_bytes(b"")
    env = {**_env(tmp_path, no_uv=True), "EXO_INSTALL_ENV_SUBKEY": path_key}
    original = _user_path(path_key)
    result = _run([*PS, "-File", str(REPO / "uninstall.ps1")], env)
    assert "was not installed" in result.stdout
    assert not (data / "path-entry.txt").exists()
    assert _user_path(path_key) == original


@WINDOWS_ONLY
def test_install_ps1_remoto_carpeta_de_datos_con_corchetes(
    tmp_path: Path, path_key: str, remoto: _remote.Remote
) -> None:
    """Instala y desinstala con `[1]` en EXO_DATA_DIR, sin tocar la carpeta que calza."""
    data = tmp_path / "datos[1]"
    other = _carpeta_ajena(tmp_path)
    env = {
        **_remote_env(tmp_path, remoto.url, no_uv=True),
        "EXO_DATA_DIR": str(data),
        "EXO_INSTALL_ENV_SUBKEY": path_key,
    }
    original = _user_path(path_key)
    _run(_irm_iex(remoto.raw("install.ps1")), env)
    bin_dir = data / "venv" / "Scripts"
    exe = bin_dir / f"{_meta.NAME}.exe"
    assert _run([str(exe), "--version"], env).stdout.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert _user_path(path_key)[0] == f"{original[0]};{bin_dir}"
    assert (data / "path-entry.txt").is_file()
    _run(_irm_iex(remoto.raw("uninstall.ps1")), env)
    assert not (data / "venv").exists()
    assert _user_path(path_key) == original
    assert (other / "ajeno.txt").read_text(encoding="utf-8") == "no es del motor\n"


def _ps1_suelto(tmp_path: Path) -> Path:
    """install.ps1 bajado suelto, fuera de un clon: también instala desde el remoto."""
    script = tmp_path / "bajado" / "install.ps1"
    script.parent.mkdir()
    shutil.copy2(REPO / "install.ps1", script)
    return script


@WINDOWS_ONLY
@pytest.mark.parametrize("url", INSECURE_URLS)
def test_install_ps1_remoto_solo_https(tmp_path: Path, url: str) -> None:
    env = {**_remote_env(tmp_path, url, no_uv=True), "EXO_INSTALL_NO_PATH": "1"}
    result = _exec([*PS, "-File", str(_ps1_suelto(tmp_path))], env)
    assert result.returncode != 0
    assert "EXO_REPO_URL" in result.stdout + result.stderr
    assert not (tmp_path / "datos").exists()


@WINDOWS_ONLY
@pytest.mark.parametrize("ref", BAD_REFS)
def test_install_ps1_remoto_rechaza_refs_raros(tmp_path: Path, ref: str) -> None:
    env = {
        **_remote_env(tmp_path, "https://example.invalid/owner/exo-harness", no_uv=True, ref=ref),
        "EXO_INSTALL_NO_PATH": "1",
    }
    result = _exec([*PS, "-File", str(_ps1_suelto(tmp_path))], env)
    assert result.returncode != 0
    assert "Not a valid tag, branch or commit" in result.stdout + result.stderr
