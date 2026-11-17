"""Lectura y escritura de `<carpeta del motor>/discovery/` (ADR-0015).

Los JSON se escriben deterministas (claves ordenadas, indentados, salto final) y solo
si cambian, con `"schema"`: un motor más viejo rechaza un esquema más nuevo. Nada que
varíe entre corridas iguales (sha de HEAD, versión del motor, fechas) entra acá.

"Si cambian" ignora los fines de línea: en un checkout de Windows con `core.autocrlf`
los archivos commiteados tienen CRLF, y reescribirlos con LF sería un cambio falso.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import fsutil

SCHEMA = 1
FOLDER = "discovery"


class DiscoveryError(ValueError):
    """El estado de discovery no se puede usar: falta, está roto o es de un motor más nuevo."""


def root(project: Path) -> Path:
    return Path(project) / _meta.PROJECT_DIR / FOLDER


def rel(name: str) -> str:
    """La ruta, relativa al proyecto, de un archivo de discovery (con /)."""
    return f"{_meta.PROJECT_DIR}/{FOLDER}/{name}"


def dumps(payload: dict[str, Any]) -> bytes:
    data = {"schema": SCHEMA, **payload}
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _write(project: Path, name: str, data: bytes) -> bool:
    """Escribe `discovery/<name>` si cambió algo más que los fines de línea."""
    path = fsutil.join_within(Path(project), rel(name))
    try:
        if _lf(fsutil.read_bytes(path)) == _lf(data):
            return False
    except (FileNotFoundError, IsADirectoryError):
        pass
    fsutil.write_atomic(path, data)
    return True


def write_json(project: Path, name: str, payload: dict[str, Any]) -> bool:
    """Escribe `discovery/<name>` si cambió. Devuelve si escribió."""
    return _write(project, name, dumps(payload))


def write_text(project: Path, name: str, text: str) -> bool:
    return _write(project, name, text.encode("utf-8"))


def read_json(project: Path, name: str) -> dict[str, Any] | None:
    """El JSON de `discovery/<name>`, o None si no existe."""
    path = root(project) / name
    try:
        text = fsutil.read_text_auto(path)
    except FileNotFoundError:
        return None
    except ValueError as exc:  # ni UTF-8 ni UTF-16
        raise DiscoveryError(f"{rel(name)} is not UTF-8 text; run the step again") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DiscoveryError(f"{rel(name)} is not valid JSON ({exc}); run the step again") from exc
    if not isinstance(data, dict):
        raise DiscoveryError(f"{rel(name)} must be a JSON object; run the step again")
    schema = data.get("schema")
    if not isinstance(schema, int) or schema > SCHEMA:
        raise DiscoveryError(
            f"{rel(name)} has schema {schema!r}, newer than this engine ({SCHEMA}); "
            f"update {_meta.NAME}"
        )
    return data
