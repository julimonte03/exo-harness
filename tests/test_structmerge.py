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
    with pytest.raises(StructMergeError, match="valid JSON"):
        structmerge.merge_json_key(target, "servers.exo", SERVER)
    assert target.read_bytes() == original


def test_raiz_que_no_es_objeto(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_bytes(b"[1]")
    with pytest.raises(StructMergeError, match="object"):
        structmerge.merge_json_key(target, "a", 1)


def test_intermedio_que_no_es_objeto(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_bytes(b'{"mcpServers": []}')
    with pytest.raises(StructMergeError, match="mcpServers"):
        structmerge.merge_json_key(target, "mcpServers.exo", SERVER)
    assert target.read_bytes() == b'{"mcpServers": []}'


@pytest.mark.parametrize("bad", ["", ".", "a..b", ".a", "a."])
def test_clave_invalida(tmp_path: Path, bad: str) -> None:
    with pytest.raises(StructMergeError, match="key"):
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


def test_add_y_remove_list_item(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "settings.json"
    target.parent.mkdir()
    target.write_bytes(b'{\n  "permissions": {\n    "allow": [\n      "Bash(git:*)"\n    ]\n  }\n}\n')
    assert structmerge.add_json_list_item(target, "permissions.allow", "Bash(exo:*)") is True
    assert json.loads(target.read_text())["permissions"]["allow"] == ["Bash(git:*)", "Bash(exo:*)"]
    assert structmerge.add_json_list_item(target, "permissions.allow", "Bash(exo:*)") is False
    assert structmerge.remove_json_list_item(target, "permissions.allow", "Bash(exo:*)") is True
    assert target.read_bytes() == b'{\n  "permissions": {\n    "allow": [\n      "Bash(git:*)"\n    ]\n  }\n}\n'
    assert structmerge.remove_json_list_item(target, "permissions.allow", "Bash(exo:*)") is False


def test_list_item_crea_la_lista_y_poda_al_quitar(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    structmerge.add_json_list_item(target, "permissions.allow", "Bash(exo:*)")
    assert json.loads(target.read_text()) == {"permissions": {"allow": ["Bash(exo:*)"]}}
    structmerge.remove_json_list_item(target, "permissions.allow", "Bash(exo:*)", prune_empty=True)
    assert json.loads(target.read_text()) == {}
    assert structmerge.remove_json_list_item(tmp_path / "no.json", "a", "x") is False


def test_list_item_sobre_algo_que_no_es_lista(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text('{"permissions": {"allow": "todo"}}', encoding="utf-8")
    with pytest.raises(StructMergeError, match="is not a list"):
        structmerge.add_json_list_item(target, "permissions.allow", "Bash(exo:*)")
    assert structmerge.remove_json_list_item(target, "permissions.allow", "x") is False


def test_missing_containers(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    assert structmerge.missing_containers(target, "permissions.allow", leaf=True) == ["permissions", "permissions.allow"]
    assert structmerge.missing_containers(target, "mcpServers.exo", leaf=False) == ["mcpServers"]
    target.write_text('{"permissions": {"deny": []}}', encoding="utf-8")
    assert structmerge.missing_containers(target, "permissions.allow", leaf=True) == ["permissions.allow"]
    assert structmerge.missing_containers(target, "permissions.deny", leaf=True) == []


def test_prune_empty_keys_solo_quita_lo_pedido_y_vacio(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text('{"permissions": {"allow": [], "deny": []}, "x": {}}', encoding="utf-8")
    assert structmerge.prune_empty_keys(target, ["permissions", "permissions.allow", "nada.aca"]) is True
    assert json.loads(target.read_text()) == {"permissions": {"deny": []}, "x": {}}
    assert structmerge.prune_empty_keys(target, ["permissions"]) is False
    assert structmerge.prune_empty_keys(tmp_path / "no.json", ["a"]) is False


@pytest.mark.parametrize(
    "original",
    [b'{"permissions": {"allow": []}}\n', b'{"permissions":{"allow":[]},"model":"x"}', b"{}\n"],
    ids=["compacto", "compacto-sin-espacios", "vacio"],
)
def test_json_de_una_linea_vuelve_identico(tmp_path: Path, original: bytes) -> None:
    target = tmp_path / "settings.json"
    target.write_bytes(original)
    structmerge.add_json_list_item(target, "permissions.allow", "Bash(exo:*)")
    if original != b"{}\n":
        assert target.read_bytes().count(b"\n") <= 1
    structmerge.remove_json_list_item(target, "permissions.allow", "Bash(exo:*)")
    structmerge.prune_empty_keys(target, [] if b"allow" in original else ["permissions", "permissions.allow"])
    assert target.read_bytes() == original
