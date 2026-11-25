"""Las 15 tools de memoria (criterio 8 de F3).

Los `inputSchema` son definiciones propias. Cada tool abre la base, hace
su operación y la cierra, así el CLI y el servidor MCP pueden trabajar a la vez
(WAL). Sin `project`, el proyecto se detecta desde `cwd` (`git remote origin`
normalizado, o `local/<carpeta>`).
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from exo.memory import projects
from exo.memory.model import (
    COMMON_TYPES,
    MAX_CONTENT,
    MAX_TITLE,
    SCOPES,
    SEARCH_MODES,
    Observation,
)
from exo.memory.store import MAX_LIMIT, MemoryStore
from exo.tools.base import CWD, Context, Tool, project_dir, schema

_PROJECT = {
    "project": {
        "type": "string",
        "maxLength": 300,
        "description": "memory project; detected from cwd if missing",
    }
}
_ALL = {"all_projects": {"type": "boolean", "description": "across all projects"}}
_FILTERS = {
    "type": {"type": "string", "description": f"type ({', '.join(COMMON_TYPES)}…)"},
    "scope": {"type": "string", "enum": list(SCOPES)},
}
MAX_ID = 2**63 - 1  # el mayor entero de SQLite
_LIMIT = {"limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT}}
_ID = {
    "id": {
        "type": "integer",
        "minimum": 1,
        "maximum": MAX_ID,
        "description": "observation id",
    }
}
_SESSION = {"session_id": {"type": "integer", "minimum": 1, "maximum": MAX_ID}}


def _open(context: Context) -> MemoryStore:
    return MemoryStore(context.memory_db)


def _detected(context: Context, args: dict[str, Any]) -> projects.DetectedProject:
    return projects.detect(project_dir(context, args))


def _resolved(store: MemoryStore, found: projects.DetectedProject) -> str:
    """Sin remoto, dos repos con la misma carpeta (`a/api` y `b/api`) no comparten memoria:
    el primero se queda con `local/api` y el otro suma un hash de su ruta."""
    if found.source != "folder":
        return found.name
    known = store.project_path(found.name)
    if known is None or os.path.normcase(known) == os.path.normcase(str(found.path)):
        return found.name
    digest = hashlib.sha256(os.path.normcase(str(found.path)).encode("utf-8")).hexdigest()
    return f"{found.name}-{digest[:8]}"


def _project(context: Context, args: dict[str, Any], store: MemoryStore) -> str:
    """Proyecto pedido o detectado; si se detecta, queda registrado con su remoto."""
    if "project" in args:
        return str(args["project"])
    found = _detected(context, args)
    name = _resolved(store, found)
    store.register_project(name, remote=found.remote, path=found.path)
    return name


def _scoped(context: Context, args: dict[str, Any], store: MemoryStore) -> str | None:
    return None if args.get("all_projects") else _project(context, args, store)


def _summary(obs: Observation) -> dict[str, Any]:
    data = asdict(obs)
    data.pop("content")
    data.pop("content_hash")
    return data


def _with(fn: Callable[[MemoryStore, Context, dict[str, Any]], Any]) -> Callable[..., Any]:
    def handler(context: Context, args: dict[str, Any]) -> Any:
        with _open(context) as store:
            return fn(store, context, args)

    return handler


# -- observaciones ----------------------------------------------------------------------


def _save(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    result = store.save(
        project=_project(context, args, store) if args.get("scope") != "personal" else "",
        title=args["title"],
        content=args["content"],
        type=args.get("type", "note"),
        topic_key=args.get("topic_key"),
        scope=args.get("scope", "project"),
        session_id=args.get("session_id"),
    )
    return {
        "id": result.id,
        "action": result.action,
        "similar": [asdict(hit) for hit in result.similar],
    }


def _search(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    project = _scoped(context, args, store)
    result = store.query(
        args["query"],
        project=project,
        type=args.get("type"),
        scope=args.get("scope"),
        limit=args.get("limit", 10),
        mode=args.get("mode", "auto"),
    )
    return {
        "project": project,
        "mode": result.mode,
        "note": result.note,
        "results": [asdict(hit) for hit in result.hits],
    }


def _list(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    project = _scoped(context, args, store)
    items = store.list(
        project,
        type=args.get("type"),
        scope=args.get("scope"),
        limit=args.get("limit", 20),
        offset=args.get("offset", 0),
    )
    return {"project": project, "observations": [_summary(obs) for obs in items]}


def _get(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    return asdict(store.get(args["id"]))


def _context(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    project = _project(context, args, store)
    return {"project": project, "context": store.context(project, limit=args.get("limit", 10))}


def _delete(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    deleted = store.delete(args["id"])
    if not deleted:
        store.get(args["id"])  # NotFoundError con el mensaje de siempre
    return {"id": args["id"], "deleted": deleted}


# -- sesiones ---------------------------------------------------------------------------


def _session_start(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    return asdict(store.session_start(_project(context, args, store), agent=args.get("agent")))


def _session_end(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    return asdict(store.session_end(args["session_id"], summary=args.get("summary")))


def _session_summary(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    session_id = args.get("session_id")
    if session_id is not None:
        project = store.session_show(session_id).session.project
    else:
        project = _project(context, args, store)
    return asdict(store.session_summary(project, args["content"], session_id=session_id))


def _session_show(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    session_id = args.get("session_id")
    project = None if session_id is not None else _scoped(context, args, store)
    view = store.session_show(session_id, project=project)
    return {
        "session": asdict(view.session),
        "observations": [_summary(obs) for obs in view.observations],
    }


# -- proyectos y stats --------------------------------------------------------------------


def _projects_list(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    return {"projects": [asdict(info) for info in store.projects_list()]}


def _projects_merge(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    return asdict(store.projects_merge(args["source"], args["target"]))


def _projects_consolidate(
    store: MemoryStore, context: Context, args: dict[str, Any]
) -> dict[str, Any]:
    dry_run = bool(args.get("dry_run", False))
    return {"dry_run": dry_run, "merges": store.projects_consolidate(dry_run=dry_run)}


def _stats(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    return asdict(store.stats())


def _detect_project(store: MemoryStore, context: Context, args: dict[str, Any]) -> dict[str, Any]:
    found = _detected(context, args)
    return {
        "name": _resolved(store, found),
        "source": found.source,
        "remote": found.remote,
        "path": str(found.path),
    }


TOOLS: tuple[Tool, ...] = (
    Tool(
        "mem_save",
        "Saves an observation (decision, fixed bug, discovery). With topic_key, "
        "updates the existing one instead of duplicating it.",
        schema(
            {
                **CWD,
                **_PROJECT,
                "title": {"type": "string", "minLength": 1, "maxLength": MAX_TITLE},
                "content": {"type": "string", "minLength": 1, "maxLength": MAX_CONTENT},
                "type": _FILTERS["type"],
                "topic_key": {"type": "string", "maxLength": 200},
                "scope": _FILTERS["scope"],
                **_SESSION,
            },
            ["title", "content"],
        ),
        _with(_save),
        ("mem", "save"),
    ),
    Tool(
        "mem_search",
        "Searches the memory and returns previews; get the full content with mem_get.",
        schema(
            {
                **CWD,
                **_PROJECT,
                **_ALL,
                "query": {"type": "string", "minLength": 1, "maxLength": 1000},
                "mode": {
                    "type": "string",
                    "enum": list(SEARCH_MODES),
                    "description": "auto: hybrid if there is a semantic index, otherwise lexical",
                },
                **_FILTERS,
                **_LIMIT,
            },
            ["query"],
        ),
        _with(_search),
        ("mem", "search"),
    ),
    Tool(
        "mem_list",
        "Lists the most recent observations, without their content.",
        schema(
            {
                **CWD,
                **_PROJECT,
                **_ALL,
                **_FILTERS,
                **_LIMIT,
                "offset": {"type": "integer", "minimum": 0, "maximum": MAX_ID},
            }
        ),
        _with(_list),
        ("mem", "list"),
    ),
    Tool(
        "mem_get",
        "Gets a full observation by id.",
        schema(_ID, ["id"]),
        _with(_get),
        ("mem", "get"),
    ),
    Tool(
        "mem_context",
        "Recent project context to start a session: latest observations and last summary.",
        schema({**CWD, **_PROJECT, **_LIMIT}),
        _with(_context),
        ("mem", "context"),
    ),
    Tool(
        "mem_delete",
        "Deletes an observation by id.",
        schema(_ID, ["id"]),
        _with(_delete),
        ("mem", "delete"),
    ),
    Tool(
        "mem_session_start",
        "Opens a work session in the project.",
        schema({**CWD, **_PROJECT, "agent": {"type": "string", "maxLength": 100}}),
        _with(_session_start),
        ("mem", "session", "start"),
    ),
    Tool(
        "mem_session_end",
        "Closes a session, optionally with its summary.",
        schema(
            {**_SESSION, "summary": {"type": "string", "maxLength": MAX_CONTENT}},
            ["session_id"],
        ),
        _with(_session_end),
        ("mem", "session", "end"),
    ),
    Tool(
        "mem_session_summary",
        "Saves the session summary (in the project's most recent open session, or a new one).",
        schema(
            {
                **CWD,
                **_PROJECT,
                **_SESSION,
                "content": {"type": "string", "minLength": 1, "maxLength": MAX_CONTENT},
            },
            ["content"],
        ),
        _with(_session_summary),
        ("mem", "session", "summary"),
    ),
    Tool(
        "mem_session_show",
        "Shows a session with its summary and observations; without an id, the most recent one.",
        schema({**CWD, **_PROJECT, **_ALL, **_SESSION}),
        _with(_session_show),
        ("mem", "session", "show"),
    ),
    Tool(
        "mem_projects_list",
        "Lists the memory projects, with their observation and session counts.",
        schema(),
        _with(_projects_list),
        ("mem", "projects", "list"),
    ),
    Tool(
        "mem_projects_merge",
        "Moves everything from one project to another; if a topic_key is in both, the most "
        "recent one is kept.",
        schema(
            {
                "source": {"type": "string", "minLength": 1, "maxLength": 300},
                "target": {"type": "string", "minLength": 1, "maxLength": 300},
            },
            ["source", "target"],
        ),
        _with(_projects_merge),
        ("mem", "projects", "merge"),
    ),
    Tool(
        "mem_projects_consolidate",
        "Merges the projects that are variants of the same git remote.",
        schema({"dry_run": {"type": "boolean", "description": "only show what would be merged"}}),
        _with(_projects_consolidate),
        ("mem", "projects", "consolidate"),
    ),
    Tool(
        "mem_stats",
        "Memory statistics: counts (total, by type and by project) and size.",
        schema(),
        _with(_stats),
        ("mem", "stats"),
    ),
    Tool(
        "mem_detect_project",
        "Detects the memory project from cwd (normalized git remote origin).",
        schema(CWD),
        _with(_detect_project),
        ("mem", "projects", "detect"),
    ),
)
