"""Subcomandos del CLI. Cada módulo expone `register(subparsers)`.

Los módulos se importan cuando hacen falta (F8): con un subcomando conocido, solo el que
lo registra; con `--version`, ninguno; para la ayuda general, o con un nombre que no está
en la tabla, todos. Así
`exo sync` no carga la memoria, el validador ni los gates, y el arranque de cada
llamada (la de una persona o la de un agente) es más corto.
"""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Iterable, Sequence

# Módulo -> subcomandos de primer nivel que registra, en el orden de la ayuda. Un
# subcomando nuevo va acá: `tests/test_cli.py` compara la tabla con lo que registra cada
# módulo. Si falta, el CLI lo encuentra igual (carga todos), pero arranca más lento.
MODULES: dict[str, tuple[str, ...]] = {
    "version": ("version",),
    "inject": ("inject",),
    "backups": ("backups", "restore"),
    "registry": ("registry",),
    "fitness": ("fitness",),
    "speclint": ("speclint",),
    "specs": ("specs",),
    "check": ("check",),
    "hook": ("hook",),
    "gate": ("gate",),
    "governance": ("p0", "codeowners"),
    "validate": ("validate",),
    "tools": ("skills", "change", "discover", "mcp"),
    "doctor": ("doctor",),
    "project": ("init", "sync", "update", "status", "add-agent", "remove-agent", "uninstall"),
    "memory": ("mem",),
    "persona": ("persona",),
}


def needed(argv: Sequence[str]) -> list[str]:
    """Los módulos que hacen falta para `argv`: ninguno para `--version` (argparse responde
    antes de mirar los subcomandos), el del subcomando pedido, o todos (la ayuda general, o
    un nombre que no está en la tabla, para que argparse dé su error con la lista)."""
    first = list(argv[:1])
    if first == ["--version"]:
        return []
    for module, names in MODULES.items():
        if first and first[0] in names:
            return [module]
    return list(MODULES)


def register(sub: argparse._SubParsersAction, modules: Iterable[str] | None = None) -> None:
    """Registra los subcomandos de `modules` (por defecto, todos) en el orden de la tabla."""
    for module in MODULES if modules is None else modules:
        importlib.import_module(f"{__name__}.{module}").register(sub)
