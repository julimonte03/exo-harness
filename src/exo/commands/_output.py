"""Salida común del CLI: JSON en UTF-8 con versión de esquema y errores a stderr."""

from __future__ import annotations

import json
import sys
from typing import Any

JSON_SCHEMA = 1


def emit_json(payload: dict[str, Any]) -> None:
    """Imprime `{"schema": 1, …}` en UTF-8, sin depender de la consola."""
    text = json.dumps({"schema": JSON_SCHEMA, **payload}, ensure_ascii=False, indent=2) + "\n"
    stream = sys.stdout
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(text)
        return
    stream.flush()
    buffer.write(text.encode("utf-8"))
    buffer.flush()


def error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def usage_error(message: str) -> int:
    print(f"usage error: {message}", file=sys.stderr)
    return 2
