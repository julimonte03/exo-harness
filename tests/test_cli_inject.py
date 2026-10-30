"""`exo inject` y la base del CLI (`exo version`, salida --json, errores)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from exo import _meta
from exo.cli import main

B = f"<!-- BEGIN:{_meta.BLOCK_PREFIX}:core -->"
E = f"<!-- END:{_meta.BLOCK_PREFIX}:core -->"


def _json(capsys: pytest.CaptureFixture[str]) -> dict:
    return json.loads(capsys.readouterr().out)


def test_version_subcomando(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == f"{_meta.NAME} {_meta.VERSION}"
    assert main(["version", "--json"]) == 0
    assert _json(capsys) == {"schema": 1, "name": _meta.NAME, "version": _meta.VERSION}


def test_inject_crea_y_es_idempotente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "AGENTS.md"
    assert main(["inject", str(target), "--id", "core", "--content", "regla"]) == 0
    assert "actualizado" in capsys.readouterr().out
    assert target.read_text(encoding="utf-8") == f"{B}\nregla\n{E}\n"
    assert main(["inject", str(target), "--id", "core", "--content", "regla", "--json"]) == 0
    assert _json(capsys) == {
        "schema": 1,
        "action": "inject",
        "path": str(target),
        "block": "core",
        "changed": False,
    }


def test_inject_desde_archivo_y_al_principio(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "bloque.txt"
    source.write_text("desde archivo\n", encoding="utf-8")
    target = tmp_path / "CLAUDE.md"
    target.write_text("# Mío\n", encoding="utf-8")
    code = main(
        ["inject", str(target), "--id", "core", "--from", str(source), "--position", "start"]
    )
    assert code == 0
    assert target.read_text(encoding="utf-8") == f"{B}\ndesde archivo\n{E}\n\n# Mío\n"


def test_inject_desde_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("por stdin\n"))
    target = tmp_path / "AGENTS.md"
    assert main(["inject", str(target), "--id", "core", "--from", "-"]) == 0
    assert "por stdin" in target.read_text(encoding="utf-8")


def test_inject_list_y_remove(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("# Humano\n", encoding="utf-8")
    main(["inject", str(target), "--id", "core", "--content", "a"])
    capsys.readouterr()
    assert main(["inject", str(target), "--list", "--json"]) == 0
    assert _json(capsys)["blocks"] == [
        {"id": "core", "start_line": 3, "end_line": 5, "content": "a"}
    ]
    assert main(["inject", str(target), "--list"]) == 0
    assert "core" in capsys.readouterr().out
    assert main(["inject", str(target), "--id", "core", "--remove"]) == 0
    assert "quitado" in capsys.readouterr().out
    assert target.read_text(encoding="utf-8") == "# Humano\n"
    assert main(["inject", str(target), "--id", "core", "--remove"]) == 0
    assert "no estaba" in capsys.readouterr().out


def test_inject_con_backup_y_estilo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "notas.txt"
    target.write_text("x\n", encoding="utf-8")
    code = main(
        ["inject", str(target), "--id", "core", "--content", "y", "--style", "hash", "--backup"]
    )
    assert code == 0
    assert (tmp_path / f"notas.txt.{_meta.NAME}.bak").read_text(encoding="utf-8") == "x\n"
    assert f"# BEGIN:{_meta.BLOCK_PREFIX}:core" in target.read_text(encoding="utf-8")


def test_inject_error_de_marcadores(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text(f"{B}\nsin cierre\n", encoding="utf-8")
    assert main(["inject", str(target), "--id", "core", "--content", "x"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "sin su END" in err


def test_inject_requiere_id_y_contenido(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "AGENTS.md"
    assert main(["inject", str(target), "--content", "x"]) == 2
    assert "--id" in capsys.readouterr().err
    assert main(["inject", str(target), "--id", "core"]) == 2
    assert "--content" in capsys.readouterr().err


def test_grupo_sin_subcomando_muestra_ayuda(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["no-existe"])
    assert exc.value.code == 2
