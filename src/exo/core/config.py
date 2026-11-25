"""Config del proyecto (`<PROJECT_DIR>/config.json`, esquema 3).

Esquema en `docs/plan/02-ARQUITECTURA.md` §2.12, más `mcp.enabled` (ADR-0005).
El esquema 2 (F4) reemplaza `tracker` por `tickets {pattern, example}`
(ADR-0012) y suma `sdd {persistence, mode}` (§6.5 B y §6.6 del reporte). El
esquema 3 (F5, ADR-0014) suma `governance.gates`, `data_protection.pii` y
`review {host, publish_command}`, y saca `governance.dpa_profile`.
La lectura es tolerante: si el archivo falta, se usan los defaults sin avisar;
si un campo es inválido, vuelve a su default y queda una advertencia para
`exo doctor`. Las claves desconocidas se conservan para no perder datos del
humano. `save` valida y rechaza valores inválidos.
"""

from __future__ import annotations

import contextlib
import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import fsutil, scan, tickets

CURRENT_SCHEMA = 4
FILENAME = "config.json"

SDD_PERSISTENCE = ("filesystem", "memory", "hybrid", "none")
SDD_MODES = ("interactive", "auto")
REVIEW_HOSTS = ("github", "azure-devops", "gitlab", "other")
TIERS = ("1", "2", "3")
# D-52 (ADR-0019): tres tiers; los gates del Tier 3 son la unión de los del 3 y el 4 de la 1.0.
DEFAULT_GATES = {
    "1": [],
    "2": ["contract_check", "code_review"],
    "3": [
        "contract_check",
        "code_review",
        "security_review",
        "threat_model",
        "secure_coding_check",
    ],
}
# Los defaults del esquema 3 (cuatro tiers): la migración 3 -> 4 completa con ellos.
DEFAULT_GATES_V3 = {
    "1": [],
    "2": ["contract_check", "code_review"],
    "3": ["contract_check", "code_review", "security_review", "threat_model"],
    "4": [
        "contract_check",
        "code_review",
        "security_review",
        "threat_model",
        "secure_coding_check",
    ],
}
MEMORY_BACKENDS = ("auto", "lexical", "hybrid-sqlite", "qdrant")
EMBEDDING_PROVIDERS = ("local", "none", "static", "onnx", "ollama", "openai-compatible")
DISCOVERY_DEPTHS = ("quick", "standard", "deep")

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_GATE = re.compile(r"^[a-z][a-z0-9_]*$")
_PREFIX = re.compile(r"^[A-Z][A-Z0-9]*$")
_LANG = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")


class ConfigError(ValueError):
    """La config no se puede guardar porque tiene valores inválidos."""


@dataclass
class LoadResult:
    config: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    source: Path | None = None
    # El archivo existe pero no se pudo usar (JSON roto, esquema desconocido): todo
    # viene de los defaults. Quien escribe a partir de la config tiene que abortar.
    fallback: bool = False
    invalid: list[str] = field(default_factory=list)  # campos que volvieron a su default
    # El esquema del archivo, si se migró al leerlo: `exo update --apply` lo guarda migrado.
    migrated_from: int | None = None
    # El esquema del archivo, si lo escribió un motor más nuevo (`fallback` también es True).
    newer_schema: int | None = None


def newer_message(schema: int) -> str:
    """Una config de un esquema más nuevo no está rota: la escribió otra versión del motor."""
    return (
        f"{_meta.PROJECT_DIR}/{FILENAME} was written by a newer {_meta.NAME} (schema {schema}; "
        f"this engine understands up to {CURRENT_SCHEMA}); upgrade {_meta.NAME} and retry"
    )


