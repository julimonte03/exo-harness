"""core/fsutil: escritura atómica, hashes y saneo de rutas."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path, PurePosixPath

import pytest

from exo.core import fsutil
from exo.core.fsutil import UnsafePathError


def test_write_atomic_crea_directorios_y_escribe_bytes(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "file.txt"
    fsutil.write_atomic(target, b"hola\n")
    assert target.read_bytes() == b"hola\n"


def test_write_atomic_preserva_crlf_y_bytes_arbitrarios(tmp_path: Path) -> None:
    data = b"linea 1\r\nlinea 2\r\n\x00\xff fin"
    target = tmp_path / "crlf.md"
    fsutil.write_atomic(target, data)
    assert target.read_bytes() == data


def test_write_atomic_reemplaza_y_no_deja_temporales(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_bytes(b"viejo")
    fsutil.write_atomic(target, b"nuevo")
    assert target.read_bytes() == b"nuevo"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["f.txt"]


def test_write_atomic_limpia_el_temporal_si_falla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(src: str, dst: str) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr(fsutil.os, "replace", boom)
    with pytest.raises(OSError, match="disco lleno"):
        fsutil.write_atomic(tmp_path / "f.txt", b"x")
    assert list(tmp_path.iterdir()) == []


def test_write_atomic_reintenta_ante_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = {"n": 0}

    def flaky(src: str, dst: str) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            raise PermissionError("archivo bloqueado")
        real_replace(src, dst)

    monkeypatch.setattr(fsutil.os, "replace", flaky)
    monkeypatch.setattr(fsutil, "_RETRY_DELAY", 0)
    fsutil.write_atomic(tmp_path / "f.txt", b"ok")
    assert calls["n"] == 3
    assert (tmp_path / "f.txt").read_bytes() == b"ok"


def test_write_atomic_agota_reintentos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def locked(src: str, dst: str) -> None:
        raise PermissionError("archivo bloqueado")

    monkeypatch.setattr(fsutil.os, "replace", locked)
    monkeypatch.setattr(fsutil, "_RETRY_DELAY", 0)
    with pytest.raises(PermissionError):
        fsutil.write_atomic(tmp_path / "f.txt", b"x")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="permisos POSIX")
def test_write_atomic_conserva_el_modo_del_archivo_existente(tmp_path: Path) -> None:
    target = tmp_path / "script.sh"
    target.write_bytes(b"#!/bin/sh\n")
    target.chmod(0o755)
    fsutil.write_atomic(target, b"#!/bin/sh\necho hi\n")
    assert target.stat().st_mode & 0o777 == 0o755


@pytest.mark.skipif(sys.platform == "win32", reason="permisos POSIX")
def test_write_atomic_archivo_nuevo_es_legible(tmp_path: Path) -> None:
    target = tmp_path / "nuevo.txt"
    fsutil.write_atomic(target, b"x")
    assert target.stat().st_mode & 0o777 == 0o644


def test_write_if_changed_no_reescribe_si_es_igual(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    assert fsutil.write_if_changed(target, b"uno") is True
    before = target.stat().st_mtime_ns
    os.utime(target, ns=(before - 10_000_000_000, before - 10_000_000_000))
    stamped = target.stat().st_mtime_ns
    assert fsutil.write_if_changed(target, b"uno") is False
    assert target.stat().st_mtime_ns == stamped
    assert fsutil.write_if_changed(target, b"dos") is True
    assert target.read_bytes() == b"dos"


def test_ruta_larga(tmp_path: Path) -> None:
    deep = tmp_path.joinpath(*(["d" * 40] * 8)) / "archivo-con-nombre-largo.txt"
    assert len(str(deep)) > 260
    # Sin skip: en Windows el prefijo de ruta larga tiene que funcionar aunque el
    # sistema no tenga habilitadas las rutas largas; Linux y macOS las soportan.
    fsutil.write_atomic(deep, b"largo")
    assert fsutil.read_bytes(deep) == b"largo"
    assert fsutil.sha256_file(deep) == hashlib.sha256(b"largo").hexdigest()


@pytest.mark.skipif(sys.platform != "win32", reason="prefijo de ruta larga de Windows")
def test_temporal_usa_el_prefijo_si_el_destino_es_largo(tmp_path: Path) -> None:
    parent = tmp_path / ("p" * (230 - len(str(tmp_path)) - 1))
    target = parent / ("n" * 30 + ".txt")
    assert len(str(parent)) < 240 <= len(str(target))
    os_parent = fsutil._os_parent(target, fsutil._os_path(target))
    assert os_parent.startswith(fsutil._LONG_PREFIX)
    fsutil.write_atomic(target, b"ok")
    assert fsutil.read_bytes(target) == b"ok"


def test_sha256(tmp_path: Path) -> None:
    data = b"abc" * 100_000
    target = tmp_path / "big.bin"
    target.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert fsutil.sha256_bytes(data) == expected
    assert fsutil.sha256_file(target) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a/b/c.md", "a/b/c.md"),
        (r"a\b\c.md", "a/b/c.md"),
        ("./a//b/./c", "a/b/c"),
        ("specs", "specs"),
        (PurePosixPath("x/y"), "x/y"),
    ],
)
def test_safe_relpath_normaliza(raw: str, expected: str) -> None:
    assert fsutil.safe_relpath(raw) == PurePosixPath(expected)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        ".",
        "../x",
        "a/../../x",
        "a/..",
        "/etc/passwd",
        r"\Windows\System32",
        r"C:\Windows",
        "C:/Windows",
        "c:relativo",
        r"\\server\share\x",
        "a\x00b",
    ],
)
def test_safe_relpath_rechaza(raw: str) -> None:
    with pytest.raises(UnsafePathError):
        fsutil.safe_relpath(raw)


def test_resolve_within_acepta_rutas_internas(tmp_path: Path) -> None:
    assert fsutil.resolve_within(tmp_path, "a/b.txt") == (tmp_path / "a" / "b.txt").resolve()


def test_resolve_within_rechaza_escape(tmp_path: Path) -> None:
    with pytest.raises(UnsafePathError):
        fsutil.resolve_within(tmp_path, "../fuera.txt")


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks requieren privilegios en Windows")
def test_resolve_within_rechaza_symlink_que_escapa(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafePathError):
        fsutil.resolve_within(root, "link/secreto.txt")


def test_is_link_reconoce_links_de_directorio(tmp_path: Path, make_dir_link) -> None:
    target = tmp_path / "destino"
    target.mkdir()
    (tmp_path / "archivo.txt").write_bytes(b"x")
    make_dir_link(tmp_path / "link", target)
    assert fsutil.is_link(tmp_path / "link") is True
    assert fsutil.is_link(target) is False
    assert fsutil.is_link(tmp_path / "archivo.txt") is False
    assert fsutil.is_link(tmp_path / "no-existe") is False


def test_link_cache_verifica_cada_componente_una_sola_vez(
    tmp_path: Path, make_dir_link, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    calls: list[str] = []
    real = fsutil.is_link

    def counting(path: Path) -> bool:
        calls.append(Path(path).relative_to(tmp_path).as_posix())
        return real(path)

    monkeypatch.setattr(fsutil, "is_link", counting)
    rels = [".claude/skills/a/SKILL.md", ".claude/skills/b/SKILL.md", ".claude/skills/a/SKILL.md"]
    for rel in rels:
        fsutil.join_within(tmp_path, rel)
    assert len(calls) == 12  # sin caché, cada componente de cada ruta
    calls.clear()
    with fsutil.link_cache():
        for rel in rels:
            fsutil.join_within(tmp_path, rel)
        with fsutil.link_cache():  # anidada: la misma caché
            fsutil.join_within(tmp_path, ".claude/skills/b/SKILL.md")
    assert sorted(calls) == [
        ".claude",
        ".claude/skills",
        ".claude/skills/a",
        ".claude/skills/a/SKILL.md",
        ".claude/skills/b",
        ".claude/skills/b/SKILL.md",
    ]
    # Un link se sigue rechazando con la caché, y al salir del bloque la caché se descarta.
    outside = tmp_path / "afuera"
    outside.mkdir()
    make_dir_link(tmp_path / ".claude" / "skills" / "c", outside)
    with fsutil.link_cache(), pytest.raises(UnsafePathError, match="symlink or junction"):
        fsutil.join_within(tmp_path, ".claude/skills/c/SKILL.md")
    calls.clear()
    fsutil.join_within(tmp_path, ".claude/skills/a/SKILL.md")
    assert len(calls) == 4


def test_walk_files_no_entra_en_links(tmp_path: Path, make_dir_link) -> None:
    outside = tmp_path / "afuera"
    outside.mkdir()
    (outside / "secreto.txt").write_bytes(b"no")
    root = tmp_path / "raiz"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_bytes(b"a")
    (root / "sub" / "b.txt").write_bytes(b"b")
    make_dir_link(root / "sub" / "link", outside)
    assert [p.relative_to(root).as_posix() for p in fsutil.walk_files(root)] == ["a.txt", "sub/b.txt"]
    assert fsutil.walk_files(tmp_path / "no-existe") == []


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks de archivo requieren privilegios en Windows")
def test_write_atomic_escribe_en_el_destino_del_symlink(tmp_path: Path) -> None:
    real = tmp_path / "AGENTS.md"
    real.write_bytes(b"viejo")
    link = tmp_path / "CLAUDE.md"
    link.symlink_to(real)
    fsutil.write_atomic(link, b"nuevo")
    assert link.is_symlink()
    assert real.read_bytes() == b"nuevo"
    fsutil.write_atomic(link, b"reemplazo", follow_symlinks=False)
    assert not link.is_symlink()
    assert real.read_bytes() == b"nuevo"


def test_write_atomic_no_deja_temporales_si_el_destino_es_de_solo_lectura(tmp_path: Path) -> None:
    import stat

    target = tmp_path / "solo-lectura.txt"
    target.write_bytes(b"viejo")
    target.chmod(stat.S_IREAD)
    try:
        try:
            fsutil.write_atomic(target, b"nuevo")
        except PermissionError:
            assert target.read_bytes() == b"viejo"
        assert [p.name for p in tmp_path.iterdir()] == ["solo-lectura.txt"]
    finally:
        target.chmod(stat.S_IREAD | stat.S_IWRITE)
