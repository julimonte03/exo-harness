"""Validador mínimo de JSON Schema, solo con biblioteca estándar (invariante 1).

Cubre el subconjunto que usan los esquemas del motor (por ahora el AI Usage
Record): `type` (uno o una lista), `required`, `properties`,
`additionalProperties` (booleano o esquema), `items`, `enum`, `minItems`,
`minLength`, `maxLength`, `pattern` (con `re.search`, como el estándar) y
`minimum`. Las anotaciones (`$schema`, `$id`, `title`, `description`,
`examples`, `default`) se aceptan y no validan nada.

Una palabra clave fuera de ese subconjunto es un error del esquema y no se
ignora: así un esquema nuevo no pasa por válido sin que nadie lo chequee.
Los errores llevan la ruta del valor (`$.capabilities_used[0].name: …`).
"""

from __future__ import annotations

import re
from typing import Any

ANNOTATIONS = frozenset({"$schema", "$id", "title", "description", "examples", "default"})
KEYWORDS = frozenset(
    {
        "type",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "enum",
        "minItems",
        "minLength",
        "maxLength",
        "pattern",
        "minimum",
    }
)
_TYPES = ("object", "array", "string", "integer", "number", "boolean", "null")


class SchemaError(ValueError):
    """El esquema usa algo que este validador no soporta o está mal formado."""


def check_schema(schema: Any, path: str = "#") -> None:
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: a schema must be an object")
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        raise SchemaError(f"{path}: unsupported keyword(s): {', '.join(sorted(unknown))}")
    types = schema.get("type")
    for name in [types] if isinstance(types, str) else types or []:
        if name not in _TYPES:
            raise SchemaError(f"{path}: unknown type {name!r}")
    for key, sub in (schema.get("properties") or {}).items():
        check_schema(sub, f"{path}/properties/{key}")
    if isinstance(schema.get("additionalProperties"), dict):
        check_schema(schema["additionalProperties"], f"{path}/additionalProperties")
    if "items" in schema:
        check_schema(schema["items"], f"{path}/items")
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except (re.error, TypeError) as exc:
            raise SchemaError(f"{path}: invalid pattern ({exc})") from exc


def _is(value: Any, name: str) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    return value is None


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _check(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    types = schema.get("type")
    if types is not None:
        names = [types] if isinstance(types, str) else list(types)
        if not any(_is(value, name) for name in names):
            errors.append(f"{path}: must be of type {' or '.join(names)}")
            return
    if "enum" in schema and value not in schema["enum"]:
        options = ", ".join(str(option) for option in schema["enum"])
        errors.append(f"{path}: must be one of: {options}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: must have at least {_plural(schema['minLength'], 'character')}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: must have at most {_plural(schema['maxLength'], 'character')}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: must match {schema['pattern']}")
    if _is(value, "number") and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: must be ≥ {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: must have at least {_plural(schema['minItems'], 'item')}")
        if "items" in schema:
            for index, item in enumerate(value):
                _check(item, schema["items"], f"{path}[{index}]", errors)
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                _check(item, properties[key], f"{path}.{key}", errors)
            elif extra is False:
                errors.append(f"{path}: unexpected property {key!r}")
            elif isinstance(extra, dict):
                _check(item, extra, f"{path}.{key}", errors)


def validate(value: Any, schema: dict[str, Any]) -> list[str]:
    """Devuelve la lista de errores (vacía si el valor cumple el esquema)."""
    check_schema(schema)
    errors: list[str] = []
    _check(value, schema, "$", errors)
    return errors
