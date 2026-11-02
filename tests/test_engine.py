"""installer/engine: altas, cambios, bajas, conflictos, adopción, dry-run e idempotencia."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import _meta
from exo.core import fsutil, lock, snapshots
from exo.installer import engine
from exo.installer.ops import MergeBlock, MergeKey, MergeListItem, WriteFile, merge_duplicates

OWNER = "adapter:test"


def _ops(skill: bytes = b"skill v1\n") -> list:
    return [
        WriteFile(".claude/skills/demo/SKILL.md", skill, OWNER, kind="mirror"),
        WriteFile(f"{_meta.PROJECT_DIR}/skill-registry.md", b"# registro\n", "engine"),
        MergeBlock("AGENTS.md", "core", "reglas", "engine"),
        MergeKey(".mcp.json", "mcpServers.motor", {"command": "x"}, OWNER),
        MergeListItem(".claude/settings.json", "permissions.allow", "Bash(x:*)", OWNER),
    ]


def _apply(project: Path, ops: list, **kwargs) -> engine.Result:
    return engine.apply(project, ops, agents=["claude-code"], packs=["core"], **kwargs)


def _tree(project: Path) -> dict[str, bytes]:
    backups = project / _meta.PROJECT_DIR / "backups"
    return {
        p.relative_to(project).as_posix(): p.read_bytes()
        for p in sorted(project.rglob("*"))
        if p.is_file() and not p.is_relative_to(backups)
    }


def test_alta_en_proyecto_vacio(tmp_path: Path) -> None:
    result = _apply(tmp_path, _ops())
    assert result.applied and result.changed
    assert sorted(a.action for a in result.actions) == ["create"] * 5
    assert (tmp_path / ".claude" / "skills" / "demo" / "SKILL.md").read_bytes() == b"skill v1\n"
    assert json.loads((tmp_path / ".mcp.json").read_text()) == {"mcpServers": {"motor": {"command": "x"}}}
    assert json.loads((tmp_path / ".claude" / "settings.json").read_text()) == {"permissions": {"allow": ["Bash(x:*)"]}}
    data = lock.read(tmp_path)
    assert len(data.files) == 5
    assert {e.kind: e.created for e in data.files} == {"mirror": False, "file": False, "block": True, "key": True, "item": True}
    assert result.snapshot is not None
    assert lock.drift(tmp_path) == []


def test_segunda_vez_sin_cambios_ni_snapshot(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    before = _tree(tmp_path)
    snaps = snapshots.list_snapshots(tmp_path)
    result = _apply(tmp_path, _ops())
    assert result.changed is False
    assert result.snapshot is None
    assert _tree(tmp_path) == before
    assert snapshots.list_snapshots(tmp_path) == snaps


def test_cambio_de_contenido(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    result = _apply(tmp_path, _ops(b"skill v2\n"))
    assert [(a.action, a.path) for a in result.actions if a.action != "adopt"] == [("update", ".claude/skills/demo/SKILL.md")]
    assert (tmp_path / ".claude" / "skills" / "demo" / "SKILL.md").read_bytes() == b"skill v2\n"
    assert result.snapshot is not None


def test_baja_borra_y_poda_directorios(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    ops = [op for op in _ops() if not op.path.startswith(".claude/skills")]
    result = _apply(tmp_path, ops)
    assert ("remove", ".claude/skills/demo/SKILL.md") in [(a.action, a.path) for a in result.actions]
    assert not (tmp_path / ".claude" / "skills").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()


def test_desinstalar_todo_deja_el_proyecto_como_estaba(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_bytes(b"# del humano\r\n\r\ntexto\r\n")
    (tmp_path / ".mcp.json").write_bytes(b'{\n  "mcpServers": {\n    "otro": {}\n  }\n}\n')
    original = _tree(tmp_path)
    _apply(tmp_path, _ops())
    result = engine.apply(tmp_path, [], agents=[], packs=[])
    assert all(a.action == "remove" for a in result.actions)
    after = {k: v for k, v in _tree(tmp_path).items() if not k.startswith(_meta.PROJECT_DIR)}
    assert after == original


def test_conflicto_por_edicion_manual_no_escribe_nada(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    skill = tmp_path / ".claude" / "skills" / "demo" / "SKILL.md"
    skill.write_bytes(b"editado a mano\n")
    before = _tree(tmp_path)
    result = _apply(tmp_path, _ops(b"skill v2\n"))
    assert result.applied is False
    assert [(c.path, c.reason) for c in result.conflicts] == [(".claude/skills/demo/SKILL.md", "modificado a mano desde la última instalación")]
    assert _tree(tmp_path) == before
    forced = _apply(tmp_path, _ops(b"skill v2\n"), force=True)
    assert forced.applied
    assert skill.read_bytes() == b"skill v2\n"
    archive = snapshots.read_archive((tmp_path / _meta.PROJECT_DIR / "backups" / forced.snapshot).read_bytes())
    assert archive.files[".claude/skills/demo/SKILL.md"][0] == b"editado a mano\n"


def test_archivo_del_humano_con_otro_contenido_es_conflicto(tmp_path: Path) -> None:
    skill = tmp_path / ".claude" / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"mia\n")
    result = _apply(tmp_path, _ops())
    assert [c.path for c in result.conflicts] == [".claude/skills/demo/SKILL.md"]
    assert skill.read_bytes() == b"mia\n"
    assert not (tmp_path / "AGENTS.md").exists()


def test_archivo_igual_se_adopta_sin_registrarlo(tmp_path: Path) -> None:
    skill = tmp_path / ".claude" / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"skill v1\n")
    result = _apply(tmp_path, _ops())
    assert ("adopt", ".claude/skills/demo/SKILL.md") in [(a.action, a.path) for a in result.actions]
    assert ".claude/skills/demo/SKILL.md" not in [e.path for e in lock.read(tmp_path).files]
    engine.apply(tmp_path, [], agents=[], packs=[])
    assert skill.read_bytes() == b"skill v1\n"


def test_archivo_generado_borrado_se_recrea(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    (tmp_path / _meta.PROJECT_DIR / "skill-registry.md").unlink()
    result = _apply(tmp_path, _ops())
    assert ("create", f"{_meta.PROJECT_DIR}/skill-registry.md") in [(a.action, a.path) for a in result.actions]
    assert result.conflicts == []


def test_baja_de_algo_editado_a_mano_es_conflicto(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    (tmp_path / _meta.PROJECT_DIR / "skill-registry.md").write_bytes(b"tocado")
    result = engine.apply(tmp_path, [], agents=[], packs=[])
    assert [c.reason for c in result.conflicts] == ["modificado a mano; no se quita"]
    assert (tmp_path / "AGENTS.md").exists()


def test_baja_de_algo_que_ya_no_existe(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    (tmp_path / _meta.PROJECT_DIR / "skill-registry.md").unlink()
    result = _apply(tmp_path, [op for op in _ops() if "registry" not in op.path])
    assert ("forget", f"{_meta.PROJECT_DIR}/skill-registry.md") in [(a.action, a.path) for a in result.actions]


def test_jsonc_se_saltea_con_snippet(tmp_path: Path) -> None:
    original = b'{\n  // comentario\n  "mcpServers": {}\n}\n'
    (tmp_path / ".mcp.json").write_bytes(original)
    result = _apply(tmp_path, _ops())
    assert result.applied
    assert ("skip", ".mcp.json") in [(a.action, a.path) for a in result.actions]
    assert '"motor"' in result.warnings[0]
    assert (tmp_path / ".mcp.json").read_bytes() == original
    assert ".mcp.json" not in [e.path for e in lock.read(tmp_path).files]


def test_dry_run_no_escribe(tmp_path: Path) -> None:
    result = _apply(tmp_path, _ops(), dry_run=True)
    assert result.applied is False
    assert len(result.actions) == 5
    assert list(tmp_path.iterdir()) == []


def test_bloque_en_archivo_del_humano_y_marcadores_rotos(tmp_path: Path) -> None:
    begin = f"<!-- BEGIN:{_meta.BLOCK_PREFIX}:core -->"
    (tmp_path / "AGENTS.md").write_text(f"{begin}\nsin cierre\n", encoding="utf-8")
    result = _apply(tmp_path, _ops())
    assert result.applied is False
    assert "marcadores inválidos" in result.conflicts[0].reason


def test_ruta_que_pasa_por_un_link_es_conflicto(tmp_path: Path, make_dir_link) -> None:
    outside = tmp_path / "afuera"
    outside.mkdir()
    project = tmp_path / "proyecto"
    project.mkdir()
    make_dir_link(project / ".claude", outside)
    result = _apply(project, _ops())
    assert any("symlink o junction" in c.reason for c in result.conflicts)
    assert list(outside.iterdir()) == []


def test_cambio_solo_del_lock(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    snaps = snapshots.list_snapshots(tmp_path)
    result = engine.apply(tmp_path, _ops(), agents=["claude-code", "copilot"], packs=["core"])
    assert result.lock_changed and result.snapshot is None
    assert lock.read(tmp_path).agents == ["claude-code", "copilot"]
    assert snapshots.list_snapshots(tmp_path) == snaps


def test_merge_duplicates() -> None:
    a = WriteFile("x", b"1", "adapter:claude-code", kind="mirror")
    b = WriteFile("x", b"1", "adapter:copilot", kind="mirror")
    assert [op.owner for op in merge_duplicates([a, b])] == ["adapter:claude-code,copilot"]
    with pytest.raises(ValueError, match="distintos"):
        merge_duplicates([a, WriteFile("x", b"2", "adapter:copilot", kind="mirror")])
    key1 = MergeKey("m.json", "k", {"a": 1, "b": 2}, "adapter:x")
    key2 = MergeKey("m.json", "k", {"b": 2, "a": 1}, "engine")
    assert [op.owner for op in merge_duplicates([key1, key2])] == ["engine;adapter:x"]


def test_hashes_del_lock_coinciden_con_el_disco(tmp_path: Path) -> None:
    _apply(tmp_path, _ops())
    for entry in lock.read(tmp_path).files:
        assert lock.current_hash(tmp_path, entry) == entry.sha256, entry
    assert fsutil.sha256_file(tmp_path / ".claude" / "skills" / "demo" / "SKILL.md") == fsutil.sha256_bytes(b"skill v1\n")
