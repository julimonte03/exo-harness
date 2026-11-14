"""Mapa fase → skills del ciclo SDD (§6.4 del reporte), leído de su contrato.

El mapa vive en `packs/sdd/shared/phase-skill-map.md` y se instala como
contrato compartido. Tiene dos tablas que el motor lee:

- `## Map`: qué skills carga cada fase. Toda skill entre comillas invertidas en
  esa sección es una mención.
- `## Skills from packs not installed yet`: las skills que el mapa nombra pero
  todavía no existen, con su pack y el criterio inline que se aplica cuando
  faltan. `exo validate` acepta una referencia `skill:` sin resolver solo si
  está declarada acá, y el test de consistencia exige que toda mención exista o
  esté declarada (F4, tarea 8).

Los comentarios HTML y los bloques de código no cuentan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAP_FILE = PurePosixPath("packs/sdd/shared/phase-skill-map.md")
MAP_SECTION = "Map"
DEGRADATIONS_SECTION = "Skills from packs not installed yet"
NOTE = "{pack}/{skill} not installed — applying inline criteria"

_NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_TICKED = re.compile(rf"`({_NAME})`")
_ROW = re.compile(rf"^\|\s*`({_NAME})`\s*\|\s*({_NAME})\s*\|(.*)\|\s*$")
_H2 = re.compile(r"^##(?!#)\s+(.+?)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass(frozen=True)
class Degradation:
    skill: str
    pack: str
    criteria: str
    line: int


@dataclass(frozen=True)
class PhaseMap:
    mentions: dict[str, int]  # skill -> primera línea donde aparece
    degradations: dict[str, Degradation]


def note(pack: str, skill: str) -> str:
    """El texto exacto que el agente dice cuando una skill falta (§2.5 del reporte)."""
    return NOTE.format(pack=pack, skill=skill)


def parse(text: str) -> PhaseMap:
    masked = _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    mentions: dict[str, int] = {}
    degradations: dict[str, Degradation] = {}
    section = ""
    in_code = False
    for number, line in enumerate(masked.splitlines(), start=1):
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading = _H2.match(line)
        if heading:
            section = heading.group(1)
            continue
        if section == MAP_SECTION:
            for name in _TICKED.findall(line):
                mentions.setdefault(name, number)
        elif section == DEGRADATIONS_SECTION:
            row = _ROW.match(line)
            if row:
                skill, pack, criteria = row.groups()
                degradations[skill] = Degradation(skill, pack, criteria.strip(), number)
    return PhaseMap(mentions, degradations)


def load(root: Path) -> PhaseMap | None:
    path = Path(root) / MAP_FILE
    if not path.is_file():
        return None
    return parse(path.read_text(encoding="utf-8"))
