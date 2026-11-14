"""registry: render determinista de skill-registry.md y `exo registry`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import _meta, registry
from exo.cli import main
from exo.installer import project
from exo.packs import Skill


def _skills(base: Path) -> list[Skill]:
    return [
        Skill("zeta", "última | con barra", "sdd", base / "packs" / "sdd" / "skills" / "zeta", {}),
        Skill("alfa", "primera\n  en dos líneas", "core", base / "packs" / "core" / "skills" / "alfa", {}),
    ]


def test_render_ordenado_y_escapado(tmp_path: Path) -> None:
    text = registry.render(_skills(tmp_path), base=tmp_path)
    lines = text.splitlines()
    assert lines[0] == "# Skill registry"
    assert f"{_meta.NAME} registry" in text
    rows = [line for line in lines if line.startswith("| ") and not line.startswith("| Skill")]
    assert rows == [
        "| alfa | core | primera en dos líneas | packs/core/skills/alfa/SKILL.md |",
        "| zeta | sdd | última \\| con barra | packs/sdd/skills/zeta/SKILL.md |",
    ]
    assert registry.render(list(reversed(_skills(tmp_path))), base=tmp_path) == text
    assert text.endswith("\n")


def test_render_vacio(tmp_path: Path) -> None:
    assert "_No skills._" in registry.render([], base=tmp_path)


def test_cli_registry_desde_el_contenido(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["registry", "--project", str(tmp_path)]) == 0
    out = tmp_path / _meta.PROJECT_DIR / "skill-registry.md"
    assert "| memory-protocol | core |" in out.read_text(encoding="utf-8")
    assert "updated" in capsys.readouterr().out
    assert main(["registry", "--project", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed"] is False
    assert "memory-protocol" in [s["name"] for s in payload["skills"]]


def test_cli_registry_desde_skills_instaladas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installed = tmp_path / ".agents" / "skills" / "mia"
    installed.mkdir(parents=True)
    (installed / "SKILL.md").write_text(
        "---\nname: mia\ndescription: propia\nmetadata:\n  exo-pack: core\n---\n", encoding="utf-8"
    )
    assert main(["registry", "--project", str(tmp_path), "--from", str(tmp_path / ".agents" / "skills"), "--stdout"]) == 0
    out = capsys.readouterr().out
    assert "| mia | core | propia | .agents/skills/mia/SKILL.md |" in out
    assert not (tmp_path / _meta.PROJECT_DIR / "skill-registry.md").exists()


def test_cli_registry_from_inexistente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["registry", "--project", str(tmp_path), "--from", str(tmp_path / "nada")]) == 1
    assert "does not exist" in capsys.readouterr().err


def test_cli_registry_no_pisa_el_registro_instalado(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """El registro instalado está en el lock: si `exo registry` lo pisa, el próximo sync da conflicto."""
    project.sync(tmp_path, agents=["claude-code"])
    target = registry.registry_path(tmp_path)
    before = target.read_bytes()
    capsys.readouterr()
    assert main(["registry", "--project", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "exo sync" in err and "--stdout" in err
    assert target.read_bytes() == before
    assert main(["registry", "--project", str(tmp_path), "--stdout"]) == 0
    assert "| memory-protocol | core |" in capsys.readouterr().out
    assert project.sync(tmp_path).engine.conflicts == []
