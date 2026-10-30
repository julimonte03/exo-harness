"""structmerge no pierde datos del humano (revisión F1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo.core import structmerge
from exo.core.structmerge import StructMergeError

BOM = chr(0xFEFF)


@pytest.mark.parametrize(
    ("original", "fragment"),
    [
        ('{"a": 1, "a": 2}', "repetida"),
        ('{"big": 12345678901234567890.5}', "precisión"),
        ('{"x": 1e400}', "precisión"),
        ('{"x": NaN}', "NaN"),
        ('{"x": -Infinity}', "Infinity"),
    ],
)
def test_json_que_perderia_datos_no_se_toca(tmp_path: Path, original: str, fragment: str) -> None:
    target = tmp_path / "x.json"
    target.write_text(original, encoding="utf-8")
    with pytest.raises(StructMergeError, match=fragment):
        structmerge.merge_json_key(target, "mcpServers.motor", {"command": "x"})
    assert target.read_text(encoding="utf-8") == original


def test_numeros_normales_se_conservan(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_text('{\n  "a": 0.1,\n  "b": 1.5,\n  "c": 12345678901234567890\n}\n', encoding="utf-8")
    structmerge.merge_json_key(target, "d", True)
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 0.1, "b": 1.5, "c": 12345678901234567890, "d": True}


def test_bom_se_conserva(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_bytes((BOM + '{\n  "a": 1\n}\n').encode("utf-8"))
    structmerge.merge_json_key(target, "b", 2)
    data = target.read_bytes()
    assert data.startswith(BOM.encode("utf-8"))
    assert json.loads(data.decode("utf-8-sig")) == {"a": 1, "b": 2}


def test_valor_no_serializable_como_json_estricto(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_text("{}\n", encoding="utf-8")
    with pytest.raises(StructMergeError, match="JSON"):
        structmerge.merge_json_key(target, "x", float("nan"))
    assert target.read_text(encoding="utf-8") == "{}\n"
