"""Datos del usuario privados en POSIX (threat model, TM-27 y M-9).

La carpeta de datos tiene la memoria (sin redactar, ADR-0009), la persona, los comandos
aprobados y los backups de desinstalación: en Linux y macOS, con el umask típico (022),
quedaban legibles por los demás usuarios de la máquina.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from exo import doctor, paths, persona
from exo.cli import main
from exo.governance import approvals
from exo.memory import db

POSIX = pytest.mark.skipif(sys.platform == "win32", reason="los permisos POSIX no aplican")


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "datos" / "exo-harness"
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(folder))
    monkeypatch.delenv(paths.ENV_MEMORY_DB, raising=False)
    return folder


def test_private_dir_crea_lo_que_falta(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b"
    assert paths.private_dir(target) == target
    assert target.is_dir()
    assert paths.private_dir(target) == target  # idempotente


@POSIX
def test_private_dir_en_0700_sin_tocar_lo_que_ya_existe(tmp_path: Path) -> None:
    previous = os.umask(0o022)
    try:
        existing = tmp_path / "ya"
        existing.mkdir(mode=0o755)
        target = existing / "nueva" / "hoja"
        paths.private_dir(target)
    finally:
        os.umask(previous)
    assert _mode(target) == 0o700 and _mode(target.parent) == 0o700
    assert _mode(existing) == 0o755  # no es nuestra: la avisa exo doctor


@POSIX
def test_persona_y_aprobaciones_en_0600(data_dir: Path) -> None:
    persona.write("qa")
    approvals.approve("echo hola")
    assert _mode(data_dir) == 0o700
    assert _mode(data_dir / persona.FILE_NAME) == 0o600
    assert _mode(data_dir / approvals.FILE_NAME) == 0o600


@POSIX
def test_la_memoria_en_0600(data_dir: Path) -> None:
    path = paths.memory_db_path()
    conn = db.connect(path)
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (1)")
    assert _mode(data_dir) == 0o700
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists():
            assert _mode(candidate) == 0o600, candidate
    conn.close()
    # Una base vieja en 0644 queda privada en la próxima apertura.
    os.chmod(path, 0o644)
    db.connect(path).close()
    assert _mode(path) == 0o600


@POSIX
def test_export_en_0600(data_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "export.json"
    assert main(["mem", "export", "--output", str(output)]) == 0
    assert _mode(output) == 0o600


@POSIX
@pytest.mark.parametrize(("mode", "status"), [(0o755, "warn"), (0o700, "ok")])
def test_doctor_avisa_si_la_carpeta_de_datos_la_leen_otros(
    data_dir: Path, tmp_path: Path, mode: int, status: str
) -> None:
    data_dir.mkdir(parents=True)
    os.chmod(data_dir, mode)
    check = {c.name: c for c in doctor.run_checks(tmp_path)}["data-dir"]
    assert check.status == status
    if status == "warn":
        assert f"chmod 700 {data_dir}" in check.detail


def test_doctor_sin_carpeta_de_datos(data_dir: Path, tmp_path: Path) -> None:
    check = {c.name: c for c in doctor.run_checks(tmp_path)}["data-dir"]
    assert check.status in ("info", "ok")
