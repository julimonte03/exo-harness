"""core/jsonschema: el subconjunto de JSON Schema que usan los esquemas del motor."""

from __future__ import annotations

import pytest

from exo.core import jsonschema
from exo.core.jsonschema import SchemaError

PERSON = {
    "type": "object",
    "required": ["name", "tags"],
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 10, "pattern": "^[a-z]+$"},
        "age": {"type": "integer", "minimum": 0},
        "nick": {"type": ["string", "null"]},
        "role": {"enum": ["dev", "lead"]},
        "tags": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "ok": {"type": "boolean"},
        "score": {"type": "number"},
    },
}


def test_valido() -> None:
    data = {"name": "ana", "age": 3, "nick": None, "role": "dev", "tags": ["x"], "ok": True, "score": 1.5}
    assert jsonschema.validate(data, PERSON) == []


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ([], "$: must be of type object"),
        ({"tags": ["x"]}, "$: missing required property 'name'"),
        ({"name": "ana", "tags": ["x"], "otro": 1}, "$: unexpected property 'otro'"),
        ({"name": "", "tags": ["x"]}, "$.name: must have at least 1 character"),
        ({"name": "abcdefghijk", "tags": ["x"]}, "$.name: must have at most 10 characters"),
        ({"name": "Ana", "tags": ["x"]}, "$.name: must match ^[a-z]+$"),
        ({"name": "ana", "tags": ["x"], "age": -1}, "$.age: must be ≥ 0"),
        ({"name": "ana", "tags": ["x"], "age": 1.5}, "$.age: must be of type integer"),
        ({"name": "ana", "tags": ["x"], "age": True}, "$.age: must be of type integer"),
        ({"name": "ana", "tags": ["x"], "nick": 3}, "$.nick: must be of type string or null"),
        ({"name": "ana", "tags": ["x"], "role": "boss"}, "$.role: must be one of: dev, lead"),
        ({"name": "ana", "tags": []}, "$.tags: must have at least 1 item"),
        ({"name": "ana", "tags": ["x", 2]}, "$.tags[1]: must be of type string"),
        ({"name": "ana", "tags": ["x"], "ok": 1}, "$.ok: must be of type boolean"),
        ({"name": "ana", "tags": ["x"], "score": "1"}, "$.score: must be of type number"),
    ],
)
def test_errores_con_ruta(data: object, error: str) -> None:
    assert error in jsonschema.validate(data, PERSON)


def test_junta_todos_los_errores() -> None:
    errors = jsonschema.validate({"name": 1, "tags": "x", "otro": 0}, PERSON)
    assert len(errors) == 3


def test_additional_properties_con_esquema() -> None:
    schema = {"type": "object", "additionalProperties": {"type": "integer"}}
    assert jsonschema.validate({"a": 1}, schema) == []
    assert jsonschema.validate({"a": "x"}, schema) == ["$.a: must be of type integer"]


def test_anotaciones_permitidas() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "x",
        "title": "t",
        "description": "d",
        "examples": [],
        "type": "string",
    }
    assert jsonschema.validate("a", schema) == []


@pytest.mark.parametrize("schema", [{"oneOf": []}, {"type": "object", "properties": {"a": {"format": "x"}}}])
def test_palabra_clave_no_soportada(schema: dict) -> None:
    """Un esquema con algo que el validador no entiende falla, no se ignora en silencio."""
    with pytest.raises(SchemaError, match="unsupported"):
        jsonschema.check_schema(schema)


def test_tipo_desconocido() -> None:
    with pytest.raises(SchemaError, match="unknown type"):
        jsonschema.check_schema({"type": "fecha"})
