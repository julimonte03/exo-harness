"""core/lock: archivos generados, sus hashes y detección de cambios manuales."""

from __future__ import annotations

import copy
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
        ("[]", "object"),
        ('{"schema": 2, "files": []}', "schema"),
        ('{"schema": 1, "files": {}}', "files"),
        ('{"schema": 1, "files": [{"path": "../x", "kind": "file", "owner": "o", "sha256": "a"}]}', "unsafe"),
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


def test_entrada_item(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    structmerge.add_json_list_item(settings, "permissions.allow", "Bash(motor:*)")
    entry = LockEntry(
        ".claude/settings.json", "item", "adapter:claude-code", lock.hash_json_value("Bash(motor:*)"),
        key="permissions.allow", item="Bash(motor:*)",
    )
    data = Lock("0.0.1", files=[entry])
    assert lock.drift(tmp_path, data) == []
    lock.write(tmp_path, data)
    raw = json.loads(lock.lock_path(tmp_path).read_text(encoding="utf-8"))
    assert raw["files"][0]["item"] == "Bash(motor:*)"
    assert lock.read(tmp_path).files == [entry]
    structmerge.remove_json_list_item(settings, "permissions.allow", "Bash(motor:*)")
    assert [d.status for d in lock.drift(tmp_path, data)] == ["missing"]


def test_created_por_archivo_ida_y_vuelta(tmp_path: Path) -> None:
    created = [
        lock.Created(".mcp.json", file=False, containers=("mcpServers",)),
        lock.Created("AGENTS.md", file=True),
    ]
    lock.write(tmp_path, Lock("0.0.1", created=list(reversed(created))))
    raw = json.loads(lock.lock_path(tmp_path).read_text(encoding="utf-8"))
    assert raw["created"] == [
        {"path": ".mcp.json", "containers": ["mcpServers"]},
        {"path": "AGENTS.md", "file": True},
    ]
    assert lock.read(tmp_path).created == created


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ('"files": [{"path": "x", "kind": "item", "owner": "o", "sha256": "a", "key": "k"}]', "needs item"),
        ('"files": [{"path": "x", "kind": "item", "owner": "o", "sha256": "a", "item": "i"}]', "needs key"),
        ('"created": [{"path": "x", "file": "si"}]', "file"),
        ('"created": [{"path": "../x", "file": true}]', "unsafe"),
        ('"created": [{"path": "x", "containers": [1]}]', "containers"),
        ('"created": {"x": true}', "created"),
        # F8 (auditoría de la adopción de exo): antes, un TypeError o letras sueltas.
        ('"agents": null', "agents must be a list of names"),
        ('"packs": null', "packs must be a list of names"),
        ('"agents": "claude-code"', "agents must be a list of names"),
        ('"agents": [1, 2]', "agents must be a list of names"),
    ],
)
def test_item_o_created_invalidos(tmp_path: Path, payload: str, fragment: str) -> None:
    path = tmp_path / _meta.PROJECT_DIR / "lock.json"
    path.parent.mkdir()
    path.write_text('{"schema": 1, ' + payload + "}", encoding="utf-8")
    with pytest.raises(LockError, match=fragment):
        lock.read(tmp_path)


# -- migraciones (F8) -------------------------------------------------------------------


def _write_raw(project: Path, payload: dict) -> None:
    path = lock.lock_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _v1_to_v2(raw: dict) -> dict:
    """Paso de prueba: el esquema 2 inventado renombra un dueño viejo."""
    out = copy.deepcopy(raw)
    for entry in out.get("files", []):
        if entry.get("owner") == "adapter:claude":
            entry["owner"] = "adapter:claude-code"
    out["schema"] = 2
    return out


V1 = {
    "schema": 1,
    "engine_version": "0.2.0",
    "agents": ["claude-code"],
    "packs": ["core"],
    "files": [{"path": "AGENTS.md", "kind": "block", "block_id": "core", "owner": "adapter:claude", "sha256": "a"}],
}


def test_un_esquema_2_de_prueba_migra_al_leer_y_se_guarda_al_escribir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lock, "SCHEMA", 2)
    monkeypatch.setattr(lock, "MIGRATIONS", {1: _v1_to_v2})
    _write_raw(tmp_path, V1)
    data = lock.read(tmp_path)
    assert [e.owner for e in data.files] == ["adapter:claude-code"]
    assert data.engine_version == "0.2.0"
    assert lock.write(tmp_path, data) is True
    assert json.loads(lock.lock_path(tmp_path).read_text(encoding="utf-8"))["schema"] == 2
    assert lock.read(tmp_path).files == data.files


def test_sin_el_paso_que_falta_no_se_adivina(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lock, "SCHEMA", 3)
    monkeypatch.setattr(lock, "MIGRATIONS", {1: _v1_to_v2})
    _write_raw(tmp_path, V1)
    with pytest.raises(LockError, match="no migration from schema 2 to 3"):
        lock.read(tmp_path)


def test_un_lock_de_un_motor_mas_nuevo_pide_actualizar(tmp_path: Path) -> None:
    _write_raw(tmp_path, {**V1, "schema": lock.SCHEMA + 1})
    with pytest.raises(LockError, match=f"upgrade {_meta.NAME}") as info:
        lock.read(tmp_path)
    assert f"schema {lock.SCHEMA + 1}" in str(info.value)


@pytest.mark.parametrize("schema", [None, 0, "1", True])
def test_un_esquema_que_no_es_un_entero_valido(tmp_path: Path, schema: object) -> None:
    _write_raw(tmp_path, {**V1, "schema": schema})
    with pytest.raises(LockError, match="schema"):
        lock.read(tmp_path)


def test_el_esquema_actual_no_tiene_pasos_pendientes() -> None:
    assert sorted(lock.MIGRATIONS) == list(range(1, lock.SCHEMA))
