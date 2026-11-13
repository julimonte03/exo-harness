"""Las 15 tools de memoria (§5.3 del reporte; criterio 8 de F3).

Los nombres son los del reporte. Los `inputSchema` son definiciones propias: el
apéndice E con los originales nunca se fotografió. Cada tool abre la base, hace
su operación y la cierra, así el CLI y el servidor MCP pueden trabajar a la vez
(WAL). Sin `project`, el proyecto se detecta desde `cwd` (`git remote origin`
normalizado, o `local/<carpeta>`).
"""

from __future__ import annotations

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
        "description": "proyecto de la memoria; si falta, se detecta desde cwd",
    }
}
_ALL = {"all_projects": {"type": "boolean", "description": "en todos los proyectos"}}
_FILTERS = {
    "type": {"type": "string", "description": f"tipo ({', '.join(COMMON_TYPES)}…)"},
    "scope": {"type": "string", "enum": list(SCOPES)},
}
_LIMIT = {"limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT}}
_ID = {"id": {"type": "integer", "minimum": 1, "description": "id de la observación"}}
_SESSION = {"session_id": {"type": "integer", "minimum": 1}}


def _open(context: Context) -> MemoryStore:
    return MemoryStore(context.memory_db)


def _detected(context: Context, args: dict[str, Any]) -> projects.DetectedProject:
    return projects.detect(project_dir(context, args))


def _project(context: Context, args: dict[str, Any], store: MemoryStore) -> str:
    """Proyecto pedido o detectado; si se detecta, queda registrado con su remoto."""
    if "project" in args:
        return str(args["project"])
    found = _detected(context, args)
    store.register_project(found.name, remote=found.remote, path=found.path)
    return found.name


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


def _detect_project(context: Context, args: dict[str, Any]) -> dict[str, Any]:
    found = _detected(context, args)
    return {
        "name": found.name,
        "source": found.source,
        "remote": found.remote,
        "path": str(found.path),
    }


TOOLS: tuple[Tool, ...] = (
    Tool(
        "mem_save",
        "Guarda una observación (decisión, bug resuelto, descubrimiento). Con topic_key, "
        "actualiza la existente en lugar de duplicar.",
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
        "Busca en la memoria y devuelve previews; el contenido completo sale de mem_get.",
        schema(
            {
                **CWD,
                **_PROJECT,
                **_ALL,
                "query": {"type": "string", "minLength": 1, "maxLength": 1000},
                "mode": {
                    "type": "string",
                    "enum": list(SEARCH_MODES),
                    "description": "auto: híbrida si hay índice semántico, si no léxica",
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
        "Lista las observaciones más recientes, sin el contenido.",
        schema(
            {
                **CWD,
                **_PROJECT,
                **_ALL,
                **_FILTERS,
                **_LIMIT,
                "offset": {"type": "integer", "minimum": 0},
            }
        ),
        _with(_list),
        ("mem", "list"),
    ),
    Tool(
        "mem_get",
        "Una observación completa, por id.",
        schema(_ID, ["id"]),
        _with(_get),
        ("mem", "get"),
    ),
    Tool(
        "mem_context",
        "Contexto reciente del proyecto para empezar una sesión: últimas observaciones y "
        "último resumen.",
        schema({**CWD, **_PROJECT, **_LIMIT}),
        _with(_context),
        ("mem", "context"),
    ),
    Tool(
        "mem_delete",
        "Borra una observación por id.",
        schema(_ID, ["id"]),
        _with(_delete),
        ("mem", "delete"),
    ),
    Tool(
        "mem_session_start",
        "Abre una sesión de trabajo en el proyecto.",
        schema({**CWD, **_PROJECT, "agent": {"type": "string", "maxLength": 100}}),
        _with(_session_start),
        ("mem", "session", "start"),
    ),
    Tool(
        "mem_session_end",
        "Cierra una sesión, opcionalmente con su resumen.",
        schema(
            {**_SESSION, "summary": {"type": "string", "maxLength": MAX_CONTENT}},
            ["session_id"],
        ),
        _with(_session_end),
        ("mem", "session", "end"),
    ),
    Tool(
        "mem_session_summary",
        "Guarda el resumen de la sesión (la abierta más reciente del proyecto, o una nueva).",
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
        "Una sesión con su resumen y sus observaciones; sin id, la más reciente.",
        schema({**CWD, **_PROJECT, **_ALL, **_SESSION}),
        _with(_session_show),
        ("mem", "session", "show"),
    ),
    Tool(
        "mem_projects_list",
        "Proyectos de la memoria, con cantidad de observaciones y sesiones.",
        schema(),
        _with(_projects_list),
        ("mem", "projects", "list"),
    ),
    Tool(
        "mem_projects_merge",
        "Mueve todo de un proyecto a otro; si un topic_key está en los dos, queda el más reciente.",
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
        "Une los proyectos que son variantes del mismo remoto de git.",
        schema({"dry_run": {"type": "boolean", "description": "solo muestra qué uniría"}}),
        _with(_projects_consolidate),
        ("mem", "projects", "consolidate"),
    ),
    Tool(
        "mem_stats",
        "Estadísticas de la memoria: cantidades, por tipo y por proyecto, y tamaño.",
        schema(),
        _with(_stats),
        ("mem", "stats"),
    ),
    Tool(
        "mem_detect_project",
        "Proyecto que se detecta desde cwd (git remote origin normalizado).",
        schema(CWD),
        _detect_project,
        ("mem", "projects", "detect"),
    ),
)
