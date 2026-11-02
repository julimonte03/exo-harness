"""Adaptador de Claude Code (Tier 1, ADR-0006). Convenciones en `docs/agent-matrix.md`.

- Skills en `.claude/skills/` (Claude Code no lee `.agents/skills/`).
- Subagentes en `.claude/agents/`.
- Permiso para ejecutar el CLI del motor sin preguntar (`permissions.allow` de
  `.claude/settings.json`), porque las tools se usan por terminal (ADR-0005).
- `CLAUDE.md`: Claude Code ≥ 2.1.281 lee `AGENTS.md` si no hay `CLAUDE.md`, así
  que no se crea; si ya existe, se le agrega al principio el import `@AGENTS.md`
  (ADR-0007). Con `claude_md="always"` se crea igual.
- `.mcp.json` solo si el MCP opcional está habilitado.
"""

from __future__ import annotations

from exo import _meta
from exo.adapters.base import (
    CLAUDE_SKILLS,
    Capabilities,
    Context,
    mcp_entry,
    mirror_skills,
    mirror_subagents,
)
from exo.installer.ops import MergeBlock, MergeKey, MergeListItem, Op

OWNER = "adapter:claude-code"
PERMISSION = f"Bash({_meta.NAME}:*)"


class ClaudeCodeAdapter:
    id = "claude-code"

    def capabilities(self) -> Capabilities:
        return Capabilities(rules=True, skills=True, subagents=True, hooks=True, mcp=True)

    def plan(self, ctx: Context) -> list[Op]:
        ops: list[Op] = [
            *mirror_skills(ctx, CLAUDE_SKILLS, OWNER),
            *mirror_subagents(ctx, OWNER),
            MergeListItem(".claude/settings.json", "permissions.allow", PERMISSION, OWNER),
        ]
        if ctx.claude_md == "always" or (ctx.project / "CLAUDE.md").exists():
            ops.append(MergeBlock("CLAUDE.md", "core", "@AGENTS.md", OWNER, position="start"))
        if ctx.mcp_enabled:
            ops.append(
                MergeKey(".mcp.json", f"mcpServers.{_meta.NAME}", mcp_entry(ctx.targets), OWNER)
            )
        return ops
