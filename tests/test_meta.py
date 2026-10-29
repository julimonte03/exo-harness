"""Los nombres visibles del motor salen solo de `_meta.py` (invariante 17, ADR-0001).

Falla si algún módulo de `src/exo` distinto de `_meta.py` contiene como
literal de string el directorio del proyecto o el prefijo de variables.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from exo import _meta

SRC = Path(__file__).resolve().parents[1] / "src" / "exo"
FORBIDDEN = (_meta.PROJECT_DIR, _meta.ENV_PREFIX)


def _string_literals(path: Path) -> Iterator[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value


def find_offenders(package_root: Path) -> list[str]:
    meta = package_root / "_meta.py"
    offenders = []
    for path in sorted(package_root.rglob("*.py")):
        if path == meta:
            continue
        for lineno, value in _string_literals(path):
            if any(token in value for token in FORBIDDEN):
                rel = path.relative_to(package_root).as_posix()
                offenders.append(f"{rel}:{lineno}: {value!r}")
    return offenders


def test_nombres_visibles_solo_en_meta() -> None:
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
