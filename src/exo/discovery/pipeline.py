"""Las etapas deterministas juntas, el estado y la actualización incremental (F6, ADR-0015).

- `structure`: R1 (grafo y métricas de git) sobre una sola lista de archivos.
- `status`: unidades por estado, las próximas, registros huérfanos y **los cambios
  fuera de las rutas permitidas** (solo lectura sobre el código del proyecto). Si git
  falla, `outside_changes_error` dice por qué: "no pude mirar" no es "no hay nada".
- `update`: recalcula R0 y R1 e informa unidades stale, archivos nuevos o borrados y
  capacidades stale (una de sus citas `[Code]` apunta a un archivo que cambió). No
  persiste nada "stale" ni replanifica.
"""

from __future__ import annotations

import fnmatch
import posixpath
import shutil
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import config
from exo.discovery import capabilities, git_metrics, graph, inventory, planner, store, units
from exo.discovery import files as files_mod
from exo.governance import git
from exo.sdd import specs

CONTEXT_FILE = "context.md"


def structure(project: Path, fileset: files_mod.FileSet | None = None) -> dict[str, Any]:
    fileset = fileset if fileset is not None else files_mod.list_files(project)
    data, wrote = graph.write(project, fileset)
    metrics, wrote_metrics = git_metrics.write(project, fileset)
    return {
        "modules": len(data["modules"]),
        "edges": len(data["edges"]),
        "warnings": [*data["warnings"], *metrics["hotspots"]["warnings"]],
        "written": wrote or wrote_metrics,
    }


def allowed(project: Path) -> tuple[list[str], list[str]]:
    """(prefijos, patrones) de lo que la ingeniería inversa puede escribir."""
    cfg = config.load(project).config
    data = store.read_json(project, inventory.FILENAME) or {}
    adr_dir = str(data.get("adr_dir") or inventory.DEFAULT_ADR_DIR).strip("/")
    capabilities = posixpath.join(cfg["specs_dir"].strip("/"), specs.CAPABILITIES)
    prefixes = [store.rel(""), capabilities + "/"]
    exact = [f"{_meta.PROJECT_DIR}/{CONTEXT_FILE}", f"{adr_dir}/{files_mod.RECOVERED_ADR}"]
    return prefixes, exact


def _is_allowed(path: str, prefixes: list[str], patterns: list[str]) -> bool:
    """Por prefijo desde la raíz, o por patrón sobre la ruta entera (`*` no cruza carpetas)."""
    if any(path.startswith(prefix) for prefix in prefixes):
        return True
    return any(
        path.count("/") == pattern.count("/") and fnmatch.fnmatchcase(path, pattern)
        for pattern in patterns
    )


def _in_repo(project: Path) -> bool:
    """¿Hay git y el proyecto está en un repo? Sin correr git: su mensaje depende del idioma."""
    if shutil.which("git") is None:
        return False
    folder = Path(project).resolve()
    return any((p / ".git").exists() for p in (folder, *folder.parents))


def outside_changes(project: Path) -> list[str] | None:
    """Rutas que `git status` muestra cambiadas fuera de las permitidas.

    None solo sin git (no está instalado o el proyecto no es un repo). Si git falla
    (timeout, error), `git.GitError` con el detalle.
    """
    if not _in_repo(project):
        return None
    # `--no-optional-locks`: mirar no toma el lock del índice ni lo reescribe.
    done = git.run(
        project,
        "--no-optional-locks",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if not done.ok:
        raise git.GitError(f"git status failed: {done.err.strip() or 'no output'}")
    entries = done.out.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        paths.append(path)
        if "R" in code or "C" in code:
            # El origen viene en la entrada siguiente: sacar algo de una ruta no permitida
            # también es un cambio fuera de las permitidas.
            if index < len(entries) and entries[index]:
                paths.append(entries[index])
            index += 1
    # El formato porcelain da rutas relativas a la raíz del repo: se pasan al proyecto.
    top = git.toplevel(project)
    if top is None:
        raise git.GitError("git rev-parse --show-toplevel failed")
    relative = Path(project).resolve().relative_to(top.resolve()).as_posix()
    base = "" if relative == "." else relative + "/"
    local = [p[len(base) :] for p in paths if p.startswith(base)]
    prefixes, patterns = allowed(project)
    return sorted({p for p in local if not _is_allowed(p, prefixes, patterns)})


def status(project: Path) -> dict[str, Any]:
    project = Path(project)
    plan = store.read_json(project, planner.FILENAME)
    try:
        outside, outside_error = outside_changes(project), None
    except git.GitError as exc:
        outside, outside_error = None, str(exc)
    warnings: list[str] = []
    capabilities.load(project, warnings)
    payload: dict[str, Any] = {
        "steps": {
            name: (store.root(project) / name).is_file()
            for name in (inventory.FILENAME, graph.FILENAME, planner.FILENAME)
        },
        "outside_changes": outside,
        "outside_changes_error": outside_error,
        "warnings": warnings,
    }
    if plan is None:
        payload["units"] = None
        payload["skipped"] = []
        return payload
    fileset = files_mod.list_files(project)
    found = units.states(project, plan, fileset)
    counts = dict.fromkeys(units.STATUSES, 0)
    for state in found:
        counts[state.status] += 1
    by_id = {s.id: s.status for s in found}
    payload["depth"] = plan["depth"]
    payload["units"] = counts
    payload["next"] = [u["id"] for u in plan["units"] if by_id[u["id"]] not in ("done", "skipped")][
        :5
    ]
    payload["skipped"] = [
        {"id": s.id, "reason": s.reason, "changed": s.changed}
        for s in found
        if s.status == "skipped"
    ]
    payload["orphans"] = units.orphans(project, plan)
    return payload


def cited_files(project: Path, warnings: list[str] | None = None) -> dict[str, set[str]]:
    """Capacidad con preámbulo -> archivos que citan sus FR (las specs que no son UTF-8 se
    saltean, en `warnings`)."""
    return {
        spec.name: capabilities.cited(spec)
        for spec in capabilities.with_preamble(project, warnings)
    }


def update(project: Path) -> dict[str, Any]:
    project = Path(project)
    fileset = files_mod.list_files(project)  # una sola lista para R0, R1 y los estados
    inventory.write(project, fileset)
    structure(project, fileset)
    plan = planner.load(project)
    found = units.states(project, plan, fileset)
    stale = {s.id: s.changed for s in found if s.status == "stale"}
    planned = {p for item in plan["units"] for p in item["files"]}
    code = {f.path for f in fileset.files if f.category == "code"}
    changed = {p for paths in stale.values() for p in paths}
    deleted = sorted(planned - code)
    warnings: list[str] = []
    stale_capabilities = sorted(
        name
        for name, paths in cited_files(project, warnings).items()
        if paths & changed or paths & set(deleted)
    )
    skipped = {s.id: s.changed for s in found if s.status == "skipped" and s.changed}
    return {
        "stale_units": {k: v for k, v in sorted(stale.items())},
        "changed_skipped_units": dict(sorted(skipped.items())),
        "new_files": sorted(code - planned),
        "deleted_files": deleted,
        "stale_capabilities": stale_capabilities,
        "warnings": warnings,
    }
