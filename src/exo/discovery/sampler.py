"""R5, muestra y veredictos de la auditoría (F6, ADR-0015).

- **Población:** los FR de las specs con preámbulo (`as-is` o `as-is-validated`), que
  es lo que la persona valida, no las notas intermedias de las unidades.
- **Selección:** ponderada y sin reemplazo con claves exponenciales sacadas de
  `sha256(semilla|id)`. Es portable entre versiones de Python y no usa `random`. Un
  FR crítico (por las palabras de criticidad) pesa el doble, y cada capacidad tiene
  al menos uno si alcanza la muestra.
- **Semilla:** por defecto, la derivada del contenido (los IDs de la población), y
  queda registrada en `sample.json`.
- **Veredictos** (`audit.json`): correcto, incorrecto o no verificable, solo para
  los IDs de la muestra.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from exo.discovery import planner, store
from exo.sdd import specs

SAMPLE = "sample.json"
AUDIT = "audit.json"
VERDICTS = ("correct", "incorrect", "unverifiable")
DEFAULT_N = 30


class AuditError(ValueError):
    """No hay población, o los veredictos no corresponden a la muestra."""


def population(project: Path) -> list[dict[str, Any]]:
    project = Path(project)
    root = specs.capabilities_root(project)
    found: list[dict[str, Any]] = []
    if not root.is_dir():
        return found
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and p.name[0] not in "._"):
        path = folder / specs.SPEC_FILE
        if not path.is_file():
            continue
        cap = specs.parse_capability(path.read_bytes().decode("utf-8-sig"), folder.name)
        if cap.status is None:
            continue
        rel = path.relative_to(project).as_posix()
        for block in cap.requirements.values():
            if "-NFR-" in block.id:
                continue
            text = "\n".join(block.lines)
            found.append(
                {
                    "id": block.id,
                    "capability": folder.name,
                    "spec": rel,
                    "line": block.line,
                    "critical": bool(planner.criticality(f"{folder.name} {text}")),
                }
            )
    return sorted(found, key=lambda item: item["id"])


def default_seed(items: list[dict[str, Any]]) -> int:
    digest = hashlib.sha256("|".join(i["id"] for i in items).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _key(seed: int, item: dict[str, Any]) -> float:
    digest = hashlib.sha256(f"{seed}|{item['id']}".encode()).hexdigest()
    uniform = (int(digest[:13], 16) + 1) / (16**13 + 1)
    weight = 2.0 if item["critical"] else 1.0
    return -math.log(uniform) / weight


def choose(items: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    ranked = sorted(items, key=lambda i: (_key(seed, i), i["id"]))
    picked: list[dict[str, Any]] = []
    if n >= len({i["capability"] for i in items}):
        for capability in sorted({i["capability"] for i in items}):
            picked.append(next(i for i in ranked if i["capability"] == capability))
    for item in ranked:
        if len(picked) >= n:
            break
        if item not in picked:
            picked.append(item)
    return sorted(picked[:n], key=lambda i: i["id"])


def sample(project: Path, n: int = DEFAULT_N, seed: int | None = None) -> dict[str, Any]:
    items = population(project)
    if not items:
        raise AuditError("no as-is specs to audit yet: synthesize the capabilities first (R4)")
    used = default_seed(items) if seed is None else seed
    data = {"seed": used, "n": n, "population": len(items), "items": choose(items, n, used)}
    store.write_json(project, SAMPLE, data)
    return data


def record(project: Path, results: Any) -> dict[str, Any]:
    """Guarda los veredictos del auditor: `{"results": [{"id", "verdict", "note"}]}`."""
    current = store.read_json(project, SAMPLE)
    if current is None:
        raise AuditError("there is no sample yet: run the sample step first")
    wanted = {i["id"] for i in current["items"]}
    rows = results.get("results") if isinstance(results, dict) else None
    if not isinstance(rows, list):
        raise AuditError('the results must be {"results": [{"id", "verdict", "note"}]}')
    clean: dict[str, dict[str, str]] = {}
    problems: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            problems.append(f"bad result: {row!r}")
            continue
        if row["id"] not in wanted:
            problems.append(f"{row['id']} is not in the sample")
        elif row.get("verdict") not in VERDICTS:
            problems.append(f"{row['id']}: verdict must be one of {', '.join(VERDICTS)}")
        else:
            clean[row["id"]] = {"verdict": row["verdict"], "note": str(row.get("note", ""))}
    if problems:
        raise AuditError("; ".join(problems))
    missing = sorted(wanted - set(clean))
    data = {
        "seed": current["seed"],
        "results": [{"id": k, **v} for k, v in sorted(clean.items())],
        "missing": missing,
    }
    store.write_json(project, AUDIT, data)
    return data
