"""installer/bundle: lo que se instala, leído del contenido del motor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import _content
from exo import content
from exo.installer.bundle import build_bundle
from exo.packs import PackError
from exo.sdd import record, speclint


def test_bundle_del_contenido_real() -> None:
    bundle = build_bundle(content.content_root(), ["sdd"])
    assert bundle.packs == ("core", "sdd")
    names = [s.name for s in bundle.skills]
    assert names == sorted(names)
    assert {"memory-protocol", "sdd-status"} <= set(names)
    assert {a.name for a in bundle.subagents} == {"sdd-explorer", "sdd-implementer", "sdd-verifier", "sdd-judge"}
    skill = next(s for s in bundle.skills if s.name == "memory-protocol")
    assert skill.pack == "core"
    assert "SKILL.md" in skill.files
    assert skill.files["SKILL.md"] == (content.content_root() / "packs/core/skills/memory-protocol/SKILL.md").read_bytes()
    assert bundle.rules.startswith("# Project rules")


def test_las_carpetas_del_runtime_son_las_de_speclint_y_record() -> None:
    """El bundle arma las rutas sin importar speclint ni record (F8); tienen que ser las mismas."""
    from exo.installer import bundle

    folders = {name: source for name, source, _pattern in bundle.ENGINE_SHARED}
    assert folders == {"templates": speclint.TEMPLATES_DIR, "schemas": record.SCHEMAS_DIR}


def test_solo_core_no_trae_lo_de_sdd() -> None:
    bundle = build_bundle(content.content_root(), ["core"])
    assert bundle.packs == ("core",)
    assert "sdd-status" not in [s.name for s in bundle.skills]
    assert bundle.subagents == ()


def test_pack_inexistente() -> None:
    with pytest.raises(PackError, match="does not exist"):
        build_bundle(content.content_root(), ["fantasma"])


def test_shared_por_pack(tmp_path: Path) -> None:
    root = _content.build(tmp_path / "c")
    solo_core = build_bundle(root, ["core"])
    assert "demo-contract.md" not in solo_core.shared
    con_sdd = build_bundle(root, ["sdd"])
    assert con_sdd.shared["demo-contract.md"] == _content.CONTRACT.encode()
    assert json.loads(con_sdd.shared["schemas/demo.schema.json"]) == _content.SCHEMA


def test_las_plantillas_de_speclint_van_con_core(tmp_path: Path) -> None:
    """Core se instala siempre y sus skills citan las plantillas (test-spec, pr)."""
    root = _content.build(tmp_path / "c")
    shared = build_bundle(root, ["core"]).shared
    templates = sorted(speclint.TEMPLATES_DIR.glob("*.md"))
    assert templates
    for path in templates:
        assert shared[f"templates/{path.name}"] == path.read_bytes()


def test_los_esquemas_del_runtime_van_con_core(tmp_path: Path) -> None:
    root = _content.build(tmp_path / "c")
    shared = build_bundle(root, ["core"]).shared
    assert shared["schemas/ai-usage-record.schema.json"] == record.SCHEMA_FILE.read_bytes()
    assert "schemas/demo.schema.json" not in shared  # ese es del pack sdd
    assert "schemas/demo.schema.json" in build_bundle(root, ["sdd"]).shared


def test_dos_packs_con_el_mismo_contrato(tmp_path: Path) -> None:
    root = _content.build(tmp_path / "c")
    clash = root / "packs" / "core" / "shared" / "demo-contract.md"
    clash.parent.mkdir(parents=True)
    clash.write_bytes(b"# Other\n")
    with pytest.raises(ValueError, match="demo-contract.md"):
        build_bundle(root, ["sdd"])


def test_shared_en_la_raiz_del_contenido_no_se_instala(tmp_path: Path) -> None:
    root = _content.build(tmp_path / "c")
    (root / "shared").mkdir()
    (root / "shared" / "suelto.md").write_bytes(b"# Loose\n")
    assert "suelto.md" not in build_bundle(root, ["sdd"]).shared