def defaults() -> dict[str, Any]:
    return {
        "schema": CURRENT_SCHEMA,
        "project": {"name": None, "chat_language": None, "artifact_language": "en"},
        "agents": [],
        "packs": [],
        "tickets": {"pattern": None, "example": None},
        "specs_dir": "specs",
        "sdd": {"persistence": "filesystem", "mode": "interactive"},
        "memory": {
            "backend": "auto",
            "embeddings": {"provider": "local", "model": None, "allow_remote": False},
        },
        "governance": {
            "protected_branches": ["main", "master", "prod", "production"],
            "roles": {"tech_lead": [], "developer": []},
            "githooks": True,
            "gates": copy.deepcopy(DEFAULT_GATES),
        },
        "data_protection": {"pii": list(scan.DEFAULT_PII)},
        "review": {"host": None, "publish_command": None},
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

    def invalid_value(self, path: str, message: str, action: str = "using the default") -> None:
        self.warnings.append(f"{path}: {message}; {action}")
        self.invalid.append(f"{path}: {message}")

    def note(self, path: str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")


Validator = Callable[[Any, str, _Collector, Any], Any]


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _section(spec: dict[str, Validator]) -> Validator:
    def validate(value: Any, path: str, col: _Collector, default: Any) -> Any:
        if not isinstance(value, dict):
            col.invalid_value(path, "must be an object")
            return copy.deepcopy(default)
        out: dict[str, Any] = {}
        for key, validator in spec.items():
            if key in value:
                out[key] = validator(value[key], _join(path, key), col, default[key])
            else:
                out[key] = copy.deepcopy(default[key])
        for key, extra in value.items():
            if key not in spec:
                col.note(_join(path, key), "unknown key; kept without validation")
                out[key] = extra
        return out

    return validate


def _choice(options: tuple[str, ...]) -> Validator:
    def validate(value: Any, path: str, col: _Collector, default: Any) -> Any:
        if isinstance(value, str) and value in options:
            return value
        col.invalid_value(path, f"must be one of: {', '.join(options)}")
        return default

    return validate


def _bool(value: Any, path: str, col: _Collector, default: Any) -> Any:
    if isinstance(value, bool):
        return value
    col.invalid_value(path, "must be true or false")
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
            col.invalid_value(path, "must be a list")
            return copy.deepcopy(default)
        out: list[str] = []
        for index, item in enumerate(value):
            if isinstance(item, str) and item and (pattern is None or pattern.match(item)):
                if item not in out:
                    out.append(item)
            else:
                col.invalid_value(f"{path}[{index}]", hint, "dropped")
        return out

    return validate


def _roles(value: Any, path: str, col: _Collector, default: Any) -> Any:
    if not isinstance(value, dict):
        col.invalid_value(path, "must be an object {role: [people]}")
        return copy.deepcopy(default)
    people = _text_list(None, "must be a non-empty string")
    out: dict[str, Any] = {}
    for role, members in value.items():
        role_path = _join(path, str(role))
        if not isinstance(members, list):
            col.invalid_value(role_path, "must be a list of people", "dropped")
            continue
        out[role] = people(members, role_path, col, [])
    return out


def _specs_dir(value: Any, path: str, col: _Collector, default: Any) -> Any:
    if isinstance(value, str):
        try:
            return str(fsutil.safe_relpath(value))
        except fsutil.UnsafePathError as exc:
            col.invalid_value(path, f"unsafe path ({exc})")
            return default
    col.invalid_value(path, "must be a relative path")
    return default


def _schema(value: Any, path: str, col: _Collector, default: Any) -> Any:
    return CURRENT_SCHEMA


def _gates(value: Any, path: str, col: _Collector, default: Any) -> Any:
    """`{tier: [gate, ...]}` con los tiers 1 a 3; un tier que falta toma su default."""
    if not isinstance(value, dict):
        col.invalid_value(path, "must be an object {tier: [gates]}, with tiers 1 to 3")
        return copy.deepcopy(default)
    out = copy.deepcopy(default)
    names = _text_list(_GATE, "must be a gate name in snake_case, such as code_review")
    for tier, gates in value.items():
        if str(tier) not in TIERS:
            message = "tiers are 1, 2 and 3"
            if str(tier) == "4":
                message += (
                    " (Tier 4 merged into Tier 3 in schema 4: move these gates to \"3\" "
                    "as a list of gate names)"
                )
            col.invalid_value(_join(path, str(tier)), message, "ignored")
            continue
        out[str(tier)] = names(gates, _join(path, str(tier)), col, default[str(tier)])
    return out


def _optional_choice(options: tuple[str, ...]) -> Validator:
    def validate(value: Any, path: str, col: _Collector, default: Any) -> Any:
        if value is None or (isinstance(value, str) and value in options):
            return value
        col.invalid_value(path, f"must be one of: {', '.join(options)}, or null")
        return default

    return validate


def _tickets(value: Any, path: str, col: _Collector, default: Any) -> Any:
    """`{pattern, example}`: el ejemplo tiene que cumplir el patrón (ADR-0012)."""
    if not isinstance(value, dict):
        col.invalid_value(path, "must be an object {pattern, example}")
        return copy.deepcopy(default)
    pattern = value.get("pattern")
    if pattern is not None:
        try:
            tickets.compile_pattern(pattern)
        except tickets.TicketError as exc:
            col.invalid_value(_join(path, "pattern"), str(exc), "no ticket pattern")
            pattern = None
    example = value.get("example")
    if example is not None:
        example_path = _join(path, "example")
        if pattern is None:
            col.invalid_value(example_path, "an example needs a valid pattern", "dropped")
            example = None
        else:
            try:
                tickets.check_example(pattern, example)
            except tickets.TicketError as exc:
                col.invalid_value(example_path, str(exc), "dropped")
                example = None
    out: dict[str, Any] = {"pattern": pattern, "example": example}
    for key, extra in value.items():
        if key not in out:
            col.note(_join(path, key), "unknown key; kept without validation")
            out[key] = extra
    return out


_SLUG_HINT = "must be lowercase kebab-case (a-z, 0-9, hyphens)"
_PII = re.compile("^(?:" + "|".join(re.escape(name) for name in scan.KNOWN_PII) + ")$")
_PII_HINT = "must be a personal-data detector: " + ", ".join(scan.KNOWN_PII)

_SPEC = _section(
    {
        "schema": _schema,
        "project": _section(
            {
                "name": _text(None, "must be a non-empty string or null", optional=True),
                "chat_language": _text(
                    _LANG, "must be a language code such as es or en, or null", optional=True
                ),
                "artifact_language": _text(_LANG, "must be a language code such as es or en"),
            }
        ),
        "agents": _text_list(_SLUG, _SLUG_HINT),
        "packs": _text_list(_SLUG, _SLUG_HINT),
        "tickets": _tickets,
        "specs_dir": _specs_dir,
        "sdd": _section({"persistence": _choice(SDD_PERSISTENCE), "mode": _choice(SDD_MODES)}),
        "memory": _section(
            {
                "backend": _choice(MEMORY_BACKENDS),
                "embeddings": _section(
                    {
                        "provider": _choice(EMBEDDING_PROVIDERS),
                        "model": _text(None, "must be a string or null", optional=True),
                        "allow_remote": _bool,
                    }
                ),
            }
        ),
        "governance": _section(
            {
                "protected_branches": _text_list(None, "must be a branch name"),
                "roles": _roles,
                "githooks": _bool,
                "gates": _gates,
            }
        ),
        "data_protection": _section({"pii": _text_list(_PII, _PII_HINT)}),
        "review": _section(
            {
                "host": _optional_choice(REVIEW_HOSTS),
                "publish_command": _text(
                    None, "must be a non-empty command line or null", optional=True
                ),
            }
        ),
        "discovery": _section(
            {
                "ignore": _text_list(None, "must be a non-empty pattern"),
                "depth": _choice(DISCOVERY_DEPTHS),
            }
        ),
        "mcp": _section({"enabled": _bool}),
    }
)


# -- migraciones --------------------------------------------------------------

_JIRA_STYLE = (r"[A-Z][A-Z0-9]*-\d+", "PROJ-123")
_HASH_STYLE = (r"#\d+", "#123")


def _tickets_from_tracker(tracker: Any) -> dict[str, Any]:
    """Traduce el `tracker` de lista cerrada del esquema 1 a un patrón (ADR-0012)."""
    none = {"pattern": None, "example": None}
    if not isinstance(tracker, dict) or tracker.get("type") in (None, "none"):
        return none
    prefixes: list[str] = []
    candidates = [tracker.get("prefix")]
    if isinstance(tracker.get("prefixes"), list):
        candidates += tracker["prefixes"]
    for item in candidates:
        if isinstance(item, str) and _PREFIX.match(item) and item not in prefixes:
            prefixes.append(item)
    kind = tracker.get("type")
    if prefixes:
        body = prefixes[0] if len(prefixes) == 1 else "(?:" + "|".join(prefixes) + ")"
        return {"pattern": body + r"-\d+", "example": f"{prefixes[0]}-123"}
    if kind in ("jira", "linear"):
        return {"pattern": _JIRA_STYLE[0], "example": _JIRA_STYLE[1]}
    if kind in ("github", "gitlab"):
        return {"pattern": _HASH_STYLE[0], "example": _HASH_STYLE[1]}
    return none


def _v1_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
    out = dict(raw)
    tracker = out.pop("tracker", None)
    if "tickets" not in out:
        out["tickets"] = _tickets_from_tracker(tracker)
    out["schema"] = 2
    return out


def _v2_to_v3(raw: dict[str, Any]) -> dict[str, Any]:
    """ADR-0014: sale el perfil de organización.

    Los gates, los datos y la revisión toman su default.
    """
    out = dict(raw)
    governance = out.get("governance")
    if isinstance(governance, dict):
        out["governance"] = {k: v for k, v in governance.items() if k != "dpa_profile"}
    out["schema"] = 3
    return out


def _v3_to_v4(raw: dict[str, Any]) -> dict[str, Any]:
    """D-52 (ADR-0019): tres tiers. Los gates del Tier 4 se suman a los del Tier 3.

    Une las dos listas sin repetir, primero las del 3 y en su orden, y borra la
    clave "4". Un tier que falta toma el default del esquema 3, como lo hacía al
    leerla. Si alguna de las dos no es una lista de textos, no se toca: la validación
    lo marca.
    """
    out = dict(raw)
    governance = out.get("governance")
    gates = governance.get("gates") if isinstance(governance, dict) else None
    if isinstance(gates, dict) and ("3" in gates or "4" in gates):
        three = gates.get("3", DEFAULT_GATES_V3["3"])
        four = gates.get("4", DEFAULT_GATES_V3["4"])
        if all(isinstance(g, list) and all(isinstance(x, str) for x in g) for g in (three, four)):
            merged = {k: v for k, v in gates.items() if k != "4"}
            merged["3"] = list(dict.fromkeys([*three, *four]))
            out["governance"] = {**governance, "gates": merged}
    out["schema"] = 4
    return out


# MIGRATIONS[n] convierte un dict del esquema n al n + 1.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _v1_to_v2,
    2: _v2_to_v3,
    3: _v3_to_v4,
}


def validate(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """Devuelve `(config normalizada, advertencias, valores inválidos)`."""
    col = _Collector()
    cfg = _SPEC(raw, "", col, defaults())
    return cfg, col.warnings, col.invalid


def _migrate(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    schema = raw.get("schema")
    if schema is None:
        warnings.append("schema: field missing; assuming 1")
        schema = 1
    if isinstance(schema, bool) or not isinstance(schema, int) or schema < 1:
        return None, [*warnings, "schema: must be an integer ≥ 1; using the defaults"]
    if schema > CURRENT_SCHEMA:
        return None, [
            *warnings,
            f"schema: schema {schema} was written by a newer {_meta.NAME} (this engine "
            f"understands up to {CURRENT_SCHEMA}); using the defaults until you upgrade "
            f"{_meta.NAME}",
        ]
    original = schema
    while schema < CURRENT_SCHEMA:
        step = MIGRATIONS.get(schema)
        if step is None:
            return None, [
                *warnings,
                f"schema: no migration from schema {schema} to {schema + 1}; using the defaults",
            ]
        raw = step(raw)
        schema += 1
    if schema != original:
        warnings.append(f"schema: config migrated from schema {original} to {schema}")
    return raw, warnings


def _fallback(path: Path, problem: str) -> LoadResult:
    return LoadResult(
        defaults(), [f"{FILENAME}: {problem}; using the defaults"], path, fallback=True
    )


def load(project: Path) -> LoadResult:
    path = config_path(project)
    try:
        text = fsutil.read_bytes(path).decode("utf-8-sig")
    except FileNotFoundError:
        return LoadResult(defaults())
    except (OSError, UnicodeDecodeError) as exc:
        return _fallback(path, f"could not be read ({exc})")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return _fallback(path, f"is not valid JSON (line {exc.lineno}: {exc.msg})")
    if not isinstance(raw, dict):
        return _fallback(path, "the root must be a JSON object")
    migrated, warnings = _migrate(raw)
    if migrated is None:
        schema = raw.get("schema")
        newer = schema if isinstance(schema, int) and schema > CURRENT_SCHEMA else None
        return LoadResult(defaults(), warnings, path, fallback=True, newer_schema=newer)
    cfg, field_warnings, invalid = validate(migrated)
    original = raw.get("schema", 1)
    return LoadResult(
        cfg,
        warnings + field_warnings,
        path,
        invalid=invalid,
        migrated_from=original if original != CURRENT_SCHEMA else None,
    )


_BOM = b"\xef\xbb\xbf"
_INDENT = re.compile(r"\n([ \t]+)\S")


def _ordered(new: Any, old: Any) -> Any:
    """`new` con las claves en el orden de `old` (las nuevas, al final), en cada nivel."""
    if not (isinstance(new, dict) and isinstance(old, dict)):
        return new
    keys = [k for k in old if k in new] + [k for k in new if k not in old]
    return {k: _ordered(new[k], old.get(k)) for k in keys}


def dumps(cfg: dict[str, Any], like: bytes | None = None) -> bytes:
    """La config como JSON. Con `like` (el archivo que reemplaza), conserva lo de la persona
    (invariante 2): el fin de línea, el BOM, la sangría y el orden de sus claves."""
    indent: int | str = 2
    if like is not None:
        text = like.decode("utf-8-sig", errors="replace")
        found = _INDENT.search(text.replace("\r\n", "\n"))
        if found:
            indent = found.group(1) if "\t" in found.group(1) else len(found.group(1))
        with contextlib.suppress(json.JSONDecodeError):
            cfg = _ordered(cfg, json.loads(text))
    out = json.dumps(cfg, indent=indent, ensure_ascii=False) + "\n"
    if like is not None and b"\r\n" in like:
        out = out.replace("\n", "\r\n")
    data = out.encode("utf-8")
    return _BOM + data if like is not None and like.startswith(_BOM) else data


def current_bytes(project: Path) -> bytes | None:
    """El archivo de config tal como está, o None si falta o no se puede leer."""
    try:
        return fsutil.read_bytes(config_path(project))
    except OSError:
        return None


def save(project: Path, cfg: dict[str, Any]) -> bool:
    """Valida y escribe la config de forma atómica, con el estilo del archivo que reemplaza.
    Devuelve si escribió."""
    normalized, _, invalid = validate(cfg)
    if invalid:
        raise ConfigError("the config has invalid values: " + " | ".join(invalid))
    on_disk = _schema_on_disk(project)
    if on_disk is not None and on_disk > CURRENT_SCHEMA:
        raise ConfigError(f"{newer_message(on_disk)} (it was not overwritten)")
    data = dumps(normalized, like=current_bytes(project))
    return fsutil.write_if_changed(config_path(project), data)


def _schema_on_disk(project: Path) -> int | None:
    try:
        raw = json.loads(fsutil.read_bytes(config_path(project)).decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    schema = raw.get("schema") if isinstance(raw, dict) else None
    return schema if isinstance(schema, int) and not isinstance(schema, bool) else None
