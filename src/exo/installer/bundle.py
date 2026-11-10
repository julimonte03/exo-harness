"""Bundle canónico: lo que el motor instala, leído del contenido una sola vez.

Lo construye el motor y los adaptadores solo lo leen (`docs/plan/fases/F2-…`).
Reúne, para los packs resueltos: las reglas (`rules/AGENTS.base.md`), las
skills con todos sus archivos byte a byte, los subagentes y los contratos de
`shared/` si existen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from exo import packs
from exo.core import fsutil

RULES_FILE = Path("rules") / "AGENTS.base.md"


@dataclass(frozen=True)
class SkillFiles:
    name: str
    pack: str
    description: str
    files: dict[str, bytes]  # ruta relativa con / -> bytes


@dataclass(frozen=True)
class SubagentFile:
    name: str
    pack: str
    content: bytes


@dataclass(frozen=True)
class Bundle:
    packs: tuple[str, ...]
    rules: str
    skills: tuple[SkillFiles, ...]
    subagents: tuple[SubagentFile, ...]
    shared: dict[str, bytes] = field(default_factory=dict)


def _files(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in fsutil.walk_files(folder)}


def build_bundle(content_root: Path, wanted: list[str]) -> Bundle:
    root = Path(content_root)
    collection = packs.load_collection(root)
    order = packs.resolve(collection.packs, wanted)
    chosen = set(order)
    skills = tuple(
        SkillFiles(s.name, s.pack, s.description, _files(s.path))
        for s in sorted(collection.skills, key=lambda s: s.name)
        if s.pack in chosen
    )
    subagents = tuple(
        SubagentFile(a.name, a.pack, a.path.read_bytes())
        for a in sorted(collection.subagents, key=lambda a: a.name)
        if a.pack in chosen
    )
    shared_dir = root / "shared"
    shared = _files(shared_dir) if shared_dir.is_dir() else {}
    rules = (root / RULES_FILE).read_text(encoding="utf-8")
    return Bundle(tuple(order), rules, skills, subagents, shared)
