"""`exo check`: los chequeos de un change antes del PR (F4 y F5, ADR-0014).

Por cada change (los activos; o los nombrados, o los tocados en el diff contra
`--base`, que pueden estar archivados: `sdd-archive` mueve el change antes del PR
y el chequeo del PR lo tiene que seguir viendo):

- speclint sobre la carpeta del change;
- `ai-usage-record.json` presente, legible, válido contra su esquema y con el
  `change_name` de la carpeta;
- el tier de `fitness-assessment.json` (si falta o no se lee, Tier 4 y error);
- los artefactos que exige el tier (D-27).

Desde que hay `verify-record.md` (o el change está archivado), además:

- el veredicto tiene que ser `ready`;
- los gates del tier (`governance.gates`) tienen que estar, bien formados; uno
  escalado o que pide aprobación queda como aviso para `tech_lead` (el motor no
  verifica roles, §7.3);
- en Tier 4, `judgment-day` aprobado en el AI Usage Record.

También: la config válida, el escaneo de secretos y datos personales de lo que
agrega el diff contra `--base` (con los waivers vigentes) y las specs de
capacidad. `--fast` (lo usa `pre-push`) deja solo lo que vale para una rama en
curso: speclint de lo que existe, el registro y el escaneo del diff. Con
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


class CheckUsageError(CheckError):
    """Argumento inválido (por ejemplo `--base`): es un error de uso."""


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
    config: list[Finding] = field(default_factory=list)
    diff: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        cap_errors = any(f.severity == "error" for _, items in self.capabilities for f in items)
        other = any(f.severity == "error" for f in self.config + self.diff)
        return all(c.ok for c in self.changes) and not cap_errors and not other


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


def fork_point(project: Path, base: str) -> str:
    """El commit donde la rama salió de `base` (merge-base con HEAD)."""
    if base.startswith("-") or not _SAFE_REF.match(base):
        raise CheckUsageError(f"invalid --base {base!r}: use a branch, tag or commit")
    found = _git(project, "merge-base", base, "HEAD")
    if not found:
        raise CheckError(f"{base} and HEAD have no common history; pass the branch the PR goes to")
    return found[0].strip()


def touched(project: Path, base: str) -> list[str]:
    """Rutas (relativas al proyecto) que cambian contra `base`, más las sin trackear."""
    if base.startswith("-") or not _SAFE_REF.match(base):
        raise CheckUsageError(f"invalid --base {base!r}: use a branch, tag or commit")
    # Contra el punto donde la rama salió de la base, no contra la punta de la base: si no,
    # lo que la base cambió después parece tocado por la rama.
    found = _git(project, "merge-base", base, "HEAD")
    if not found:
        raise CheckError(f"{base} and HEAD have no common history; pass the branch the PR goes to")
    fork = found[0].strip()
    diff = _git(project, "diff", "--name-only", "-z", "--relative", fork, "--")
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


def _delta_capabilities(project: Path, change: observability.Change) -> set[str]:
    path = project / change.path / specs.SPEC_FILE
    if not path.is_file():
        return set()
    try:
        delta = specs.parse_delta(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError):
        return set()
    return {block.capability for _, block in delta.blocks()}


def _gates(project: Path, change: observability.Change, tier: int, cfg: dict) -> list[Finding]:
    folder = project / change.path
    found: list[Finding] = []
    for name in cfg["governance"]["gates"].get(str(tier), []):
        if name == speclint.CONTRACT_GATE:
            path = folder / "verify-record.md"
            info = speclint.contract_gate(path) if path.is_file() else None
        else:
            path = folder / speclint.GATES_DIR / f"{name}.md"
            info = speclint.gate_info(path) if path.is_file() else None
        if info is None:
            found.append(
                Finding(
                    "error",
                    change.path,
                    0,
                    f"Tier {tier} requires the gate {name} ({speclint.GATES_DIR}/{name}.md): "
                    "run the skill that owns it",
                )
            )
        elif info.needs_approval:
            found.append(
                Finding(
                    "warning",
                    _rel(project, info.path),
                    0,
                    f"the gate {name} is {info.verdict or 'not readable'} or asks for approval: "
                    "it needs the tech_lead role's approval in the PR",
                )
            )
    return found


def _judgment_day(project: Path, change: observability.Change) -> list[Finding]:
    data = observability.ai_usage_record(project, change.name).get("record") or {}
    judges = data.get("judges_invoked") if isinstance(data, dict) else None
    approved = any(
        isinstance(j, dict) and j.get("name") == "judgment-day" and j.get("result") == "approved"
        for j in judges or []
    )
    if approved:
        return []
    return [
        Finding(
            "error",
            change.path,
            0,
            "Tier 4 needs an approved judgment-day: judges_invoked has no "
            '{"name": "judgment-day", "result": "approved"}',
        )
    ]


def _readiness(
    project: Path, change: observability.Change, tier: int, cfg: dict
) -> list[Finding]:
    """Lo que se exige desde el verify: veredicto listo, gates y judgment-day."""
    folder = project / change.path
    verify = folder / "verify-record.md"
    if not verify.is_file():
        if change.archived:
            return [Finding("error", change.path, 0, "archived without verify-record.md")]
        return []
    found: list[Finding] = []
    result = speclint.verdict(verify.read_text(encoding="utf-8-sig"))
    if result != "ready":
        found.append(
            Finding(
                "error",
                _rel(project, verify),
                0,
                f"the verify says {result or 'nothing readable'}: the change is not ready",
            )
        )
    found += _gates(project, change, tier, cfg)
    if tier == 4:
        found += _judgment_day(project, change)
    return found


def _check_change(
    project: Path, change: observability.Change, cfg: dict | None = None, fast: bool = False
) -> ChangeCheck:
    folder = project / change.path
    tier = changes.read_tier(folder)
    assessment = folder / changes.ASSESSMENT
    source = (
        "assessment" if tier is not None else ("unreadable" if assessment.exists() else "missing")
    )
    effective = changes.effective_tier(folder)
    item = ChangeCheck(change.name, change.path, effective, source)
    if fast:
        if any((folder / name).is_file() for name in speclint.ARTIFACTS):
            item.findings += _lint(project, folder)
        item.findings += _check_record(project, change)
        return item
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
    if cfg is not None:
        item.findings += _readiness(project, change, effective, cfg)
    return item


def _scan_diff(project: Path, fork: str, cfg: dict) -> list[Finding]:
    """Secretos y datos personales en lo que agrega el diff (y en los archivos nuevos)."""
    from exo.governance import git, hookrun

    added = git.added_lines(project, fork)
    for rel in _git(project, "ls-files", "--others", "--exclude-standard", "-z"):
        path = project / rel
        try:
            if path.stat().st_size > 1_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        added.setdefault(rel, []).extend(enumerate(text.splitlines(), start=1))
    outcome = hookrun.scan_added(project, added, cfg)
    found = [Finding("error", "", 0, message) for message in outcome.errors]
    found += [Finding("warning", "", 0, message) for message in outcome.warnings]
    return found


def check(
    project: Path,
    *,
    base: str | None = None,
    names: list[str] | None = None,
    fast: bool = False,
) -> CheckResult:
    project = Path(project)
    loaded = config.load(project)
    if loaded.fallback:
        raise CheckError("the project config cannot be used: " + "; ".join(loaded.warnings))
    result = CheckResult()
    cfg = loaded.config
    result.config = [
        Finding("error", f"{_meta.PROJECT_DIR}/{config.FILENAME}", 0, f"config: {problem}")
        for problem in loaded.invalid
    ]
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
        touched_caps = set().union(*(_delta_capabilities(project, c) for c in selected))
        cap_files = [f for f in cap_files if f.parent.name in touched_caps]
    elif base is not None:
        paths = touched(project, base)
        result.diff = _scan_diff(project, fork_point(project, base), cfg)
        every = observability.find_changes(project, include_archived=True)
        selected = [c for c in every if any(_within(p, c.path) for p in paths)]
        cap_files = [f for f in cap_files if _rel(project, f) in paths]
        result.notes.append(f"checking what changed against {base}: {len(paths)} files")
    else:
        selected = active
    for change in selected:
        result.changes.append(_check_change(project, change, cfg, fast))
    if fast:
        return result
    for path in cap_files:
        result.capabilities.append((_rel(project, path), _lint(project, path, "capability")))
    return result
