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


# GitHub acepta hasta 10 anotaciones de error por paso.
MAX_ANNOTATIONS = 10
ANNOTATION_LINES = 15


def _escape(text: str, *, prop: bool = False) -> str:
    """Escapa un valor para un comando de workflow de GitHub Actions."""
    text = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return text.replace(":", "%3A").replace(",", "%2C") if prop else text


def annotation(report: pytest.CollectReport | pytest.TestReport) -> str:
    """El `::error` de un test que falló: archivo, línea, nombre y el final del error."""
    location = getattr(report, "location", None)
    path = (location[0] if location else report.nodeid.split("::")[0]).replace("\\", "/")
    line = (location[1] or 0) + 1 if location else 1
    tail = "\n".join(report.longreprtext.strip().splitlines()[-ANNOTATION_LINES:])
    title = _escape(report.nodeid, prop=True)
    return f"::error file={_escape(path, prop=True)},line={line},title={title}::{_escape(tail)}"


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int, config: pytest.Config
) -> None:
    """En GitHub Actions, cada test que falló sale como anotación de la corrida.

    Las anotaciones se leen con la API pública sin autenticación; los logs no (D-45).
    """
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    stats = terminalreporter.stats
    reports = [r for key in ("failed", "error") for r in stats.get(key, []) if r.failed]
    for report in reports[:MAX_ANNOTATIONS]:
        terminalreporter.write_line(annotation(report))
    if exitstatus != 0 and not reports:
        terminalreporter.write_line(
            f"::error title=pytest::exit status {exitstatus} with no failed test "
            "(coverage under the threshold, or an internal error)"
        )


@pytest.fixture(autouse=True)
def _datos_de_usuario_aislados(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Ningún test toca la carpeta de datos real ni la memoria real del usuario.

    Tampoco ve la config global de git del dev: un `core.hooksPath` o un
    `init.templateDir` globales cambiarían lo que prueban los tests de hooks.
    Usa un MonkeyPatch propio: si un test hace `monkeypatch.undo()`, no deshace esto.
    """
    from exo import paths
    from exo.memory import embeddings

    patch = pytest.MonkeyPatch()
    patch.setenv(paths.ENV_DATA_DIR, str(tmp_path_factory.mktemp("datos-usuario")))
    patch.delenv(paths.ENV_MEMORY_DB, raising=False)
    gitconfig = tmp_path_factory.mktemp("git-global") / "gitconfig"
    gitconfig.write_text("", encoding="utf-8")
    patch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    patch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    embeddings._CACHE.clear()
    yield
    embeddings._CACHE.clear()
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
def synthetic_content(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Apunta el motor a un contenido canónico chico y fijo (`tests/_content.py`)."""
    import _content
    from exo import content

    root = _content.build(tmp_path_factory.mktemp("contenido"))
    monkeypatch.setenv(content.ENV_VAR, str(root))
    return root


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
