"""Waivers de protección de datos (D-12, ADR-0014).

`<carpeta del motor>/waivers.json` lista excepciones aprobadas y con vencimiento
para datos personales (nivel Restringido) en rutas concretas, por ejemplo datos
sintéticos de tests. Es del humano: el motor no lo genera ni lo registra en el
lock. Un secreto (nivel Crítico) nunca tiene waiver.

La lectura es tolerante: un archivo roto o una entrada inválida no cubre nada y
queda en `problems`, para que el hook o `exo check` lo informen.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from exo import _meta
from exo.core import fsutil, jsonschema, scan

FILENAME = "waivers.json"
SCHEMA_FILE = Path(__file__).resolve().parents[1] / "sdd" / "schemas" / "waivers.schema.json"


@dataclass(frozen=True)
class Waiver:
    detector: str
    path: str
    reason: str
    approved_by: str
    expires: date


@dataclass
class Waivers:
    active: list[Waiver] = field(default_factory=list)
    expired: list[Waiver] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def path_for(project: Path) -> Path:
    return Path(project) / _meta.PROJECT_DIR / FILENAME


def load(project: Path, *, today: date | None = None) -> Waivers:
    today = today or datetime.now(timezone.utc).date()
    path = path_for(project)
    result = Waivers()
    try:
        data = json.loads(fsutil.read_bytes(path).decode("utf-8-sig"))
    except FileNotFoundError:
        return result
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result.problems.append(f"{FILENAME} is not valid JSON ({exc}); no waiver applies")
        return result
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = jsonschema.validate(data, schema)
    if errors:
        result.problems += [f"{FILENAME}: {error}" for error in errors]
        return result
    for item in data["waivers"]:
        try:
            expires = date.fromisoformat(item["expires"])
        except ValueError:
            result.problems.append(f"{FILENAME}: expires {item['expires']!r} is not a date")
            continue
        waiver = Waiver(
            item["detector"], item["path"], item["reason"], item["approved_by"], expires
        )
        (result.active if expires >= today else result.expired).append(waiver)
    return result


def covers(loaded: Waivers, finding: scan.Finding, rel_path: str) -> Waiver | None:
    """El waiver vigente que permite este hallazgo en esta ruta, si hay uno."""
    if finding.level != scan.RESTRICTED:
        return None
    posix = rel_path.replace("\\", "/")
    for waiver in loaded.active:
        if waiver.detector == finding.kind and fnmatch.fnmatchcase(posix, waiver.path):
            return waiver
    return None
