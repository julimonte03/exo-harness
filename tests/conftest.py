"""Fixtures compartidas."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="regenera tests/golden/*.json (revisá el diff antes de commitear)",
    )


@pytest.fixture(autouse=True)
def _datos_de_usuario_aislados(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Ningún test toca la carpeta de datos real ni la memoria real del usuario.

    Usa un MonkeyPatch propio: si un test hace `monkeypatch.undo()`, no deshace esto.
    """
    from exo import paths

    patch = pytest.MonkeyPatch()
    patch.setenv(paths.ENV_DATA_DIR, str(tmp_path_factory.mktemp("datos-usuario")))
    patch.delenv(paths.ENV_MEMORY_DB, raising=False)
    yield
    patch.undo()


@pytest.fixture
def make_dir_link() -> Callable[[Path, Path], None]:
    """Crea un link de directorio: junction en Windows (sin privilegios), symlink en POSIX."""

    def create(link: Path, target: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
        else:
            os.symlink(target, link, target_is_directory=True)

    return create


@pytest.fixture
def golden(request: pytest.FixtureRequest) -> Callable[[str, dict[str, bytes]], None]:
    """Compara un árbol de archivos contra tests/golden/<nombre>.json, byte a byte."""
    from _projects import decode_tree, encode_tree

    update = request.config.getoption("--update-golden")

    def check(name: str, files: dict[str, bytes]) -> None:
        path = GOLDEN_DIR / f"{name}.json"
        if update:
            GOLDEN_DIR.mkdir(exist_ok=True)
            path.write_text(encode_tree(files), encoding="utf-8", newline="\n")
            return
        assert path.exists(), f"falta {path.name}: corré `pytest --update-golden` y revisá el diff"
        expected = decode_tree(path.read_text(encoding="utf-8"))
        assert sorted(files) == sorted(expected), "el árbol generado no tiene los mismos archivos"
        for rel, data in expected.items():
            assert files[rel] == data, f"{rel} difiere del golden {path.name}"

    return check
