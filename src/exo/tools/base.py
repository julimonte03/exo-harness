"""Tipos comunes de las tools: contexto, definición y helpers de `inputSchema`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exo.tools.validation import validate_cwd


@dataclass(frozen=True)
class Context:
    """Raíz del proyecto sobre la que trabajan las tools (`cwd` no puede salir de acá).

    `memory_db` cambia la base de la memoria (por defecto, la del usuario).
    """

    project: Path
    memory_db: Path | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[Context, dict[str, Any]], Any]
    cli: tuple[str, ...]  # subcomando equivalente, por ejemplo ("mem", "session", "start")

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict:
    result: dict[str, Any] = {
        "type": "object",
        "properties": properties or {},
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


CWD = {"cwd": {"type": "string", "description": "project directory, inside the root"}}


def project_dir(context: Context, args: dict[str, Any]) -> Path:
    if "cwd" in args:
        return validate_cwd(args["cwd"], root=context.project)
    return context.project.resolve()
