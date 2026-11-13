"""`exo mem …`: la memoria del usuario por CLI (mismo registro que el servidor MCP).

`--project` es el proyecto de la memoria (si falta, se detecta desde `--cwd`,
que por defecto es el directorio actual). `export` e `import` son solo del CLI,
como en el reporte.
"""

from __future__ import annotations

import argparse
import json
import locale
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from exo import _meta
from exo.commands._output import emit_json, error
from exo.memory import embeddings, exchange
from exo.memory.model import SEARCH_MODES
from exo.memory.store import MemoryStore
from exo.tools import registry
from exo.tools.validation import InputError

Build = Callable[[argparse.Namespace], dict[str, Any]]
Printer = Callable[[dict[str, Any]], None]
PROVIDER_CHOICES: tuple[str, ...] = ("local", *embeddings.PROVIDERS)


def _opt(**values: Any) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None and v is not False}


def _text(value: str) -> str:
    """`-` lee stdin en UTF-8 (con o sin BOM); si no lo es, con la codificación del sistema."""
    if value != "-":
        return value
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is None:
        return sys.stdin.read()
    data = buffer.read()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode(locale.getpreferredencoding(False), errors="replace")


def _common(parser: argparse.ArgumentParser, *, project: bool = True) -> None:
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.add_argument(
        "--cwd", type=Path, default=Path("."), help="directorio desde el que se detecta el proyecto"
    )
    if project:
        parser.add_argument("--project", help="proyecto de la memoria (si falta, se detecta)")


def _filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--all", action="store_true", help="en todos los proyectos")
    parser.add_argument("--type", help="filtra por tipo")
    parser.add_argument("--scope", choices=("project", "personal"))
    parser.add_argument("--limit", type=int)


def _run(tool: str, build: Build, printer: Printer) -> Callable[[argparse.Namespace], int]:
    def handler(args: argparse.Namespace) -> int:
        try:
            result = registry.call(tool, build(args), registry.Context(args.cwd.resolve()))
        except InputError as exc:
            return error(str(exc))
        if args.json:
            emit_json(result)
        else:
            printer(result)
        return 0

    return handler


# -- salida humana -----------------------------------------------------------------------


def _print_hits(result: dict[str, Any]) -> None:
    if result.get("note"):
        print(f"nota: {result['note']}", file=sys.stderr)
    items = result.get("results", result.get("observations", []))
    for item in items:
        where = item["project"] or "personal"
        print(f"#{item['id']}\t[{item['type']}]\t{item['title']}\t{where}")
        if item.get("preview"):
            print(f"\t{item['preview']}")
    if not items:
        print("sin resultados")


def _print_saved(result: dict[str, Any]) -> None:
    print(f"guardada #{result['id']} ({result['action']})")
    for hit in result.get("similar", []):
        print(f"parecida: #{hit['id']} {hit['title']} (similitud {hit['score']:.2f})")
    if result.get("similar"):
        print("si es lo mismo, actualizá esa en lugar de tener dos; si se contradicen, preguntá")


def _print_observation(obs: dict[str, Any]) -> None:
    key = f" · {obs['topic_key']}" if obs["topic_key"] else ""
    print(f"#{obs['id']} [{obs['type']}] {obs['title']}{key}")
    where = obs["project"] or "personal"
    print(f"proyecto: {where} · revisión {obs['revision']} · {obs['updated_at']}")
    print()
    print(obs["content"])


def _print_session(result: dict[str, Any]) -> None:
    session = result.get("session", result)
    state = f"cerrada {session['ended_at']}" if session["ended_at"] else "abierta"
    print(f"sesión #{session['id']} · {session['project']} · {state}")
    if session.get("summary"):
        print(f"resumen: {session['summary']}")
    for obs in result.get("observations", []):
        print(f"  #{obs['id']} [{obs['type']}] {obs['title']}")


def _print_projects(result: dict[str, Any]) -> None:
    for info in result["projects"]:
        print(
            f"{info['name']}\t{info['observations']} observaciones\t{info['sessions']} sesiones"
            f"\t{info['last_activity'] or '-'}"
        )
    if not result["projects"]:
        print("sin proyectos")


def _print_merges(result: dict[str, Any]) -> None:
    for canon, variants in result["merges"].items():
        for variant in variants:
            print(f"{variant} -> {canon}")
    if not result["merges"]:
        print("nada para unir")
    elif result["dry_run"]:
        print("dry-run: no se unió nada")


def _print_keys(result: dict[str, Any]) -> None:
    for key, value in result.items():
        print(f"{key}: {value}")


# -- export / import ------------------------------------------------------------------------


