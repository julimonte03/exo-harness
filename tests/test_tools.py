"""tools: validadores S2, registro compartido y paridad CLI ↔ MCP (ADR-0005)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from exo.cli import build_parser, main
from exo.tools import registry
from exo.tools.validation import (
    InputError,
    check_arguments,
    validate_change_name,
    validate_cwd,
    validate_skill_name,
)


def _project(tmp_path: Path) -> Path:
    change = tmp_path / "specs" / "PROJ-1-login"
    change.mkdir(parents=True)
    (change / "proposal.md").write_text("x\n", encoding="utf-8")
    (change / "ai-usage-record.json").write_text(json.dumps({"jira_key": "PROJ-1"}), encoding="utf-8")
    (change / "followups.json").write_text(
        json.dumps({"followups": [{"id": "J1-1", "judge": "j", "rule": "r", "summary": "s"}]}),
        encoding="utf-8",
    )
    return tmp_path


# -- validadores S2 -----------------------------------------------------------


@pytest.mark.parametrize("ok", ["sdd-new", "a", "hello-exo", "a1-b2"])
def test_skill_name_valido(ok: str) -> None:
    assert validate_skill_name(ok) == ok


@pytest.mark.parametrize("bad", ["../x", "Sdd", "a--b", "-a", "a/b", "", "a" * 65, 3, None])
def test_skill_name_invalido(bad: object) -> None:
    with pytest.raises(InputError):
        validate_skill_name(bad)


@pytest.mark.parametrize("ok", ["login", "PROJ-123-login-flow", "AB1-9-x"])
def test_change_name_valido(ok: str) -> None:
    assert validate_change_name(ok) == ok


@pytest.mark.parametrize(
    "bad",
    ["../x", "a/b", "a\\b", "..", "PROJ-123", "Login", "a b", "a" * 101, "", None, ["x"]],
)
def test_change_name_invalido(bad: object) -> None:
    with pytest.raises(InputError):
        validate_change_name(bad)


def test_validate_cwd(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    assert validate_cwd("sub", root=tmp_path) == (tmp_path / "sub").resolve()
    assert validate_cwd(str(tmp_path / "sub"), root=tmp_path) == (tmp_path / "sub").resolve()
    assert validate_cwd(str(tmp_path)) == tmp_path.resolve()
    for bad in ("..", "../..", str(tmp_path.parent), "no-existe", "", "a\x00b", 7):
        with pytest.raises(InputError):
            validate_cwd(bad, root=tmp_path)


def test_check_arguments() -> None:
    schema = registry.get("get_followups").input_schema
    assert check_arguments(schema, {"change_name": "x"}) == {"change_name": "x"}
    for bad, fragment in (
        ([], "object"),
        ({}, "missing"),
        ({"change_name": 1}, "string"),
        ({"change_name": "x", "status": "raro"}, "one of"),
        ({"change_name": "x", "otro": 1}, "unknown"),
    ):
        with pytest.raises(InputError, match=fragment):
            check_arguments(schema, bad)
    with pytest.raises(InputError, match="true or false"):
        check_arguments(registry.get("list_changes").input_schema, {"include_archived": "si"})
    assert check_arguments(registry.get("list_changes").input_schema, None) == {}


# -- registro -----------------------------------------------------------------


def test_tools_con_schema() -> None:
    names = [t.name for t in registry.TOOLS if not t.name.startswith("mem_")]
    assert names == [
        "skills_list",
        "skill_info",
        "skills_diff",
        "list_changes",
        "get_change_state",
        "get_followups",
        "get_ai_usage_record",
    ]
    for tool in registry.TOOLS:
        described = tool.describe()
        assert described["inputSchema"]["type"] == "object"
        assert described["inputSchema"]["additionalProperties"] is False
        assert described["description"]


def _subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def test_paridad_cli_mcp() -> None:
    for tool in registry.TOOLS:
        level = _subcommands(build_parser())
        for part in tool.cli:
            assert part in level, (tool.name, tool.cli)
            parser = level[part]
            level = _subcommands(parser)
        assert level == {}, f"{tool.name}: {tool.cli} no llega a un subcomando final"


def test_call_desconocida() -> None:
    with pytest.raises(KeyError):
        registry.call("no_existe", {}, registry.Context(Path(".")))


def test_tools_de_skills(tmp_path: Path) -> None:
    ctx = registry.Context(tmp_path)
    listed = registry.call("skills_list", {}, ctx)["skills"]
    assert "hello-exo" in [s["name"] for s in listed]
    assert registry.call("skills_list", {"pack": "core"}, ctx)["skills"]
    with pytest.raises(InputError, match="pack"):
        registry.call("skills_list", {"pack": "fantasma"}, ctx)
    info = registry.call("skill_info", {"name": "hello-exo"}, ctx)
    assert info["pack"] == "core"
    assert "SKILL.md" in info["files"]
    with pytest.raises(InputError, match="not found"):
        registry.call("skill_info", {"name": "no-hay"}, ctx)
    with pytest.raises(InputError):
        registry.call("skill_info", {"name": "../x"}, ctx)


def test_skills_diff(tmp_path: Path) -> None:
    ctx = registry.Context(tmp_path)
    assert "hello-exo" in registry.call("skills_diff", {}, ctx)["added"]
    target = tmp_path / ".agents" / "skills"
    installed = target / "hello-exo"
    installed.mkdir(parents=True)
    source = registry.call("skill_info", {"name": "hello-exo"}, ctx)
    from exo import content

    skill_md = (content.content_root() / source["path"] / "SKILL.md").read_bytes()
    (installed / "SKILL.md").write_bytes(skill_md)
    assert "hello-exo" in registry.call("skills_diff", {}, ctx)["unchanged"]
    (installed / "SKILL.md").write_bytes(skill_md + b"\nextra\n")
    changed = registry.call("skills_diff", {}, ctx)["changed"]
    assert changed == [{"name": "hello-exo", "files": ["SKILL.md"]}]
    (target / "propia").mkdir()
    (target / "propia" / "SKILL.md").write_text("---\nname: propia\ndescription: x\n---\n", encoding="utf-8")
    assert registry.call("skills_diff", {}, ctx)["removed"] == ["propia"]
    with pytest.raises(InputError):
        registry.call("skills_diff", {"target": "../fuera"}, ctx)


def test_tools_de_observabilidad(tmp_path: Path) -> None:
    ctx = registry.Context(_project(tmp_path))
    assert [c["name"] for c in registry.call("list_changes", {}, ctx)["changes"]] == ["PROJ-1-login"]
    state = registry.call("get_change_state", {"change_name": "PROJ-1-login"}, ctx)
    assert state["ticket_key"] == "PROJ-1"
    followups = registry.call("get_followups", {"change_name": "PROJ-1-login", "status": "all"}, ctx)
    assert [f["id"] for f in followups["followups"]] == ["J1-1"]
    record = registry.call("get_ai_usage_record", {"change_name": "PROJ-1-login"}, ctx)
    assert record["record"] == {"jira_key": "PROJ-1"}
    with pytest.raises(InputError, match="otro"):
        registry.call("get_change_state", {"change_name": "otro"}, ctx)
    with pytest.raises(InputError, match="outside"):
        registry.call("list_changes", {"cwd": ".."}, ctx)


# -- CLI ----------------------------------------------------------------------


def test_cli_skills_y_change(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = str(_project(tmp_path))
    assert main(["skills", "list"]) == 0
    assert "hello-exo" in capsys.readouterr().out
    assert main(["skills", "info", "hello-exo", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["name"] == "hello-exo"
    assert main(["skills", "diff", "--project", project]) == 0
    assert "added\thello-exo" in capsys.readouterr().out
    assert main(["change", "list", "--project", project]) == 0
    assert "PROJ-1-login\tpropose\tactive" in capsys.readouterr().out
    assert main(["change", "status", "PROJ-1-login", "--project", project]) == 0
    assert "ticket_key: PROJ-1" in capsys.readouterr().out
    assert main(["change", "followups", "PROJ-1-login", "--status", "all", "--project", project]) == 0
    assert "J1-1\topen" in capsys.readouterr().out
    assert main(["change", "ai-usage", "PROJ-1-login", "--project", project, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ticket_key"] == "PROJ-1"
    assert main(["change", "status", "../x", "--project", project]) == 1
    assert "invalid" in capsys.readouterr().err
    assert main(["change", "list", "--no-archived", "--project", str(tmp_path / "vacio")]) == 0
    assert "no changes" in capsys.readouterr().out


def test_cli_grupos_sin_accion(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["skills"]) == 0
    assert main(["change"]) == 0
    assert "status" in capsys.readouterr().out
