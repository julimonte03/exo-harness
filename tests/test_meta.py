"""Los nombres visibles del motor salen solo de `_meta.py`.

Invariante 17 de `docs/plan/02-ARQUITECTURA.md` §2.13 (12 en `AGENTS.md`), ADR-0001.
Falla si algún módulo de `src/exo` distinto de `_meta.py` contiene como
literal de string el directorio del proyecto, el prefijo de variables o el
nombre de la carpeta de datos de usuario. Los docstrings también cuentan, a
propósito: en la documentación del código se nombra la constante, no su valor.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from importlib import metadata
from pathlib import Path

import pytest

from exo import _meta

SRC = Path(_meta.__file__).resolve().parent
FORBIDDEN = (_meta.PROJECT_DIR, _meta.ENV_PREFIX, _meta.USER_DIR_NAME)


def python_modules(package_root: Path) -> list[Path]:
    meta = package_root / "_meta.py"
    return sorted(p for p in package_root.rglob("*.py") if p != meta)


def _string_literals(path: Path) -> Iterator[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value


def find_offenders(package_root: Path) -> list[str]:
    offenders = []
    for path in python_modules(package_root):
        for lineno, value in _string_literals(path):
            if any(token in value for token in FORBIDDEN):
                rel = path.relative_to(package_root).as_posix()
                offenders.append(f"{rel}:{lineno}: {value!r}")
    return offenders


def test_nombres_visibles_solo_en_meta() -> None:
    assert (SRC / "_meta.py").is_file(), f"no se encontró _meta.py en {SRC}"
    assert python_modules(SRC), f"no hay módulos para revisar en {SRC}"
    offenders = find_offenders(SRC)
    assert not offenders, (
        "Nombres visibles escritos como literal fuera de _meta.py; "
        "importalos de exo._meta:\n" + "\n".join(offenders)
    )


def test_detector_encuentra_literales_prohibidos(tmp_path: Path) -> None:
    (tmp_path / "_meta.py").write_text(f"PROJECT_DIR = {_meta.PROJECT_DIR!r}\n", encoding="utf-8")
    sub = tmp_path / "core"
    sub.mkdir()
    (sub / "config.py").write_text(
        f"CONFIG = {_meta.PROJECT_DIR + '/config.json'!r}\n"
        f"ENV = f'{_meta.ENV_PREFIX}{{name}}'\n",
        encoding="utf-8",
    )
    locations = [o.split(":")[:2] for o in find_offenders(tmp_path)]
    assert locations == [["core/config.py", "1"], ["core/config.py", "2"]]


def test_distribucion_instalada_coincide_con_meta() -> None:
    try:
        dist = metadata.distribution(_meta.DIST_NAME)
    except metadata.PackageNotFoundError:
        pytest.skip(f"{_meta.DIST_NAME} no está instalado con `pip install -e .`")
    assert dist.version == _meta.VERSION
    scripts = {ep.name: ep.value for ep in dist.entry_points if ep.group == "console_scripts"}
    assert scripts == {_meta.NAME: f"{_meta.NAME}.cli:main"}
