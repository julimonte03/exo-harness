"""Merge por clave en archivos JSON, sin tocar el resto.

Se usa para registrar el motor en configs de agentes (por ejemplo su entrada
dentro de `mcpServers` en `.mcp.json`). Conserva orden de claves, indentación
detectada, fines de línea y si el archivo terminaba en salto de línea. Si el
archivo no es JSON estricto (por ejemplo JSONC con comentarios), da
`StructMergeError` y no lo modifica: quien llama imprime el snippet para pegar.
"""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal
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


_BOM = chr(0xFEFF)


class _Lossy(ValueError):
    """Reescribir el archivo perdería o alteraría datos."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _Lossy(f"la clave {key!r} está repetida y una de las dos se perdería")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise _Lossy(f"{name} no es JSON estándar")


def _exact_float(text: str) -> float:
    value = float(text)
    if math.isinf(value) or Decimal(text) != Decimal(repr(value)):
        raise _Lossy(f"el número {text} perdería precisión al reescribirlo")
    return value


def _load(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        raw = fsutil.read_bytes(path)
    except FileNotFoundError:
        return {}, None
    try:
        text = raw.decode("utf-8")
        data = json.loads(
            text.removeprefix(_BOM),
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
            parse_float=_exact_float,
        )
    except _Lossy as exc:
        raise StructMergeError(f"{path}: {exc}; editalo a mano. No se modificó.") from exc
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
    bom = ""
    if original is not None:
        bom = _BOM if original.startswith(_BOM) else ""
        match = _INDENT.match(original.removeprefix(_BOM))
        if match:
            indent = match.group(1)
        if "\r\n" in original:
            newline = "\r\n"
        trailing = original.endswith("\n")
    try:
        text = json.dumps(data, indent=indent, ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise StructMergeError(f"el valor no se puede escribir como JSON estándar ({exc})") from exc
    if newline != "\n":
        text = text.replace("\n", newline)
    return (bom + text + (newline if trailing else "")).encode("utf-8")


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
        _prune(data, keys)
    return fsutil.write_if_changed(path, _dump(data, original))


def _prune(data: dict[str, Any], keys: list[str]) -> None:
    """De adentro hacia afuera, borra cada padre de `keys` que haya quedado vacío."""
    for depth in range(len(keys) - 1, 0, -1):
        container: Any = data
        for key in keys[: depth - 1]:
            container = container[key]
        if container.get(keys[depth - 1]) != {}:
            break
        del container[keys[depth - 1]]


def add_json_list_item(path: Path, dotted_key: str, item: Any) -> bool:
    """Agrega `item` a la lista en `dotted_key` si no está. No toca los demás ítems."""
    keys = _keys(dotted_key)
    data, original = _load(path)
    parent = _parent(data, keys, path, create=True)
    current = parent.get(keys[-1], MISSING)
    if current is MISSING:
        parent[keys[-1]] = [item]
    elif not isinstance(current, list):
        raise StructMergeError(f"{path}: {dotted_key} no es una lista; no se modificó")
    elif item in current:
        return False
    else:
        current.append(item)
    return fsutil.write_if_changed(path, _dump(data, original))


def remove_json_list_item(
    path: Path, dotted_key: str, item: Any, *, prune_empty: bool = False
) -> bool:
    """Quita `item` de la lista. Con `prune_empty`, si la lista queda vacía, la quita a ella
    y a los padres vacíos."""
    keys = _keys(dotted_key)
    if not Path(path).exists():
        return False
    data, original = _load(path)
    parent = _parent(data, keys, path, create=False)
    if parent is MISSING or not isinstance(parent.get(keys[-1]), list):
        return False
    current = parent[keys[-1]]
    if item not in current:
        return False
    current.remove(item)
    if prune_empty and not current:
        del parent[keys[-1]]
        _prune(data, keys)
    return fsutil.write_if_changed(path, _dump(data, original))
