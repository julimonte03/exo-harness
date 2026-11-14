"""Detección de los agentes que se usan en un proyecto (ADR-0006, `docs/agent-matrix.md`).

Puntaje por señal (se suma una vez por categoría):

- **3**: variable de entorno del agente que está ejecutando el comando.
- **2**: archivos del agente en el repo.
- **1**: ejecutable en el `PATH`.

Se preseleccionan los agentes con 2 o más. `code` no cuenta como señal de
Copilot, porque VS Code puede estar sin Copilot. La detección nunca se usa para
decisiones de seguridad.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from exo.adapters import KNOWN_AGENTS

ENV_SCORE, FILE_SCORE, EXE_SCORE = 3, 2, 1
STRONG = 2


@dataclass(frozen=True)
class Signals:
    files: tuple[str, ...]
    exes: tuple[str, ...]
    env: tuple[str, ...]  # variables cuya presencia indica el agente
    ai_agent: str  # prefijo del valor de AI_AGENT


SIGNALS: dict[str, Signals] = {
    "claude-code": Signals(
        files=("CLAUDE.md", ".claude"),
        exes=("claude",),
        env=("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"),
        ai_agent="claude-code",
    ),
    "copilot": Signals(
        files=(
            ".github/copilot-instructions.md",
            ".github/instructions",
            ".github/agents",
            ".github/skills",
            ".github/prompts",
            ".vscode/mcp.json",
        ),
        exes=("copilot",),
        env=("COPILOT_CLI", "COPILOT_AGENT_SESSION_ID", "VSCODE_AGENT"),
        ai_agent="github_copilot",
    ),
    "cursor": Signals(
        files=(".cursor", ".cursorrules"),
        exes=("cursor",),
        env=("CURSOR_AGENT",),
        ai_agent="cursor",
    ),
    "codex": Signals(
        files=(".codex", "AGENTS.override.md"),
        exes=("codex",),
        env=("CODEX_THREAD_ID", "CODEX_SESSION_ID"),
        ai_agent="codex",
    ),
    "gemini": Signals(
        files=("GEMINI.md", ".gemini"),
        exes=("gemini", "agy"),
        env=("GEMINI_CLI",),
        ai_agent="gemini",
    ),
    "devin": Signals(
        files=(".devin", ".windsurf", ".windsurfrules"),
        exes=("devin", "windsurf"),
        env=(),
        ai_agent="devin",
    ),
}


@dataclass(frozen=True)
class Detection:
    agent: str
    score: int
    evidence: tuple[str, ...]

    @property
    def strong(self) -> bool:
        return self.score >= STRONG


def _score(
    agent: str, project: Path, env: Mapping[str, str], which: Callable[[str], str | None]
) -> Detection:
    signals = SIGNALS[agent]
    evidence: list[str] = []
    score = 0
    env_hits = [name for name in signals.env if env.get(name)]
    ai_agent = env.get("AI_AGENT", "")
    if ai_agent.startswith(signals.ai_agent):
        env_hits.append(f"AI_AGENT={ai_agent}")
    if env_hits:
        score += ENV_SCORE
        evidence += [f"env var {name}" for name in env_hits]
    files = [rel for rel in signals.files if (project / rel).exists()]
    if files:
        score += FILE_SCORE
        evidence += [f"file {rel}" for rel in files]
    exes = [name for name in signals.exes if which(name)]
    if exes:
        score += EXE_SCORE
        evidence += [f"executable {name}" for name in exes]
    return Detection(agent, score, tuple(evidence))


def detect(
    project: Path,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] | None = None,
) -> list[Detection]:
    """Agentes con alguna señal, del más probable al menos probable."""
    env = os.environ if env is None else env
    which = shutil.which if which is None else which
    found = [_score(agent, Path(project), env, which) for agent in SIGNALS]
    order = {agent: i for i, agent in enumerate(KNOWN_AGENTS)}
    return sorted((d for d in found if d.score), key=lambda d: (-d.score, order[d.agent]))


def preselect(detections: list[Detection]) -> list[str]:
    """Agentes a preseleccionar (señal fuerte), en el orden conocido."""
    order = {agent: i for i, agent in enumerate(KNOWN_AGENTS)}
    return sorted((d.agent for d in detections if d.strong), key=order.__getitem__)
