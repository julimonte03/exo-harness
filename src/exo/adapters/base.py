"""Interfaz de los adaptadores y helpers compartidos (`docs/plan/02-ARQUITECTURA.md` §2.8).

Un adaptador es **puro**: recibe el contexto (proyecto, bundle, agentes destino,
config) y devuelve operaciones. Puede mirar si un archivo existe para decidir,
pero nunca escribe; toda escritura pasa por `installer.engine`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from exo import _meta
from exo.installer.bundle import Bundle
from exo.installer.ops import Op, WriteFile

# Agentes que leen `.claude/skills/` y `.claude/agents/` (ADR-0007, docs/agent-matrix.md).
CLAUDE_DIR_AGENTS = frozenset({"claude-code", "copilot"})
CLAUDE_SKILLS = ".claude/skills"
AGENTS_SKILLS = ".agents/skills"
CLAUDE_AGENTS = ".claude/agents"


@dataclass(frozen=True)
class Capabilities:
    rules: bool
    skills: bool
    subagents: bool
    hooks: bool
    mcp: bool


@dataclass(frozen=True)
class Context:
    project: Path
    bundle: Bundle
    targets: tuple[str, ...]  # agentes destino; ("generic",) si no hay ninguno
    config: dict[str, Any]
    claude_md: str = "auto"  # "auto": solo si CLAUDE.md existe | "always"

    @property
    def mcp_enabled(self) -> bool:
        return bool(self.config.get("mcp", {}).get("enabled", False))


class Adapter(Protocol):
    id: str

    def capabilities(self) -> Capabilities: ...

    def plan(self, ctx: Context) -> list[Op]: ...


def skills_dirs(targets: tuple[str, ...]) -> list[str]:
    """Carpetas de skills a mantener (ADR-0007): solo las que leen los agentes destino."""
    chosen = set(targets)
    dirs = []
    if chosen & CLAUDE_DIR_AGENTS:
        dirs.append(CLAUDE_SKILLS)
    if not chosen or chosen - CLAUDE_DIR_AGENTS:
        dirs.append(AGENTS_SKILLS)
    return dirs


def mirror_skills(ctx: Context, folder: str, owner: str) -> list[Op]:
    return [
        WriteFile(f"{folder}/{skill.name}/{rel}", data, owner, kind="mirror")
        for skill in ctx.bundle.skills
        for rel, data in sorted(skill.files.items())
    ]


def mirror_subagents(ctx: Context, owner: str) -> list[Op]:
    return [
        WriteFile(f"{CLAUDE_AGENTS}/{agent.name}.md", agent.content, owner, kind="mirror")
        for agent in ctx.bundle.subagents
    ]


def mcp_entry(targets: tuple[str, ...]) -> dict[str, Any]:
    """Entrada del servidor MCP opcional (ADR-0005). Copilot exige `tools`."""
    entry: dict[str, Any] = {"type": "stdio", "command": _meta.NAME, "args": ["mcp"]}
    if "copilot" in targets:
        entry["tools"] = ["*"]
    return entry
