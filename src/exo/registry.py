"""Render de `<PROJECT_DIR>/skill-registry.md` a partir del frontmatter de las skills.

El frontmatter es la fuente de verdad de `name` y `description` (invariante 6
de `docs/plan/02-ARQUITECTURA.md` §2.13). El render es determinista: ordenado
por nombre, una línea por skill.
"""

from __future__ import annotations

from pathlib import Path

from exo import _meta
from exo.packs import SKILL_FILE, Skill

FILENAME = "skill-registry.md"


def registry_path(project: Path) -> Path:
    return Path(project) / _meta.PROJECT_DIR / FILENAME


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(Path(base).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def render(skills: list[Skill], *, base: Path) -> str:
    lines = [
        "# Skill registry",
        "",
        f"<!-- Generado por {_meta.NAME} {_meta.VERSION}. No editar a mano: "
        f"se regenera con `{_meta.NAME} registry`. -->",
        "",
    ]
    if not skills:
        lines.append("_No hay skills._")
    else:
        lines += ["| Skill | Pack | Descripción | Ruta |", "|---|---|---|---|"]
        for skill in sorted(skills, key=lambda s: (s.name, s.pack)):
            path = _relative(skill.path / SKILL_FILE, Path(base))
            lines.append(
                f"| {_cell(skill.name)} | {_cell(skill.pack)} | "
                f"{_cell(skill.description)} | {path} |"
            )
    return "\n".join(lines) + "\n"
