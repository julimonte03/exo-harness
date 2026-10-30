"""core/frontmatter: subconjunto de YAML para el estándar Agent Skills."""

from __future__ import annotations

import pytest

from exo.core.frontmatter import FrontmatterError, parse

SKILL = """---
name: sdd-verify
description: >-
  Verifica que la implementación cumple spec y diseño,
  en contexto fresco.

  Usala cuando ... / Use when ...
metadata:
  exo-pack: sdd
  exo-execution: subagent        # subagent | inline
  exo-subagent: sdd-verifier
  exo-tags: [verify, "fresh context"]
---

# sdd-verify
cuerpo
"""


def test_skill_canonica() -> None:
    data, body = parse(SKILL, strict=True)
    assert data["name"] == "sdd-verify"
    assert data["description"] == (
        "Verifica que la implementación cumple spec y diseño, en contexto fresco.\n"
        "Usala cuando ... / Use when ..."
    )
    assert data["metadata"] == {
        "exo-pack": "sdd",
        "exo-execution": "subagent",
        "exo-subagent": "sdd-verifier",
        "exo-tags": ["verify", "fresh context"],
    }
    assert body == "\n# sdd-verify\ncuerpo\n"


def test_escalares_y_tipos() -> None:
    text = (
        "---\n"
        "a: hola mundo\n"
        "b: 'con '' comilla'\n"
        'c: "tab\\tsalto\\ncomilla\\" barra\\\\"\n'
        "d: true\n"
        "e: False\n"
        "f: 42\n"
        "g: -7\n"
        "h: null\n"
        "i: ~\n"
        "j: 1.0\n"
        "k: http://x.y/z#frag\n"
        "l: valor # comentario\n"
        "m: ''\n"
        "---\n"
    )
    data, body = parse(text, strict=True)
    assert data == {
        "a": "hola mundo",
        "b": "con ' comilla",
        "c": 'tab\tsalto\ncomilla" barra\\',
        "d": True,
        "e": False,
        "f": 42,
        "g": -7,
        "h": None,
        "i": None,
        "j": "1.0",
        "k": "http://x.y/z#frag",
        "l": "valor",
        "m": "",
    }
    assert body == ""


def test_listas_en_bloque_y_en_linea() -> None:
    text = (
        "---\n"
        "tools:\n"
        "  - Read\n"
        "  - 'Bash(git:*)'\n"
        "requires:\n"
        "- core\n"
        "- sdd\n"
        "optional: []\n"
        "flow: [a, 'b c', \"d\"]\n"
        "---\n"
    )
    data, _ = parse(text, strict=True)
    assert data == {
        "tools": ["Read", "Bash(git:*)"],
        "requires": ["core", "sdd"],
        "optional": [],
        "flow": ["a", "b c", "d"],
    }


def test_bloques_literal_y_plegado() -> None:
    text = (
        "---\n"
        "keep: |\n"
        "  linea 1\n"
        "    indentada\n"
        "\n"
        "  linea 3\n"
        "strip: |-\n"
        "  sin salto final\n"
        "fold: >\n"
        "  uno\n"
        "  dos\n"
        "\n"
        "  tres\n"
        "empty: |\n"
        "after: x\n"
        "---\n"
    )
    data, _ = parse(text, strict=True)
    assert data["keep"] == "linea 1\n  indentada\n\nlinea 3\n"
    assert data["strip"] == "sin salto final"
    assert data["fold"] == "uno dos\ntres\n"
    assert data["empty"] == ""
    assert data["after"] == "x"


def test_crlf_bom_y_comentarios() -> None:
    text = "\ufeff---\r\n# comentario\r\nname: x\r\n\r\ndescription: y\r\n---\r\ncuerpo\r\n"
    data, body = parse(text, strict=True)
    assert data == {"name": "x", "description": "y"}
    assert body == "cuerpo\r\n"


def test_sin_frontmatter_en_modo_tolerante() -> None:
    assert parse("# solo cuerpo\n") == ({}, "# solo cuerpo\n")


