"""Las partes puras del runner de escenarios de F8 (`tests/_agents.py`): sin agentes reales."""

from __future__ import annotations

import json
from pathlib import Path

import _agents as agents


def _lines(*events: dict) -> list[str]:
    return [json.dumps(e) for e in events]


def test_comando_de_copilot_con_permisos_y_sin_python_por_defecto(tmp_path: Path) -> None:
    command = agents.copilot_command(
        ["copilot"], "hola", python=False, usage=tmp_path / "u.json", logs=tmp_path / "logs"
    )
    assert command[:2] == ["copilot", "-p"]
    assert command[2] == "hola" + agents.COPILOT_NOTE and "git --no-pager" in command[2]
    assert {"--no-ask-user", "--disable-builtin-mcps"} <= set(command)
    allowed = [command[i + 1] for i, a in enumerate(command) if a == "--allow-tool"]
    denied = [command[i + 1] for i, a in enumerate(command) if a == "--deny-tool"]
    assert allowed == ["shell(exo:*)", "shell(git:*)", "write"]
    assert denied == ["shell(git push)"]
    assert "--model" not in command
    with_python = agents.copilot_command(
        ["copilot"], "x", python=True, usage=tmp_path / "u", logs=tmp_path / "l", model="m-1"
    )
    assert "shell(python:*)" in with_python and with_python[-2:] == ["--model", "m-1"]


def test_lanzador_de_copilot(tmp_path: Path) -> None:
    npm = tmp_path / "npm"
    loader = npm / "node_modules" / "@github" / "copilot" / "npm-loader.js"
    loader.parent.mkdir(parents=True)
    loader.write_text("", encoding="utf-8")
    (npm / "copilot.cmd").write_text("", encoding="utf-8")
    launcher = agents.copilot_launcher(str(npm / "copilot.cmd"), {})
    assert launcher is not None and launcher[-1] == str(loader)
    assert agents.copilot_launcher("/usr/bin/copilot", {}) == [str(Path("/usr/bin/copilot"))]
    assert agents.copilot_launcher(None, {}) is None
    custom = agents.copilot_launcher(None, {"EXO_SCENARIOS_COPILOT": str(tmp_path / "x.js")})
    assert custom is not None and custom[-1] == str(tmp_path / "x.js")


def test_copilot_home_aislado(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".copilot").mkdir(parents=True)
    (home / ".copilot" / "config.json").write_text('{"loggedInUsers": []}', encoding="utf-8")
    target = agents.copilot_home(tmp_path / "run" / "copilot", {}, home)
    assert (target / "config.json").read_text(encoding="utf-8") == '{"loggedInUsers": []}'
    settings = json.loads((target / "settings.json").read_text(encoding="utf-8"))
    assert settings["ignoredSkillsLocations"] == [
        str(home / ".agents" / "skills"),
        str(home / ".claude" / "skills"),
        str(home / ".copilot" / "skills"),
    ]
    env = agents.copilot_env({"PATH": "x"}, target, model=None)
    assert env["COPILOT_HOME"] == str(target) and env["COPILOT_AUTO_TIER"] == "intelligence"
    assert env["GIT_PAGER"] == "cat"
    assert "COPILOT_AUTO_TIER" not in agents.copilot_env({}, target, model="m-1")
    # Sin config.json (nunca inició sesión): igual arma el settings.
    empty = agents.copilot_home(tmp_path / "otro", {"COPILOT_HOME": str(tmp_path / "nada")}, home)
    assert not (empty / "config.json").exists() and (empty / "settings.json").is_file()


def test_lectura_de_copilot() -> None:
    lines = _lines(
        {"type": "session.skills_loaded", "data": {"skills": [{"name": "sdd-new", "source": "project"}]}},
        {"type": "tool.execution_start", "data": {"toolName": "skill", "arguments": {"skill": "sdd-new"}}},
        {
            "type": "tool.execution_start",
            "data": {"toolName": "powershell", "arguments": {"command": "exo change status --json"}},
        },
        {
            "type": "tool.execution_start",
            "data": {"toolName": "view", "arguments": {"path": "C:\\p\\.claude\\skills\\risk-tiering\\SKILL.md"}},
        },
        {"type": "tool.execution_start", "data": {"toolName": "task", "arguments": {"agent_type": "sdd-verifier"}}},
        {"type": "assistant.message", "data": {"content": "", "toolRequests": [{}]}},
        {"type": "assistant.message", "data": {"content": "Done: Tier 1."}},
        {"type": "result", "exitCode": 0, "usage": {"premiumRequests": 1}},
        "no es json",  # se ignora
    )
    run = agents.parse_copilot(lines)
    assert run.visible == ["sdd-new (project)"]
    assert run.used == ["sdd-new", "risk-tiering"]
    assert run.commands == ["exo change status --json"]
    assert run.subagents == ["sdd-verifier"]
    assert run.answer == "Done: Tier 1."
    assert run.error is None and run.usage == {"premiumRequests": 1}
    failed = agents.parse_copilot(_lines({"type": "result", "exitCode": 1}))
    assert failed.error == "exit code 1"


def test_lectura_de_claude() -> None:
    lines = _lines(
        {"type": "system", "subtype": "init", "skills": ["sdd-new"]},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "sdd-new"}},
                    {"type": "tool_use", "name": "Bash", "input": {"command": "exo check --base main"}},
                    {"type": "tool_use", "name": "Task", "input": {"subagent_type": "sdd-implementer"}},
                ]
            },
        },
        {"type": "result", "result": "Archived.", "num_turns": 12, "total_cost_usd": 1.5},
    )
    run = agents.parse_claude(lines)
    assert run.visible == ["sdd-new"]
    assert run.used == ["sdd-new"]
    assert run.commands == ["exo check --base main"]
    assert run.subagents == ["sdd-implementer"]
    assert run.answer == "Archived." and run.usage["turns"] == 12
    errored = agents.parse_claude(
        _lines({"type": "result", "is_error": True, "terminal_reason": "api_error"})
    )
    assert errored.error == "api_error"


def test_resumen_de_uso_de_copilot(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    assert agents.read_usage(path) == {}
    path.write_text(
        json.dumps(
            {"totalPremiumRequestCost": 1, "totalUserRequests": 1, "modelMetrics": {"m-2": {}, "m-1": {}}}
        ),
        encoding="utf-8",
    )
    assert agents.read_usage(path) == {
        "totalPremiumRequestCost": 1,
        "totalUserRequests": 1,
        "models": ["m-1", "m-2"],
    }
