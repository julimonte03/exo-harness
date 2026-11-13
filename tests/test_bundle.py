"""installer/bundle: lo que se instala, leído del contenido del motor."""

from __future__ import annotations

import pytest

from exo import content
from exo.installer.bundle import build_bundle
from exo.packs import PackError


def test_bundle_del_contenido_real() -> None:
    bundle = build_bundle(content.content_root(), ["sdd"])
    assert bundle.packs == ("core", "sdd")
    names = [s.name for s in bundle.skills]
    assert names == sorted(names)
    assert {"hello-exo", "memory-protocol", "sdd-status"} <= set(names)
    assert {a.name for a in bundle.subagents} == {"sdd-explorer", "sdd-implementer", "sdd-verifier", "sdd-judge"}
    skill = next(s for s in bundle.skills if s.name == "hello-exo")
    assert skill.pack == "core"
    assert set(skill.files) == {"SKILL.md"}
    assert skill.files["SKILL.md"] == (content.content_root() / "packs/core/skills/hello-exo/SKILL.md").read_bytes()
    assert bundle.rules.startswith("# Project rules")


def test_solo_core_no_trae_lo_de_sdd() -> None:
    bundle = build_bundle(content.content_root(), ["core"])
    assert bundle.packs == ("core",)
    assert "sdd-status" not in [s.name for s in bundle.skills]
    assert bundle.subagents == ()


def test_pack_inexistente() -> None:
    with pytest.raises(PackError, match="does not exist"):
        build_bundle(content.content_root(), ["fantasma"])
