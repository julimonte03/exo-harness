"""R3, unidades: estado derivado, la próxima unidad y el cierre validado (F6, ADR-0015).

- **Estado derivado:** una unidad está `done` si existe `units/<id>.json` y los hashes
  de sus archivos no cambiaron; `stale` si cambió alguno; `pending` si no hay
  `units/<id>.json`. No hay un estado compartido ni "en curso" (D-34): una extracción
  cortada se rehace entera, y dos personas no se pisan.
- **`next`:** entrega N unidades pendientes por prioridad. Marca las líneas de
  secretos (para no copiarlas; leerlas igual las manda al modelo) y las posibles
  instrucciones sospechosas.
- **`done`:** valida `units/<id>.md` (secciones, una marca de evidencia por afirmación,
  rutas y líneas reales) y el escáner. Solo entonces escribe `units/<id>.json`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo.core import config, fsutil, scan
from exo.discovery import files as files_mod
from exo.discovery import planner, store
from exo.sdd import specs

FOLDER = "units"
SECTIONS = (
    "Responsibilities",
    "Entities",
    "Operations",
    "Business rules",
    "Invariants",
    "Integrations",
    "Error handling",
    "Tests",
    "Open questions",
)
# Las secciones cuyas viñetas son afirmaciones sobre el sistema: cada una lleva evidencia.
CLAIM_SECTIONS = SECTIONS[:8]
_NONE = re.compile(r"^\s*(?:none|n/a)\.?\s*$", re.IGNORECASE)
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_CODE_REF = re.compile(r"\[Code\]\s+([^\s\[\]]+):(\d+)(?:-(\d+))?")
_DOC_REF = re.compile(r"\[Doc\]\s+([^\s\[\]]+)")
_INFERRED = re.compile(r"\[Inferred:\s*(?:high|medium|low)\]")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


class UnitError(ValueError):
    """La unidad no existe o su documento no pasa la validación."""


@dataclass
class UnitState:
    id: str
    status: str  # pending | done | stale
    changed: list[str] = field(default_factory=list)


def unit_doc(unit_id: str) -> str:
    return f"{FOLDER}/{unit_id}.md"


def unit_record(unit_id: str) -> str:
    return f"{FOLDER}/{unit_id}.json"


def _current_hashes(fileset: files_mod.FileSet) -> dict[str, str]:
    return {f.path: f.sha for f in fileset.files}


def states(project: Path, plan: dict[str, Any], fileset: files_mod.FileSet) -> list[UnitState]:
    current = _current_hashes(fileset)
    found: list[UnitState] = []
    for item in plan["units"]:
        record = store.read_json(project, unit_record(item["id"]))
        if record is None:
            found.append(UnitState(item["id"], "pending"))
            continue
        recorded = dict(record.get("files", {}))
        recorded.update(record.get("tests", {}))
        changed = sorted(p for p, sha in recorded.items() if current.get(p) != sha)
        found.append(UnitState(item["id"], "stale" if changed else "done", changed))
    return found


def _flags(project: Path, rel: str) -> dict[str, Any]:
    from exo.validate import suspicious_instructions

    try:
        text = fsutil.read_text_auto(project / rel)
    except (OSError, UnicodeDecodeError):
        return {}
    flags: dict[str, Any] = {}
    secrets = sorted({f.line for f in scan.scan_text(text, skip_code_blocks=False, pii=())})
    if secrets:
        flags["secret_lines"] = secrets
    suspicious = sorted({line for line, _, _ in suspicious_instructions(text)})
    if suspicious:
        flags["suspicious_lines"] = suspicious
    return flags


def next_units(project: Path, count: int = 1) -> list[dict[str, Any]]:
    """Las próximas unidades a extraer (pendientes o stale), por prioridad."""
    project = Path(project)
    plan = planner.load(project)
    fileset = files_mod.list_files(project)
    by_id = {s.id: s for s in states(project, plan, fileset)}
    picked: list[dict[str, Any]] = []
    for item in plan["units"]:  # ya ordenadas por prioridad
        state = by_id[item["id"]]
        if state.status == "done":
            continue
        flags = {p: f for p in item["files"] + item["tests"] if (f := _flags(project, p))}
        picked.append(
            {
                **item,
                "status": state.status,
                "changed": state.changed,
                "document": store.rel(unit_doc(item["id"])),
                "flags": flags,
            }
        )
        if len(picked) >= count:
            break
    return picked


def _without_comments(text: str) -> str:
    """Los comentarios HTML (la guía de la plantilla) como líneas vacías: no son afirmaciones."""
    return _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _sections(text: str) -> dict[str, list[tuple[int, str]]]:
    found: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    for number, line in enumerate(_without_comments(text).split("\n"), start=1):
        heading = _HEADING.match(line)
        if heading and len(heading.group(1)) == 2:
            current = heading.group(2).strip()
            found.setdefault(current, [])
            continue
        if current is not None:
            found[current].append((number, line.rstrip("\r")))
    return found


def validate_doc(
    project: Path, item: dict[str, Any], text: str, fileset: files_mod.FileSet
) -> tuple[list[str], dict[str, int]]:
    """(errores, conteo de afirmaciones) del documento de una unidad."""
    errors: list[str] = []
    counts = {"claims": 0, "code": 0, "doc": 0, "inferred": 0}
    rel = store.rel(unit_doc(item["id"]))
    first = next((line for line in text.split("\n") if line.strip()), "")
    if first.strip() != f"# Unit: {item['id']}":
        errors.append(f"{rel}:1: the title must be '# Unit: {item['id']}'")
    sections = _sections(text)
    for name in SECTIONS:
        if name not in sections:
            errors.append(f"{rel}: missing section '## {name}'")
        elif not any(line.strip() for _, line in sections[name]):
            errors.append(f"{rel}: '## {name}' is empty; write 'None.' when there is nothing")
    allowed = set(item["files"]) | set(item["tests"])
    lines_of = {f.path: f.lines for f in fileset.files}
    analyzed = set(lines_of)
    for name in CLAIM_SECTIONS:
        for number, line in sections.get(name, []):
            stripped = line.strip()
            if not stripped.startswith(("- ", "* ")):
                continue
            counts["claims"] += 1
            body = stripped[2:]
            if _NONE.match(body):
                counts["claims"] -= 1
                continue
            if not specs.EVIDENCE.search(body):
                errors.append(
                    f"{rel}:{number}: a claim without evidence: add [Code] path:line, "
                    "[Doc] path or [Inferred: high|medium|low]"
                )
                continue
            for match in _CODE_REF.finditer(body):
                path, start, end = match.group(1), int(match.group(2)), match.group(3)
                stop = int(end) if end else start
                if path not in allowed:
                    errors.append(
                        f"{rel}:{number}: [Code] {path} is not a file of this unit or of its tests"
                    )
                elif not 1 <= start <= stop <= lines_of.get(path, 0):
                    errors.append(
                        f"{rel}:{number}: {path}:{match.group(0).split(':')[-1]} is out of range"
                    )
                counts["code"] += 1
            for match in _DOC_REF.finditer(body):
                if match.group(1) not in analyzed:
                    errors.append(f"{rel}:{number}: [Doc] {match.group(1)} is not an analyzed file")
                counts["doc"] += 1
            counts["inferred"] += len(_INFERRED.findall(body))
    pii = config.load(project).config["data_protection"]["pii"]
    for finding in scan.scan_text(text, skip_code_blocks=False, pii=pii):
        what = "a secret" if finding.level == scan.CRITICAL else "personal data"
        errors.append(
            f"{rel}:{finding.line}: {what} ({finding.kind}, {finding.excerpt}) was copied: cite "
            "the location, never the value"
        )
    return errors, counts


def done(project: Path, unit_id: str) -> dict[str, Any]:
    """Valida el documento de la unidad y la cierra con los hashes de sus archivos."""
    project = Path(project)
    plan = planner.load(project)
    item = planner.unit(plan, unit_id)
    path = store.root(project) / unit_doc(unit_id)
    rel = store.rel(unit_doc(unit_id))
    try:
        text = fsutil.read_text_auto(path)
    except FileNotFoundError as exc:
        raise UnitError(f"{rel} does not exist: write the unit's extraction there first") from exc
    except UnicodeDecodeError as exc:
        raise UnitError(f"{rel} is not UTF-8 text") from exc
    fileset = files_mod.list_files(project)
    errors, counts = validate_doc(project, item, text, fileset)
    if errors:
        raise UnitError("\n".join(errors))
    current = _current_hashes(fileset)
    record = {
        "id": unit_id,
        "files": {p: current.get(p, "") for p in item["files"]},
        "tests": {p: current.get(p, "") for p in item["tests"]},
        "counts": counts,
    }
    store.write_json(project, unit_record(unit_id), record)
    return record


def file_unit(plan: dict[str, Any]) -> dict[str, str]:
    """Archivo -> unidad que lo contiene."""
    return {path: item["id"] for item in plan["units"] for path in item["files"]}


def orphans(project: Path, plan: dict[str, Any]) -> list[str]:
    """Registros de unidades que ya no están en el plan (después de un `--replan`)."""
    folder = store.root(project) / FOLDER
    ids = {item["id"] for item in plan["units"]}
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.json") if p.stem not in ids)


def reopen(
    project: Path, ids: list[str] | None = None, *, capability: str | None = None
) -> list[str]:
    """Vuelve a pendientes unidades cerradas, para extraerlas otra vez (R5 por debajo del umbral).

    Por ID, o las unidades que contienen los archivos que citan los FR de una capacidad.
    Borra solo `units/<id>.json`: el documento queda como referencia hasta la nueva extracción.
    """
    from exo.discovery import pipeline

    project = Path(project)
    plan = planner.load(project)
    known = {item["id"] for item in plan["units"]}
    wanted = list(ids or [])
    if capability is not None:
        cited = pipeline.cited_files(project).get(capability, set())
        owners = file_unit(plan)
        found = sorted({owners[p] for p in cited if p in owners})
        if not found:
            raise UnitError(f"the capability {capability} cites no file of a unit of the plan")
        wanted += found
    unknown = sorted(set(wanted) - known)
    if unknown:
        raise UnitError(f"{', '.join(unknown)} is not a unit of the plan")
    reopened = []
    for unit_id in sorted(set(wanted)):
        path = store.root(project) / unit_record(unit_id)
        if path.is_file():
            path.unlink()
            reopened.append(unit_id)
    return reopened
