"""Adaptadores por agente (ADR-0006): base genérica más Claude Code y Copilot."""

from __future__ import annotations

from exo.adapters.base import Context
from exo.adapters.claude_code import ClaudeCodeAdapter
from exo.adapters.copilot import CopilotAdapter
from exo.adapters.generic import GenericAdapter
from exo.installer.ops import Op

GENERIC = GenericAdapter()
# Agentes con adaptador propio.
ADAPTERS = {"claude-code": ClaudeCodeAdapter(), "copilot": CopilotAdapter()}
# Agentes que se detectan y quedan cubiertos por la base genérica.
GENERIC_ONLY = ("cursor", "codex", "gemini", "devin")
KNOWN_AGENTS = (*ADAPTERS, *GENERIC_ONLY, "generic")


def plan_all(ctx: Context) -> list[Op]:
    ops = GENERIC.plan(ctx)
    for agent in ctx.targets:
        if agent in ADAPTERS:
            ops += ADAPTERS[agent].plan(ctx)
    return ops
