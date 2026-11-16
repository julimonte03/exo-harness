"""Las etapas deterministas juntas, el estado y la actualización incremental (F6, ADR-0015).

- `structure`: R1 (grafo y métricas de git) sobre una sola lista de archivos.
- `status`: unidades por estado, las próximas, registros huérfanos y **los cambios
  fuera de las rutas permitidas** (solo lectura sobre el código del proyecto).
- `update`: recalcula R0 y R1 e informa unidades stale, archivos nuevos o borrados y
  capacidades stale (una de sus citas `[Code]` apunta a un archivo que cambió). No
  persiste nada "stale" ni replanifica.
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import Any

from exo import _meta
from exo.core import config
from exo.discovery import files as files_mod
from exo.discovery import git_metrics, graph, inventory, planner, store, units
from exo.governance import git
from exo.sdd import specs

CONTEXT_FILE = "context.md"
_CITED = re.compile(r"\[Code\]\s+([^\s\[\]]+):\d+")


def structure(project: Path) -> dict[str, Any]:
    fileset = files_mod.list_files(project)
    data, wrote = graph.write(project, fileset)
    metrics, wrote_metrics = git_metrics.write(project, fileset)
    return {
        "modules": len(data["modules"]),
        "edges": len(data["edges"]),
        "warnings": metrics["hotspots"]["warnings"],
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
    if any(path.startswith(prefix) for prefix in prefixes):
        return True
    return any(PurePosixPath(path).match(pattern) for pattern in patterns)


def outside_changes(project: Path) -> list[str] | None:
    """Rutas que `git status` muestra cambiadas fuera de las permitidas; None sin git."""
    done = git.run(project, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if not done.ok:
        return None
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
            index += 1  # el origen del rename viene en la entrada siguiente
    # El formato porcelain da rutas relativas a la raíz del repo: se pasan al proyecto.
    top = git.toplevel(project)
    base = ""
    if top is not None:
        relative = Path(project).resolve().relative_to(top.resolve()).as_posix()
        base = "" if relative == "." else relative + "/"
    local = [p[len(base) :] for p in paths if p.startswith(base)]
    prefixes, patterns = allowed(project)
    return sorted({p for p in local if not _is_allowed(p, prefixes, patterns)})


def status(project: Path) -> dict[str, Any]:
    project = Path(project)
    plan = store.read_json(project, planner.FILENAME)
    payload: dict[str, Any] = {
        "steps": {
            name: (store.root(project) / name).is_file()
            for name in (inventory.FILENAME, graph.FILENAME, planner.FILENAME)
        },
        "outside_changes": outside_changes(project),
    }
    if plan is None:
        payload["units"] = None
        return payload
    fileset = files_mod.list_files(project)
    found = units.states(project, plan, fileset)
    counts = {"pending": 0, "done": 0, "stale": 0}
    for state in found:
        counts[state.status] += 1
    by_id = {s.id: s.status for s in found}
    payload["depth"] = plan["depth"]
    payload["units"] = counts
    payload["next"] = [u["id"] for u in plan["units"] if by_id[u["id"]] != "done"][:5]
    payload["orphans"] = units.orphans(project, plan)
    return payload


def cited_files(project: Path) -> dict[str, set[str]]:
    """Capacidad con preámbulo -> archivos que citan sus FR."""
    root = specs.capabilities_root(project)
    found: dict[str, set[str]] = {}
    if not root.is_dir():
        return found
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and p.name[0] not in "._"):
        path = folder / specs.SPEC_FILE
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8-sig")
        if specs.parse_capability(text, folder.name).status is None:
            continue
        found[folder.name] = set(_CITED.findall(text))
    return found


def update(project: Path) -> dict[str, Any]:
    project = Path(project)
    inventory.write(project)
    structure(project)
    plan = planner.load(project)
    fileset = files_mod.list_files(project)
    found = units.states(project, plan, fileset)
    stale = {s.id: s.changed for s in found if s.status == "stale"}
    planned = {p for item in plan["units"] for p in item["files"]}
    code = {f.path for f in fileset.files if f.category == "code"}
    changed = {p for paths in stale.values() for p in paths}
    deleted = sorted(planned - code)
    capabilities = sorted(
        name
        for name, paths in cited_files(project).items()
        if paths & changed or paths & set(deleted)
    )
    return {
        "stale_units": {k: v for k, v in sorted(stale.items())},
        "new_files": sorted(code - planned),
        "deleted_files": deleted,
        "stale_capabilities": capabilities,
    }
