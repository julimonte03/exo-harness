"""Las capacidades que sintetiza la ingeniería inversa (R4, F6, ADR-0015).

- **Lectura:** las specs de `<specs_dir>/capabilities/`, parseadas. Una que no es UTF-8
  se saltea con un aviso que la nombra: una spec ilegible no frena a las demás.
- **Citas:** los archivos que citan sus requisitos con `[Code] path:line`.
- **`synthesized`:** `re-synthesize` lo corre después de escribir cada spec. Valida que
  exista, que tenga preámbulo y que no tenga errores (los warnings no frenan), y
  registra en `discovery/capabilities/<cap>.json` los hashes de los archivos analizados
  que cita y la ronda.
- **Stale:** una capacidad registrada con un archivo citado que cambió o que falta. La
  señal queda hasta el próximo `synthesized`, aunque las unidades se vuelvan a cerrar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exo.discovery import files as files_mod
from exo.discovery import store
from exo.sdd import specs

FOLDER = "capabilities"
_CITED = re.compile(r"\[Code\]\s+([^\s\[\]]+):\d+")
_NAME = re.compile(specs.CAPABILITY_NAME)


class CapabilityError(ValueError):
    """La spec no se puede registrar: no existe, no tiene preámbulo o tiene errores."""


@dataclass(frozen=True)
class Spec:
    name: str
    path: str  # relativa al proyecto, con /
    text: str
    capability: specs.Capability

    @property
    def status(self) -> str | None:
        return self.capability.status


def load(project: Path, warnings: list[str] | None = None) -> list[Spec]:
    """Las specs de capacidad legibles, por nombre (las que no son UTF-8 van a `warnings`)."""
    project = Path(project)
    return [
        Spec(name, path.relative_to(project).as_posix(), text, specs.parse_capability(text, name))
        for name, path, text in specs.capability_texts(project, warnings)
    ]


def with_preamble(project: Path, warnings: list[str] | None = None) -> list[Spec]:
    """Las specs con preámbulo (`Status: as-is` o `as-is-validated`): las de discovery."""
    return [spec for spec in load(project, warnings) if spec.status is not None]


def cited(spec: Spec) -> set[str]:
    """Los archivos que citan sus requisitos con `[Code] path:line` (sin las lápidas)."""
    return {
        path
        for block in spec.capability.requirements.values()
        for line in block.lines
        for path in _CITED.findall(line)
    }


def record_name(name: str) -> str:
    return f"{FOLDER}/{name}.json"


def _validated(project: Path, name: str, problems: list[str]) -> Spec | None:
    if not _NAME.fullmatch(name):
        problems.append(f"{name!r} is not a capability name: lowercase words joined by hyphens")
        return None
    path = specs.capabilities_root(project) / name / specs.SPEC_FILE
    rel = path.relative_to(project).as_posix()
    if not path.is_file():
        problems.append(f"{rel} does not exist: write the capability's spec there first")
        return None
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        problems.append(f"{rel} is not UTF-8 text ({exc.reason}); save it as UTF-8")
        return None
    capability = specs.parse_capability(text, name)
    if capability.status is None:
        problems.append(
            f"{rel} has no preamble: an as-is spec starts with 'Status: as-is' and "
            "'Source: ...' before ## Purpose"
        )
        return None
    if capability.errors:
        problems += [f"{rel}:{p.line}: {p.message}" for p in capability.errors]
        return None
    return Spec(name, rel, text, capability)


def synthesized(project: Path, names: list[str]) -> list[dict[str, Any]]:
    """Valida las specs y registra cada una (todas o ninguna). Devuelve los registros."""
    project = Path(project)
    problems: list[str] = []
    valid = [_validated(project, name, problems) for name in dict.fromkeys(names)]
    if problems:
        raise CapabilityError("\n".join(problems))
    current = {f.path: f.sha for f in files_mod.list_files(project).files if not f.sensitive}
    written: list[dict[str, Any]] = []
    for spec in (s for s in valid if s is not None):
        previous = store.read_json(project, record_name(spec.name)) or {}
        rounds = previous.get("rounds")
        record = {
            "capability": spec.name,
            "files": {p: current[p] for p in sorted(cited(spec)) if p in current},
            "rounds": (rounds if isinstance(rounds, int) else 0) + 1,
        }
        store.write_json(project, record_name(spec.name), record)
        written.append(record)
    return written


def records(project: Path) -> dict[str, dict[str, Any]]:
    """Capacidad -> su registro de `synthesized`."""
    folder = store.root(project) / FOLDER
    if not folder.is_dir():
        return {}
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.json")):
        data = store.read_json(project, record_name(path.stem))
        if data is not None:
            found[path.stem] = data
    return found


def stale(
    recorded: dict[str, dict[str, Any]], fileset: files_mod.FileSet, present: set[str]
) -> list[str]:
    """Las capacidades con preámbulo (`present`) cuyo registro cita un archivo que cambió o
    que ya no está entre los analizados."""
    current = {f.path: f.sha for f in fileset.files}
    return sorted(
        name
        for name, record in recorded.items()
        if name in present
        and any(current.get(path) != sha for path, sha in record.get("files", {}).items())
    )
