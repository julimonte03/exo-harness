"""core/structmerge: merge por clave en JSON sin tocar el resto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo.core import structmerge
from exo.core.structmerge import StructMergeError

SERVER = {"command": "exo", "args": ["mcp"]}


def test_crea_archivo_y_claves_intermedias(tmp_path: Path) -> None:
    target = tmp_path / ".mcp.json"
    assert structmerge.merge_json_key(target, "mcpServers.exo", SERVER) is True
    assert json.loads(target.read_text()) == {"mcpServers": {"exo": SERVER}}
    assert target.read_bytes().endswith(b"}\n")


def test_conserva_el_resto_orden_e_indentacion(tmp_path: Path) -> None:
    target = tmp_path / ".mcp.json"
    target.write_bytes(
        b'{\n    "z": 1,\n    "mcpServers": {\n'
        b'        "otro": {"command": "x"}\n    },\n    "a": 2\n}'
    )
    structmerge.merge_json_key(target, "mcpServers.exo", SERVER)
    text = target.read_text()
    data = json.loads(text)
    assert list(data) == ["z", "mcpServers", "a"]
    assert list(data["mcpServers"]) == ["otro", "exo"]
    assert data["mcpServers"]["otro"] == {"command": "x"}
    assert '\n    "z": 1' in text
    assert not text.endswith("\n")


def test_conserva_crlf_y_tabs(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_bytes(b'{\r\n\t"a": 1\r\n}\r\n')
    structmerge.merge_json_key(target, "b", True)
    raw = target.read_bytes()
    assert raw == b'{\r\n\t"a": 1,\r\n\t"b": true\r\n}\r\n'


def test_idempotente(tmp_path: Path) -> None:
    target = tmp_path / ".mcp.json"
    structmerge.merge_json_key(target, "mcpServers.exo", SERVER)
    before = target.read_bytes()
    assert structmerge.merge_json_key(target, "mcpServers.exo", dict(SERVER)) is False
    assert target.read_bytes() == before


def test_jsonc_da_error_tipado_y_no_toca_el_archivo(tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    original = b'{\n  // comentario\n  "servers": {}\n}\n'
    target.write_bytes(original)
    with pytest.raises(StructMergeError, match="JSON válido"):
        structmerge.merge_json_key(target, "servers.exo", SERVER)
    assert target.read_bytes() == original


def test_raiz_que_no_es_objeto(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_bytes(b"[1]")
    with pytest.raises(StructMergeError, match="objeto"):
        structmerge.merge_json_key(target, "a", 1)


def test_intermedio_que_no_es_objeto(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_bytes(b'{"mcpServers": []}')
    with pytest.raises(StructMergeError, match="mcpServers"):
        structmerge.merge_json_key(target, "mcpServers.exo", SERVER)
    assert target.read_bytes() == b'{"mcpServers": []}'


@pytest.mark.parametrize("bad", ["", ".", "a..b", ".a", "a."])
def test_clave_invalida(tmp_path: Path, bad: str) -> None:
    with pytest.raises(StructMergeError, match="clave"):
        structmerge.merge_json_key(tmp_path / "x.json", bad, 1)


def test_get_json_key(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    assert structmerge.get_json_key(target, "a") is structmerge.MISSING
    structmerge.merge_json_key(target, "a.b", 3)
    assert structmerge.get_json_key(target, "a.b") == 3
    assert structmerge.get_json_key(target, "a.c") is structmerge.MISSING
    assert structmerge.get_json_key(target, "a.b.c") is structmerge.MISSING


def test_remove_json_key(tmp_path: Path) -> None:
    target = tmp_path / ".mcp.json"
    target.write_bytes(b'{\n  "mcpServers": {\n    "otro": 1\n  }\n}\n')
    structmerge.merge_json_key(target, "mcpServers.exo", SERVER)
    assert structmerge.remove_json_key(target, "mcpServers.exo") is True
    assert target.read_bytes() == b'{\n  "mcpServers": {\n    "otro": 1\n  }\n}\n'
    assert structmerge.remove_json_key(target, "mcpServers.exo") is False
    assert structmerge.remove_json_key(tmp_path / "no.json", "a") is False


def test_remove_con_poda_de_padres_vacios(tmp_path: Path) -> None:
    target = tmp_path / ".mcp.json"
    target.write_bytes(b'{\n  "otra": 1\n}\n')
    structmerge.merge_json_key(target, "mcpServers.exo", SERVER)
    structmerge.remove_json_key(target, "mcpServers.exo", prune_empty=True)
    assert target.read_bytes() == b'{\n  "otra": 1\n}\n'


def test_remove_sin_poda_deja_el_padre(tmp_path: Path) -> None:
    target = tmp_path / ".mcp.json"
    structmerge.merge_json_key(target, "mcpServers.exo", SERVER)
    structmerge.remove_json_key(target, "mcpServers.exo")
    assert json.loads(target.read_text()) == {"mcpServers": {}}
