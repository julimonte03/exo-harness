"""core/snapshots: tar.gz deterministas, dedup, pins, poda, restore y extracción segura."""

from __future__ import annotations

import gzip
import io
import json
import os
import tarfile
from pathlib import Path

import pytest

from exo import _meta
from exo.cli import main
from exo.core import fsutil, snapshots
from exo.core.snapshots import SnapshotError, UnsafeArchiveError


def _tree(root: Path) -> None:
    (root / "a").mkdir(parents=True)
    (root / "a" / "uno.md").write_bytes(b"uno\r\n")
    (root / "a" / "dos.txt").write_bytes(b"dos")
    (root / "AGENTS.md").write_bytes(b"# reglas\n")


def test_criterio_3_mismo_arbol_mismo_sha(tmp_path: Path) -> None:
    left, right = tmp_path / "l", tmp_path / "r"
    _tree(left)
    _tree(right)
    os.utime(right / "AGENTS.md", (1, 1))
    paths = ["AGENTS.md", "a"]
    first = snapshots.build_archive(left, paths)
    assert snapshots.build_archive(left, list(reversed(paths))) == first
    assert snapshots.build_archive(right, paths) == first
    assert fsutil.sha256_bytes(first) == fsutil.sha256_bytes(snapshots.build_archive(left, paths))


def test_archivo_normalizado(tmp_path: Path) -> None:
    _tree(tmp_path)
    data = snapshots.build_archive(tmp_path, ["a", "AGENTS.md", "no-existe.md"])
    assert data[:2] == b"\x1f\x8b"
    assert data[4:8] == b"\x00\x00\x00\x00"  # mtime del header gzip
    assert gzip.decompress(data)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        manifest = json.loads(tar.extractfile(members[0]).read())
    assert names == [snapshots.MANIFEST_NAME, "AGENTS.md", "a/dos.txt", "a/uno.md"]
    for member in members:
        assert (member.mtime, member.uid, member.gid, member.uname, member.gname) == (0, 0, 0, "", "")
    assert manifest == {
        "schema": 1,
        "roots": ["AGENTS.md", "a", "no-existe.md"],
        "dirs": ["a"],
        "absent": ["no-existe.md"],
    }


def test_snapshot_dedup_y_listado(tmp_path: Path) -> None:
    _tree(tmp_path)
    first = snapshots.snapshot(tmp_path, ["AGENTS.md"])
    again = snapshots.snapshot(tmp_path, ["AGENTS.md"])
    assert again == first
    assert [s.name for s in snapshots.list_snapshots(tmp_path)] == [first.name]
    assert first.path.parent == tmp_path / _meta.PROJECT_DIR / "backups"
    (tmp_path / "AGENTS.md").write_bytes(b"cambio")
    second = snapshots.snapshot(tmp_path, ["AGENTS.md"])
    assert second.name != first.name
    assert [s.name for s in snapshots.list_snapshots(tmp_path)] == [first.name, second.name]


def test_prune_respeta_keep_y_pins(tmp_path: Path) -> None:
    _tree(tmp_path)
    made = []
    for i in range(8):
        (tmp_path / "AGENTS.md").write_bytes(f"v{i}".encode())
        made.append(snapshots.snapshot(tmp_path, ["AGENTS.md"], keep=100).name)
    snapshots.pin(tmp_path, made[0])
    removed = snapshots.prune(tmp_path, keep=5)
    assert removed == made[1:3]
    remaining = [s.name for s in snapshots.list_snapshots(tmp_path)]
    assert remaining == [made[0], *made[3:]]
    assert [s.pinned for s in snapshots.list_snapshots(tmp_path)][0] is True


def test_snapshot_poda_por_defecto_a_5(tmp_path: Path) -> None:
    _tree(tmp_path)
    for i in range(7):
        (tmp_path / "AGENTS.md").write_bytes(f"v{i}".encode())
        snapshots.snapshot(tmp_path, ["AGENTS.md"])
    assert len(snapshots.list_snapshots(tmp_path)) == snapshots.DEFAULT_KEEP


def test_pin_y_unpin(tmp_path: Path) -> None:
    _tree(tmp_path)
    snap = snapshots.snapshot(tmp_path, ["AGENTS.md"])
    assert snapshots.pin(tmp_path, snap.name) is True
    assert snapshots.pin(tmp_path, snap.name) is False
    assert snapshots.list_snapshots(tmp_path)[0].pinned
    assert snapshots.unpin(tmp_path, snap.name) is True
    assert snapshots.unpin(tmp_path, snap.name) is False
    with pytest.raises(SnapshotError, match="no existe"):
        snapshots.pin(tmp_path, "20990101T000000000000Z-000000000000.tar.gz")


def test_restore_vuelve_al_estado_y_snapshotea_antes(tmp_path: Path) -> None:
    _tree(tmp_path)
    snap = snapshots.snapshot(tmp_path, ["AGENTS.md", "a", "nuevo.md"])
    (tmp_path / "AGENTS.md").write_bytes(b"pisado")
    (tmp_path / "a" / "uno.md").unlink()
    (tmp_path / "a" / "extra.md").write_bytes(b"no estaba")
    (tmp_path / "nuevo.md").write_bytes(b"creado despues")
    result = snapshots.restore(tmp_path, snap.name)
    assert (tmp_path / "AGENTS.md").read_bytes() == b"# reglas\n"
    assert (tmp_path / "a" / "uno.md").read_bytes() == b"uno\r\n"
    assert not (tmp_path / "a" / "extra.md").exists()
    assert not (tmp_path / "nuevo.md").exists()
    assert sorted(result.removed) == ["a/extra.md", "nuevo.md"]
    assert result.before is not None
    pre = snapshots.read_archive(result.before.path.read_bytes())
    assert pre.files["AGENTS.md"][0] == b"pisado"


