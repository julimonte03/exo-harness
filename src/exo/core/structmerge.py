"""Merge por clave en archivos JSON, sin tocar el resto.

Se usa para registrar el motor en configs de agentes (por ejemplo su entrada
dentro de `mcpServers` en `.mcp.json`). Conserva orden de claves, indentación
detectada, fines de línea y si el archivo terminaba en salto de línea. Si el
archivo no es JSON estricto (por ejemplo JSONC con comentarios), da
`StructMergeError` y no lo modifica: quien llama imprime el snippet para pegar.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from exo.core import fsutil


class StructMergeError(ValueError):
    """El archivo o la clave no permiten un merge seguro."""


class _Missing:
    def __repr__(self) -> str:
        return "MISSING"


MISSING: Any = _Missing()
_INDENT = re.compile(r"^\{\s*?\r?\n([ \t]+)\S")


def _keys(dotted_key: str) -> list[str]:
    parts = dotted_key.split(".")
    if not dotted_key or any(not part for part in parts):
        raise StructMergeError(f"clave inválida: {dotted_key!r} (formato a.b.c)")
    return parts


def _load(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        raw = fsutil.read_bytes(path)
    except FileNotFoundError:
        return {}, None
    try:
        text = raw.decode("utf-8-sig")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StructMergeError(
            f"{path} no es JSON válido ({exc}); si tiene comentarios (JSONC), "
            "agregá la entrada a mano. No se modificó."
        ) from exc
    if not isinstance(data, dict):
        raise StructMergeError(f"{path}: la raíz tiene que ser un objeto JSON; no se modificó")
    return data, text


def _dump(data: dict[str, Any], original: str | None) -> bytes:
    indent: str | int = 2
    newline = "\n"
    trailing = True
    if original is not None:
        match = _INDENT.match(original.lstrip("﻿"))
        if match:
            indent = match.group(1)
        if "\r\n" in original:
            newline = "\r\n"
        trailing = original.endswith("\n")
    text = json.dumps(data, indent=indent, ensure_ascii=False)
    if newline != "\n":
        text = text.replace("\n", newline)
    return (text + (newline if trailing else "")).encode("utf-8")


def _parent(data: dict[str, Any], keys: list[str], path: Path, *, create: bool) -> Any:
    node: Any = data
    for depth, key in enumerate(keys[:-1]):
        if key not in node:
            if not create:
                return MISSING
            node[key] = {}
        node = node[key]
        if not isinstance(node, dict):
            where = ".".join(keys[: depth + 1])
            raise StructMergeError(f"{path}: {where} no es un objeto; no se modificó")
    return node


def get_json_key(path: Path, dotted_key: str) -> Any:
    keys = _keys(dotted_key)
    data, _ = _load(path)
    node: Any = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return MISSING
        node = node[key]
    return node


def merge_json_key(path: Path, dotted_key: str, value: Any) -> bool:
    """Escribe `value` en `dotted_key`. Devuelve si el archivo cambió."""
    keys = _keys(dotted_key)
    data, original = _load(path)
    parent = _parent(data, keys, path, create=True)
    if keys[-1] in parent and parent[keys[-1]] == value and original is not None:
        return False
    parent[keys[-1]] = value
    return fsutil.write_if_changed(path, _dump(data, original))


def remove_json_key(path: Path, dotted_key: str, *, prune_empty: bool = False) -> bool:
    """Quita `dotted_key`. Con `prune_empty`, también los padres que queden vacíos."""
    keys = _keys(dotted_key)
    if not Path(path).exists():
        return False
    data, original = _load(path)
    parent = _parent(data, keys, path, create=False)
    if parent is MISSING or keys[-1] not in parent:
        return False
    del parent[keys[-1]]
    if prune_empty:
        # De adentro hacia afuera: borra cada padre que haya quedado vacío.
        for depth in range(len(keys) - 1, 0, -1):
            container: Any = data
            for key in keys[: depth - 1]:
                container = container[key]
            if container.get(keys[depth - 1]) != {}:
                break
            del container[keys[depth - 1]]
    return fsutil.write_if_changed(path, _dump(data, original))
