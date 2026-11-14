"""Bundle canónico: lo que el motor instala, leído del contenido una sola vez.

Lo construye el motor y los adaptadores solo lo leen (`docs/plan/fases/F2-…`).
Reúne, para los packs resueltos: las reglas (`rules/AGENTS.base.md`), las
skills con todos sus archivos byte a byte, los subagentes y los contratos
compartidos.

Los contratos viven en `packs/<pack>/shared/` y se instalan solo con su pack:
sin `sdd`, un proyecto no recibe los contratos del ciclo. Con `sdd` van además
las plantillas de speclint (`templates/`) y los esquemas JSON (`schemas/`), que
siguen teniendo una sola fuente en `exo/sdd/` porque el runtime los usa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from exo import packs
from exo.core import fsutil
from exo.sdd import record, speclint

RULES_FILE = Path("rules") / "AGENTS.base.md"
SHARED_DIR = "shared"
ENGINE_SHARED_PACK = "sdd"
# Archivos del runtime que se instalan con el pack: (carpeta en shared/, origen, patrón).
ENGINE_SHARED = (
    ("templates", speclint.TEMPLATES_DIR, "*.md"),
    ("schemas", record.SCHEMAS_DIR, "*.json"),
)


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


def _shared(collection: packs.Collection, order: list[str]) -> dict[str, bytes]:
    """Contratos de los packs elegidos; dos packs no pueden traer la misma ruta."""
    shared: dict[str, bytes] = {}
    origin: dict[str, str] = {}

    def add(rel: str, data: bytes, source: str) -> None:
        if rel in shared:
            raise ValueError(
                f"shared/{rel} comes from both {origin[rel]} and {source}; rename one of them"
            )
        shared[rel] = data
        origin[rel] = source

    for name in order:
        folder = collection.packs[name].path / SHARED_DIR
        if folder.is_dir():
            for rel, data in _files(folder).items():
                add(rel, data, f"pack {name}")
    if ENGINE_SHARED_PACK in order:
        for folder_name, source, pattern in ENGINE_SHARED:
            for path in sorted(source.glob(pattern)):
                add(f"{folder_name}/{path.name}", path.read_bytes(), f"the engine {folder_name}")
    return dict(sorted(shared.items()))


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
    shared = _shared(collection, order)
    rules = (root / RULES_FILE).read_text(encoding="utf-8")
    return Bundle(tuple(order), rules, skills, subagents, shared)
