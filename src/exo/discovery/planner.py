"""R2, plan: unidades de trabajo acotadas, con prioridad y estimación (F6, ADR-0015).

- **Unidad:** los archivos de producción de un módulo. Un módulo que pasa el
  presupuesto de líneas se parte **solo entre archivos**, en orden de ruta.
- **ID:** estable, en minúscula y kebab-case, desde la ruta del módulo. Ante una
  colisión o un nombre reservado de Windows lleva un sufijo de hash.
- **Prioridad:** palabras de criticidad (autenticación, pagos, seguridad, datos
  personales), fan-in y churn.
- **Profundidad:** `quick` extrae en detalle solo las unidades más críticas y resume
  el resto; `standard` y `deep` extraen todas (`deep` con presupuesto más chico y
  leyendo los tests).
- **Tests:** a cada unidad se le asocian los tests que importan sus archivos.

`plan` no pisa un plan con unidades cerradas sin `replan` (D-34: lo commiteado es de
todos), y `update` nunca replanifica.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import config, fsutil
from exo.discovery import files as files_mod
from exo.discovery import graph, store

FILENAME = "plan.json"
DEPTHS = ("quick", "standard", "deep")
BUDGETS = {"quick": 1200, "standard": 800, "deep": 500}
QUICK_SHARE = 0.3
TOKENS_PER_BYTE = 0.25  # unos 4 bytes por token
CRITICAL_WORDS = (
    "account",
    "admin",
    "auth",
    "billing",
    "card",
    "checkout",
    "credential",
    "crypto",
    "customer",
    "invoice",
    "login",
    "member",
    "password",
    "payment",
    "permission",
    "personal",
    "pii",
    "role",
    "secret",
    "security",
    "session",
    "token",
    "user",
)
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(-|$)")
MAX_ID = 60


class PlanError(ValueError):
    """El plan no se puede escribir sin perder trabajo, o la profundidad no existe."""


def slug(path: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    return text or "root"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:6]


def unit_ids(keys: list[str]) -> dict[str, str]:
    """IDs estables para cada clave (`<módulo>` o `<módulo>#<n>`)."""
    base: dict[str, str] = {}
    for key in keys:
        module, _, part = key.partition("#")
        name = slug(module) + (f"-{part}" if part else "")
        if len(name) > MAX_ID:
            name = name[: MAX_ID - 7].rstrip("-") + "-" + _hash(key)
        base[key] = name
    counts: dict[str, int] = {}
    for name in base.values():
        counts[name] = counts.get(name, 0) + 1
    ids: dict[str, str] = {}
    for key, name in base.items():
        if counts[name] > 1 or _RESERVED.match(name):
            name = f"{name}-{_hash(key)}"
        ids[key] = name
    return ids


def criticality(path: str) -> list[str]:
    words = set(re.split(r"[^a-z0-9]+", path.lower()))
    stems = {w.rstrip("s") for w in words}
    return sorted(w for w in CRITICAL_WORDS if w in words or w in stems)


def _chunks(paths: list[str], lines: dict[str, int], budget: int) -> list[list[str]]:
    chunks: list[list[str]] = [[]]
    total = 0
    for path in sorted(paths):
        size = lines[path]
        if chunks[-1] and total + size > budget:
            chunks.append([])
            total = 0
        chunks[-1].append(path)
        total += size
    return chunks


def _tests_by_file(project: Path, fileset: files_mod.FileSet) -> dict[str, set[str]]:
    """Archivo de producción -> tests que lo importan."""
    readable = [f.path for f in fileset.files if not f.sensitive]
    index = graph.Index.build(project, readable)
    found: dict[str, set[str]] = {}
    for item in fileset.files:
        if item.category != "test":
            continue
        if item.language == "python":
            targets, _ = graph.python_imports(
                item.path, fsutil.read_bytes(project / item.path), index
            )
        elif item.language in ("javascript", "typescript"):
            targets, _ = graph.js_imports(item.path, graph._read(project, item.path), index)
        elif item.language == "java":
            targets, _ = graph.java_imports(item.path, graph._read(project, item.path), index)
        else:
            continue
        for target in targets:
            found.setdefault(target, set()).add(item.path)
    return found


def build(
    project: Path,
    depth: str | None = None,
    *,
    fileset: files_mod.FileSet | None = None,
    structure: dict[str, Any] | None = None,
    hotspots: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = Path(project)
    depth = depth or config.load(project).config["discovery"]["depth"]
    if depth not in DEPTHS:
        raise PlanError(f"unknown depth {depth!r}: use {', '.join(DEPTHS)}")
    fileset = fileset or files_mod.list_files(project)
    structure = structure or graph.build(project, fileset)
    hotspots = hotspots or store.read_json(project, "hotspots.json") or {"modules": []}
    budget = BUDGETS[depth]
    code = {f.path: f for f in fileset.files if f.category == "code"}
    lines = {p: f.lines for p, f in code.items()}
    sizes = {p: f.size for p, f in code.items()}
    fan_in = {m["path"]: m["fan_in"] for m in structure["modules"]}
    churn = {m["path"]: m["commits"] for m in hotspots.get("modules", [])}
    tests = _tests_by_file(project, fileset)
    by_module: dict[str, list[str]] = {}
    for path in code:
        by_module.setdefault(graph.module_of(path), []).append(path)
    keyed: list[tuple[str, str, list[str]]] = []
    for module in sorted(by_module):
        chunks = _chunks(by_module[module], lines, budget)
        for number, chunk in enumerate(chunks, start=1):
            key = module if len(chunks) == 1 else f"{module}#{number}"
            keyed.append((key, module, chunk))
    ids = unit_ids([key for key, _, _ in keyed])
    units: list[dict[str, Any]] = []
    for key, module, chunk in keyed:
        words = sorted({w for path in chunk for w in criticality(path)})
        priority = (
            min(len(words), 3) * 1000 + fan_in.get(module, 0) * 10 + min(churn.get(module, 0), 9)
        )
        unit_tests = sorted({t for path in chunk for t in tests.get(path, set())})
        units.append(
            {
                "id": ids[key],
                "module": module,
                "files": chunk,
                "tests": unit_tests,
                "lines": sum(lines[p] for p in chunk),
                "criticality": words,
                "priority": priority,
                "estimate_tokens": int(sum(sizes[p] for p in chunk) * TOKENS_PER_BYTE * 2),
            }
        )
    units.sort(key=lambda u: (-u["priority"], u["id"]))
    detailed = len(units) if depth != "quick" else max(1, round(len(units) * QUICK_SHARE))
    for position, unit in enumerate(units):
        unit["detail"] = "full" if position < detailed else "summary"
    return {
        "depth": depth,
        "budget_lines": budget,
        "units": units,
        "totals": {
            "units": len(units),
            "detailed": detailed,
            "lines": sum(u["lines"] for u in units),
            "estimate_tokens": sum(u["estimate_tokens"] for u in units),
        },
    }


def closed_units(project: Path) -> list[str]:
    folder = store.root(project) / "units"
    return sorted(p.stem for p in folder.glob("*.json")) if folder.is_dir() else []


def write(
    project: Path, depth: str | None = None, *, replan: bool = False, **kwargs: Any
) -> tuple[dict[str, Any], bool]:
    """Escribe `plan.json`. Sin `replan`, no pisa un plan que ya tiene unidades cerradas."""
    project = Path(project)
    current = store.read_json(project, FILENAME)
    data = build(project, depth, **kwargs)
    closed = closed_units(project)
    if current is not None and closed and not replan:
        if {k: v for k, v in current.items() if k != "schema"} == data:
            return data, False
        raise PlanError(
            f"the plan has {len(closed)} closed units; pass --replan to rebuild it (closed units "
            "whose files did not change keep their extraction)"
        )
    return data, store.write_json(project, FILENAME, data)


def load(project: Path) -> dict[str, Any]:
    data = store.read_json(project, FILENAME)
    if data is None:
        raise PlanError(f"there is no plan yet: run `{_meta.NAME} discover plan` first")
    return data


def unit(plan: dict[str, Any], unit_id: str) -> dict[str, Any]:
    for item in plan["units"]:
        if item["id"] == unit_id:
            return item
    raise PlanError(f"{unit_id} is not a unit of the plan")
