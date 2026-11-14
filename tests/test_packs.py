"""packs y raíz de contenido: manifiestos, dependencias y descubrimiento."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import _meta, content, packs
from exo.packs import PackError


def _pack(root: Path, pack_name: str, /, **fields: object) -> Path:
    folder = root / "packs" / pack_name
    folder.mkdir(parents=True)
    manifest = {"name": pack_name, "version": "0.1.0", "description": f"pack {pack_name}", **fields}
    (folder / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def _skill(pack_dir: Path, name: str, description: str = "hace algo", folder: str | None = None) -> Path:
    skill = pack_dir / "skills" / (folder or name)
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n", encoding="utf-8"
    )
    return skill


# -- raíz de contenido --------------------------------------------------------


def test_contenido_del_repo_en_modo_editable() -> None:
    root = content.content_root()
    assert (root / "packs" / "core" / "pack.json").is_file()


def test_variable_de_entorno_gana(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "packs").mkdir()
    monkeypatch.setenv(content.ENV_VAR, str(tmp_path))
    assert content.content_root() == tmp_path.resolve()
    assert f"{_meta.ENV_PREFIX}CONTENT_ROOT" == content.ENV_VAR


def test_variable_de_entorno_invalida(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(content.ENV_VAR, str(tmp_path / "no-existe"))
    with pytest.raises(content.ContentError, match=content.ENV_VAR):
        content.content_root()


def test_sin_contenido_disponible(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(content.ENV_VAR, raising=False)
    monkeypatch.setattr(content, "_CANDIDATES", (tmp_path / "a", tmp_path / "b"))
    with pytest.raises(content.ContentError, match="not found"):
        content.content_root()


# -- packs reales -------------------------------------------------------------


def test_packs_del_motor() -> None:
    collection = packs.load_collection(content.content_root())
    assert {"core", "sdd"} <= set(collection.packs)
    assert collection.packs["sdd"].requires == ("core",)
    assert packs.resolve(collection.packs, ["sdd"]) == ["core", "sdd"]
    assert "memory-protocol" in {s.name for s in collection.skills}
    assert collection.duplicates() == {}


# -- manifiestos --------------------------------------------------------------


@pytest.mark.parametrize(
    ("fields", "fragment"),
    [
        ({"name": "otro"}, "match the folder name"),
        ({"version": "1.0"}, "semver"),
        ({"version": 1}, "semver"),
        ({"description": ""}, "description"),
        ({"requires": "core"}, "requires"),
        ({"optional": ["Mal Nombre"]}, "optional"),
    ],
)
def test_manifiesto_invalido(tmp_path: Path, fields: dict, fragment: str) -> None:
    folder = _pack(tmp_path, "mio", **fields)
    with pytest.raises(PackError, match=fragment):
        packs.load_pack(folder)


def test_manifiesto_faltante_o_roto(tmp_path: Path) -> None:
    folder = tmp_path / "packs" / "vacio"
    folder.mkdir(parents=True)
    with pytest.raises(PackError, match="pack.json"):
        packs.load_pack(folder)
    (folder / "pack.json").write_text("{ roto", encoding="utf-8")
    with pytest.raises(PackError, match="JSON"):
        packs.load_pack(folder)
    (folder / "pack.json").write_text("[]", encoding="utf-8")
    with pytest.raises(PackError, match="object"):
        packs.load_pack(folder)


def test_semver_con_prerelease(tmp_path: Path) -> None:
    assert packs.load_pack(_pack(tmp_path, "mio", version="1.2.3-rc.1+build.5")).version == "1.2.3-rc.1+build.5"


# -- dependencias -------------------------------------------------------------


def test_resolve_en_cascada_y_orden_topologico(tmp_path: Path) -> None:
    _pack(tmp_path, "core")
    _pack(tmp_path, "sdd", requires=["core"])
    _pack(tmp_path, "quality", requires=["core"])
    _pack(tmp_path, "java", requires=["quality", "sdd"])
    loaded = packs.load_packs(tmp_path)
    assert packs.resolve(loaded, ["java"]) == ["core", "quality", "sdd", "java"]
    assert packs.resolve(loaded, ["sdd", "core", "sdd"]) == ["core", "sdd"]


def test_resolve_detecta_ciclos(tmp_path: Path) -> None:
    _pack(tmp_path, "a", requires=["b"])
    _pack(tmp_path, "b", requires=["c"])
    _pack(tmp_path, "c", requires=["a"])
    with pytest.raises(PackError, match="cycle: a -> b -> c -> a"):
        packs.resolve(packs.load_packs(tmp_path), ["a"])


def test_resolve_pack_inexistente(tmp_path: Path) -> None:
    _pack(tmp_path, "a", requires=["fantasma"])
    loaded = packs.load_packs(tmp_path)
    with pytest.raises(PackError, match="fantasma"):
        packs.resolve(loaded, ["a"])
    with pytest.raises(PackError, match="nada"):
        packs.resolve(loaded, ["nada"])


# -- skills y subagentes ------------------------------------------------------


def test_descubrimiento_de_skills_y_subagentes(tmp_path: Path) -> None:
    core = _pack(tmp_path, "core")
    _skill(core, "uno", "primera     linea")
    (core / "skills" / "sin-skill-md").mkdir()
    (core / "skills" / "_soporte").mkdir()
    (core / "agents").mkdir()
    (core / "agents" / "sdd-explorer.md").write_text(
        "---\nname: sdd-explorer\ndescription: explora\ntools: Read, Grep\n---\ncuerpo\n",
        encoding="utf-8",
    )
    collection = packs.load_collection(tmp_path)
    assert [(s.name, s.pack, s.description) for s in collection.skills] == [("uno", "core", "primera linea")]
    assert collection.skills[0].path == core / "skills" / "uno"
    assert [(a.name, a.pack) for a in collection.subagents] == [("sdd-explorer", "core")]


def test_skill_sin_nombre_usa_la_carpeta(tmp_path: Path) -> None:
    core = _pack(tmp_path, "core")
    folder = core / "skills" / "anonima"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("# sin frontmatter\n", encoding="utf-8")
    skill = packs.load_collection(tmp_path).skills[0]
    assert (skill.name, skill.description) == ("anonima", "")


def test_nombres_duplicados_en_la_coleccion(tmp_path: Path) -> None:
    _skill(_pack(tmp_path, "core"), "repetida")
    _skill(_pack(tmp_path, "sdd"), "repetida")
    dupes = packs.load_collection(tmp_path).duplicates()
    assert list(dupes) == ["repetida"]
    assert [s.pack for s in dupes["repetida"]] == ["core", "sdd"]


def test_load_packs_ignora_carpetas_de_soporte(tmp_path: Path) -> None:
    _pack(tmp_path, "core")
    (tmp_path / "packs" / "_borrador").mkdir()
    (tmp_path / "packs" / "notas.txt").write_text("x", encoding="utf-8")
    assert list(packs.load_packs(tmp_path)) == ["core"]


def test_load_packs_sin_carpeta(tmp_path: Path) -> None:
    assert packs.load_packs(tmp_path) == {}