def test_restore_de_snapshot_que_la_poda_borraria(tmp_path: Path) -> None:
    _tree(tmp_path)
    names = []
    for i in range(5):
        (tmp_path / "AGENTS.md").write_bytes(f"v{i}".encode())
        names.append(snapshots.snapshot(tmp_path, ["AGENTS.md"]).name)
    (tmp_path / "AGENTS.md").write_bytes(b"actual")
    snapshots.restore(tmp_path, names[0])
    assert (tmp_path / "AGENTS.md").read_bytes() == b"v0"


@pytest.mark.parametrize("bad", ["../x.tar.gz", "x.tar.gz", "20990101T000000000000Z-000000000000.tar.gz"])
def test_restore_nombre_invalido_o_inexistente(tmp_path: Path, bad: str) -> None:
    with pytest.raises(SnapshotError):
        snapshots.restore(tmp_path, bad)


def _evil(build) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        manifest = json.dumps({"schema": 1, "roots": ["x"], "dirs": [], "absent": []}).encode()
        info = tarfile.TarInfo(snapshots.MANIFEST_NAME)
        info.size = len(manifest)
        tar.addfile(info, io.BytesIO(manifest))
        build(tar)
    return gzip.compress(raw.getvalue())


def _file(name: str):
    def build(tar: tarfile.TarFile) -> None:
        info = tarfile.TarInfo(name)
        info.size = 4
        tar.addfile(info, io.BytesIO(b"evil"))

    return build


def _special(name: str, kind: bytes, linkname: str = ""):
    def build(tar: tarfile.TarFile) -> None:
        info = tarfile.TarInfo(name)
        info.type = kind
        info.linkname = linkname
        tar.addfile(info)

    return build


@pytest.mark.parametrize(
    ("build", "fragment"),
    [
        (_file("../evil.txt"), "insegura"),
        (_file("a/../../evil.txt"), "insegura"),
        (_file("/etc/evil"), "insegura"),
        (_file("C:/Windows/evil"), "insegura"),
        (_file("..\\evil.txt"), "insegura"),
        (_special("link", tarfile.SYMTYPE, "/etc/passwd"), "tipo"),
        (_special("hard", tarfile.LNKTYPE, "AGENTS.md"), "tipo"),
        (_special("dev", tarfile.CHRTYPE), "tipo"),
        (_special("blk", tarfile.BLKTYPE), "tipo"),
        (_special("fifo", tarfile.FIFOTYPE), "tipo"),
        (_special("dir", tarfile.DIRTYPE), "tipo"),
    ],
)
def test_criterio_4_extraccion_segura(build, fragment: str) -> None:
    with pytest.raises(UnsafeArchiveError, match=fragment):
        snapshots.read_archive(_evil(build))


def test_archivo_sin_manifiesto_o_duplicado() -> None:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        _file("x")(tar)
    with pytest.raises(UnsafeArchiveError, match="manifiesto"):
        snapshots.read_archive(gzip.compress(raw.getvalue()))

    def twice(tar: tarfile.TarFile) -> None:
        _file("x")(tar)
        _file("x")(tar)

    with pytest.raises(UnsafeArchiveError, match="repetida"):
        snapshots.read_archive(_evil(twice))
    with pytest.raises(UnsafeArchiveError, match="tar.gz"):
        snapshots.read_archive(b"no soy un tar")


def test_restore_con_archivo_malicioso_no_escribe_nada(tmp_path: Path) -> None:
    backups = tmp_path / _meta.PROJECT_DIR / "backups"
    backups.mkdir(parents=True)
    name = "20200101T000000000000Z-0123456789ab.tar.gz"
    (backups / name).write_bytes(_evil(_file("../fuera.txt")))
    with pytest.raises(UnsafeArchiveError):
        snapshots.restore(tmp_path, name)
    assert not (tmp_path.parent / "fuera.txt").exists()
    assert [s.name for s in snapshots.list_snapshots(tmp_path)] == [name]


# -- CLI ----------------------------------------------------------------------


def test_cli_backups_y_restore(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _tree(tmp_path)
    snap = snapshots.snapshot(tmp_path, ["AGENTS.md"])
    project = ["--project", str(tmp_path)]
    assert main(["backups", "list", *project, "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)["backups"]
    assert [b["name"] for b in listed] == [snap.name]
    assert listed[0]["pinned"] is False
    assert main(["backups", "pin", snap.name, *project]) == 0
    assert "fijado" in capsys.readouterr().out
    assert main(["backups", "list", *project]) == 0
    assert "fijado" in capsys.readouterr().out
    assert main(["backups", "unpin", snap.name, *project]) == 0
    assert "liberado" in capsys.readouterr().out
    (tmp_path / "AGENTS.md").write_bytes(b"otro")
    assert main(["restore", snap.name, *project, "--yes", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["restored"] == ["AGENTS.md"]
    assert (tmp_path / "AGENTS.md").read_bytes() == b"# reglas\n"


def test_cli_restore_sin_yes_en_modo_no_interactivo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _tree(tmp_path)
    snap = snapshots.snapshot(tmp_path, ["AGENTS.md"])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert main(["restore", snap.name, "--project", str(tmp_path)]) == 2
    assert "--yes" in capsys.readouterr().err


def test_cli_backups_errores(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["backups", "list", "--project", str(tmp_path)]) == 0
    assert "sin backups" in capsys.readouterr().out
    assert main(["backups", "pin", "nada.tar.gz", "--project", str(tmp_path)]) == 1
    assert capsys.readouterr().err.startswith("error:")
    assert main(["restore", "nada.tar.gz", "--project", str(tmp_path), "--yes"]) == 1
    assert main(["backups"]) == 0
    assert "usage:" in capsys.readouterr().out
