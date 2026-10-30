"""Config del proyecto (`<PROJECT_DIR>/config.json`, esquema 1).

Esquema en `docs/plan/02-ARQUITECTURA.md` §2.12, más `mcp.enabled` (ADR-0005).
La lectura es tolerante: si el archivo falta, se usan los defaults sin avisar;
si un campo es inválido, vuelve a su default y queda una advertencia para
`exo doctor`. Las claves desconocidas se conservan para no perder datos del
humano. `save` valida y rechaza valores inválidos.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import fsutil

CURRENT_SCHEMA = 1
# MIGRATIONS[n] convierte un dict del esquema n al n + 1.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}
FILENAME = "config.json"

TRACKERS = ("jira", "github", "gitlab", "linear", "none")
MEMORY_BACKENDS = ("auto", "lexical", "hybrid-sqlite", "qdrant")
EMBEDDING_PROVIDERS = ("local", "none", "static", "onnx", "ollama", "openai-compatible")
DISCOVERY_DEPTHS = ("quick", "standard", "deep")

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PREFIX = re.compile(r"^[A-Z][A-Z0-9]*$")
_LANG = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")


class ConfigError(ValueError):
    """La config no se puede guardar porque tiene valores inválidos."""


@dataclass
class LoadResult:
    config: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    source: Path | None = None


def defaults() -> dict[str, Any]:
    return {
        "schema": CURRENT_SCHEMA,
        "project": {"name": None, "chat_language": "es", "artifact_language": "en"},
        "agents": [],
        "packs": [],
        "tracker": {"type": "none", "prefix": None, "prefixes": []},
        "specs_dir": "specs",
        "memory": {
            "backend": "auto",
            "embeddings": {"provider": "local", "model": None, "allow_remote": False},
        },
        "governance": {
            "protected_branches": ["main", "master", "prod", "production"],
            "roles": {"tech_lead": [], "developer": []},
            "dpa_profile": "legacy-profile",
            "githooks": True,
        },
        "discovery": {"ignore": [], "depth": "standard"},
        "mcp": {"enabled": False},
    }


def config_path(project: Path) -> Path:
    return Path(project) / _meta.PROJECT_DIR / FILENAME


# -- validación -------------------------------------------------------------


class _Collector:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.invalid: list[str] = []

    def invalid_value(self, path: str, message: str, action: str = "se usa el default") -> None:
        text = f"{path}: {message}; {action}"
        self.warnings.append(text)
        self.invalid.append(text)

    def note(self, path: str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")


Validator = Callable[[Any, str, _Collector, Any], Any]


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _section(spec: dict[str, Validator]) -> Validator:
    def validate(value: Any, path: str, col: _Collector, default: Any) -> Any:
        if not isinstance(value, dict):
            col.invalid_value(path, "tiene que ser un objeto")
            return copy.deepcopy(default)
        out: dict[str, Any] = {}
        for key, validator in spec.items():
            if key in value:
                out[key] = validator(value[key], _join(path, key), col, default[key])
            else:
                out[key] = copy.deepcopy(default[key])
        for key, extra in value.items():
            if key not in spec:
                col.note(_join(path, key), "clave desconocida; se conserva sin validar")
                out[key] = extra
        return out

    return validate


def _choice(options: tuple[str, ...]) -> Validator:
    def validate(value: Any, path: str, col: _Collector, default: Any) -> Any:
        if isinstance(value, str) and value in options:
            return value
        col.invalid_value(path, f"tiene que ser uno de: {', '.join(options)}")
        return default

    return validate


def _bool(value: Any, path: str, col: _Collector, default: Any) -> Any:
    if isinstance(value, bool):
        return value
    col.invalid_value(path, "tiene que ser true o false")
    return default


def _text(pattern: re.Pattern[str] | None, hint: str, *, optional: bool = False) -> Validator:
    def validate(value: Any, path: str, col: _Collector, default: Any) -> Any:
        if value is None and optional:
            return None
        if isinstance(value, str) and value and (pattern is None or pattern.match(value)):
            return value
        col.invalid_value(path, hint)
        return default

    return validate


def _text_list(pattern: re.Pattern[str] | None, hint: str) -> Validator:
    def validate(value: Any, path: str, col: _Collector, default: Any) -> Any:
        if not isinstance(value, list):
            col.invalid_value(path, "tiene que ser una lista")
            return copy.deepcopy(default)
        out: list[str] = []
        for index, item in enumerate(value):
            if isinstance(item, str) and item and (pattern is None or pattern.match(item)):
                if item not in out:
                    out.append(item)
            else:
                col.invalid_value(f"{path}[{index}]", hint, "se descarta")
        return out

    return validate


def _roles(value: Any, path: str, col: _Collector, default: Any) -> Any:
    if not isinstance(value, dict):
        col.invalid_value(path, "tiene que ser un objeto {rol: [personas]}")
        return copy.deepcopy(default)
    people = _text_list(None, "tiene que ser un texto no vacío")
    out: dict[str, Any] = {}
    for role, members in value.items():
        role_path = _join(path, str(role))
        if not isinstance(members, list):
            col.invalid_value(role_path, "tiene que ser una lista de personas", "se descarta")
            continue
        out[role] = people(members, role_path, col, [])
    return out


def _specs_dir(value: Any, path: str, col: _Collector, default: Any) -> Any:
    if isinstance(value, str):
        try:
            return str(fsutil.safe_relpath(value))
        except fsutil.UnsafePathError as exc:
            col.invalid_value(path, f"ruta insegura ({exc})")
            return default
    col.invalid_value(path, "tiene que ser una ruta relativa")
    return default


def _schema(value: Any, path: str, col: _Collector, default: Any) -> Any:
    return CURRENT_SCHEMA


_SLUG_HINT = "tiene que ser kebab-case en minúsculas (a-z, 0-9, guiones)"
_PREFIX_HINT = "tiene que cumplir ^[A-Z][A-Z0-9]*$ (por ejemplo PROJ)"

_SPEC = _section(
    {
        "schema": _schema,
        "project": _section(
            {
                "name": _text(None, "tiene que ser un texto no vacío o null", optional=True),
                "chat_language": _text(_LANG, "tiene que ser un código de idioma como es o en"),
                "artifact_language": _text(_LANG, "tiene que ser un código de idioma como es o en"),
            }
        ),
        "agents": _text_list(_SLUG, _SLUG_HINT),
        "packs": _text_list(_SLUG, _SLUG_HINT),
        "tracker": _section(
            {
                "type": _choice(TRACKERS),
                "prefix": _text(_PREFIX, _PREFIX_HINT, optional=True),
                "prefixes": _text_list(_PREFIX, _PREFIX_HINT),
            }
        ),
        "specs_dir": _specs_dir,
        "memory": _section(
            {
                "backend": _choice(MEMORY_BACKENDS),
                "embeddings": _section(
                    {
                        "provider": _choice(EMBEDDING_PROVIDERS),
                        "model": _text(None, "tiene que ser un texto o null", optional=True),
                        "allow_remote": _bool,
                    }
                ),
            }
        ),
        "governance": _section(
            {
                "protected_branches": _text_list(None, "tiene que ser un nombre de rama"),
                "roles": _roles,
                "dpa_profile": _text(_SLUG, _SLUG_HINT),
                "githooks": _bool,
            }
        ),
        "discovery": _section(
            {
                "ignore": _text_list(None, "tiene que ser un patrón no vacío"),
                "depth": _choice(DISCOVERY_DEPTHS),
            }
        ),
        "mcp": _section({"enabled": _bool}),
    }
)


def validate(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """Devuelve `(config normalizada, advertencias, valores inválidos)`."""
    col = _Collector()
    cfg = _SPEC(raw, "", col, defaults())
    return cfg, col.warnings, col.invalid


def _migrate(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    schema = raw.get("schema")
    if schema is None:
        warnings.append("schema: falta el campo; se asume 1")
        schema = 1
    if isinstance(schema, bool) or not isinstance(schema, int) or schema < 1:
        return None, [*warnings, "schema: tiene que ser un entero ≥ 1; se usan los defaults"]
    if schema > CURRENT_SCHEMA:
        return None, [
            *warnings,
            f"schema: esquema {schema} desconocido (este motor entiende hasta el "
            f"{CURRENT_SCHEMA}); se usan los defaults. Actualizá {_meta.NAME}.",
        ]
    original = schema
    while schema < CURRENT_SCHEMA:
        step = MIGRATIONS.get(schema)
        if step is None:
            return None, [
                *warnings,
                f"schema: no hay migración del esquema {schema} al {schema + 1}; "
                "se usan los defaults",
            ]
        raw = step(raw)
        schema += 1
    if schema != original:
        warnings.append(f"schema: config migrada del esquema {original} al {schema}")
    return raw, warnings


def _fallback(path: Path, problem: str) -> LoadResult:
    return LoadResult(defaults(), [f"{FILENAME}: {problem}; se usan los defaults"], path)


def load(project: Path) -> LoadResult:
    path = config_path(project)
    try:
        text = fsutil.read_bytes(path).decode("utf-8-sig")
    except FileNotFoundError:
        return LoadResult(defaults())
    except (OSError, UnicodeDecodeError) as exc:
        return _fallback(path, f"no se pudo leer ({exc})")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return _fallback(path, f"no es JSON válido (línea {exc.lineno}: {exc.msg})")
    if not isinstance(raw, dict):
        return _fallback(path, "la raíz tiene que ser un objeto JSON")
    migrated, warnings = _migrate(raw)
    if migrated is None:
        return LoadResult(defaults(), warnings, path)
    cfg, field_warnings, _ = validate(migrated)
    return LoadResult(cfg, warnings + field_warnings, path)


def dumps(cfg: dict[str, Any]) -> bytes:
    return (json.dumps(cfg, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def save(project: Path, cfg: dict[str, Any]) -> bool:
    """Valida y escribe la config de forma atómica. Devuelve si escribió."""
    normalized, _, invalid = validate(cfg)
    if invalid:
        raise ConfigError("la config tiene valores inválidos: " + " | ".join(invalid))
    return fsutil.write_if_changed(config_path(project), dumps(normalized))
