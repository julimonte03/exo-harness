"""Packs del contenido: manifiestos, dependencias y descubrimiento de skills y subagentes.

Cada pack vive en `packs/<nombre>/` con un `pack.json`:
`{name, version, description, requires, optional}`. `requires` se instala en
cascada; `optional` habilita referencias a skills de otro pack sin instalarlo
(`docs/plan/02-ARQUITECTURA.md` §2.5). Las carpetas que empiezan con `_` son de
soporte y no se tratan como packs ni skills.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo import _meta
from exo.core import frontmatter, fsutil

MANIFEST = "pack.json"
PACK_KEY = f"{_meta.NAME}-pack"  # metadata de la skill que indica su pack
SKILL_FILE = "SKILL.md"
_KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


class PackError(ValueError):
    """Manifiesto inválido o dependencias imposibles de resolver."""


@dataclass(frozen=True)
class Pack:
    name: str
    version: str
    description: str
    requires: tuple[str, ...]
    optional: tuple[str, ...]
    path: Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    pack: str
    path: Path  # carpeta de la skill
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Subagent:
    name: str
    description: str
    pack: str
    path: Path  # archivo .md


@dataclass
class Collection:
    packs: dict[str, Pack] = field(default_factory=dict)
    skills: list[Skill] = field(default_factory=list)
    subagents: list[Subagent] = field(default_factory=list)

    def duplicates(self) -> dict[str, list[Skill]]:
        seen: dict[str, list[Skill]] = {}
        for skill in self.skills:
            seen.setdefault(skill.name, []).append(skill)
        return {name: found for name, found in seen.items() if len(found) > 1}


def _names(value: Any, field_name: str, where: Path) -> tuple[str, ...]:
    valid = isinstance(value, list) and all(isinstance(v, str) and _KEBAB.match(v) for v in value)
    if not valid:
        raise PackError(f"{where}: {field_name} tiene que ser una lista de nombres kebab-case")
    return tuple(value)


def load_pack(folder: Path) -> Pack:
    folder = Path(folder)
    manifest = folder / MANIFEST
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PackError(f"{folder}: falta {MANIFEST}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackError(f"{manifest}: no es JSON válido ({exc})") from exc
    if not isinstance(raw, dict):
        raise PackError(f"{manifest}: la raíz tiene que ser un objeto")
    name = raw.get("name")
    if name != folder.name or not isinstance(name, str) or not _KEBAB.match(name):
        raise PackError(
            f"{manifest}: name tiene que ser kebab-case e igual a la carpeta ({folder.name})"
        )
    version = raw.get("version")
    if not isinstance(version, str) or not _SEMVER.match(version):
        raise PackError(f"{manifest}: version tiene que ser semver (por ejemplo 0.1.0)")
    description = raw.get("description")
    if not isinstance(description, str) or not description.strip():
        raise PackError(f"{manifest}: falta description")
    return Pack(
        name=name,
        version=version,
        description=description.strip(),
        requires=_names(raw.get("requires", []), "requires", manifest),
        optional=_names(raw.get("optional", []), "optional", manifest),
        path=folder,
    )


def load_packs(root: Path) -> dict[str, Pack]:
    """Packs bajo `<root>/packs/`, ordenados por nombre."""
    folder = Path(root) / "packs"
    if not folder.is_dir():
        return {}
    return {
        p.name: load_pack(p)
        for p in sorted(folder.iterdir())
        if p.is_dir() and not p.name.startswith("_")
    }


def resolve(available: dict[str, Pack], wanted: list[str]) -> list[str]:
    """Packs a instalar, con `requires` en cascada y en orden topológico."""
    order: list[str] = []
    done: set[str] = set()

    def visit(name: str, chain: list[str]) -> None:
        if name in done:
            return
        if name in chain:
            cycle = " -> ".join([*chain[chain.index(name) :], name])
            raise PackError(f"dependencias en ciclo: {cycle}")
        pack = available.get(name)
        if pack is None:
            if chain:
                raise PackError(f"{chain[-1]} requiere {name!r}, que no existe")
            raise PackError(f"no existe el pack {name!r}")
        for required in pack.requires:
            visit(required, [*chain, name])
        done.add(name)
        order.append(name)

    for name in wanted:
        visit(name, [])
    return order


def _description(data: dict[str, Any]) -> str:
    value = data.get("description")
    return " ".join(value.split()) if isinstance(value, str) else ""


def discover_skills(skills_dir: Path, pack: str | None = None) -> list[Skill]:
    """Skills (carpetas con SKILL.md) de un directorio. Sin `pack`, lo toma de la metadata."""
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        return []
    found: list[Skill] = []
    for folder in sorted(skills_dir.iterdir()):
        skill_file = folder / SKILL_FILE
        if folder.name.startswith("_") or fsutil.is_link(folder) or not skill_file.is_file():
            continue
        data, _ = frontmatter.parse(skill_file.read_text(encoding="utf-8"))
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        name = data.get("name") if isinstance(data.get("name"), str) else folder.name
        owner = pack if pack is not None else str(metadata.get(PACK_KEY, ""))
        found.append(Skill(name, _description(data), owner, folder, metadata))
    return found


def discover_subagents(agents_dir: Path, pack: str) -> list[Subagent]:
    agents_dir = Path(agents_dir)
    if not agents_dir.is_dir():
        return []
    found: list[Subagent] = []
    for path in sorted(agents_dir.glob("*.md")):
        data, _ = frontmatter.parse(path.read_text(encoding="utf-8"))
        name = data.get("name") if isinstance(data.get("name"), str) else path.stem
        found.append(Subagent(name, _description(data), pack, path))
    return found


def load_collection(root: Path) -> Collection:
    """Todo el contenido: packs, skills y subagentes, en orden de pack y nombre."""
    collection = Collection(packs=load_packs(root))
    for pack in collection.packs.values():
        collection.skills.extend(discover_skills(pack.path / "skills", pack.name))
        collection.subagents.extend(discover_subagents(pack.path / "agents", pack.name))
    return collection
