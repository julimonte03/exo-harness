"""`exo check` v1: los chequeos de un change antes del PR (F4; F5 los extiende).

Por cada change activo (todos, los nombrados, o los tocados en el diff contra
`--base`):

- speclint sobre la carpeta del change;
- `ai-usage-record.json` presente, legible, válido contra su esquema y con el
  `change_name` de la carpeta;
- el tier de `fitness-assessment.json` (si falta o no se lee, Tier 4 y error);
- los artefactos que exige el tier (D-27).

También lintea las specs de capacidad (todas, o las tocadas en el diff). Con
persistencia `memory` o `none` los artefactos no están en disco y no hay nada
que revisar.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from exo import _meta
from exo.core import config, fsutil
from exo.sdd import changes, observability, record, speclint, specs

# Artefactos obligatorios por tier (D-27). `spec.md` en Tier 1 es opcional: solo avisa.
REQUIRED: dict[int, tuple[str, ...]] = {
    1: ("proposal.md",),
    2: ("proposal.md", "spec.md", "test-spec.md"),
    3: ("proposal.md", "spec.md", "design.md", "tasks.md", "test-spec.md"),
    4: ("proposal.md", "spec.md", "design.md", "tasks.md", "test-spec.md"),
}
NO_DISK = ("memory", "none")
_SAFE_REF = re.compile(r"^[A-Za-z0-9._/@{}^~:+-]+$")
_GIT_TIMEOUT = 30


class CheckError(ValueError):
    """No se pudo armar la lista de qué revisar (change inexistente, git, config)."""


@dataclass(frozen=True)
class Finding:
    severity: str  # error | warning
    path: str  # relativa al proyecto, con /
    line: int
    message: str


@dataclass
class ChangeCheck:
    name: str
    path: str
    tier: int
    tier_source: str  # assessment | missing | unreadable
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


@dataclass
class CheckResult:
    changes: list[ChangeCheck] = field(default_factory=list)
    capabilities: list[tuple[str, list[Finding]]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        cap_errors = any(f.severity == "error" for _, items in self.capabilities for f in items)
        return all(c.ok for c in self.changes) and not cap_errors


def _rel(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def _git(project: Path, *args: str) -> list[str]:
    command = ["git", "-c", "core.quotepath=false", "-C", str(project), *args]
    try:
        result = subprocess.run(command, capture_output=True, timeout=_GIT_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CheckError(f"could not run git ({exc}); --base needs git") from exc
    if result.returncode != 0:
        detail = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        raise CheckError(f"git {' '.join(args[:2])} failed: {detail or result.returncode}")
    out = (result.stdout or b"").decode("utf-8", errors="replace")
    return [item for item in out.split("\0") if item]


def touched(project: Path, base: str) -> list[str]:
    """Rutas (relativas al proyecto) que cambian contra `base`, más las sin trackear."""
    if base.startswith("-") or not _SAFE_REF.match(base):
        raise CheckError(f"invalid --base {base!r}: use a branch, tag or commit")
    diff = _git(project, "diff", "--name-only", "-z", "--relative", base, "--")
    untracked = _git(project, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted(set(diff) | set(untracked))


def _within(path: str, folder: str) -> bool:
    return PurePosixPath(path).is_relative_to(PurePosixPath(folder))


def _lint(project: Path, target: Path, kind: str | None = None) -> list[Finding]:
    try:
        report = speclint.lint_path(target, kind)
    except (speclint.SpeclintError, OSError, UnicodeDecodeError) as exc:
        return [Finding("error", _rel(project, target), 0, str(exc))]
    return [
        Finding("error", _rel(project, item.path), issue.line, issue.message)
        for item in report.files
        for issue in item.errors
    ]


def _check_record(project: Path, change: observability.Change) -> list[Finding]:
    rel = f"{change.path}/{record.FILENAME}"
    path = project / rel
    try:
        data = json.loads(fsutil.read_bytes(path).decode("utf-8"))
    except FileNotFoundError:
        return [
            Finding(
                "error",
                change.path,
                0,
                f"no {record.FILENAME}; changes get one from `{_meta.NAME} change new`",
            )
        ]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [Finding("error", rel, 0, f"{record.FILENAME} is not valid JSON ({exc})")]
    findings = [Finding("error", rel, 0, problem) for problem in record.validate(data)]
    name = data.get("change_name") if isinstance(data, dict) else None
    if isinstance(name, str) and name != change.name:
        findings.append(
            Finding(
                "error",
                rel,
                0,
                f"change_name is {name} but the folder is {change.name}; they must match",
            )
        )
    return findings


def _check_change(project: Path, change: observability.Change) -> ChangeCheck:
    folder = project / change.path
    tier = changes.read_tier(folder)
    assessment = folder / changes.ASSESSMENT
    source = (
        "assessment" if tier is not None else ("unreadable" if assessment.exists() else "missing")
    )
    effective = changes.effective_tier(folder)
    item = ChangeCheck(change.name, change.path, effective, source)
    if source != "assessment":
        problem = "is not readable" if source == "unreadable" else "is missing"
        item.findings.append(
            Finding(
                "error",
                change.path,
                0,
                f"no fitness-assessment.json: it {problem}, so the tier is unknown and Tier 4 "
                f"rules apply; run `{_meta.NAME} fitness classify --change {change.name}`",
            )
        )
    if any((folder / name).is_file() for name in speclint.ARTIFACTS):
        item.findings += _lint(project, folder)
    item.findings += _check_record(project, change)
    for name in REQUIRED[effective]:
        if not (folder / name).is_file():
            item.findings.append(
                Finding("error", change.path, 0, f"Tier {effective} requires {name}")
            )
    if effective == 1 and not (folder / "spec.md").is_file():
        item.findings.append(
            Finding(
                "warning",
                change.path,
                0,
                "no spec.md: in Tier 1 that is fine only if the change must not alter behavior "
                "(D-27); otherwise write the delta",
            )
        )
    return item


def check(project: Path, *, base: str | None = None, names: list[str] | None = None) -> CheckResult:
    project = Path(project)
    loaded = config.load(project)
    if loaded.fallback:
        raise CheckError("the project config cannot be used: " + "; ".join(loaded.warnings))
    result = CheckResult()
    persistence = loaded.config["sdd"]["persistence"]
    if persistence in NO_DISK:
        result.notes.append(
            f"sdd.persistence is {persistence}: the SDD artifacts are not on disk, so there is "
            "nothing to check"
        )
        return result
    active = observability.find_changes(project, include_archived=False)
    capabilities = specs.capabilities_root(project)
    cap_files = sorted(capabilities.glob(f"*/{specs.SPEC_FILE}")) if capabilities.is_dir() else []
    if names:
        selected = []
        for name in names:
            try:
                selected.append(observability.get_change(project, name))
            except observability.ObservabilityError as exc:
                raise CheckError(str(exc)) from exc
        cap_files = []
    elif base is not None:
        paths = touched(project, base)
        selected = [c for c in active if any(_within(p, c.path) for p in paths)]
        cap_files = [f for f in cap_files if _rel(project, f) in paths]
        result.notes.append(f"checking what changed against {base}: {len(paths)} files")
    else:
        selected = active
    for change in selected:
        if change.archived:
            result.notes.append(f"{change.name} is archived; not checked")
            continue
        result.changes.append(_check_change(project, change))
    for path in cap_files:
        result.capabilities.append((_rel(project, path), _lint(project, path, "capability")))
    return result
