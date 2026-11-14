"""Estado de los changes SDD, solo lectura.

Port de §5.4 del reporte: recorre `<specs_dir>` (de la config del proyecto),
detecta épicas, changes y `archive/`, deriva la fase por los artefactos
presentes, lee `ai-usage-record.json` y `followups.json`, aplica los descartes
(`dismissed_followups`) y proyecta `ticket_key` (antes `jira_key`) y
`attribution_schema_version` aunque sean null. Nunca escribe.

Layout: `<specs_dir>/[<épica>/]<change>/` y
`<specs_dir>/archive/[<épica>/]YYYY-MM-DD-<change>/`. `capabilities/` (specs
vivas, F4) y las carpetas que empiezan con `.` o `_` no son changes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exo.core import config, fsutil

ARCHIVE = "archive"
CAPABILITIES = "capabilities"
AI_USAGE_RECORD = "ai-usage-record.json"
FOLLOWUPS = "followups.json"
# Artefacto que marca cada fase, en orden; gana el último presente.
PHASES = (
    ("fitness-assessment.json", "risk"),
    ("exploration.md", "explore"),
    ("proposal.md", "propose"),
    ("spec.md", "spec"),
    ("design.md", "design"),
    ("tasks.md", "tasks"),
    ("verify-record.md", "verify"),
)
ARTIFACT_ORDER = (
    "fitness-assessment.json",
    "exploration.md",
    "proposal.md",
    "spec.md",
    "design.md",
    "canvas.md",
    "tasks.md",
    "test-spec.md",
    "verify-record.md",
    AI_USAGE_RECORD,
    FOLLOWUPS,
)
FOLLOWUP_STATUSES = ("open", "dismissed", "all")
_EPIC = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
_ARCHIVED = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
_CHECKED = re.compile(r"^\s*[-*+]\s+\[[xX]\]", re.MULTILINE)


class ObservabilityError(ValueError):
    """Change inexistente o ambiguo, o filtro inválido."""


@dataclass(frozen=True)
class Change:
    name: str
    epic: str | None
    path: str  # relativa al proyecto, con /
    archived: bool
    archived_on: str | None
    phase: str
    artifacts: tuple[str, ...]


def specs_root(project: Path) -> Path:
    return Path(project) / config.load(project).config["specs_dir"]


def _phase(folder: Path, archived: bool) -> str:
    if archived:
        return "archived"
    phase = "new"
    for artifact, name in PHASES:
        if (folder / artifact).is_file():
            phase = name
    tasks = (
        (folder / "tasks.md").read_text(encoding="utf-8", errors="replace")
        if phase == "tasks"
        else ""
    )
    if phase == "tasks" and _CHECKED.search(tasks):
        return "apply"
    return phase


def _change(project: Path, folder: Path, epic: str | None, archived: bool) -> Change:
    name, archived_on = folder.name, None
    if archived:
        match = _ARCHIVED.match(folder.name)
        if match:
            archived_on, name = match.groups()
    artifacts = tuple(a for a in ARTIFACT_ORDER if (folder / a).is_file())
    path = folder.relative_to(project).as_posix()
    return Change(name, epic, path, archived, archived_on, _phase(folder, archived), artifacts)


def _children(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return [p for p in sorted(folder.iterdir()) if p.is_dir() and p.name[0] not in "._"]


def _walk(project: Path, root: Path, archived: bool) -> list[Change]:
    found: list[Change] = []
    for entry in _children(root):
        if not archived and entry.name in (ARCHIVE, CAPABILITIES):
            continue
        if _EPIC.match(entry.name):
            found.extend(
                _change(project, child, entry.name, archived) for child in _children(entry)
            )
        else:
            found.append(_change(project, entry, None, archived))
    return found


def find_changes(project: Path, *, include_archived: bool = True) -> list[Change]:
    project = Path(project)
    root = specs_root(project)
    # Solo lectura dentro del proyecto: un specs/ que sale por un link no se recorre.
    if root.exists() and not root.resolve().is_relative_to(project.resolve()):
        return []
    changes = _walk(project, root, archived=False)
    if include_archived:
        changes += _walk(project, root / ARCHIVE, archived=True)
    return sorted(changes, key=lambda c: (c.archived, c.path))


def get_change(project: Path, name: str) -> Change:
    matches = [c for c in find_changes(project) if c.name == name]
    active = [c for c in matches if not c.archived]
    pool = active or matches
    if not pool:
        raise ObservabilityError(f"change {name!r} does not exist")
    if len(pool) > 1:
        paths = ", ".join(c.path for c in pool)
        raise ObservabilityError(f"name {name!r} is ambiguous: {paths}")
    return pool[0]


# -- AI Usage Record y followups ----------------------------------------------


def _read_json(path: Path, warnings: list[str]) -> Any:
    try:
        return json.loads(fsutil.read_bytes(path).decode("utf-8"))
    except FileNotFoundError:
        return None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        warnings.append(f"{path.name} is unreadable ({exc}); ignored")
        return None


def _record(project: Path, change: Change, warnings: list[str]) -> dict[str, Any] | None:
    raw = _read_json(Path(project) / change.path / AI_USAGE_RECORD, warnings)
    if raw is not None and not isinstance(raw, dict):
        warnings.append(f"{AI_USAGE_RECORD} is unreadable (the root is not an object); ignored")
        return None
    return raw


def _projection(record: dict[str, Any] | None) -> dict[str, Any]:
    record = record or {}
    return {
        "ticket_key": record.get("ticket_key", record.get("jira_key")),
        "attribution_schema_version": record.get("attribution_schema_version"),
    }


def _dismissal(item: dict[str, Any], dismissed: list[dict[str, Any]]) -> str | None:
    for entry in dismissed:
        same_id = entry.get("id") is not None and entry.get("id") == item.get("id")
        same_rule = (entry.get("judge"), entry.get("rule")) == (item.get("judge"), item.get("rule"))
        if same_id or (entry.get("judge") is not None and same_rule):
            return str(entry.get("reason", entry.get("motivo", "")))
    return None


def _followups(project: Path, change: Change, warnings: list[str]) -> list[dict[str, Any]]:
    raw = _read_json(Path(project) / change.path / FOLLOWUPS, warnings)
    items = raw.get("followups", []) if isinstance(raw, dict) else raw
    if items is not None and not isinstance(items, list):
        warnings.append(f"{FOLLOWUPS} is unreadable (followups is not a list); ignored")
        items = []
    record = _record(project, change, [])
    raw_dismissed = (record or {}).get("dismissed_followups", [])
    if not isinstance(raw_dismissed, list):
        warnings.append("dismissed_followups is not a list; ignored")
        raw_dismissed = []
    dismissed = [d for d in raw_dismissed if isinstance(d, dict)]
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        reason = _dismissal(item, dismissed)
        state = "open" if reason is None else "dismissed"
        result.append({**item, "status": state, "dismissal": reason})
    return result


def followups(project: Path, name: str, status: str = "open") -> list[dict[str, Any]]:
    if status not in FOLLOWUP_STATUSES:
        options = ", ".join(FOLLOWUP_STATUSES)
        raise ObservabilityError(f"invalid status: {status!r} (one of {options})")
    items = _followups(project, get_change(project, name), [])
    return items if status == "all" else [f for f in items if f["status"] == status]


def ai_usage_record(project: Path, name: str) -> dict[str, Any]:
    warnings: list[str] = []
    record = _record(project, get_change(project, name), warnings)
    return {"record": record, **_projection(record), "warnings": warnings}


def change_state(project: Path, name: str) -> dict[str, Any]:
    change = get_change(project, name)
    warnings: list[str] = []
    record = _record(project, change, warnings)
    items = _followups(project, change, warnings)
    return {
        "name": change.name,
        "epic": change.epic,
        "path": change.path,
        "archived": change.archived,
        "archived_on": change.archived_on,
        "phase": change.phase,
        "artifacts": list(change.artifacts),
        **_projection(record),
        "followups": {
            "open": sum(f["status"] == "open" for f in items),
            "dismissed": sum(f["status"] == "dismissed" for f in items),
        },
        "warnings": warnings,
    }
