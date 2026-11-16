"""Las etapas deterministas juntas, el estado y la actualización incremental (F6, ADR-0015).

- `structure`: R1 (grafo y métricas de git) sobre una sola lista de archivos.
- `status`: unidades por estado (las salteadas con su razón), las próximas, las cerradas
  que ninguna capacidad lista en su `Source:`, las capacidades por status, stale, sin
  registro y sus rondas, la auditoría pendiente y las marcadas, y **los cambios fuera
  de las rutas permitidas** (solo lectura sobre el código del proyecto). Si git falla,
  `outside_changes_error` dice por qué: "no pude mirar" no es "no hay nada".
- `update`: recalcula R0 y R1 e informa unidades stale, archivos nuevos o borrados y
  capacidades stale (un archivo que citan cambió desde su `synthesized`) o sin
  registro. No persiste nada "stale" ni replanifica.
"""

from __future__ import annotations

import fnmatch
import posixpath
import shutil
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import config
from exo.discovery import (
    capabilities,
    coverage,
    git_metrics,
    graph,
    inventory,
    planner,
    sampler,
    store,
    units,
)
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
    """El estado de la adopción, de solo lectura: lista los archivos una vez y solo lee
    JSON y specs (no recalcula la cobertura)."""
    project = Path(project)
    plan = store.read_json(project, planner.FILENAME)
    try:
        outside, outside_error = outside_changes(project), None
    except git.GitError as exc:
        outside, outside_error = None, str(exc)
    warnings: list[str] = []
    loaded = capabilities.with_preamble(project, warnings)
    recorded = capabilities.records(project)
    present = {spec.name for spec in loaded}
    payload: dict[str, Any] = {
        "steps": {
            name: (store.root(project) / name).is_file()
            for name in (inventory.FILENAME, graph.FILENAME, planner.FILENAME)
        },
        "outside_changes": outside,
        "outside_changes_error": outside_error,
        "units": None,
        "skipped": [],
        "unsynthesized_units": [],
        "capabilities": {s: sum(1 for c in loaded if c.status == s) for s in specs.STATUSES},
        "stale_capabilities": [],
        "unrecorded_capabilities": sorted(present - set(recorded)),
        "rounds": {name: record.get("rounds") for name, record in sorted(recorded.items())},
        "coverage": (store.root(project) / coverage.FILENAME).is_file(),
    }
    fileset = files_mod.list_files(project) if plan is not None or recorded else None
    if fileset is not None:
        payload["stale_capabilities"] = capabilities.stale(recorded, fileset, present)
    if plan is not None and fileset is not None:
        payload.update(_unit_status(project, plan, fileset, loaded))
    rows, missing, audit_warnings = coverage.precision(
        project, sampler.population(project, loaded=loaded)
    )
    payload["audit_missing"] = missing
    payload["flagged"] = [row["capability"] for row in rows if row["flags"]]
    payload["warnings"] = warnings + audit_warnings
    return payload


def _unit_status(
    project: Path,
    plan: dict[str, Any],
    fileset: files_mod.FileSet,
    loaded: list[capabilities.Spec],
) -> dict[str, Any]:
    found = units.states(project, plan, fileset)
    counts = dict.fromkeys(units.STATUSES, 0)
    for state in found:
        counts[state.status] += 1
    by_id = {s.id: s.status for s in found}
    sourced = {unit for spec in loaded for unit in capabilities.source_units(spec)}
    return {
        "depth": plan["depth"],
        "units": counts,
        "next": [u["id"] for u in plan["units"] if by_id[u["id"]] not in ("done", "skipped")][:5],
        "skipped": [
            {"id": s.id, "reason": s.reason, "changed": s.changed}
            for s in found
            if s.status == "skipped"
        ],
        "unsynthesized_units": sorted(
            s.id for s in found if s.status == "done" and s.id not in sourced
        ),
        "orphans": units.orphans(project, plan),
    }


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
    warnings: list[str] = []
    stale_capabilities, unrecorded = capability_signals(project, fileset, warnings)
    skipped = {s.id: s.changed for s in found if s.status == "skipped" and s.changed}
    return {
        "stale_units": {k: v for k, v in sorted(stale.items())},
        "changed_skipped_units": dict(sorted(skipped.items())),
        "new_files": sorted(code - planned),
        "deleted_files": sorted(planned - code),
        "stale_capabilities": stale_capabilities,
        "unrecorded_capabilities": unrecorded,
        "warnings": warnings,
    }


def capability_signals(
    project: Path, fileset: files_mod.FileSet, warnings: list[str] | None = None
) -> tuple[list[str], list[str]]:
    """(capacidades stale, capacidades con preámbulo sin registro de `synthesized`)."""
    present = {spec.name for spec in capabilities.with_preamble(project, warnings)}
    recorded = capabilities.records(project)
    return capabilities.stale(recorded, fileset, present), sorted(present - set(recorded))
