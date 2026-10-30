"""Servidor MCP por stdio, opcional (ADR-0005).

JSON-RPC 2.0, un mensaje por línea. stdout queda reservado al protocolo y los
logs van a stderr (invariante 9 de `docs/plan/02-ARQUITECTURA.md` §2.13). Los
errores de dominio (por ejemplo una entrada que no pasa S2) vuelven como
resultado con `isError: true`; los errores JSON-RPC son solo para fallas de
protocolo. Las tools salen de `exo.tools.registry`, las mismas que usa el CLI.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, BinaryIO

from exo import _meta
from exo.tools import registry
from exo.tools.validation import InputError

SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

log = logging.getLogger(f"{_meta.NAME}.mcp")


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _tool_result(payload: Any, *, is_error: bool) -> dict[str, Any]:
    text = (
        payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2)
    )
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if isinstance(payload, dict) and not is_error:
        result["structuredContent"] = payload
    return result


def _initialize(params: dict[str, Any]) -> dict[str, Any]:
    requested = params.get("protocolVersion")
    version = requested if requested in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": _meta.NAME, "version": _meta.VERSION},
        "instructions": (
            f"Tools de {_meta.DISPLAY_NAME}: skills y estado de changes SDD (solo lectura). "
            f"Cada tool tiene su equivalente en el CLI `{_meta.NAME}`."
        ),
    }


def _call_tool(params: dict[str, Any], context: registry.Context) -> dict[str, Any] | None:
    name = params.get("name")
    tool = registry.get(name) if isinstance(name, str) else None
    if tool is None:
        return None
    try:
        return _tool_result(
            registry.call(tool.name, params.get("arguments"), context), is_error=False
        )
    except InputError as exc:
        return _tool_result(str(exc), is_error=True)
    except Exception as exc:  # una tool nunca tira abajo el servidor
        log.exception("falló la tool %s", tool.name)
        return _tool_result(f"error interno en {tool.name}: {exc}", is_error=True)


def handle(message: Any, context: registry.Context) -> dict[str, Any] | None:
    """Respuesta a un mensaje, o None si es una notificación."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        msg_id = message.get("id") if isinstance(message, dict) else None
        return _error(msg_id, INVALID_REQUEST, "se espera un objeto JSON-RPC 2.0")
    method = message.get("method")
    msg_id = message.get("id")
    if not isinstance(method, str):
        return _error(msg_id, INVALID_REQUEST, "falta method")
    if "id" not in message:
        log.debug("notificación %s", method)
        return None
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _error(msg_id, INVALID_PARAMS, "params tiene que ser un objeto")
    if method == "initialize":
        return _result(msg_id, _initialize(params))
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": [tool.describe() for tool in registry.TOOLS]})
    if method == "tools/call":
        result = _call_tool(params, context)
        if result is None:
            return _error(msg_id, INVALID_PARAMS, f"tool desconocida: {params.get('name')!r}")
        return _result(msg_id, result)
    return _error(msg_id, METHOD_NOT_FOUND, f"método no soportado: {method}")


def _write(stream: BinaryIO, payload: dict[str, Any]) -> None:
    # ASCII: cualquier texto (incluso surrogates sueltos) sale como JSON válido.
    stream.write((json.dumps(payload, ensure_ascii=True) + "\n").encode("ascii"))
    stream.flush()


def _respond(line: bytes, context: registry.Context) -> dict[str, Any] | None:
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        return _error(None, PARSE_ERROR, f"JSON inválido: {exc}")
    try:
        return handle(message, context)
    except Exception as exc:  # el servidor nunca se cae por un mensaje
        log.exception("error procesando un mensaje")
        msg_id = message.get("id") if isinstance(message, dict) else None
        return _error(msg_id, INTERNAL_ERROR, f"error interno: {exc}")


def serve(
    project: Path,
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | None = None,
) -> int:
    """Atiende mensajes hasta EOF."""
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    context = registry.Context(Path(project).resolve())
    log.info("servidor MCP de %s %s en %s", _meta.NAME, _meta.VERSION, context.project)
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        response = _respond(line, context)
        if response is not None:
            _write(stdout, response)
    return 0
