"""validate: reglas del contenido (§10.5 adaptado), un fixture por violación."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from exo import _meta, content
from exo.cli import main
from exo.validate import validate

PREFIX = f"{_meta.NAME}-"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _skill_md(name: str, description: str = "Hace algo. Use when needed.", extra: str = "", body: str = "") -> str:
    return f"---\nname: {name}\ndescription: {description}\n{extra}---\n\n# {name}\n{body}"


def _base(root: Path) -> Path:
    for name, requires, optional in (("core", [], []), ("sdd", ["core"], [])):
        _write(
            root / "packs" / name / "pack.json",
            json.dumps({"name": name, "version": "0.1.0", "description": f"pack {name}", "requires": requires, "optional": optional}),
        )
    _write(root / "packs" / "core" / "skills" / "base" / "SKILL.md", _skill_md("base"))
    _write(
        root / "packs" / "sdd" / "skills" / "flujo" / "SKILL.md",
        _skill_md("flujo", extra=f"metadata:\n  {PREFIX}pack: sdd\n", body="Usa skill:base y ver [reglas](references/reglas.md).\n"),
    )
    _write(root / "packs" / "sdd" / "skills" / "flujo" / "references" / "reglas.md", "reglas\n")
    _write(root / "packs" / "sdd" / "agents" / "sdd-explorer.md", "---\nname: sdd-explorer\ndescription: explora\n---\ncuerpo\n")
    _write(root / "rules" / "AGENTS.base.md", "# Reglas\n- una\n")
    return root


def _messages(root: Path) -> list[str]:
    return [f"{f.path}: {f.message}" for f in validate(root).errors]


def test_contenido_del_motor_es_valido() -> None:
    report = validate(content.content_root())
    assert report.errors == [], [f.message for f in report.errors]
    assert report.counts["packs"] >= 2
    assert report.counts["skills"] >= 1


def test_base_sintetica_es_valida(tmp_path: Path) -> None:
    report = validate(_base(tmp_path))
    assert report.errors == []
    assert report.counts == {"packs": 2, "skills": 2, "subagents": 1, "shared": 0}


Mutation = Callable[[Path], None]


def _replace(rel: str, old: str, new: str) -> Mutation:
    def apply(root: Path) -> None:
        path = root / rel
        path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    return apply


def _put(rel: str, text: str) -> Mutation:
    return lambda root: _write(root / rel, text)


FLUJO = "packs/sdd/skills/flujo/SKILL.md"
BASE = "packs/core/skills/base/SKILL.md"


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (_replace("packs/sdd/pack.json", '"name": "sdd"', '"name": "otro"'), "match the folder name"),
        (_replace("packs/sdd/pack.json", '"0.1.0"', '"1.0"'), "semver"),
        (_replace("packs/sdd/pack.json", '"requires": ["core"]', '"requires": ["fantasma"]'), "fantasma"),
        (_replace(BASE, "name: base", "name: otra"), "match the folder name"),
        (_replace(BASE, "name: base", "name: Base_Mal"), "kebab-case"),
        (_put("packs/core/skills/" + "a" * 65 + "/SKILL.md", _skill_md("a" * 65)), "64"),
        (_put("packs/core/skills/con--doble/SKILL.md", _skill_md("con--doble")), "kebab-case"),
        (_replace(BASE, "description: Hace algo. Use when needed.\n", ""), "missing description"),
        (_replace(BASE, "Hace algo.", "x" * 1025), "1024"),
        (_put("packs/sdd/skills/base/SKILL.md", _skill_md("base")), "duplicate skill name"),
        (_replace(BASE, "Hace algo.", "Ense\\u00f1a algo."), "Unicode escape"),
        (_replace(BASE, "# base\n", "# base\nCuerpo con ense\\u00f1anza.\n"), "Unicode escape"),
        (_replace(BASE, "---\n\n# base", "triggers: [a]\n---\n\n# base"), "not part of the Agent Skills standard"),
        (_replace(FLUJO, f"  {PREFIX}pack: sdd\n", f"  {PREFIX}pack: [sdd]\n"), "string"),
        (_replace(BASE, "name: base\n", "name: base\nname: base\n"), "duplicate key"),
        (_replace(BASE, "---\nname", "name"), "frontmatter"),
        (_replace(FLUJO, "skill:base", "skill:inexistente"), "inexistente"),
        (_replace("packs/sdd/pack.json", '"requires": ["core"]', '"requires": []'), "does not declare"),
        (_replace(FLUJO, "references/reglas.md", "references/falta.md"), "references/falta.md"),
        (_put("rules/AGENTS.base.md", "linea\n" * 61), "60 lines"),
        (_replace(BASE, "# base\n", "# base\npassword = \"" + "s3cr3t" + "-real-123\"\n"), "secret"),
        (_put("packs/sdd/agents/sin-nombre.md", "---\ndescription: x\n---\n"), "name"),
        (_put("packs/core/agents/sdd-explorer.md", "---\nname: sdd-explorer\ndescription: x\n---\n"), "duplicate subagent"),
    ],
)
def test_cada_violacion_da_un_error_especifico(tmp_path: Path, mutate: Mutation, fragment: str) -> None:
    root = _base(tmp_path)
    mutate(root)
    messages = _messages(root)
    assert any(fragment in m for m in messages), messages


def test_secretos_dentro_de_bloques_de_codigo_no_cuentan(tmp_path: Path) -> None:
    root = _base(tmp_path)
    _replace(BASE, "# base\n", "# base\n```\npassword = \"" + "s3cr3t" + "-real-123\"\n```\n")(root)
    assert _messages(root) == []


def test_skill_larga_da_advertencia(tmp_path: Path) -> None:
    root = _base(tmp_path)
    _replace(BASE, "# base\n", "# base\n" + "linea\n" * 501)(root)
    report = validate(root)
    assert report.errors == []
    assert any("500 lines" in w.message for w in report.warnings)


MAP_PATH = Path("packs") / "core" / "shared" / "phase-skill-map.md"
MAP = """# Phase → skill map

