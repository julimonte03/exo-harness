"""Criterio 4 de F3: el servidor MCP y el CLI escriben y leen a la vez, sin errores de lock.

Dos procesos sobre la misma base con índice semántico (hybrid-sqlite: sqlite-vec si
está instalado, si no el backend de Python). Los dos usan el proveedor falso de los
tests, así no dependen de modelos bajados.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _memory_fakes import FakeProvider
from exo import paths
from exo.memory import embeddings
from exo.memory.store import MemoryStore

TESTS = Path(__file__).resolve().parent
N = 60
P = "github.com/acme/api"

_PATCH = (
    "from _memory_fakes import FakeProvider\n"
    "from exo.memory import embeddings\n"
    "embeddings.FACTORIES['fake'] = lambda model, allow_remote: FakeProvider(model)\n"
)

_SERVER = _PATCH + ("import sys\nfrom exo.mcp import server\nsys.exit(server.serve(sys.argv[1]))\n")

_CLI = _PATCH + (
    "import sys\n"
    "from exo.cli import main\n"
    "for i in range(int(sys.argv[1])):\n"
    "    for argv in (\n"
    "        ['mem', 'save', '--project', sys.argv[2], '--title', f'cli {i}',\n"
    "         '--content', f'colas desde el cli {i}', '--json'],\n"
    "        ['mem', 'search', 'colas', '--project', sys.argv[2], '--json'],\n"
    "    ):\n"
    "        if main(argv) != 0:\n"
    "            sys.exit(f'falló {argv}')\n"
)


def _messages(n: int) -> bytes:
    lines = []
    for i in range(n):
        save = {
            "name": "mem_save",
            "arguments": {
                "project": P,
                "title": f"mcp {i}",
                "content": f"colas desde el servidor {i}",
            },
        }
        search = {"name": "mem_search", "arguments": {"project": P, "query": "colas"}}
        lines.append({"jsonrpc": "2.0", "id": 2 * i, "method": "tools/call", "params": save})
        lines.append({"jsonrpc": "2.0", "id": 2 * i + 1, "method": "tools/call", "params": search})
    return b"".join((json.dumps(m) + "\n").encode() for m in lines)


@pytest.mark.parametrize("semantic", [True, False], ids=["hybrid-sqlite", "lexical"])
def test_criterio_4_mcp_y_cli_a_la_vez(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, semantic: bool
) -> None:
    db_path = tmp_path / "memory.db"
    monkeypatch.setitem(
        embeddings.FACTORIES, "fake", lambda model, allow_remote: FakeProvider(model)
    )
    with MemoryStore(db_path) as store:
        if semantic:
            store.reindex(provider="fake")
    env = {
        **os.environ,
        paths.ENV_MEMORY_DB: str(db_path),
        "PYTHONPATH": os.pathsep.join([str(TESTS), *sys.path]),
    }
    server = subprocess.Popen(
        [sys.executable, "-c", _SERVER, str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    cli = subprocess.Popen(
        [sys.executable, "-c", _CLI, str(N), P],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    server_out, server_err = server.communicate(_messages(N), timeout=300)
    cli_out, cli_err = cli.communicate(timeout=300)
    assert server.returncode == 0, server_err.decode(errors="replace")
    assert cli.returncode == 0, cli_err.decode(errors="replace")
    for stream in (server_err, cli_err):
        assert b"locked" not in stream and b"Traceback" not in stream, stream.decode(
            errors="replace"
        )
    replies = [json.loads(line) for line in server_out.splitlines()]
    assert len(replies) == 2 * N
    assert all(r["result"]["isError"] is False for r in replies), [
        r for r in replies if r["result"]["isError"]
    ][:1]
    with MemoryStore(db_path) as store:
        assert store.stats().observations == 2 * N
        if semantic:
            assert store.semantic is not None
            assert store.semantic.missing(store.conn) == 0
            assert store.query("mensajeria", project=P).mode == "hybrid"
