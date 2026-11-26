"""Tools de memoria en el registro (criterio 8 de F3: los 15 nombres del §5.3) y por MCP."""

from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

import pytest

from exo.mcp import server
from exo.tools import registry
from exo.tools.validation import InputError, check_arguments

MEMORY_TOOLS = [
    "mem_save",
    "mem_search",
    "mem_list",
    "mem_get",
    "mem_context",
    "mem_delete",
    "mem_session_start",
    "mem_session_end",
    "mem_session_summary",
    "mem_session_show",
    "mem_projects_list",
    "mem_projects_merge",
    "mem_projects_consolidate",
    "mem_stats",
    "mem_detect_project",
]
P = "github.com/acme/api"


@pytest.fixture
def ctx(tmp_path: Path) -> registry.Context:
    root = tmp_path / "Repo"
    root.mkdir()
    return registry.Context(root)


def call(ctx: registry.Context, name: str, **args):
    return registry.call(name, args, ctx)


def test_criterio_8_los_15_nombres() -> None:
    names = [t.name for t in registry.TOOLS if t.name.startswith("mem_")]
    assert names == MEMORY_TOOLS
    for name in MEMORY_TOOLS:
        assert registry.get(name).cli[0] == "mem"


def test_save_search_get_delete(ctx: registry.Context) -> None:
    saved = call(
        ctx, "mem_save", project=P, title="Timeout", content="PROJ-1234: 30 s", type="bugfix"
    )
    assert saved["action"] == "created"
    found = call(ctx, "mem_search", project=P, query="PROJ-1234")
    assert [r["id"] for r in found["results"]] == [saved["id"]]
    assert found["results"][0]["preview"] == "PROJ-1234: 30 s"
    full = call(ctx, "mem_get", id=saved["id"])
    assert (full["title"], full["content"], full["type"]) == (
        "Timeout",
        "PROJ-1234: 30 s",
        "bugfix",
    )
    assert call(ctx, "mem_delete", id=saved["id"]) == {"id": saved["id"], "deleted": True}
    with pytest.raises(InputError, match="not found"):
        call(ctx, "mem_get", id=saved["id"])


def test_el_proyecto_se_detecta_desde_cwd(ctx: registry.Context) -> None:
    detected = call(ctx, "mem_detect_project")
    assert (detected["name"], detected["source"]) == ("local/repo", "folder")
    saved = call(ctx, "mem_save", title="Nota", content="sin proyecto explícito")
    assert call(ctx, "mem_get", id=saved["id"])["project"] == "local/repo"
    assert [p["name"] for p in call(ctx, "mem_projects_list")["projects"]] == ["local/repo"]
    assert call(ctx, "mem_search", query="explícito")["project"] == "local/repo"
    assert call(ctx, "mem_search", query="explícito", project="otro/proyecto")["results"] == []
    assert len(call(ctx, "mem_search", query="explícito", all_projects=True)["results"]) == 1


def test_list_context_y_stats(ctx: registry.Context) -> None:
    for i in range(3):
        call(ctx, "mem_save", project=P, title=f"Decisión {i}", content="detalle", type="decision")
    listed = call(ctx, "mem_list", project=P, limit=2)
    assert [o["title"] for o in listed["observations"]] == ["Decisión 2", "Decisión 1"]
    assert "content" not in listed["observations"][0]
    context = call(ctx, "mem_context", project=P)
    assert "Decisión 2" in context["context"]
    stats = call(ctx, "mem_stats")
    assert (stats["observations"], stats["by_type"]) == (3, {"decision": 3})


def test_sesiones(ctx: registry.Context) -> None:
    session = call(ctx, "mem_session_start", project=P, agent="claude-code")
    call(ctx, "mem_save", project=P, title="Hecho", content="algo", session_id=session["id"])
    summary = call(ctx, "mem_session_summary", project=P, content="Quedó el retry.")
    assert summary["session_id"] == session["id"]
    ended = call(ctx, "mem_session_end", session_id=session["id"])
    assert ended["ended_at"] is not None
    shown = call(ctx, "mem_session_show", project=P)
    assert shown["session"]["summary"] == "Quedó el retry."
    assert [o["title"] for o in shown["observations"]] == ["Hecho"]


