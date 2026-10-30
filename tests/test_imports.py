"""El núcleo usa solo biblioteca estándar (criterio 7 de F1, invariante 4 de 02-ARQUITECTURA §2.13).

Única excepción declarada: `memory/backends/` y `memory/embeddings/`, que
importan sus dependencias de forma diferida (F3).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from exo import _meta

SRC = Path(_meta.__file__).resolve().parent
EXCEPTIONS = (SRC / "memory" / "backends", SRC / "memory" / "embeddings")
ALLOWED = set(sys.stdlib_module_names) | {_meta.NAME, "__future__"}


def _imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name.split(".")[0]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module.split(".")[0]))
    return found


def _modules() -> list[Path]:
    return [
        p
        for p in sorted(SRC.rglob("*.py"))
        if not any(p.is_relative_to(exception) for exception in EXCEPTIONS)
    ]


def test_solo_stdlib_en_el_nucleo() -> None:
    modules = _modules()
    assert len(modules) >= 20, "el test no encontró los módulos del paquete"
    offenders = [
        f"{p.relative_to(SRC).as_posix()}:{line}: {name}"
        for p in modules
        for line, name in _imports(p)
        if name not in ALLOWED
    ]
    assert not offenders, "imports fuera de la biblioteca estándar:\n" + "\n".join(offenders)


def test_el_detector_encuentra_dependencias_externas(tmp_path: Path) -> None:
    module = tmp_path / "x.py"
    module.write_text("import os\nimport yaml\nfrom requests import get\nfrom . import local\n", encoding="utf-8")
    assert [name for _, name in _imports(module) if name not in ALLOWED] == ["yaml", "requests"]