@pytest.mark.parametrize(
    ("text", "line", "fragment"),
    [
        ("# solo cuerpo\n", 1, "falta el frontmatter"),
        ("---\nname: x\n", 1, "no se cierra"),
        ("---\nname: x\nname: y\n---\n", 3, "clave repetida"),
        ("---\nname:\tx\n---\n", 2, "tabulación"),
        ("---\n\tname: x\n---\n", 2, "tabulación"),
        ("---\nname: &ancla x\n---\n", 2, "no soportado"),
        ("---\nname: *alias\n---\n", 2, "no soportado"),
        ("---\nname: !!str x\n---\n", 2, "no soportado"),
        ("---\nname: {a: 1}\n---\n", 2, "no soportado"),
        ("---\nname: \"sin cerrar\n---\n", 2, "comilla"),
        ("---\nname: 'sin cerrar\n---\n", 2, "comilla"),
        ("---\nname: \"mal \\u00f1\"\n---\n", 2, "escape"),
        ("---\nsolo texto\n---\n", 2, "clave"),
        ("---\nmeta:\n  a:\n    b: 1\n---\n", 4, "un nivel"),
        ("---\nmeta:\n  a: |\n    x\n---\n", 3, "un nivel"),
        ("---\nlista:\n  - a\n  b: 1\n---\n", 4, "mezcla"),
        ("---\nname: x\n  suelto: 1\n---\n", 3, "indentación"),
        ("---\nfold: |+\n  x\n---\n", 2, "no soportado"),
        ("---\nflow: [a, [b]]\n---\n", 2, "no soportado"),
        ("---\nflow: [a, b\n---\n", 2, "corchete"),
    ],
)
def test_errores_estrictos_con_numero_de_linea(text: str, line: int, fragment: str) -> None:
    with pytest.raises(FrontmatterError) as exc:
        parse(text, strict=True)
    assert exc.value.line == line
    assert fragment in str(exc.value)
    assert f"línea {line}" in str(exc.value)


def test_modo_tolerante_ignora_lo_que_no_entiende() -> None:
    text = "---\nname: x\nname: y\nraro: &a b\nsolo texto\ndescription: ok\n---\ncuerpo\n"
    data, body = parse(text)
    assert data["name"] == "y"
    assert data["description"] == "ok"
    assert "raro" not in data
    assert body == "cuerpo\n"


def test_modo_tolerante_con_frontmatter_sin_cerrar() -> None:
    assert parse("---\nname: x\n") == ({}, "---\nname: x\n")


def test_casos_borde_validos() -> None:
    text = (
        "---\n"
        "vacio:\n"
        "items:\n"
        "  - 'a'\n"
        "  -\n"
        "  - # solo comentario\n"
        "meta:\n"
        "  sin_valor:\n"
        "  otro: 1\n"
        "flow: [ ] # vacia\n"
        "---\n"
    )
    data, _ = parse(text, strict=True)
    assert data == {
        "vacio": None,
        "items": ["a", None, None],
        "meta": {"sin_valor": None, "otro": 1},
        "flow": [],
    }


@pytest.mark.parametrize(
    ("text", "line", "fragment"),
    [
        ("---\nname: 'x' sobra\n---\n", 2, "después de la comilla"),
        ("---\nflow: [a] sobra\n---\n", 2, "después de ']'"),
        ("---\nflow: ['a' b]\n---\n", 2, "',' o ']'"),
        ("---\nmeta:\n  a: 1\n  a: 2\n---\n", 4, "clave repetida"),
        ("---\nmeta:\n    a: 1\n  b: 2\n---\n", 4, "inconsistente"),
        ("---\nmeta:\n  - a\n  -x\n---\n", 4, "mezcla"),
        ("---\nmeta:\n  a: 1\n  - b\n---\n", 4, "mezcla"),
        ("---\nmeta:\n  solo texto\n---\n", 3, "clave"),
        ("---\nlista:\n  - [a]\n---\n", 3, "listas anidadas"),
        ("---\nlista:\n  - a\n    - b\n---\n", 4, "un nivel"),
        ("---\nmeta:\n  a:\tb\n---\n", 3, "tabulación"),
    ],
)
def test_mas_errores_estrictos(text: str, line: int, fragment: str) -> None:
    with pytest.raises(FrontmatterError) as exc:
        parse(text, strict=True)
    assert exc.value.line == line
    assert fragment in str(exc.value)


@pytest.mark.parametrize(
    "value",
    [
        "Use when: the user asks",
        "Pasos:",
        "`codigo`",
        "@usuario",
        "%dato",
        ", coma",
        "- guion",
        "? pregunta",
        "a-b: no",
    ],
)
def test_estricto_rechaza_escalares_que_yaml_no_acepta(value: str) -> None:
    text = f"---\nname: x\ndescription: {value}\n---\n"
    with pytest.raises(FrontmatterError) as exc:
        parse(text, strict=True)
    assert exc.value.line == 3
    data, _ = parse(text)
    assert data["name"] == "x"


@pytest.mark.parametrize(
    "value",
    ["http://x.y/z", "ratio 1:2", "-flag", "texto # comentario: ok"],
)
def test_estricto_acepta_escalares_validos(value: str) -> None:
    parse(f"---\nd: {value}\n---\n", strict=True)


def test_estricto_acepta_lo_mismo_entre_comillas() -> None:
    data, _ = parse("---\ndescription: \"Use when: the user asks\"\n---\n", strict=True)
    assert data["description"] == "Use when: the user asks"
