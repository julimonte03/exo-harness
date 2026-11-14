"""Escrituras sobre un change SDD: crearlo, actualizar su AI Usage Record y registrar su tier.

`observability` solo lee; lo que escribe vive acá y siempre de forma atómica:

- `new_change` (`exo change new`): valida el nombre con el patrón de tickets del
  proyecto (ADR-0012, D-26), crea el change-root y su AI Usage Record inicial.
- `update_record` (`exo change record`): agrega entradas sin duplicarlas o fija
  un campo, y valida el resultado contra el esquema antes de escribir (§7.7:
  escritura atómica e idempotente).
- `record_assessment` (`exo fitness classify --change`): guarda la clasificación
  en `fitness-assessment.json`. Un upgrade es automático; un downgrade exige la
  confirmación literal de la persona (§6.3), que queda en el historial.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import config, fsutil, tickets
from exo.sdd import fitness, observability, record

ASSESSMENT = observability.ASSESSMENT
ASSESSMENT_SCHEMA = 1
LIST_FIELDS = (
    "skills_used",
    "knowledge_used",
    "capabilities_used",
    "judges_invoked",
    "decisions",
    "dismissed_followups",
    "gates",
)
SET_FIELDS = ("purpose",)
PHASES = (
    "risk",
    "new",
    "explore",
    "propose",
    "spec",
    "design",
    "tasks",
    "apply",
    "verify",
    "judgment",
    "archive",
)


class ChangeError(ValueError):
    """No se puede crear o actualizar el change; no se escribió nada."""


@dataclass(frozen=True)
class NewChange:
    name: str
    path: str  # relativa al proyecto, con /
    epic: str | None  # carpeta de la épica
    ticket: str | None  # ID exacto
    record: str


@dataclass(frozen=True)
class RecordUpdate:
    changed: bool
    path: str
    record: dict[str, Any]


@dataclass(frozen=True)
class Assessment:
    tier: int
    previous: int | None
    comparison: str  # initial | same | upgrade | downgrade
    written: bool
    path: str
    decision: fitness.FitnessDecision


def _stamp(now: datetime | None) -> str:
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _config(project: Path) -> dict[str, Any]:
    loaded = config.load(project)
    if loaded.fallback:
        raise ChangeError(
            "the project config cannot be used (" + "; ".join(loaded.warnings) + "); fix it first"
        )
    return loaded.config


def _get(project: Path, name: str) -> observability.Change:
    try:
        return observability.get_change(project, name)
    except observability.ObservabilityError as exc:
        raise ChangeError(str(exc)) from exc


def _within(project: Path, rel: str) -> Path:
    """La ruta dentro del proyecto, sin pasar por links: el motor no escribe a través de ellos."""
    try:
        return fsutil.join_within(project, rel)
    except fsutil.UnsafePathError as exc:
        raise ChangeError(str(exc)) from exc


# -- exo change new -------------------------------------------------------------------


def new_change(
    project: Path,
    slug: str,
    *,
    ticket: str | None = None,
    epic: str | None = None,
    purpose: str | None = None,
    now: datetime | None = None,
) -> NewChange:
    project = Path(project)
    cfg = _config(project)
    pattern, example = cfg["tickets"]["pattern"], cfg["tickets"]["example"]
    try:
        name = tickets.change_name(slug, ticket, pattern=pattern, example=example)
        epic_dir = (
            tickets.epic_folder(epic, pattern=pattern, example=example)
            if epic is not None
            else None
        )
    except tickets.TicketError as exc:
        raise ChangeError(str(exc)) from exc
    clash = [
        c for c in observability.find_changes(project, include_archived=False) if c.name == name
    ]
    if clash:
        raise ChangeError(
            f"a change named {name} already exists at {clash[0].path}; change names are unique "
            "across epics, choose another slug"
        )
    specs_dir = cfg["specs_dir"]
    if epic_dir is not None:
        epic_path = project / specs_dir / epic_dir
        if any((epic_path / a).is_file() for a in observability.ARTIFACT_ORDER):
            raise ChangeError(
                f"{specs_dir}/{epic_dir} is a change, not an epic folder; use another epic ID"
            )
    rel = f"{specs_dir}/{epic_dir}/{name}" if epic_dir else f"{specs_dir}/{name}"
    try:
        root = fsutil.join_within(project, rel)
    except fsutil.UnsafePathError as exc:
        raise ChangeError(str(exc)) from exc
    if root.exists():
        raise ChangeError(f"{rel} already exists; choose another slug")
    data: dict[str, Any] = {
        "attribution_schema_version": record.ATTRIBUTION_SCHEMA_VERSION,
        "change_name": name,
        "ticket_key": ticket,
        "epic_key": epic,
    }
    if purpose:
        data["purpose"] = purpose
    data["capabilities_used"] = [
        {"name": f"{_meta.NAME} change new", "type": "command", "activation": "requested"}
    ]
    data["updated_at"] = _stamp(now)
    errors = record.validate(data)
    if errors:
        raise ChangeError("the initial record does not match its schema: " + "; ".join(errors))
    fsutil.write_atomic(root / record.FILENAME, _dump(data))
    return NewChange(name, rel, epic_dir, ticket, f"{rel}/{record.FILENAME}")


# -- exo change record ----------------------------------------------------------------


def _present(field: str, items: list[Any], value: Any) -> bool:
    if field == "capabilities_used" and isinstance(value, dict):
        key = (value.get("name"), value.get("type"))
        return any(isinstance(i, dict) and (i.get("name"), i.get("type")) == key for i in items)
    return value in items


def update_record(
    project: Path,
    change: str,
    *,
    add: Iterable[tuple[str, Any]] = (),
    set_: Iterable[tuple[str, Any]] = (),
    phase_done: str | None = None,
    now: datetime | None = None,
) -> RecordUpdate:
    project = Path(project)
    found = _get(project, change)
    rel = f"{found.path}/{record.FILENAME}"
    path = _within(project, rel)
    if phase_done is not None and phase_done not in PHASES:
        raise ChangeError(f"{phase_done!r} is not a phase (one of: {', '.join(PHASES)})")
    try:
        data = json.loads(fsutil.read_bytes(path).decode("utf-8"))
    except FileNotFoundError as exc:
        raise ChangeError(
            f"{found.path} has no {record.FILENAME}; changes get one from `{_meta.NAME} change new`"
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ChangeError(f"{rel} is not valid JSON ({exc}); fix it by hand first") from exc
    if not isinstance(data, dict):
        raise ChangeError(f"{rel}: the root must be a JSON object")
    before = copy.deepcopy(data)
    for field, value in add:
        if field not in LIST_FIELDS:
            raise ChangeError(f"{field} is not a list field (one of: {', '.join(LIST_FIELDS)})")
        items = data.setdefault(field, [])
        if not isinstance(items, list):
            raise ChangeError(f"{field} in {rel} is not a list; fix it by hand first")
        if not _present(field, items, value):
            items.append(value)
    for field, value in set_:
        if field not in SET_FIELDS:
            raise ChangeError(
                f"{field} cannot be set (only: {', '.join(SET_FIELDS)}); list fields take --add"
            )
        data[field] = value
    stamp = _stamp(now)
    if phase_done is not None:
        log = data.setdefault("phases_done", [])
        if not isinstance(log, list):
            raise ChangeError(f"phases_done in {rel} is not a list; fix it by hand first")
        last = log[-1] if log and isinstance(log[-1], dict) else {}
        if last.get("phase") != phase_done:
            log.append({"phase": phase_done, "at": stamp})
    if data == before:
        return RecordUpdate(False, rel, data)
    data["updated_at"] = stamp
    errors = record.validate(data)
    if errors:
        raise ChangeError(
            "the record would not match its schema, nothing was written: " + "; ".join(errors)
        )
    fsutil.write_atomic(path, _dump(data))
    return RecordUpdate(True, rel, data)


# -- fitness-assessment.json ----------------------------------------------------------------


def _read_assessment(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(fsutil.read_bytes(path).decode("utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def read_tier(folder: Path) -> int | None:
    """El tier registrado, o None si falta o no se puede leer."""
    tier, source = observability.tier_of(folder)
    return tier if source == "assessment" else None


def effective_tier(folder: Path) -> int:
    """Tier desconocido o ilegible es Tier 4 (§6.3)."""
    tier = read_tier(folder)
    return fitness.FAILSAFE_TIER if tier is None else tier


def record_assessment(
    project: Path,
    change: str,
    evidence: Any,
    *,
    confirm_downgrade: str | None = None,
    now: datetime | None = None,
) -> Assessment:
    project = Path(project)
    found = _get(project, change)
    rel = f"{found.path}/{ASSESSMENT}"
    path = _within(project, rel)
    folder = path.parent
    _, problems = fitness.parse_evidence(evidence)
    malformed = [p for p in problems if not p.startswith("missing ")]
    if malformed:
        raise ChangeError(
            "the evidence is malformed (" + "; ".join(malformed) + "), so nothing was recorded: "
            "fix it and run again. A missing dimension is fine: it gives Tier 4 (FM-00)"
        )
    decision = fitness.classify(evidence)
    exists = path.exists()
    previous = read_tier(folder) if exists else None
    old = _read_assessment(path) if exists else None
    if not exists:
        comparison = "initial"
    else:
        current = fitness.FAILSAFE_TIER if previous is None else previous
        comparison = fitness.compare_tiers(current, decision.tier)
        if comparison == "downgrade" and not (confirm_downgrade or "").strip():
            raise ChangeError(
                f"Tier {current} -> Tier {decision.tier} is a downgrade. Only the orchestrator "
                "decides it, with the person's literal confirmation: run again with "
                '--confirm-downgrade "<their exact words>"'
            )
    payload = decision.to_dict()
    unchanged = old is not None and {k: old.get(k) for k in payload} == json.loads(
        json.dumps(payload)
    )
    if comparison == "same" and unchanged:
        return Assessment(decision.tier, previous, comparison, False, rel, decision)
    stamp = _stamp(now)
    history = old.get("history") if old else None
    entry: dict[str, Any] = {
        "tier": decision.tier,
        "rule": decision.rule,
        "at": stamp,
        "change": comparison,
    }
    if comparison == "downgrade":
        entry["confirmation"] = confirm_downgrade
    data = {
        "schema": ASSESSMENT_SCHEMA,
        **payload,
        "assessed_at": stamp,
        "history": [*(history if isinstance(history, list) else []), entry],
    }
    fsutil.write_atomic(path, _dump(data))
    return Assessment(decision.tier, previous, comparison, True, rel, decision)