def _export(args: argparse.Namespace) -> int:
    try:
        with MemoryStore() as store:
            project = None
            if not args.all and args.scope != "personal":
                project = (
                    args.project
                    or registry.call(
                        "mem_detect_project", {}, registry.Context(args.cwd.resolve())
                    )["name"]
                )
            data = exchange.export(store, project=project, scope=args.scope)
    except (InputError, ValueError, OSError, sqlite3.Error) as exc:
        return error(str(exc))
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    count = len(data["observations"])
    noun = "observación" if count == 1 else "observaciones"
    if args.output is None:
        sys.stdout.flush()
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    try:
        args.output.write_bytes(text.encode("utf-8"))
    except OSError as exc:
        return error(f"no se pudo escribir {args.output} ({exc})")
    print(f"exportadas {count} {noun} a {args.output}", file=sys.stderr)
    return 0


def _progress(done: int, total: int) -> None:
    print(f"vectores: {done}/{total}", file=sys.stderr, flush=True)


def _model_pull(args: argparse.Namespace) -> int:
    print("bajando el modelo (puede tardar)...", file=sys.stderr, flush=True)
    try:
        provider, model, path = embeddings.pull(args.provider, args.model)
    except (ValueError, ImportError, OSError) as exc:
        return error(str(exc))
    if args.json:
        emit_json({"provider": provider, "model": model, "path": str(path)})
    else:
        print(f"listo: {provider}:{model} en {path}")
        print(f"siguiente paso: `{_meta.NAME} mem reindex --provider {provider}`")
    return 0


def _model_list(args: argparse.Namespace) -> int:
    found = embeddings.list_models()
    if args.json:
        emit_json(
            {"models": [{"provider": p, "model": m, "path": str(path)} for p, m, path in found]}
        )
        return 0
    for provider, model, path in found:
        print(f"{provider}\t{model}\t{path}")
    if not found:
        print(f"sin modelos; bajá uno con `{_meta.NAME} mem model pull`")
    return 0


def _reindex(args: argparse.Namespace) -> int:
    if args.provider is not None and args.provider not in PROVIDER_CHOICES:
        return error(
            f"proveedor desconocido: {args.provider} (uno de {', '.join(PROVIDER_CHOICES)})"
        )
    try:
        with MemoryStore() as store:
            result = store.reindex(
                provider=args.provider,
                model=args.model,
                allow_remote=args.allow_remote,
                progress=None if args.json else _progress,
            )
    except (ValueError, ImportError, OSError, sqlite3.Error) as exc:
        return error(str(exc))
    if args.json:
        emit_json(vars(result))
        return 0
    semantic = (
        f"{result.vectors} vectores ({result.provider}:{result.model}, dim {result.dim})"
        if result.provider
        else "sin índice semántico"
    )
    print(f"reindexado: {result.fts} en el índice léxico, {semantic}")
    return 0


