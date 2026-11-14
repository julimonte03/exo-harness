"""Registro único de las capacidades del motor (ADR-0005).

Cada tool se define una sola vez, con nombre, descripción, `inputSchema` y un
handler puro que devuelve un objeto serializable. El CLI (`exo skills …`,
`exo change …`) y el servidor MCP opcional consumen este mismo registro, así
que validan igual (S2) y responden igual. `cli` indica el subcomando
equivalente; un test de paridad verifica que exista. Las tools de memoria
(F3) viven en `exo.tools.memory`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from exo import content, packs
from exo.core import frontmatter, fsutil
from exo.sdd import observability
from exo.tools import memory
from exo.tools.base import CWD as _CWD
from exo.tools.base import Context, Tool
from exo.tools.base import project_dir as _project
from exo.tools.base import schema as _schema
from exo.tools.validation import (
    InputError,
    check_arguments,
    validate_change_name,
    validate_skill_name,
)

__all__ = ["TOOLS", "Context", "InputError", "Tool", "call", "get"]

DEFAULT_SKILLS_TARGET = ".agents/skills"


_CHANGE = {"change_name": {"type": "string", "description": "change name ([PREFIX-123-]slug)"}}


# -- skills -------------------------------------------------------------------


def _collection() -> tuple[Path, packs.Collection]:
    root = content.content_root()
    return root, packs.load_collection(root)


def _skill_summary(skill: packs.Skill, root: Path) -> dict[str, Any]:
    return {
        "name": skill.name,
        "pack": skill.pack,
        "description": skill.description,
        "path": skill.path.relative_to(root).as_posix(),
    }


def _skills_list(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    root, collection = _collection()
    pack = args.get("pack")
    if pack is not None and pack not in collection.packs:
        raise InputError(f"pack {pack!r} not found")
    skills = [s for s in collection.skills if pack is None or s.pack == pack]
    return {"skills": [_skill_summary(s, root) for s in sorted(skills, key=lambda s: s.name)]}


def _skill_info(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    name = validate_skill_name(args["name"])
    root, collection = _collection()
    skill = next((s for s in collection.skills if s.name == name), None)
    if skill is None:
        raise InputError(f"skill {name!r} not found")
    data, body = frontmatter.parse((skill.path / packs.SKILL_FILE).read_text(encoding="utf-8"))
    files = [p.relative_to(skill.path).as_posix() for p in fsutil.walk_files(skill.path)]
    return {
        **_skill_summary(skill, root),
        "metadata": skill.metadata,
        "frontmatter": data,
        "files": files,
        "body_lines": len(body.splitlines()),
    }


def _hashes(folder: Path) -> dict[str, str]:
    # Sin seguir links: un junction dentro del destino no filtra archivos de afuera.
    return {
        p.relative_to(folder).as_posix(): fsutil.sha256_file(p) for p in fsutil.walk_files(folder)
    }


def _skills_diff(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    project = _project(context, args)
    target_arg = args.get("target", DEFAULT_SKILLS_TARGET)
    try:
        target = fsutil.resolve_within(project, target_arg)
    except fsutil.UnsafePathError as exc:
        raise InputError(str(exc)) from exc
    _, collection = _collection()
    source = {s.name: s.path for s in collection.skills}
    installed = {s.name: s.path for s in packs.discover_skills(target)} if target.is_dir() else {}
    result: dict[str, list[Any]] = {"added": [], "changed": [], "removed": [], "unchanged": []}
    for name in sorted(set(source) | set(installed)):
        if name not in installed:
            result["added"].append(name)
        elif name not in source:
            result["removed"].append(name)
        else:
            left, right = _hashes(source[name]), _hashes(installed[name])
            files = sorted(f for f in set(left) | set(right) if left.get(f) != right.get(f))
            if files:
                result["changed"].append({"name": name, "files": files})
            else:
                result["unchanged"].append(name)
    return {"target": target.relative_to(project).as_posix(), **result}


# -- observabilidad -----------------------------------------------------------


def _wrap(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except observability.ObservabilityError as exc:
        raise InputError(str(exc)) from exc


def _list_changes(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    project = _project(context, args)
    include = args.get("include_archived", True)
    changes = observability.find_changes(project, include_archived=include)
    return {
        "changes": [
            {
                "name": c.name,
                "epic": c.epic,
                "path": c.path,
                "archived": c.archived,
                "archived_on": c.archived_on,
                "phase": c.phase,
            }
            for c in changes
        ]
    }


def _get_change_state(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    name = validate_change_name(args["change_name"])
    project = _project(context, args)
    return _wrap(lambda: observability.change_state(project, name))


def _get_followups(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    name = validate_change_name(args["change_name"])
    project = _project(context, args)
    status = args.get("status", "open")
    items = _wrap(lambda: observability.followups(project, name, status))
    return {"change_name": name, "status": status, "followups": items}


def _get_ai_usage_record(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    name = validate_change_name(args["change_name"])
    project = _project(context, args)
    return {"change_name": name, **_wrap(lambda: observability.ai_usage_record(project, name))}


TOOLS: tuple[Tool, ...] = (
    Tool(
        "skills_list",
        "Lists the skills in the engine content, optionally from one pack.",
        _schema({"pack": {"type": "string", "description": "filter by pack"}}),
        _skills_list,
        ("skills", "list"),
    ),
    Tool(
        "skill_info",
        "Details of a skill: frontmatter, metadata and files.",
        _schema({"name": {"type": "string", "description": "skill name"}}, ["name"]),
        _skill_info,
        ("skills", "info"),
    ),
    Tool(
        "skills_diff",
        "Compares the engine skills with the ones installed in a project directory.",
        _schema(
            {
                **_CWD,
                "target": {
                    "type": "string",
                    "description": (
                        f"skills directory relative to the project ({DEFAULT_SKILLS_TARGET})"
                    ),
                },
            }
        ),
        _skills_diff,
        ("skills", "diff"),
    ),
    Tool(
        "list_changes",
        "Lists the project's SDD changes with their phase (read-only).",
        _schema(
            {**_CWD, "include_archived": {"type": "boolean", "description": "include archive/"}}
        ),
        _list_changes,
        ("change", "list"),
    ),
    Tool(
        "get_change_state",
        "State of a change: phase, artifacts, ticket, attribution and followups (read-only).",
        _schema({**_CWD, **_CHANGE}, ["change_name"]),
        _get_change_state,
        ("change", "status"),
    ),
    Tool(
        "get_followups",
        "Judge followups of a change, filtered by status (read-only).",
        _schema(
            {
                **_CWD,
                **_CHANGE,
                "status": {"type": "string", "enum": list(observability.FOLLOWUP_STATUSES)},
            },
            ["change_name"],
        ),
        _get_followups,
        ("change", "followups"),
    ),
    Tool(
        "get_ai_usage_record",
        "AI Usage Record of a change, with ticket and attribution version (read-only).",
        _schema({**_CWD, **_CHANGE}, ["change_name"]),
        _get_ai_usage_record,
        ("change", "ai-usage"),
    ),
    *memory.TOOLS,
)
_BY_NAME = {tool.name: tool for tool in TOOLS}


def get(name: str) -> Tool | None:
    return _BY_NAME.get(name)


def call(name: str, arguments: Any, context: Context) -> Any:
    """Valida los argumentos (S2) y ejecuta la tool. Errores de entrada: `InputError`."""
    tool = _BY_NAME.get(name)
    if tool is None:
        raise KeyError(name)
    args = check_arguments(tool.input_schema, arguments)
    try:
        return tool.handler(context, args)
    except InputError:
        raise
    except (content.ContentError, ValueError, OSError) as exc:
        # Contenido roto, frontmatter o JSON ilegible, rutas inseguras, disco.
        raise InputError(str(exc)) from exc
    except sqlite3.Error as exc:
        raise InputError(f"memory database error: {exc}") from exc
