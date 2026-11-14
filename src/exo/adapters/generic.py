"""Adaptador genérico: la base agnóstica que se instala siempre (ADR-0006).

- Bloque `core` en `AGENTS.md` con las reglas del motor.
- Bloque `core` en `.gitignore` para no versionar los backups.
- Registro de skills del proyecto.
- `.agents/skills/` solo si algún agente destino la necesita (ADR-0007).
- Contratos compartidos de los packs instalados (y las plantillas SDD) en la carpeta del motor.
"""

from __future__ import annotations

from exo import _meta, registry
from exo.adapters.base import (
    AGENTS_SKILLS,
    Capabilities,
    Context,
    mirror_skills,
    skills_dirs,
)
from exo.core import filemerge
from exo.installer.ops import MergeBlock, Op, WriteFile
from exo.packs import Skill

OWNER = "engine"
# Agentes que se detectan pero no tienen adaptador propio, con el paso manual que les falta.
MANUAL_STEPS = {
    "gemini": (
        "Gemini CLI reads GEMINI.md by default: to make it read AGENTS.md, add "
        '"context": {"fileName": ["AGENTS.md", "GEMINI.md"]} to .gemini/settings.json.'
    ),
}


class GenericAdapter:
    id = "generic"

    def capabilities(self) -> Capabilities:
        return Capabilities(rules=True, skills=True, subagents=False, hooks=False, mcp=False)

    def plan(self, ctx: Context) -> list[Op]:
        ops: list[Op] = [
            MergeBlock("AGENTS.md", "core", ctx.bundle.rules, OWNER),
            MergeBlock(
                ".gitignore",
                "core",
                f"{_meta.PROJECT_DIR}/backups/",
                OWNER,
                style=filemerge.STYLE_HASH,
            ),
            WriteFile(f"{_meta.PROJECT_DIR}/skill-registry.md", self._registry(ctx), OWNER),
        ]
        if AGENTS_SKILLS in skills_dirs(ctx.targets):
            ops += mirror_skills(ctx, AGENTS_SKILLS, "adapter:generic")
        ops += [
            WriteFile(f"{_meta.PROJECT_DIR}/shared/{rel}", data, OWNER)
            for rel, data in sorted(ctx.bundle.shared.items())
        ]
        return ops

    def _registry(self, ctx: Context) -> bytes:
        folder = skills_dirs(ctx.targets)[0]
        skills = [
            Skill(s.name, s.description, s.pack, ctx.project / folder / s.name, {})
            for s in ctx.bundle.skills
        ]
        return registry.render(skills, base=ctx.project).encode("utf-8")

    def notes(self, ctx: Context) -> list[str]:
        return [MANUAL_STEPS[agent] for agent in ctx.targets if agent in MANUAL_STEPS]
