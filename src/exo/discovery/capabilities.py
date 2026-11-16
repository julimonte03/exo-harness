"""Las capacidades que sintetiza la ingeniería inversa (R4, F6, ADR-0015).

- **Lectura:** las specs de `<specs_dir>/capabilities/`, parseadas. Una que no es UTF-8
  se saltea con un aviso que la nombra: una spec ilegible no frena a las demás.
- **Citas:** los archivos que citan sus requisitos con `[Code] path:line`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from exo.sdd import specs

_CITED = re.compile(r"\[Code\]\s+([^\s\[\]]+):\d+")


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
