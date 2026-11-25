"""Adaptador de GitHub Copilot en VS Code y Copilot CLI (Tier 1, ADR-0006).

Copilot lee `AGENTS.md`, `.claude/skills/`, `.claude/agents/` y `.mcp.json`
(`docs/agent-matrix.md`), así que comparte archivos con Claude Code: si los dos
son destino, el motor unifica las operaciones. El cloud agent de GitHub.com no es
destino: el adaptador no genera nada específico para él (ADR-0017 dejó sin efecto la
razón de ADR-0008, que los repos estaban en Azure DevOps).
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
from exo.installer.ops import MergeKey, Op

OWNER = "adapter:copilot"


class CopilotAdapter:
    id = "copilot"

    def capabilities(self) -> Capabilities:
        return Capabilities(rules=True, skills=True, subagents=True, hooks=False, mcp=True)

    def plan(self, ctx: Context) -> list[Op]:
        ops: list[Op] = [*mirror_skills(ctx, CLAUDE_SKILLS, OWNER), *mirror_subagents(ctx, OWNER)]
        if ctx.mcp_enabled:
            ops.append(
                MergeKey(".mcp.json", f"mcpServers.{_meta.NAME}", mcp_entry(ctx.targets), OWNER)
            )
        return ops
