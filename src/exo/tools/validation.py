"""Validación de entradas antes de tocar el filesystem (control S2).

La usan por igual el CLI y el servidor MCP: toda tool valida sus argumentos acá
antes de leer nada. Los errores son `InputError`, que el servidor MCP devuelve
como resultado con `isError: true`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from exo.core import tickets

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SKILL_NAME = 64


class InputError(ValueError):
    """Argumento inválido: se rechaza antes de tocar el filesystem."""


def validate_skill_name(value: Any) -> str:
    if not isinstance(value, str) or not SKILL_NAME.match(value) or len(value) > MAX_SKILL_NAME:
        raise InputError(
            f"invalid skill name: {value!r} "
            f"(lowercase kebab-case, up to {MAX_SKILL_NAME} characters)"
        )
    return value


def validate_change_name(value: Any) -> str:
    """Nombre de carpeta seguro: el ticket normalizado puede tener mayúsculas o dígitos (D-26)."""
    if not tickets.is_segment(value):
        raise InputError(
            f"invalid change name: {value!r} (letters, digits and single hyphens, such as "
            f"PROJ-123-add-login or add-login; up to {tickets.MAX_CHANGE_NAME} characters)"
        )
    return value


def validate_cwd(value: Any, *, root: Path | None = None) -> Path:
    """Directorio existente; si hay `root`, tiene que quedar dentro (resolve + is_relative_to)."""
    if not isinstance(value, str) or not value or "\x00" in value:
        raise InputError(f"invalid directory: {value!r}")
    base = root.resolve() if root is not None else None
    candidate = Path(value)
    if base is not None and not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()
    if base is not None and not resolved.is_relative_to(base):
        raise InputError(f"directory {value!r} is outside the project {base}")
    if not resolved.is_dir():
        raise InputError(f"directory {value!r} does not exist")
    return resolved


def check_arguments(schema: dict[str, Any], arguments: Any) -> dict[str, Any]:
    """Subconjunto de JSON Schema que usan las tools: objeto plano de string (con
    `minLength`/`maxLength`), integer (con `minimum`/`maximum`), boolean y enum."""
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise InputError("arguments must be an object")
    properties: dict[str, Any] = schema.get("properties", {})
    unknown = sorted(set(arguments) - set(properties))
    if unknown:
        raise InputError(f"unknown arguments: {', '.join(unknown)}")
    for name in schema.get("required", []):
        if name not in arguments:
            raise InputError(f"missing argument {name!r}")
    for name, value in arguments.items():
        spec = properties[name]
        expected = spec.get("type")
        if expected == "string" and not isinstance(value, str):
            raise InputError(f"{name} must be a string")
        if expected == "string" and len(value) < spec.get("minLength", 0):
            raise InputError(f"{name} must be at least {spec['minLength']} characters long")
        if expected == "string" and "maxLength" in spec and len(value) > spec["maxLength"]:
            raise InputError(f"{name} exceeds {spec['maxLength']} characters")
        if expected == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            raise InputError(f"{name} must be an integer")
        if expected == "integer":
            low, high = spec.get("minimum"), spec.get("maximum")
            if (low is not None and value < low) or (high is not None and value > high):
                raise InputError(f"{name} must be between {low} and {high}")
        if expected == "boolean" and not isinstance(value, bool):
            raise InputError(f"{name} must be true or false")
        if "enum" in spec and value not in spec["enum"]:
            raise InputError(f"{name} must be one of: {', '.join(spec['enum'])}")
    return arguments
