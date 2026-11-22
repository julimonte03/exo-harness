"""Overlays de persona (D-17, ADR-0018).

El rol de la persona se guarda en su carpeta de datos (`persona.json`), nunca en el
repo. El overlay de cada rol es un contrato del pack `core` que se instala en
`<carpeta del motor>/shared/personas/<rol>.md`; el agente lo lee si hay rol y lo sigue
sin relajar ninguna regla, gate ni aprobación.
"""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath

from exo import _meta, paths
from exo.core import fsutil

ROLES = ("dev", "tech-lead", "qa", "product")
FILE_NAME = "persona.json"
SCHEMA = 1
MAX_OVERLAY_LINES = 40


class PersonaError(ValueError):
    """`persona.json` no se puede leer o tiene un rol desconocido."""


def file_path() -> Path:
    return paths.user_data_dir() / FILE_NAME


def overlay_path(role: str) -> PurePosixPath:
    """Ruta del overlay dentro del proyecto, relativa a su raíz."""
    return PurePosixPath(_meta.PROJECT_DIR, "shared", "personas", f"{role}.md")


def _broken(target: Path, why: str) -> PersonaError:
    return PersonaError(
        f"{target}: {why}; run `{_meta.NAME} persona clear` and set it again "
        f"with `{_meta.NAME} persona set <role>`"
    )


def read() -> str | None:
    """El rol guardado, o None si no hay. Un archivo dañado es un error accionable."""
    target = file_path()
    try:
        raw = fsutil.read_bytes(target)
    except FileNotFoundError:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _broken(target, f"not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise _broken(target, "expected a JSON object")
    if data.get("schema") != SCHEMA:
        raise _broken(target, f"unsupported schema {data.get('schema')!r} (expected {SCHEMA})")
    role = data.get("persona")
    if role not in ROLES:
        raise _broken(target, f"unknown role {role!r} (valid: {', '.join(ROLES)})")
    return str(role)


def write(role: str) -> bool:
    """Guarda el rol. Devuelve si escribió (idempotente: el mismo rol no reescribe)."""
    if role not in ROLES:
        raise PersonaError(f"unknown role {role!r} (valid: {', '.join(ROLES)})")
    data = json.dumps({"schema": SCHEMA, "persona": role}, indent=2) + "\n"
    return fsutil.write_if_changed(file_path(), data.encode("utf-8"))


def clear() -> bool:
    """Borra el rol guardado, aunque el archivo esté dañado. Devuelve si había uno."""
    try:
        os.unlink(file_path())
    except FileNotFoundError:
        return False
    return True
