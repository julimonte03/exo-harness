"""mcp/server: protocolo JSON-RPC por stdio (criterio 5 de F1)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from exo import _meta
from exo.mcp import server
from exo.tools import registry


def _ctx(tmp_path: Path) -> registry.Context:
    return registry.Context(tmp_path)


def _msg(msg_id: int | None, method: str, params: dict | None = None) -> dict:
    message: dict = {"jsonrpc": "2.0", "method": method}
    if msg_id is not None:
        message["id"] = msg_id
    if params is not None:
        message["params"] = params
    return message


# -- en proceso ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("requested", "expected"),
    [("2025-06-18", "2025-06-18"), ("2024-11-05", "2024-11-05"), ("1999-01-01", "2025-06-18"), (None, "2025-06-18")],
)
def test_initialize_negocia_version(tmp_path: Path, requested: str | None, expected: str) -> None:
    params = {"protocolVersion": requested} if requested else {}
    result = server.handle(_msg(1, "initialize", params), _ctx(tmp_path))["result"]
    assert result["protocolVersion"] == expected
    assert result["serverInfo"] == {"name": _meta.NAME, "version": _meta.VERSION}
    assert "tools" in result["capabilities"]


def test_notificaciones_no_responden(tmp_path: Path) -> None:
    assert server.handle(_msg(None, "notifications/initialized"), _ctx(tmp_path)) is None


def test_ping_y_metodo_desconocido(tmp_path: Path) -> None:
    assert server.handle(_msg(2, "ping"), _ctx(tmp_path))["result"] == {}
    error = server.handle(_msg(3, "resources/list"), _ctx(tmp_path))["error"]
    assert error["code"] == server.METHOD_NOT_FOUND


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ([1, 2], server.INVALID_REQUEST),
        ({"id": 1, "method": "ping"}, server.INVALID_REQUEST),
        ({"jsonrpc": "2.0", "id": 1}, server.INVALID_REQUEST),
        ({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": [1]}, server.INVALID_PARAMS),
        ({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "no_existe"}}, server.INVALID_PARAMS),
    ],
)
def test_errores_de_protocolo(tmp_path: Path, message: object, code: int) -> None:
    assert server.handle(message, _ctx(tmp_path))["error"]["code"] == code


def test_tools_call_ok_y_error_de_dominio(tmp_path: Path) -> None:
    ok = server.handle(_msg(4, "tools/call", {"name": "list_changes", "arguments": {}}), _ctx(tmp_path))
    assert ok["result"]["isError"] is False
    assert ok["result"]["structuredContent"] == {"changes": []}
    bad = server.handle(
        _msg(5, "tools/call", {"name": "get_change_state", "arguments": {"change_name": "../x"}}),
        _ctx(tmp_path),
    )
    assert bad["result"]["isError"] is True
    assert "inválido" in bad["result"]["content"][0]["text"]


def test_tool_que_falla_no_tira_el_servidor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(context: registry.Context, args: dict) -> dict:
        raise RuntimeError("explotó")

    tool = registry.get("list_changes")
    monkeypatch.setattr(registry, "_BY_NAME", {**registry._BY_NAME, "list_changes": tool.__class__(**{**tool.__dict__, "handler": boom})})
    result = server.handle(_msg(6, "tools/call", {"name": "list_changes"}), _ctx(tmp_path))["result"]
    assert result["isError"] is True
    assert "explotó" in result["content"][0]["text"]


def test_serve_en_proceso(tmp_path: Path) -> None:
    lines = [
        json.dumps(_msg(1, "initialize", {"protocolVersion": "2025-06-18"})),
        json.dumps(_msg(None, "notifications/initialized")),
        "",
        "{ no json",
        json.dumps(_msg(2, "tools/list")),
    ]
    out = io.BytesIO()
    assert server.serve(tmp_path, io.BytesIO(("\n".join(lines) + "\n").encode()), out) == 0
    responses = [json.loads(line) for line in out.getvalue().decode().splitlines()]
    assert [r.get("id") for r in responses] == [1, None, 2]
    assert responses[1]["error"]["code"] == server.PARSE_ERROR


# -- por subprocess (protocolo real) ------------------------------------------


def test_criterio_5_por_subprocess(tmp_path: Path) -> None:
    messages = [
        _msg(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}),
        _msg(None, "notifications/initialized"),
        _msg(2, "tools/list"),
        _msg(3, "tools/call", {"name": "get_change_state", "arguments": {"change_name": "../etc"}}),
        _msg(4, "tools/call", {"name": "skills_list", "arguments": {}}),
    ]
    payload = "".join(json.dumps(m) + "\n" for m in messages)
    proc = subprocess.run(
        [sys.executable, "-m", "exo", "mcp", "--project", str(tmp_path)],
        input=payload.encode("utf-8"),
        capture_output=True,
        timeout=60,
        check=True,
    )
    lines = proc.stdout.decode("utf-8").splitlines()
    responses = [json.loads(line) for line in lines]
    assert all(r["jsonrpc"] == "2.0" for r in responses), "stdout solo debe llevar JSON-RPC"
    by_id = {r["id"]: r for r in responses}
    assert sorted(by_id) == [1, 2, 3, 4]
    assert by_id[1]["result"]["protocolVersion"] == "2025-06-18"
    tools = by_id[2]["result"]["tools"]
    assert len(tools) == 7
    assert all("inputSchema" in t and t["inputSchema"]["type"] == "object" for t in tools)
    assert by_id[3]["result"]["isError"] is True
    assert by_id[4]["result"]["isError"] is False
    assert "hello-exo" in by_id[4]["result"]["content"][0]["text"]