def test_merge_y_consolidate(ctx: registry.Context) -> None:
    call(ctx, "mem_save", project="https://github.com/Acme/Api.git", title="a", content="1")
    call(ctx, "mem_save", project="old/api", title="b", content="2")
    assert call(ctx, "mem_projects_consolidate", dry_run=True) == {
        "dry_run": True,
        "merges": {P: ["https://github.com/Acme/Api.git"]},
    }
    call(ctx, "mem_projects_consolidate")
    merged = call(ctx, "mem_projects_merge", source="old/api", target=P)
    assert (merged["moved"], merged["target"]) == (1, P)
    assert sorted(p["name"] for p in call(ctx, "mem_projects_list")["projects"]) == [P]


@pytest.mark.parametrize(
    ("tool", "args", "fragment"),
    [
        ("mem_get", {"id": "7"}, "integer"),
        ("mem_get", {"id": True}, "integer"),
        ("mem_get", {}, "missing"),
        ("mem_search", {"query": "x", "limit": 0}, "limit"),
        ("mem_search", {"query": "x", "limit": 101}, "limit"),
        ("mem_save", {"title": "t", "content": "c", "scope": "equipo"}, "scope"),
        ("mem_save", {"title": "t" * 201, "content": "c"}, "title"),
        ("mem_save", {"title": "t", "content": "c", "extra": 1}, "unknown"),
        ("mem_search", {"query": ""}, "query"),
    ],
)
def test_validacion_de_argumentos(
    ctx: registry.Context, tool: str, args: dict, fragment: str
) -> None:
    with pytest.raises(InputError, match=fragment):
        registry.call(tool, args, ctx)


def test_check_arguments_enteros() -> None:
    schema = {
        "type": "object",
        "properties": {"n": {"type": "integer", "minimum": 1, "maximum": 3}},
    }
    assert check_arguments(schema, {"n": 2}) == {"n": 2}
    with pytest.raises(InputError, match="between 1 and 3"):
        check_arguments(schema, {"n": 4})


def test_error_de_sqlite_es_error_de_dominio(
    ctx: registry.Context, monkeypatch: pytest.MonkeyPatch
) -> None:
    from exo.memory import store

    def broken(self, *args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(store.MemoryStore, "stats", broken)
    with pytest.raises(InputError, match="database is locked"):
        call(ctx, "mem_stats")


# -- por MCP ----------------------------------------------------------------------------


def _mcp(project: Path, *messages: dict) -> list[dict]:
    lines = b"".join((json.dumps(m) + "\n").encode() for m in messages)
    out = io.BytesIO()
    server.serve(project, io.BytesIO(lines), out)
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_mcp_lista_y_llama_tools_de_memoria(ctx: registry.Context) -> None:
    save = {"name": "mem_save", "arguments": {"project": P, "title": "Por MCP", "content": "hola"}}
    search = {"name": "mem_search", "arguments": {"project": P, "query": "hola"}}
    listed, saved, found = _mcp(
        ctx.project,
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": save},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": search},
    )
    names = [t["name"] for t in listed["result"]["tools"]]
    assert set(MEMORY_TOOLS) <= set(names)
    assert saved["result"]["isError"] is False
    assert found["result"]["structuredContent"]["results"][0]["title"] == "Por MCP"


def test_mcp_stdout_protegido_de_lo_que_imprime_una_tool(
    ctx: registry.Context, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Invariante 9. `_mcp` le pasa a `serve` su propio stream de salida, así que la
    respuesta sale limpia haya o no redirect: lo que lo prueba es adónde fue el `print`
    (auditoría de la adopción de exo, F8)."""
    real = registry.get("mem_stats")

    def noisy(context, args):
        print("barra de progreso de una librería")
        return real.handler(context, args)

    monkeypatch.setitem(
        registry._BY_NAME,
        "mem_stats",
        registry.Tool(real.name, real.description, real.input_schema, noisy, real.cli),
    )
    (reply,) = _mcp(
        ctx.project,
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "mem_stats"}},
    )
    assert reply["result"]["isError"] is False
    printed = capsys.readouterr()
    assert "barra de progreso" in printed.err
    assert "barra de progreso" not in printed.out  # el stdout real del proceso es del protocolo
