"""Agentes reales para los escenarios de F8: Claude Code y GitHub Copilot CLI.

Cada agente sabe armar su comando no interactivo, aislar su config de usuario y leer su
salida en JSONL. Lo usa `tests/test_agent_scenarios.py` (marker `agent_e2e`); las partes
puras (comandos, aislamiento y lectura) tienen tests en la suite normal
(`tests/test_agents_runner.py`).

Aislamiento:
- **Claude Code:** `--setting-sources project,local --strict-mcp-config`, como el runner de
  evals de F7 (`_skill_evals.ISOLATION_FLAGS`).
- **Copilot CLI:** un `COPILOT_HOME` propio de la corrida, con una copia de `config.json`
  (la cuenta con sesión; el token queda en el almacén de credenciales del sistema) y un
  `settings.json` que ignora las skills personales (`~/.agents/skills`, `~/.claude/skills`
  y `~/.copilot/skills`), más `--disable-builtin-mcps`. Ver `copilot help config`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import _skill_evals as evals

AGENTS = ("claude-code", "copilot")
# Los subcomandos de primer nivel que pueden correr. Sin python, el agente no corre el build
# ni los tests del proyecto (la adopción, D-19).
_CLAUDE_BASE = (
    "Bash(exo:*) Bash(git:*) Bash(ls:*) Bash(cat:*) Bash(mkdir:*) "
    "PowerShell(exo:*) PowerShell(git:*) "
    "Read Edit Write Grep Glob TodoWrite Task Agent Skill"
)
_CLAUDE_PYTHON = " Bash(python:*) Bash(pytest:*) PowerShell(python:*) PowerShell(pytest:*)"
_COPILOT_ALLOW = ("shell(exo:*)", "shell(git:*)", "write")
_COPILOT_PYTHON = ("shell(python:*)", "shell(pytest:*)")
_COPILOT_DENY = ("shell(git push)",)
_PERSONAL_SKILLS = (".agents/skills", ".claude/skills", ".copilot/skills")
_SHELL_TOOLS = {"Bash", "PowerShell", "bash", "powershell", "shell"}
_SKILL_FILE = re.compile(r"(?:^|[\\/])skills[\\/]([a-z0-9-]+)[\\/]SKILL\.md$")


@dataclass
class AgentRun:
    """Lo que una corrida dejó en su salida."""

    used: list[str] = field(default_factory=list)  # skills cargadas, en orden
    commands: list[str] = field(default_factory=list)  # comandos de shell, en orden
    subagents: list[str] = field(default_factory=list)  # subagentes lanzados
    answer: str = ""
    error: str | None = None
    visible: list[str] | None = None  # skills que el agente veía, para auditar el aislamiento
    usage: dict[str, Any] = field(default_factory=dict)

    def _skill(self, name: str | None) -> None:
        if name and name not in self.used:
            self.used.append(name)


def claude_tools(python: bool) -> str:
    return _CLAUDE_BASE + (_CLAUDE_PYTHON if python else "")


def claude_command(claude: str, prompt: str, *, python: bool, max_turns: int) -> list[str]:
    return evals.claude_command(claude, prompt, claude_tools(python), max_turns)


def copilot_launcher(found: str | None, env: Mapping[str, str]) -> list[str] | None:
    """Cómo lanzar Copilot CLI. En Windows, `copilot.cmd` pasaría el pedido por cmd.exe, que
    rompe los saltos de línea y las comillas: se llama a node con el loader de npm.

    `EXO_SCENARIOS_COPILOT` reemplaza la búsqueda (un ejecutable o un `.js`)."""
    override = env.get("EXO_SCENARIOS_COPILOT")
    target = override or found
    if not target:
        return None
    path = Path(target)
    if path.suffix.lower() == ".js":
        return [shutil.which("node") or "node", str(path)]
    if path.suffix.lower() in (".cmd", ".bat"):
        loader = path.parent / "node_modules" / "@github" / "copilot" / "npm-loader.js"
        if loader.is_file():
            local = path.parent / "node.exe"
            node = str(local) if local.is_file() else (shutil.which("node") or "node")
            return [node, str(loader)]
    return [str(path)]


def copilot_command(
    launcher: list[str],
    prompt: str,
    *,
    python: bool,
    usage: Path,
    logs: Path,
    model: str | None = None,
) -> list[str]:
    command = [
        *launcher,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--no-ask-user",
        "--disable-builtin-mcps",
        "--usage-output-file",
        str(usage),
        "--log-dir",
        str(logs),
    ]
    for rule in (*_COPILOT_ALLOW, *(_COPILOT_PYTHON if python else ())):
        command += ["--allow-tool", rule]
    for rule in _COPILOT_DENY:
        command += ["--deny-tool", rule]
    if model:
        command += ["--model", model]
    return command


def copilot_home(target: Path, env: Mapping[str, str], home: Path) -> Path:
    """Arma un `COPILOT_HOME` para la corrida: la cuenta con sesión y sin skills personales."""
    target.mkdir(parents=True, exist_ok=True)
    source = Path(env.get("COPILOT_HOME") or home / ".copilot")
    config = source / "config.json"
    if config.is_file():
        shutil.copyfile(config, target / "config.json")
    ignored = [str(home.joinpath(*rel.split("/"))) for rel in _PERSONAL_SKILLS]
    settings = {"ignoredSkillsLocations": ignored}
    (target / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return target


def copilot_env(base: dict[str, str], copilot_dir: Path, model: str | None) -> dict[str, str]:
    env = dict(base)
    env["COPILOT_HOME"] = str(copilot_dir)
    env["COPILOT_AUTO_UPDATE"] = "false"
    if not model:  # en auto, el perfil que prioriza la calidad
        env.setdefault("COPILOT_AUTO_TIER", "intelligence")
    return env


def _events(lines: Iterable[str]) -> Iterable[dict[str, Any]]:
    for raw in lines:
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if isinstance(event, dict):
            yield event


def _tool(run: AgentRun, name: Any, args: Any) -> None:
    if not isinstance(args, dict):
        return
    if name in ("Skill", "skill"):
        value = args.get("skill") or args.get("command") or args.get("name")
        run._skill(str(value).split(":")[-1].lstrip("/") if value else None)
    elif name in ("Read", "view", "read"):
        match = _SKILL_FILE.search(str(args.get("file_path") or args.get("path") or ""))
        run._skill(match.group(1) if match else None)
    elif name in _SHELL_TOOLS and args.get("command"):
        run.commands.append(str(args["command"]))
    elif name in ("Task", "Agent", "task"):
        kind = args.get("subagent_type") or args.get("agent_type") or args.get("agent") or "?"
        run.subagents.append(str(kind))


def parse_claude(lines: Iterable[str]) -> AgentRun:
    """`claude -p --output-format stream-json --verbose`."""
    run = AgentRun()
    for event in _events(lines):
        if event.get("type") == "system" and event.get("subtype") == "init":
            skills = event.get("skills")
            run.visible = [str(s) for s in skills] if isinstance(skills, list) else None
        elif event.get("type") == "result":
            run.answer = str(event.get("result") or "")
            if event.get("is_error"):
                run.error = str(event.get("terminal_reason") or event.get("subtype") or "error")
            run.usage = {
                "turns": event.get("num_turns"),
                "cost_usd": event.get("total_cost_usd"),
                "duration_ms": event.get("duration_ms"),
            }
        message = event.get("message")
        blocks = message.get("content") if isinstance(message, dict) else None
        for block in blocks if isinstance(blocks, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                _tool(run, block.get("name"), block.get("input"))
    return run


def parse_copilot(lines: Iterable[str]) -> AgentRun:
    """`copilot -p --output-format json`: un evento por línea (`type` y `data`)."""
    run = AgentRun()
    for event in _events(lines):
        kind, data = event.get("type"), event.get("data")
        data = data if isinstance(data, dict) else {}
        if kind == "session.skills_loaded":
            skills = data.get("skills")
            if isinstance(skills, list):
                run.visible = [
                    f"{s.get('name')} ({s.get('source')})" for s in skills if isinstance(s, dict)
                ]
        elif kind == "tool.execution_start":
            _tool(run, data.get("toolName"), data.get("arguments"))
        elif kind == "assistant.message" and str(data.get("content") or "").strip():
            run.answer = str(data["content"])
        elif kind == "session.error":
            run.error = str(data.get("message") or data.get("errorType") or "session error")
        elif kind == "result":
            code = event.get("exitCode")
            if code not in (0, None):
                run.error = run.error or f"exit code {code}"
            usage = event.get("usage")
            run.usage = usage if isinstance(usage, dict) else {}
    return run


def read_usage(path: Path) -> dict[str, Any]:
    """El resumen de `--usage-output-file` de Copilot, si lo escribió."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    keys = ("totalPremiumRequestCost", "totalUserRequests", "totalNanoAiu", "totalApiDurationMs")
    found = {k: data[k] for k in keys if k in data}
    models = data.get("modelMetrics")
    if isinstance(models, dict):
        found["models"] = sorted(models)
    return found


def home_dir(env: Mapping[str, str]) -> Path:
    raw = env.get("USERPROFILE") if os.name == "nt" else env.get("HOME")
    return Path(raw) if raw else Path.home()
