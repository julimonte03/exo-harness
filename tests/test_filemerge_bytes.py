"""filemerge conserva byte a byte lo que está fuera de los bloques (revisión F1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from exo import _meta
from exo.core import filemerge
from exo.core.filemerge import BlockError

P = _meta.BLOCK_PREFIX
LINE_SEPARATOR = chr(0x2028)


@pytest.mark.parametrize(
    ("name", "original"),
    [
        ("AGENTS.md", b"a\r\nb\nc\r\n"),
        ("AGENTS.md", b"uno\rdos\ntres\n"),
        ("script.py", b"def f():\n    pass\n\x0c\ndef g():\n    pass\n"),
        ("AGENTS.md", f"texto{LINE_SEPARATOR}con separador\n".encode()),
        ("AGENTS.md", b"\xc2\x85 NEL y m\xc3\xa1s\n"),
    ],
)
def test_inject_y_remove_dejan_el_archivo_identico(tmp_path: Path, name: str, original: bytes) -> None:
    target = tmp_path / name
    target.write_bytes(original)
    filemerge.inject(target, "core", "regla")
    filemerge.remove(target, "core")
    assert target.read_bytes() == original


def test_inject_en_el_medio_no_toca_los_separadores_vecinos(tmp_path: Path) -> None:
    begin, end = filemerge.markers("core", filemerge.STYLE_HTML)
    original = f"antes\r\n{begin}\r\nviejo\r\n{end}\ndespués sin salto".encode()
    target = tmp_path / "AGENTS.md"
    target.write_bytes(original)
    filemerge.inject(target, "core", "nuevo")
    data = target.read_bytes()
    assert data.startswith(b"antes\r\n")
    assert data.endswith(f"{end}\ndespués sin salto".encode())


def test_contenido_con_marcadores_se_rechaza(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    for evil in (f"<!-- END:{P}:core -->\nfoo", f"x\n# BEGIN:{P}:otro"):
        with pytest.raises(BlockError, match="marcadores"):
            filemerge.inject(target, "core", evil)
    assert not target.exists()


def test_marcadores_dentro_de_bloques_de_codigo_no_cuentan(tmp_path: Path) -> None:
    begin, end = filemerge.markers("core", filemerge.STYLE_HTML)
    doc = f"# Cómo funciona\n\n```markdown\n{begin}\nejemplo\n{end}\n```\n"
    target = tmp_path / "README.md"
    target.write_text(doc, encoding="utf-8")
    assert filemerge.list_blocks(target) == []
    filemerge.inject(target, "core", "real")
    blocks = filemerge.list_blocks(target)
    assert [(b.id, b.content) for b in blocks] == [("core", "real")]
    filemerge.remove(target, "core")
    assert target.read_text(encoding="utf-8") == doc
