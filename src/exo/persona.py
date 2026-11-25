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


def _newer(target: Path, schema: int) -> PersonaError:
    """Un esquema más nuevo no es un archivo dañado: lo escribió otra versión del motor."""
    return PersonaError(
        f"{target} was written by a newer {_meta.NAME} (schema {schema}; this engine "
        f"understands up to {SCHEMA}); upgrade {_meta.NAME} to use it"
    )


def _is_newer(schema: object) -> bool:
    return isinstance(schema, int) and not isinstance(schema, bool) and schema > SCHEMA


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
    if _is_newer(data.get("schema")):
        raise _newer(target, data["schema"])
    if data.get("schema") != SCHEMA:
        raise _broken(target, f"unsupported schema {data.get('schema')!r} (expected {SCHEMA})")
    role = data.get("persona")
    if role not in ROLES:
        raise _broken(target, f"unknown role {role!r} (valid: {', '.join(ROLES)})")
    return str(role)


def _schema_on_disk(target: Path) -> object:
    try:
        data = json.loads(fsutil.read_bytes(target).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data.get("schema") if isinstance(data, dict) else None


def write(role: str) -> bool:
    """Guarda el rol. Devuelve si escribió (idempotente: el mismo rol no reescribe). No pisa
    el archivo de un motor más nuevo; uno dañado, sí."""
    if role not in ROLES:
        raise PersonaError(f"unknown role {role!r} (valid: {', '.join(ROLES)})")
    data = json.dumps({"schema": SCHEMA, "persona": role}, indent=2) + "\n"
    target = file_path()
    on_disk = _schema_on_disk(target)
    if _is_newer(on_disk):
        raise _newer(target, on_disk)  # type: ignore[arg-type]
    paths.private_dir(target.parent)
    return fsutil.write_if_changed(target, data.encode("utf-8"), mode=paths.PRIVATE_FILE)


def clear() -> bool:
    """Borra el rol guardado, aunque el archivo esté dañado. Devuelve si había uno."""
    try:
        os.unlink(file_path())
    except FileNotFoundError:
        return False
    return True
