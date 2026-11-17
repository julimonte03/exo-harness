"""R1, métricas de git: churn y ownership (F6, ADR-0015).

- **Churn** (`hotspots.json`): commits y líneas agregadas más borradas por archivo y
  por módulo, en una ventana que termina en el **último commit que toca código
  analizado**, no en HEAD ni en "ahora". Commitear los resultados de discovery no
  mueve la ventana, y dos corridas sobre la misma historia dan lo mismo.
- **Ownership** (`ownership.json`): commits por autor y por módulo, con `%aN` (respeta
  `.mailmap`) y **sin emails**.

Una sola lectura de `git log --no-merges --no-renames --numstat -z`. Sin git, o en un
clon shallow, se avisa: la historia puede estar incompleta.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exo.discovery import files as files_mod
from exo.discovery import graph, store
from exo.governance import git

HOTSPOTS = "hotspots.json"
OWNERSHIP = "ownership.json"
WINDOW_DAYS = 365
TOP_FILES = 50
_LOG_TIMEOUT = 300


@dataclass(frozen=True)
class Change:
    commit: str
    when: int
    author: str
    path: str
    churn: int


def parse_log(out: str) -> list[Change]:
    """Las entradas de `git log -z --numstat --format=%x1e%H%x1f%ct%x1f%aN`."""
    changes: list[Change] = []
    for chunk in out.split("\x1e"):
        if not chunk:
            continue
        header, _, rest = chunk.partition("\0")
        sha, _, tail_header = header.partition("\x1f")
        when_text, _, author = tail_header.partition("\x1f")
        try:
            when = int(when_text.strip())
        except ValueError:
            continue
        for entry in rest.lstrip("\n").split("\0"):
            added, tab, tail = entry.partition("\t")
            deleted, tab2, path = tail.partition("\t")
            if not tab or not tab2 or not path:
                continue
            lines = sum(int(n) for n in (added, deleted) if n.isdigit())  # binarios: "-"
            changes.append(Change(sha.strip(), when, author.strip(), path, lines))
    return changes


def _log(project: Path) -> tuple[list[Change] | None, list[str]]:
    warnings: list[str] = []
    if git.toplevel(project) is None:
        return None, ["not a git repository: no churn or ownership"]
    shallow = git.run(project, "rev-parse", "--is-shallow-repository")
    if shallow.ok and shallow.out.strip() == "true":
        warnings.append("shallow clone: the history is incomplete, so churn and ownership are too")
    done = git.run(
        project,
        "log",
        "--no-merges",
        "--no-renames",
        "--relative",
        "-z",
        "--numstat",
        "--format=%x1e%H%x1f%ct%x1f%aN",
        timeout=_LOG_TIMEOUT,
    )
    if not done.ok:
        return None, [*warnings, f"git log failed ({done.err.strip() or 'no output'})"]
    return parse_log(done.out), warnings


def build(
    project: Path, fileset: files_mod.FileSet | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    project = Path(project)
    fileset = fileset or files_mod.list_files(project)
    code = {f.path: f for f in fileset.files if f.category == "code"}
    changes, warnings = _log(project)
    relevant = [c for c in changes or [] if c.path in code]
    anchor = max((c.when for c in relevant), default=None)
    start = anchor - WINDOW_DAYS * 86400 if anchor is not None else None
    window = [c for c in relevant if start is not None and c.when >= start]
    per_file: dict[str, dict[str, Any]] = {}
    for change in window:
        entry = per_file.setdefault(change.path, {"commits": set(), "churn": 0})
        entry["commits"].add(change.commit)
        entry["churn"] += change.churn
    per_module: dict[str, dict[str, Any]] = {}
    for path, entry in per_file.items():
        module = per_module.setdefault(graph.module_of(path), {"commits": set(), "churn": 0})
        module["commits"] |= entry["commits"]
        module["churn"] += entry["churn"]
    ranked = sorted(per_file.items(), key=lambda kv: (-kv[1]["churn"], kv[0]))[:TOP_FILES]
    hotspots = {
        "window_days": WINDOW_DAYS,
        "anchor": anchor,
        "files": [
            {
                "path": path,
                "commits": len(entry["commits"]),
                "churn": entry["churn"],
                "lines": code[path].lines,
            }
            for path, entry in ranked
        ],
        "modules": [
            {"path": path, "commits": len(entry["commits"]), "churn": entry["churn"]}
            for path, entry in sorted(per_module.items(), key=lambda kv: (-kv[1]["churn"], kv[0]))
        ],
        "warnings": warnings,
    }
    owners: dict[str, dict[str, set[str]]] = {}
    for change in relevant:  # toda la historia: quién conoce cada módulo
        module = owners.setdefault(graph.module_of(change.path), {})
        module.setdefault(change.author, set()).add(change.commit)
    ownership = {
        "modules": [
            {
                "path": path,
                "authors": [
                    {"name": name, "commits": len(stamps)}
                    for name, stamps in sorted(authors.items(), key=lambda kv: (-len(kv[1]), kv[0]))
                ],
            }
            for path, authors in sorted(owners.items())
        ],
        "warnings": warnings,
    }
    return hotspots, ownership


def write(project: Path, fileset: files_mod.FileSet | None = None) -> tuple[dict[str, Any], bool]:
    hotspots, ownership = build(project, fileset)
    wrote = store.write_json(project, HOTSPOTS, hotspots)
    wrote = store.write_json(project, OWNERSHIP, ownership) or wrote
    return {"hotspots": hotspots, "ownership": ownership}, wrote
