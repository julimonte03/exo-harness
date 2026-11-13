"""`exo mem …`: CLI de la memoria (mismo registro que el MCP) y export/import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import paths
from exo.cli import main
from exo.memory.store import MemoryStore

P = "github.com/acme/api"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "Servicio"
    root.mkdir()
    return root


def mem(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    capsys.readouterr()
    code = main(["mem", *argv])
    out = capsys.readouterr()
    return code, out.out + out.err


def mem_json(capsys: pytest.CaptureFixture[str], *argv: str) -> dict:
    code, out = mem(capsys, *argv, "--json")
    assert code == 0, out
    return json.loads(out)


def test_save_search_get(capsys: pytest.CaptureFixture[str], repo: Path) -> None:
    code, out = mem(
        capsys,
        "save",
        "--cwd",
        str(repo),
        "--title",
        "Usar colas",
        "--content",
        "Para pagos usamos colas.",
        "--type",
        "decision",
    )
    assert code == 0 and "guardada #1 (created)" in out
    code, out = mem(capsys, "search", "colas", "--cwd", str(repo))
    assert code == 0 and "#1" in out and "Usar colas" in out
    code, out = mem(capsys, "get", "1")
    assert "Para pagos usamos colas." in out and "local/servicio" in out
    assert mem_json(capsys, "list", "--cwd", str(repo))["observations"][0]["title"] == "Usar colas"


def test_contenido_desde_stdin_y_topic_key(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("contenido largo\ncon saltos\n"))
    result = mem_json(
        capsys,
        "save",
        "--project",
        P,
        "--title",
        "Perfil",
        "--content",
        "-",
        "--topic-key",
        "project/profile",
    )
    assert result["action"] == "created"
    assert mem_json(capsys, "get", str(result["id"]))["content"] == "contenido largo\ncon saltos\n"


def test_context_imprime_texto(capsys: pytest.CaptureFixture[str]) -> None:
    mem_json(capsys, "save", "--project", P, "--title", "Gotcha", "--content", "UTC siempre")
    code, out = mem(capsys, "context", "--project", P)
    assert code == 0 and out.startswith("# Memoria de") and "Gotcha" in out


def test_sesiones_por_cli(capsys: pytest.CaptureFixture[str]) -> None:
    session = mem_json(capsys, "session", "start", "--project", P, "--agent", "claude-code")
    code, out = mem(capsys, "session", "summary", "--project", P, "--content", "Hecho X, falta Y.")
    assert code == 0 and f"sesión #{session['id']}" in out
    assert mem_json(capsys, "session", "end", str(session["id"]))["ended_at"]
    code, out = mem(capsys, "session", "show", "--project", P)
    assert "Hecho X, falta Y." in out


def test_projects_y_stats(capsys: pytest.CaptureFixture[str]) -> None:
    mem_json(
        capsys,
        "save",
        "--project",
        "https://github.com/Acme/Api.git",
        "--title",
        "a",
        "--content",
        "1",
    )
    code, out = mem(capsys, "projects", "consolidate", "--dry-run")
    assert "https://github.com/Acme/Api.git -> github.com/acme/api" in out
    mem(capsys, "projects", "consolidate")
    code, out = mem(capsys, "projects", "list")
    assert P in out
    assert mem_json(capsys, "stats")["observations"] == 1
    code, out = mem(capsys, "projects", "detect", "--cwd", ".")
    assert code == 0


def test_errores(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = mem(capsys, "get", "99")
    assert code == 1 and "no existe" in out
    code, out = mem(capsys, "delete", "99")
    assert code == 1 and "no existe" in out
    code, out = mem(capsys, "search", "x", "--limit", "500")
    assert code == 1 and "limit" in out


def test_export_e_import(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mem_json(capsys, "save", "--project", P, "--title", "Decisión", "--content", "colas")
    mem_json(capsys, "save", "--project", "local/otro", "--title", "Otra", "--content", "x")
    out_file = tmp_path / "export.json"
    code, out = mem(capsys, "export", "--project", P, "--output", str(out_file))
    assert code == 0 and "1 observación" in out
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert [o["title"] for o in data["observations"]] == ["Decisión"]
    code, out = mem(capsys, "export", "--all")
    assert len(json.loads(out)["observations"]) == 2
    monkeypatch.setenv(paths.ENV_MEMORY_DB, str(tmp_path / "otra.db"))
    code, out = mem(capsys, "import", str(out_file))
    assert code == 0 and "1 creadas" in out
    with MemoryStore(tmp_path / "otra.db") as store:
        assert store.list(P)[0].title == "Decisión"
    bad = tmp_path / "malo.json"
    bad.write_text("{ roto", encoding="utf-8")
    code, out = mem(capsys, "import", str(bad))
    assert code == 1 and "JSON" in out
