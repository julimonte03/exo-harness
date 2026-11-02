"""paths: carpeta de datos de usuario por sistema operativo (ADR-0001)."""

from __future__ import annotations

from pathlib import Path

import pytest

from exo import _meta, paths


@pytest.mark.parametrize(
    ("platform", "env", "expected"),
    [
        ("win32", {"LOCALAPPDATA": "C:/Users/u/AppData/Local"}, Path("C:/Users/u/AppData/Local")),
        ("linux", {"XDG_DATA_HOME": "/home/u/.data"}, Path("/home/u/.data")),
        ("linux", {}, Path.home() / ".local" / "share"),
        ("darwin", {}, Path.home() / "Library" / "Application Support"),
    ],
)
def test_user_data_dir_por_sistema(
    monkeypatch: pytest.MonkeyPatch, platform: str, env: dict[str, str], expected: Path
) -> None:
    for name in ("LOCALAPPDATA", "XDG_DATA_HOME", paths.ENV_DATA_DIR):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(paths.sys, "platform", platform)
    assert paths.user_data_dir() == expected / _meta.USER_DIR_NAME


def test_override_por_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(tmp_path))
    assert paths.user_data_dir() == tmp_path


def test_nunca_usa_la_carpeta_oculta_del_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(paths.ENV_DATA_DIR, raising=False)
    assert paths.user_data_dir() != Path.home() / _meta.PROJECT_DIR
    assert paths.user_data_dir().name == _meta.USER_DIR_NAME
