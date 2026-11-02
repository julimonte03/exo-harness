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
_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
_LOOSE = re.compile(r"[:,]\s")


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
    indent: str | int | None = 2
    newline = "\n"
    trailing = True
    bom = ""
    separators: tuple[str, str] | None = None
    if original is not None:
        bom = _BOM if original.startswith(_BOM) else ""
        body = original.removeprefix(_BOM).strip()
        match = _INDENT.match(original.removeprefix(_BOM))
        if match:
            indent = match.group(1)
        elif "\n" not in body and body != "{}":
            # JSON de una línea: se conserva compacto, con o sin espacios tras ":" y ",".
            indent = None
            loose = _LOOSE.search(_STRING.sub('""', body))
            separators = (", ", ": ") if loose else (",", ":")
        if "\r\n" in original:
            newline = "\r\n"
        trailing = original.endswith("\n")
    try:
        text = json.dumps(
            data, indent=indent, separators=separators, ensure_ascii=False, allow_nan=False
        )
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


def get_json_key(path: Path, dotted_key: str, *, strict: bool = False) -> Any:
    """Valor en `dotted_key`, o MISSING. Con `strict`, un padre que existe y no es un
    objeto es un error: ahí no se podría escribir la clave."""
    keys = _keys(dotted_key)
    data, _ = _load(path)
    node: Any = data
    for depth, key in enumerate(keys):
        if not isinstance(node, dict):
            if strict:
                where = ".".join(keys[:depth])
                raise StructMergeError(f"{path}: {where} no es un objeto; no se modificó")
            return MISSING
        if key not in node:
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


def missing_containers(path: Path, dotted_key: str, *, leaf: bool) -> list[str]:
    """Claves (con puntos) que habría que crear para escribir en `dotted_key`: los padres
    que faltan y, con `leaf`, la clave misma (la lista de un ítem). El motor las registra
    para quitar al desinstalar solo los contenedores que creó él."""
    keys = _keys(dotted_key)
    data, _ = _load(path)
    upto = len(keys) if leaf else len(keys) - 1
    node: Any = data
    for depth in range(upto):
        if not isinstance(node, dict) or keys[depth] not in node:
            return [".".join(keys[: d + 1]) for d in range(depth, upto)]
        node = node[keys[depth]]
    return []


def prune_empty_keys(path: Path, dotted_keys: list[str]) -> bool:
    """Quita, de la más profunda a la menos, cada clave de `dotted_keys` que exista y sea
    un objeto o una lista vacíos. Devuelve si el archivo cambió."""
    if not Path(path).exists():
        return False
    data, original = _load(path)
    changed = False
    for dotted in sorted(set(dotted_keys), key=lambda k: k.count("."), reverse=True):
        keys = _keys(dotted)
        parent: Any = data
        for key in keys[:-1]:
            parent = parent.get(key) if isinstance(parent, dict) else None
        if isinstance(parent, dict) and keys[-1] in parent and parent[keys[-1]] in ({}, []):
            del parent[keys[-1]]
            changed = True
    return changed and fsutil.write_if_changed(path, _dump(data, original))


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
