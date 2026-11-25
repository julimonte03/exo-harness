"""Estado de los changes SDD, solo lectura.

Port de §5.4 del reporte: recorre `<specs_dir>` (de la config del proyecto),
detecta épicas, changes y `archive/`, deriva la fase por los artefactos
presentes, lee `ai-usage-record.json` y `followups.json`, aplica los descartes
(`dismissed_followups`) y proyecta `ticket_key` (antes `jira_key`) y
`attribution_schema_version` aunque sean null. Nunca escribe.

Layout: `<specs_dir>/[<épica>/]<change>/` y
`<specs_dir>/archive/[<épica>/]YYYY-MM-DD-<change>/`. `capabilities/` (specs
vivas, F4) y las carpetas que empiezan con `.` o `_` no son changes.

Las épicas se reconocen por estructura y no por el formato de su nombre, porque
el patrón de los tickets es de cada proyecto (ADR-0012): una carpeta sin
artefactos de change que contiene subcarpetas es una épica.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exo.core import config, fsutil
from exo.sdd import fitness

ARCHIVE = "archive"
CAPABILITIES = "capabilities"
AI_USAGE_RECORD = "ai-usage-record.json"
ASSESSMENT = "fitness-assessment.json"
FAILSAFE_TIER = fitness.FAILSAFE_TIER
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
FOLLOWUP_STATUSES = ("open", "fixed", "dismissed", "all")
_ARCHIVED = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
_CHECKED = re.compile(r"^\s*[-*+]\s+\[[xX]\]", re.MULTILINE)
_UNCHECKED = re.compile(r"^\s*[-*+]\s+\[ \]", re.MULTILINE)


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


def _has_artifacts(folder: Path) -> bool:
    return any((folder / artifact).is_file() for artifact in ARTIFACT_ORDER)


def _is_epic(folder: Path) -> bool:
    return not _has_artifacts(folder) and bool(_children(folder))


def _walk(project: Path, root: Path, archived: bool) -> list[Change]:
    found: list[Change] = []
    for entry in _children(root):
        if not archived and entry.name in (ARCHIVE, CAPABILITIES):
            continue
        if _is_epic(entry):
            found.extend(
                _change(project, child, entry.name, archived)
                for child in _children(entry)
                if _has_artifacts(child)
            )
        elif _has_artifacts(entry):
            # Sin artefactos ni subcarpetas no es un change: por ejemplo, la carpeta de una
            # épica que quedó vacía al archivar su último change.
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
    """Un descarte con `id` vale solo para ese hallazgo; sin `id`, para su juez y su regla."""
    for entry in dismissed:
        if entry.get("id") is not None:
            matches = entry.get("id") == item.get("id")
        else:
            same_rule = (entry.get("judge"), entry.get("rule")) == (
                item.get("judge"),
                item.get("rule"),
            )
            matches = entry.get("judge") is not None and same_rule
        if matches:
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
        if reason is not None:
            state = "dismissed"
        else:
            state = "fixed" if item.get("fixed") is True else "open"
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


def tier_of(folder: Path) -> tuple[int, str]:
    """`(tier, origen)`: el de `fitness-assessment.json`, o 3 si falta o no se lee (§6.3).

    Un 4 escrito por la 1.0 se lee como 3 (D-52), sin reescribir el archivo.
    """
    path = Path(folder) / ASSESSMENT
    if not path.exists():
        return FAILSAFE_TIER, "missing"
    data = _read_json(path, [])
    tier = data.get("tier") if isinstance(data, dict) else None
    schema = data.get("schema", 1) if isinstance(data, dict) else None
    legacy = fitness.legacy_tier(tier) if schema == 1 and schema is not True else None
    if legacy is not None:
        return legacy, "assessment"
    if isinstance(tier, bool) or not isinstance(tier, int) or tier not in fitness.TIERS:
        return FAILSAFE_TIER, "unreadable"
    return tier, "assessment"


UNKNOWN_AREA = "the area is unknown"


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def next_phase(
    project: Path, change: Change, tier: int, source: str, record: dict[str, Any] | None
) -> tuple[str, str]:
    """`(fase siguiente, motivo)`, con las reglas del contrato de estado, sin adivinar."""
    if change.archived:
        return "none", "the change is archived"
    if source != "assessment":
        detail = "is unreadable" if source == "unreadable" else "is missing"
        return "risk", f"fitness-assessment.json {detail}: classify the risk first"
    folder = Path(project) / change.path
    has = set(change.artifacts)
    raw = (record or {}).get("phases_done")
    done = [p.get("phase") for p in raw if isinstance(p, dict)] if isinstance(raw, list) else []
    judges = (record or {}).get("judges_invoked")
    judges = judges if isinstance(judges, list) else []
    if "proposal.md" not in has:
        return "new", "there is no proposal.md"
    if tier >= 3:
        unknown = UNKNOWN_AREA in _text(folder / "proposal.md").casefold()
        if unknown and "exploration.md" not in has:
            return "explore", "the proposal says the area is unknown and there is no exploration.md"
        if "propose" not in done:
            return "propose", "the proposal is not refined yet (no propose in phases_done)"
    if tier >= 2 and "spec.md" not in has:
        return "spec", f"Tier {tier} needs spec.md"
    if tier == 2 and "test-spec.md" not in has:
        return "spec", "Tier 2 needs test-spec.md, written in the spec phase"
    if tier >= 3 and "design.md" not in has:
        return "design", f"Tier {tier} needs design.md"
    if tier >= 3 and ("tasks.md" not in has or "test-spec.md" not in has):
        return "tasks", f"Tier {tier} needs tasks.md and test-spec.md"
    result = None
    if "verify-record.md" in has:
        # Diferido: `sync` y `update` usan este módulo sin cargar speclint (F8R1-16).
        from exo.sdd import speclint

        result = speclint.verdict(_text(folder / "verify-record.md"))
    if result == "needs-rework":
        if (done[-1] if done else None) != "apply":
            return "apply", "the verify said needs-rework: fix what Issues Found lists"
        return "verify", "the rework is applied: verify again"
    if tier >= 3 and _UNCHECKED.search(_text(folder / "tasks.md")):
        return "apply", "tasks.md has unchecked tasks"
    if tier <= 2 and "apply" not in done:
        return "apply", "the code is not applied yet (no apply in phases_done)"
    if "verify-record.md" not in has:
        return "verify", "there is no verify-record.md"
    if result is None:
        return "verify", "verify-record.md has no valid Verdict"
    if result == "blocked":
        return "verify", "the verify is blocked: solve what it reports, then verify again"
    if tier == 3 and not judgment_approved(judges):
        return "judgment", "Tier 3 needs an approved judgment-day before archive"
    return "archive", "the verify is ready"


def judgment_approved(judges: Any) -> bool:
    """La última entrada de `judgment-day` dice exactamente `approved`.

    Un judgment-day posterior que escaló manda sobre un `approved` viejo.
    """
    entries = [j for j in judges or [] if isinstance(j, dict) and j.get("name") == "judgment-day"]
    return bool(entries) and entries[-1].get("result") == "approved"


def change_state(project: Path, name: str) -> dict[str, Any]:
    return state_of(project, get_change(project, name))


def state_of(project: Path, change: Change) -> dict[str, Any]:
    warnings: list[str] = []
    tier, source = tier_of(Path(project) / change.path)
    following, reason = next_phase(project, change, tier, source, _record(project, change, []))
    record = _record(project, change, warnings)
    items = _followups(project, change, warnings)
    return {
        "name": change.name,
        "epic": change.epic,
        "path": change.path,
        "archived": change.archived,
        "archived_on": change.archived_on,
        "phase": change.phase,
        "tier": tier,
        "tier_source": source,
        "next_phase": following,
        "next_reason": reason,
        "artifacts": list(change.artifacts),
        **_projection(record),
        "followups": {
            "open": sum(f["status"] == "open" for f in items),
            "fixed": sum(f["status"] == "fixed" for f in items),
            "dismissed": sum(f["status"] == "dismissed" for f in items),
        },
        "warnings": warnings,
    }