def _eval(args: argparse.Namespace) -> int:
    from exo.memory import evaluation

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    try:
        report = evaluation.evaluate(
            args.dataset,
            evaluation.default_configs(providers),
            latency_size=args.latency_size,
            measure_cost=not args.skip_cost,
            progress=lambda text: print(text, file=sys.stderr, flush=True),
        )
    except (ValueError, ImportError, OSError) as exc:
        return error(str(exc))
    text = evaluation.render(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(text.encode("utf-8"))
        print(f"reporte: {args.output}", file=sys.stderr)
    if args.json:
        emit_json(report)
    else:
        print(text, end="")
    return 0


def _import(args: argparse.Namespace) -> int:
    try:
        data = json.loads(args.file.read_bytes().decode("utf-8-sig"))
    except OSError as exc:
        return error(f"no se pudo leer {args.file} ({exc})")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return error(f"{args.file} no es JSON válido ({exc})")
    try:
        with MemoryStore() as store:
            result = exchange.import_(store, data, project=args.project)
    except (ValueError, OSError, sqlite3.Error) as exc:
        return error(str(exc))
    if args.json:
        emit_json(vars(result))
    else:
        print(
            f"importadas: {result.created} creadas, {result.updated} actualizadas, "
            f"{result.unchanged} sin cambios, {result.skipped} salteadas (más nuevas acá)"
        )
    return 0


# -- registro -------------------------------------------------------------------------------


def _group(sub: argparse._SubParsersAction, name: str, helptext: str) -> argparse._SubParsersAction:
    group = sub.add_parser(name, help=helptext)
    group.set_defaults(handler=lambda _args: (group.print_help(), 0)[1])
    return group.add_subparsers(dest=f"{name}_command", metavar="<acción>")


def _scope_args(a: argparse.Namespace) -> dict[str, Any]:
    return _opt(project=a.project, all_projects=a.all, type=a.type, scope=a.scope, limit=a.limit)


def register(sub: argparse._SubParsersAction) -> None:
    mem = _group(sub, "mem", "memoria del usuario: decisiones, bugs y descubrimientos")

    save = mem.add_parser("save", help="guarda una observación")
    save.add_argument("--title", required=True)
    save.add_argument("--content", required=True, help="texto, o - para leerlo de stdin")
    save.add_argument("--type", help="decision, bugfix, discovery, gotcha, convention…")
    save.add_argument("--topic-key", help="clave estable: actualiza en lugar de duplicar")
    save.add_argument("--scope", choices=("project", "personal"))
    save.add_argument("--session", type=int, help="id de la sesión")
    _common(save)
    save.set_defaults(
        handler=_run(
            "mem_save",
            lambda a: _opt(
                project=a.project,
                title=a.title,
                content=_text(a.content),
                type=a.type,
                topic_key=a.topic_key,
                scope=a.scope,
                session_id=a.session,
            ),
            _print_saved,
        )
    )

    search = mem.add_parser("search", help="busca (devuelve previews)")
    search.add_argument("query")
    search.add_argument(
        "--mode", choices=SEARCH_MODES, help="auto (por defecto): híbrida si hay índice semántico"
    )
    _filters(search)
    _common(search)
    search.set_defaults(
        handler=_run(
            "mem_search",
            lambda a: {"query": a.query, **_scope_args(a), **_opt(mode=a.mode)},
            _print_hits,
        )
    )

    listing = mem.add_parser("list", help="observaciones recientes")
    _filters(listing)
    listing.add_argument("--offset", type=int)
    _common(listing)
    listing.set_defaults(
        handler=_run("mem_list", lambda a: {**_scope_args(a), **_opt(offset=a.offset)}, _print_hits)
    )

    for name, tool, helptext, printer in (
        ("get", "mem_get", "una observación completa", _print_observation),
        ("delete", "mem_delete", "borra una observación", lambda r: print(f"borrada #{r['id']}")),
    ):
        parser = mem.add_parser(name, help=helptext)
        parser.add_argument("id", type=int)
        _common(parser, project=False)
        parser.set_defaults(handler=_run(tool, lambda a: {"id": a.id}, printer))

    context = mem.add_parser("context", help="contexto reciente para empezar una sesión")
    context.add_argument("--limit", type=int)
    _common(context)
    context.set_defaults(
        handler=_run(
            "mem_context",
            lambda a: _opt(project=a.project, limit=a.limit),
            lambda r: print(r["context"], end=""),
        )
    )

    stats = mem.add_parser("stats", help="estadísticas de la memoria")
    _common(stats, project=False)
    stats.set_defaults(handler=_run("mem_stats", lambda a: {}, _print_keys))

    session = _group(mem, "session", "sesiones de trabajo")
    start = session.add_parser("start", help="abre una sesión")
    start.add_argument("--agent")
    _common(start)
    start.set_defaults(
        handler=_run(
            "mem_session_start", lambda a: _opt(project=a.project, agent=a.agent), _print_session
        )
    )
    end = session.add_parser("end", help="cierra una sesión")
    end.add_argument("session_id", type=int)
    end.add_argument("--summary", help="resumen, o - para leerlo de stdin")
    _common(end, project=False)
    end.set_defaults(
        handler=_run(
            "mem_session_end",
            lambda a: _opt(
                session_id=a.session_id, summary=_text(a.summary) if a.summary else None
            ),
            _print_session,
        )
    )
    summary = session.add_parser("summary", help="guarda el resumen de la sesión")
    summary.add_argument("--content", required=True, help="texto, o - para leerlo de stdin")
    summary.add_argument("--session", type=int, help="id (por defecto, la abierta más reciente)")
    _common(summary)
    summary.set_defaults(
        handler=_run(
            "mem_session_summary",
            lambda a: _opt(project=a.project, content=_text(a.content), session_id=a.session),
            lambda r: print(f"resumen guardado en la sesión #{r['session_id']}"),
        )
    )
    show = session.add_parser("show", help="una sesión (por defecto, la más reciente)")
    show.add_argument("session_id", type=int, nargs="?")
    show.add_argument("--all", action="store_true", help="la más reciente de cualquier proyecto")
    _common(show)
    show.set_defaults(
        handler=_run(
            "mem_session_show",
            lambda a: _opt(session_id=a.session_id, project=a.project, all_projects=a.all),
            _print_session,
        )
    )

    projects = _group(mem, "projects", "proyectos de la memoria")
    plist = projects.add_parser("list", help="proyectos con sus cantidades")
    _common(plist, project=False)
    plist.set_defaults(handler=_run("mem_projects_list", lambda a: {}, _print_projects))
    merge = projects.add_parser("merge", help="mueve todo de un proyecto a otro")
    merge.add_argument("source")
    merge.add_argument("target")
    _common(merge, project=False)
    merge.set_defaults(
        handler=_run(
            "mem_projects_merge",
            lambda a: {"source": a.source, "target": a.target},
            lambda r: print(
                f"{r['source']} -> {r['target']}: {r['moved']} movidas, "
                f"{r['conflicts']} repetidas (quedó la más reciente), {r['sessions']} sesiones"
            ),
        )
    )
    consolidate = projects.add_parser("consolidate", help="une variantes del mismo remoto")
    consolidate.add_argument("--dry-run", action="store_true")
    _common(consolidate, project=False)
    consolidate.set_defaults(
        handler=_run("mem_projects_consolidate", lambda a: _opt(dry_run=a.dry_run), _print_merges)
    )
    detect = projects.add_parser("detect", help="proyecto que se detecta desde --cwd")
    _common(detect, project=False)
    detect.set_defaults(
        handler=_run(
            "mem_detect_project",
            lambda a: {},
            lambda r: print(f"{r['name']} ({r['source']})"),
        )
    )

    reindex = mem.add_parser(
        "reindex",
        help="reconstruye los índices desde la base (y cambia el semántico)",
        description=(
            "Sin --provider, rehace el índice léxico y el semántico que ya tiene la base. Con "
            "--provider, crea o cambia el semántico (local: el mejor instalado; none: lo apaga). "
            "Los modelos locales se bajan antes con `mem model pull`."
        ),
    )
    reindex.add_argument("--provider", help=f"uno de: {', '.join(PROVIDER_CHOICES)}")
    reindex.add_argument("--model", help="modelo (por defecto, el del proveedor)")
    reindex.add_argument(
        "--allow-remote",
        action="store_true",
        help="permite un proveedor remoto: manda el texto de las memorias afuera",
    )
    reindex.add_argument("--json", action="store_true", help="salida JSON")
    reindex.set_defaults(handler=_reindex)

    model = _group(mem, "model", "modelos de embeddings locales")
    pull = model.add_parser(
        "pull",
        help="baja un modelo (la única forma de bajarlos: nunca se bajan solos)",
        description="Baja el modelo de Hugging Face a la carpeta de modelos del usuario. "
        "Después, `mem reindex --provider <proveedor>` crea el índice semántico.",
    )
    pull.add_argument(
        "provider",
        nargs="?",
        default="local",
        choices=("local", "onnx", "static"),
        help="local (por defecto): el mejor instalado, onnx primero (ADR-0010)",
    )
    pull.add_argument("--model", help="modelo (por defecto, el multilingüe del proveedor)")
    pull.add_argument("--json", action="store_true", help="salida JSON")
    pull.set_defaults(handler=_model_pull)
    models = model.add_parser("list", help="modelos bajados")
    models.add_argument("--json", action="store_true", help="salida JSON")
    models.set_defaults(handler=_model_list)

    ev = mem.add_parser(
        "eval",
        help="(desarrollo) experimento: búsqueda léxica contra híbrida",
        description="Mide Recall@5, MRR@10, nDCG@10, falsos positivos, latencia, tamaño y "
        "arranque sobre una base temporal, y aplica la regla de decisión de F3.",
    )
    ev.add_argument("--dataset", type=Path, default=Path("tests/memory_eval"))
    ev.add_argument("--providers", default="static,onnx", help="separados por coma")
    ev.add_argument("--latency-size", type=int, default=5000)
    ev.add_argument("--skip-cost", action="store_true", help="sin tamaño ni arranque en frío")
    ev.add_argument("--output", type=Path, help="escribe el reporte en Markdown")
    ev.add_argument("--json", action="store_true", help="salida JSON")
    ev.set_defaults(handler=_eval)

    export = mem.add_parser("export", help="exporta a JSON (sin redactar)")
    export.add_argument("--all", action="store_true", help="todos los proyectos y lo personal")
    export.add_argument("--scope", choices=("project", "personal"))
    export.add_argument("--output", type=Path, help="archivo (por defecto, stdout)")
    _common(export)
    export.set_defaults(handler=_export)

    imp = mem.add_parser("import", help="importa un export (no pisa lo más nuevo)")
    imp.add_argument("file", type=Path)
    imp.add_argument("--project", help="importa todo en este proyecto")
    imp.add_argument("--json", action="store_true", help="salida JSON")
    imp.set_defaults(handler=_import)
