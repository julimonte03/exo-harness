"""core/lock: archivos generados, sus hashes y detección de cambios manuales."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import _meta
from exo.core import filemerge, fsutil, lock, structmerge
from exo.core.lock import Lock, LockEntry, LockError

SERVER = {"command": "x", "args": ["mcp"]}


def _project(tmp_path: Path) -> tuple[Path, Lock]:
    (tmp_path / ".claude" / "skills" / "s").mkdir(parents=True)
    skill = tmp_path / ".claude" / "skills" / "s" / "SKILL.md"
    skill.write_bytes(b"---\nname: s\n---\n")
    filemerge.inject(tmp_path / "AGENTS.md", "core", "reglas")
    structmerge.merge_json_key(tmp_path / ".mcp.json", "mcpServers.motor", SERVER)
    entries = [
        LockEntry(
            ".claude/skills/s/SKILL.md", "mirror", "adapter:claude-code", fsutil.sha256_file(skill)
        ),
        LockEntry(
            "AGENTS.md", "block", "engine", lock.hash_block_content("reglas"), block_id="core"
        ),
        LockEntry(
            ".mcp.json",
            "key",
            "adapter:claude-code",
            lock.hash_json_value(SERVER),
            key="mcpServers.motor",
        ),
    ]
    return tmp_path, Lock(engine_version="0.0.1", agents=["claude-code"], packs=["core"], files=entries)


def test_write_y_read_ida_y_vuelta(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    assert lock.write(project, data) is True
    loaded = lock.read(project)
    assert loaded is not None
    assert loaded.engine_version == "0.0.1"
    assert loaded.agents == ["claude-code"]
    assert sorted(loaded.files) == sorted(data.files)


def test_write_es_determinista_e_idempotente(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    lock.write(project, data)
    first = lock.lock_path(project).read_bytes()
    shuffled = Lock(data.engine_version, data.agents, data.packs, list(reversed(data.files)))
    assert lock.write(project, shuffled) is False
    assert lock.lock_path(project).read_bytes() == first
    payload = json.loads(first)
    assert payload["schema"] == 1
    assert [f["path"] for f in payload["files"]] == [".claude/skills/s/SKILL.md", ".mcp.json", "AGENTS.md"]
    assert "block_id" not in payload["files"][0]
    assert payload["files"][2]["block_id"] == "core"


def test_read_sin_lock(tmp_path: Path) -> None:
    assert lock.read(tmp_path) is None
    assert lock.drift(tmp_path) == []


def test_sin_drift_cuando_nada_cambio(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    lock.write(project, data)
    assert lock.drift(project) == []


def test_drift_en_archivo_modificado_y_borrado(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    skill = project / ".claude" / "skills" / "s" / "SKILL.md"
    skill.write_bytes(b"editado a mano")
    found = lock.drift(project, data)
    assert [(d.entry.path, d.status) for d in found] == [(".claude/skills/s/SKILL.md", "modified")]
    assert found[0].actual == fsutil.sha256_bytes(b"editado a mano")
    skill.unlink()
    found = lock.drift(project, data)
    assert [(d.status, d.actual) for d in found] == [("missing", None)]


def test_drift_en_bloque(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    agents = project / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "\n# texto del humano\n", encoding="utf-8")
    assert lock.drift(project, data) == []
    filemerge.inject(agents, "core", "reglas tocadas")
    assert [d.status for d in lock.drift(project, data)] == ["modified"]
    filemerge.remove(agents, "core")
    assert [d.status for d in lock.drift(project, data)] == ["missing"]


def test_bloque_con_crlf_tiene_el_mismo_hash(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    agents = project / "AGENTS.md"
    agents.write_bytes(agents.read_bytes().replace(b"\n", b"\r\n"))
    assert lock.drift(project, data) == []


def test_drift_en_clave_json(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    mcp = project / ".mcp.json"
    structmerge.merge_json_key(mcp, "otra", 1)
    assert lock.drift(project, data) == []
    structmerge.merge_json_key(mcp, "mcpServers.motor", {"command": "y"})
    assert [d.status for d in lock.drift(project, data)] == ["modified"]
    structmerge.remove_json_key(mcp, "mcpServers.motor")
    assert [d.status for d in lock.drift(project, data)] == ["missing"]


def test_clave_json_ilegible_cuenta_como_modificada(tmp_path: Path) -> None:
    project, data = _project(tmp_path)
    (project / ".mcp.json").write_text("{ roto", encoding="utf-8")
    assert [d.status for d in lock.drift(project, data)] == ["modified"]


def test_hash_json_canonico() -> None:
    assert lock.hash_json_value({"a": 1, "b": [2]}) == lock.hash_json_value({"b": [2], "a": 1})


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ("{ roto", "JSON"),
        ("[]", "objeto"),
        ('{"schema": 2, "files": []}', "esquema"),
        ('{"schema": 1, "files": {}}', "files"),
        ('{"schema": 1, "files": [{"path": "../x", "kind": "file", "owner": "o", "sha256": "a"}]}', "insegura"),
        ('{"schema": 1, "files": [{"path": "x", "kind": "raro", "owner": "o", "sha256": "a"}]}', "kind"),
        ('{"schema": 1, "files": [{"path": "x", "kind": "block", "owner": "o", "sha256": "a"}]}', "block_id"),
        ('{"schema": 1, "files": [{"path": "x", "kind": "key", "owner": "o", "sha256": "a"}]}', "key"),
        ('{"schema": 1, "files": [{"path": "x", "kind": "file", "sha256": "a"}]}', "owner"),
    ],
)
def test_lock_invalido(tmp_path: Path, payload: str, fragment: str) -> None:
    path = tmp_path / _meta.PROJECT_DIR / "lock.json"
    path.parent.mkdir()
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(LockError, match=fragment):
        lock.read(tmp_path)


def test_bloque_con_estilo_forzado_no_da_drift_falso(tmp_path: Path) -> None:
    target = tmp_path / "notas.txt"
    filemerge.inject(target, "core", "x", style="hash")
    entry = LockEntry("notas.txt", "block", "engine", lock.hash_block_content("x"), block_id="core", style="hash")
    data = Lock("0.0.1", files=[entry])
    assert lock.drift(tmp_path, data) == []
    lock.write(tmp_path, data)
    assert lock.read(tmp_path).files == [entry]


def test_entrada_ilegible_se_reporta_sin_explotar(tmp_path: Path, make_dir_link) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-afuera"
    outside.mkdir()
    (outside / "x.md").write_text("x", encoding="utf-8")
    project = tmp_path / "proyecto"
    project.mkdir()
    make_dir_link(project / "link", outside)
    entry = LockEntry("link/x.md", "file", "engine", "abc")
    assert [d.status for d in lock.drift(project, Lock("0.0.1", files=[entry]))] == ["unreadable"]


def test_style_invalido_en_el_lock(tmp_path: Path) -> None:
    path = tmp_path / _meta.PROJECT_DIR / "lock.json"
    path.parent.mkdir()
    path.write_text('{"schema": 1, "files": [{"path": "x", "kind": "block", "block_id": "c", "owner": "o", "sha256": "a", "style": "xml"}]}', encoding="utf-8")
    with pytest.raises(LockError, match="style"):
        lock.read(tmp_path)
