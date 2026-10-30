"""core/filemerge: bloques marcados en archivos del humano."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from exo import _meta
from exo.core import filemerge
from exo.core.filemerge import BlockError

P = _meta.BLOCK_PREFIX
B = f"<!-- BEGIN:{P}:core -->"
E = f"<!-- END:{P}:core -->"


def _old_mtime(path: Path) -> int:
    stamp = path.stat().st_mtime_ns - 10_000_000_000
    os.utime(path, ns=(stamp, stamp))
    return path.stat().st_mtime_ns


def test_inject_en_archivo_nuevo(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    assert filemerge.inject(target, "core", "regla 1\nregla 2\n") is True
    assert target.read_text(encoding="utf-8") == f"{B}\nregla 1\nregla 2\n{E}\n"


def test_inject_al_final_respeta_el_contenido_del_humano(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"# Mis reglas\n\nNo tocar.\n")
    filemerge.inject(target, "core", "regla")
    assert target.read_bytes().decode() == f"# Mis reglas\n\nNo tocar.\n\n{B}\nregla\n{E}\n"


def test_inject_al_principio(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_bytes(b"# Propio\n")
    filemerge.inject(target, "claude-code", "@AGENTS.md", position="start")
    begin, end = filemerge.markers("claude-code", filemerge.STYLE_HTML)
    assert target.read_bytes().decode() == f"{begin}\n@AGENTS.md\n{end}\n\n# Propio\n"


def test_inject_dos_veces_no_reescribe_criterio_8(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"# Humano\r\n\r\ntexto\r\n")
    assert filemerge.inject(target, "core", "regla") is True
    first = target.read_bytes()
    stamped = _old_mtime(target)
    assert filemerge.inject(target, "core", "regla") is False
    assert target.read_bytes() == first
    assert target.stat().st_mtime_ns == stamped


def test_inject_respeta_crlf(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"# Humano\r\ntexto\r\n")
    filemerge.inject(target, "core", "linea 1\nlinea 2")
    data = target.read_bytes()
    assert data == f"# Humano\r\ntexto\r\n\r\n{B}\r\nlinea 1\r\nlinea 2\r\n{E}\r\n".encode()
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_inject_reemplaza_bloque_existente_sin_tocar_lo_demas(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(f"antes\n{B}\nviejo\n{E}\ndespués\n".encode())
    assert filemerge.inject(target, "core", "nuevo") is True
    assert target.read_bytes().decode() == f"antes\n{B}\nnuevo\n{E}\ndespués\n"


def test_replace_exige_que_exista(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"nada\n")
    with pytest.raises(BlockError, match="no existe"):
        filemerge.replace(target, "core", "x")
    assert target.read_bytes() == b"nada\n"
    filemerge.inject(target, "core", "a")
    assert filemerge.replace(target, "core", "b") is True
    assert filemerge.list_blocks(target)[0].content == "b"


def test_inject_y_remove_son_reversibles(tmp_path: Path) -> None:
    original = b"# Humano\n\ntexto\n"
    target = tmp_path / "AGENTS.md"
    target.write_bytes(original)
    filemerge.inject(target, "core", "regla")
    assert filemerge.remove(target, "core") is True
    assert target.read_bytes() == original
    filemerge.inject(target, "core", "regla", position="start")
    filemerge.remove(target, "core")
    assert target.read_bytes() == original


def test_remove_de_archivo_que_solo_tenia_el_bloque(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    filemerge.inject(target, "core", "x")
    filemerge.remove(target, "core")
    assert target.read_bytes() == b""


def test_remove_sin_bloque_no_escribe(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"x\n")
    assert filemerge.remove(target, "core") is False
    assert filemerge.remove(tmp_path / "no-existe.md", "core") is False


def test_list_blocks(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    filemerge.inject(target, "core", "a\nb")
    filemerge.inject(target, "sdd", "c")
    blocks = filemerge.list_blocks(target)
    assert [(b.id, b.content) for b in blocks] == [("core", "a\nb"), ("sdd", "c")]
    assert blocks[0].start_line == 1
    assert blocks[0].end_line == 4


def test_estilo_numeral_para_toml(tmp_path: Path) -> None:
    target = tmp_path / ".codex" / "config.toml"
    target.parent.mkdir()
    target.write_bytes(b'model = "x"\n')
    filemerge.inject(target, "mcp", '[mcp_servers.exo]\ncommand = "exo"')
    text = target.read_text(encoding="utf-8")
    assert f"# BEGIN:{P}:mcp\n[mcp_servers.exo]\ncommand = \"exo\"\n# END:{P}:mcp\n" in text
    assert text.startswith('model = "x"\n\n')


@pytest.mark.parametrize(
    ("name", "style"),
    [
        ("AGENTS.md", "html"),
        ("x.mdc", "html"),
        ("page.html", "html"),
        ("config.toml", "hash"),
        ("ci.yml", "hash"),
        ("ci.yaml", "hash"),
        ("hook.sh", "hash"),
        (".gitignore", "hash"),
        ("CODEOWNERS", "hash"),
    ],
)
def test_style_for(name: str, style: str) -> None:
    assert filemerge.style_for(Path(name)) == style


def test_style_desconocido_pide_estilo_explicito(tmp_path: Path) -> None:
    with pytest.raises(BlockError, match="estilo"):
        filemerge.inject(tmp_path / "datos.bin", "core", "x")
    assert filemerge.inject(tmp_path / "datos.bin", "core", "x", style="hash") is True


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        (f"{B}\nsin cierre\n", "sin su END"),
        (f"suelto\n{E}\n", "sin su BEGIN"),
        (f"{B}\n{B}\n{E}\n", "anidado"),
        (f"{B}\n{E}\n{B}\n{E}\n", "repetido"),
        (f"{B}\n<!-- END:{P}:otro -->\n", "no coincide"),
    ],
)
def test_marcadores_rotos_dan_error_y_no_escriben(
    tmp_path: Path, text: str, fragment: str
) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(text.encode())
    with pytest.raises(BlockError, match=fragment):
        filemerge.inject(target, "core", "x")
    assert target.read_bytes() == text.encode()


@pytest.mark.parametrize("bad", ["", "Core", "con espacio", "a/b", "-x"])
def test_id_invalido(tmp_path: Path, bad: str) -> None:
    with pytest.raises(BlockError, match="id"):
        filemerge.inject(tmp_path / "AGENTS.md", bad, "x")


def test_archivo_no_utf8(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"\xff\xfe\x00raro")
    with pytest.raises(BlockError, match="UTF-8"):
        filemerge.inject(target, "core", "x")


def test_backup_opt_in(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"original\n")
    filemerge.inject(target, "core", "x")
    backup = tmp_path / f"AGENTS.md.{_meta.NAME}.bak"
    assert not backup.exists()
    filemerge.inject(target, "core", "y", backup=True)
    assert backup.read_bytes() == f"original\n\n{B}\nx\n{E}\n".encode()


def test_backup_no_se_crea_si_no_hay_cambios(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    filemerge.inject(target, "core", "x")
    filemerge.inject(target, "core", "x", backup=True)
    assert not (tmp_path / f"AGENTS.md.{_meta.NAME}.bak").exists()


def test_bom_se_conserva(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_bytes("﻿# Humano\n".encode())
    filemerge.inject(target, "core", "x")
    assert target.read_bytes().startswith("﻿# Humano\n".encode())
    filemerge.remove(target, "core")
    assert target.read_bytes() == "﻿# Humano\n".encode()
