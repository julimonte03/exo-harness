"""adapters/detect: señales por agente (tests tabulares, sin depender de la máquina)."""

from __future__ import annotations

from pathlib import Path

import pytest

from exo.adapters import detect
from exo.adapters.detect import SIGNALS, preselect


def _none(name: str) -> None:
    return None


def _detect(project: Path, env: dict[str, str] | None = None, exes: set[str] | None = None):
    exes = exes or set()
    return detect.detect(project, env or {}, lambda name: f"/bin/{name}" if name in exes else None)


@pytest.mark.parametrize(
    ("env", "agent"),
    [
        ({"CLAUDECODE": "1"}, "claude-code"),
        ({"CLAUDE_CODE_ENTRYPOINT": "claude-vscode"}, "claude-code"),
        ({"AI_AGENT": "claude-code_2-1-312_agent"}, "claude-code"),
        ({"COPILOT_CLI": "1"}, "copilot"),
        ({"AI_AGENT": "github_copilot_vscode_agent"}, "copilot"),
        ({"CURSOR_AGENT": "1"}, "cursor"),
        ({"CODEX_THREAD_ID": "abc"}, "codex"),
        ({"GEMINI_CLI": "1"}, "gemini"),
        ({"AI_AGENT": "devin_3000_agent"}, "devin"),
    ],
)
def test_variables_de_entorno(tmp_path: Path, env: dict[str, str], agent: str) -> None:
    found = _detect(tmp_path, env)
    assert [(d.agent, d.score) for d in found] == [(agent, detect.ENV_SCORE)]
    assert found[0].strong


@pytest.mark.parametrize(
    ("rel", "agent"),
    [
        ("CLAUDE.md", "claude-code"),
        (".claude/settings.json", "claude-code"),
        (".github/copilot-instructions.md", "copilot"),
        (".github/agents/x.agent.md", "copilot"),
        (".vscode/mcp.json", "copilot"),
        (".cursor/rules/a.mdc", "cursor"),
        (".codex/config.toml", "codex"),
        ("GEMINI.md", "gemini"),
        (".windsurf/rules/a.md", "devin"),
        (".devin/skills/x/SKILL.md", "devin"),
    ],
)
def test_archivos_del_repo(tmp_path: Path, rel: str, agent: str) -> None:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    found = _detect(tmp_path)
    assert [(d.agent, d.score) for d in found] == [(agent, detect.FILE_SCORE)]


@pytest.mark.parametrize(
    ("exe", "agent"),
    [("claude", "claude-code"), ("copilot", "copilot"), ("cursor", "cursor"), ("codex", "codex"), ("gemini", "gemini"), ("agy", "gemini"), ("windsurf", "devin")],
)
def test_ejecutables_son_senal_debil(tmp_path: Path, exe: str, agent: str) -> None:
    found = _detect(tmp_path, exes={exe})
    assert [(d.agent, d.score, d.strong) for d in found] == [(agent, detect.EXE_SCORE, False)]
    assert preselect(found) == []


def test_code_no_cuenta_como_copilot(tmp_path: Path) -> None:
    assert _detect(tmp_path, exes={"code"}) == []


def test_sin_senales(tmp_path: Path) -> None:
    assert _detect(tmp_path) == []
    assert preselect([]) == []


def test_puntajes_se_suman_por_categoria_y_ordenan(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("x", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".cursor").mkdir()
    found = _detect(tmp_path, {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli"}, {"claude", "codex"})
    assert [(d.agent, d.score) for d in found] == [("claude-code", 6), ("cursor", 2), ("codex", 1)]
    assert "variable CLAUDECODE" in found[0].evidence
    assert "archivo .claude" in found[0].evidence
    assert preselect(found) == ["claude-code", "cursor"]


def test_preselect_respeta_el_orden_conocido(tmp_path: Path) -> None:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("x", encoding="utf-8")
    found = _detect(tmp_path, {"CURSOR_AGENT": "1"}, {"copilot"})
    # Empate en 3 (variable vs archivo + ejecutable): desempata el orden conocido.
    assert [(d.agent, d.score) for d in found] == [("copilot", 3), ("cursor", 3)]
    assert preselect(found) == ["copilot", "cursor"]


def test_usa_el_entorno_real_por_defecto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for signals in SIGNALS.values():
        for name in signals.env:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_AGENT", "github_copilot_cli")
    monkeypatch.setattr(detect.shutil, "which", _none)
    assert [d.agent for d in detect.detect(tmp_path)] == ["copilot"]


def test_todos_los_agentes_conocidos_tienen_senales() -> None:
    from exo.adapters import ADAPTERS, GENERIC_ONLY

    assert set(SIGNALS) == {*ADAPTERS, *GENERIC_ONLY}