## Map

| Phase | Required |
|---|---|
| verify | `judge-security` |

## Skills from packs not installed yet

| Skill | Pack | Inline criteria when missing |
|---|---|---|
| `judge-security` | quality | Review the diff for security issues, read-only. |
"""


def _optional(root: Path, optional: list[str]) -> None:
    manifest = {"name": "sdd", "version": "0.1.0", "description": "x", "requires": ["core"], "optional": optional}
    _write(root / "packs" / "sdd" / "pack.json", json.dumps(manifest))


def test_referencia_sin_resolver_es_error_aunque_haya_opcionales(tmp_path: Path) -> None:
    """Antes era advertencia si el pack declaraba opcionales ausentes: un typo pasaba."""
    root = _base(tmp_path)
    _replace(FLUJO, "skill:base", "skill:base y skill:judge-securty")(root)
    _optional(root, ["quality"])
    assert any("skill:judge-securty" in m for m in _messages(root))


def test_referencia_declarada_en_el_mapa_degrada(tmp_path: Path) -> None:
    root = _base(tmp_path)
    _replace(FLUJO, "skill:base", "skill:base y skill:judge-security")(root)
    _optional(root, ["quality"])
    _write(root / MAP_PATH, MAP)
    report = validate(root)
    assert report.errors == [], [f.message for f in report.errors]


def test_degradacion_de_un_pack_que_no_se_declara(tmp_path: Path) -> None:
    root = _base(tmp_path)
    _replace(FLUJO, "skill:base", "skill:base y skill:judge-security")(root)
    _write(root / MAP_PATH, MAP)
    assert any("quality" in m and "optional" in m for m in _messages(root))


# -- contratos compartidos --------------------------------------------------


def test_contratos_validos_y_contados(tmp_path: Path) -> None:
    root = _base(tmp_path)
    _write(root / "packs" / "sdd" / "shared" / "contrato.md", "# Contract\n\nUses skill:base.\n")
    _write(root / "packs" / "sdd" / "shared" / "schemas" / "x.schema.json", '{"type": "object"}\n')
    report = validate(root)
    assert report.errors == []
    assert report.counts["shared"] == 2


@pytest.mark.parametrize(
    ("rel", "text", "fragment"),
    [
        ("datos.json", "{ roto", "not valid JSON"),
        ("schemas/x.schema.json", '{"oneOf": []}', "unsupported keyword"),
        ("contrato.md", "Escape \\u00f1 literal.\n", "literal Unicode escape"),
        ("contrato.md", "Uses skill:no-existe.\n", "skill:no-existe"),
    ],
)
def test_reglas_de_los_contratos(tmp_path: Path, rel: str, text: str, fragment: str) -> None:
    root = _base(tmp_path)
    _write(root / "packs" / "sdd" / "shared" / rel, text)
    assert any(fragment in m for m in _messages(root)), _messages(root)


def test_rutas_a_contratos_que_no_existen(tmp_path: Path) -> None:
    root = _base(tmp_path)
    shared = f"{_meta.PROJECT_DIR}/shared"
    _write(root / "packs" / "sdd" / "shared" / "contrato.md", "# Contract\n")
    _replace(
        FLUJO,
        "skill:base",
        f"skill:base, `{shared}/contrato.md`, `{shared}/templates/proposal.md`, `{shared}/templates/`",
    )(root)
    assert _messages(root) == []
    _replace(FLUJO, "skill:base", f"skill:base y `{shared}/no-existe.md`")(root)
    assert any("no-existe.md" in m and "does not exist" in m for m in _messages(root))


def test_cli_validate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _base(tmp_path)
    assert main(["validate", "--root", str(root)]) == 0
    assert "all valid" in capsys.readouterr().out
    _replace(BASE, "name: base", "name: otra")(root)
    assert main(["validate", "--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "error:" in out
    assert main(["validate", "--root", str(root), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["errors"][0]["path"].endswith("SKILL.md")


def test_cli_validate_contenido_del_motor(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate"]) == 0
    assert "all valid" in capsys.readouterr().out


# -- ajustes de la revisión F1 -------------------------------------------------


def test_skill_de_exactamente_500_lineas_no_avisa(tmp_path: Path) -> None:
    root = _base(tmp_path)
    head = _skill_md("base")
    padding = "linea\n" * (500 - len(head.splitlines()))
    _write(root / BASE, head + padding)
    assert len((root / BASE).read_text(encoding="utf-8").splitlines()) == 500
    assert not any("500 lines" in w.message for w in validate(root).warnings)


def test_references_dentro_de_urls_no_cuentan(tmp_path: Path) -> None:
    root = _base(tmp_path)
    _replace(BASE, "# base\n", "# base\nVer https://example.com/docs/references/guia.md y otra/references/x.md\n")(root)
    assert _messages(root) == []


def test_carpeta_de_skill_sin_skill_md_avisa(tmp_path: Path) -> None:
    root = _base(tmp_path)
    (root / "packs" / "core" / "skills" / "solo-referencias" / "references").mkdir(parents=True)
    report = validate(root)
    assert report.errors == []
    assert any("without SKILL.md" in w.message for w in report.warnings)


def test_skill_que_no_es_utf8(tmp_path: Path) -> None:
    root = _base(tmp_path)
    (root / BASE).write_bytes(b"---\nname: base\ndescription: \xff\n---\n")
    assert any("UTF-8" in m for m in _messages(root))


def test_las_references_tambien_se_revisan(tmp_path: Path) -> None:
    root = _base(tmp_path)
    references = root / "packs" / "sdd" / "skills" / "flujo" / "references"
    _write(references / "reglas.md", "See skill:no-existe.\n")
    assert any("skill:no-existe" in m and "reglas.md" in m for m in _messages(root))


def test_un_pack_cita_solo_contratos_suyos_o_de_lo_que_requiere(tmp_path: Path) -> None:
    """Con solo core instalado, un contrato de sdd no está: core no puede citarlo."""
    root = _base(tmp_path)
    shared = f"{_meta.PROJECT_DIR}/shared"
    _write(root / "packs" / "sdd" / "shared" / "ciclo.md", "# Cycle\n")
    _write(root / "packs" / "core" / "shared" / "comun.md", "# Common\n")
    _replace(FLUJO, "skill:base", f"skill:base, `{shared}/ciclo.md` y `{shared}/comun.md`")(root)
    assert _messages(root) == []
    _replace(BASE, "# base\n", f"# base\nSee `{shared}/ciclo.md`.\n")(root)
    assert any("ciclo.md" in m and "pack sdd" in m for m in _messages(root)), _messages(root)
