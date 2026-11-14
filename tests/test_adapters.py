"""Adaptadores y adopción con golden tests (criterios 2, 3 y 4 de F2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _projects import FIXTURES, tree
from exo import _meta, adapters, content
from exo.adapters.base import AGENTS_SKILLS, CLAUDE_SKILLS, Context, mcp_entry, skills_dirs
from exo.core import config, filemerge, lock, snapshots
from exo.installer import project
from exo.installer.bundle import build_bundle
from exo.installer.ops import MergeBlock, MergeKey, MergeListItem
from exo.installer.project import ProjectError

CASES = [
    ("generic__vacio", "vacio", [], False),
    ("claude-copilot__vacio", "vacio", ["claude-code", "copilot"], False),
    ("claude-copilot__agents-humano", "agents-humano", ["claude-code", "copilot"], False),
    ("claude-copilot__claude-existente", "claude-existente", ["claude-code", "copilot"], False),
    ("claude-copilot__crlf", "crlf", ["claude-code", "copilot"], False),
    ("claude-copilot-mcp__mcp-jsonc", "mcp-jsonc", ["claude-code", "copilot"], True),
]


@pytest.mark.parametrize(("case", "fixture", "agents", "mcp"), CASES, ids=[c[0] for c in CASES])
def test_golden(tmp_path: Path, golden, case: str, fixture: str, agents: list[str], mcp: bool) -> None:
    root = tmp_path / "p"
    FIXTURES[fixture](root)
    result = project.sync(root, agents=agents, mcp=mcp)
    assert result.engine.conflicts == []
    golden(case, tree(root))


@pytest.mark.parametrize("fixture", sorted(FIXTURES))
def test_criterio_3_segunda_vez_sin_cambios(tmp_path: Path, fixture: str) -> None:
    root = tmp_path / "p"
    FIXTURES[fixture](root)
    project.sync(root, agents=["claude-code", "copilot"])
    snaps = snapshots.list_snapshots(root)
    before = tree(root)
    again = project.sync(root)
    assert again.engine.changed is False
    assert again.config_written is False
    assert snapshots.list_snapshots(root) == snaps
    assert tree(root) == before


def test_criterio_4_contenido_del_humano_intacto(tmp_path: Path) -> None:
    root = tmp_path / "p"
    FIXTURES["crlf"](root)
    original = tree(root)
    project.sync(root, agents=["claude-code", "copilot"])
    for name in ("AGENTS.md", "CLAUDE.md", ".gitignore"):
        text = (root / name).read_bytes().decode()
        style = filemerge.style_for(Path(name))
        restored = filemerge.remove_text(text, "core", style=style)
        assert restored.encode() == original[name], name
    begin = f"<!-- BEGIN:{_meta.BLOCK_PREFIX}:core -->"
    assert (root / "CLAUDE.md").read_bytes().startswith(f"{begin}\r\n@AGENTS.md\r\n".encode())


def test_claude_md_solo_si_existe_o_se_pide(tmp_path: Path) -> None:
    root = tmp_path / "p"
    root.mkdir()
    project.sync(root, agents=["claude-code"])
    assert not (root / "CLAUDE.md").exists()
    other = tmp_path / "q"
    other.mkdir()
    project.sync(other, agents=["claude-code"], claude_md=True)
    begin = f"<!-- BEGIN:{_meta.BLOCK_PREFIX}:core -->"
    assert (other / "CLAUDE.md").read_text(encoding="utf-8").startswith(f"{begin}\n@AGENTS.md\n")
    project.sync(other)
    assert (other / "CLAUDE.md").exists()


def test_permiso_para_el_cli(tmp_path: Path) -> None:
    root = tmp_path / "p"
    root.mkdir()
    project.sync(root, agents=["claude-code"])
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    expected = [f"Bash({_meta.NAME}:*)", f"PowerShell({_meta.NAME}:*)"]
    assert settings == {"permissions": {"allow": expected}}


def test_solo_copilot_usa_claude_y_no_pide_permisos(tmp_path: Path) -> None:
    root = tmp_path / "p"
    root.mkdir()
    project.sync(root, agents=["copilot"])
    assert (root / CLAUDE_SKILLS / "hello-exo" / "SKILL.md").is_file()
    assert (root / ".claude" / "agents" / "sdd-explorer.md").is_file()
    assert not (root / ".claude" / "settings.json").exists()
    assert not (root / AGENTS_SKILLS).exists()


def test_dueno_compartido_en_el_lock(tmp_path: Path) -> None:
    root = tmp_path / "p"
    root.mkdir()
    project.sync(root, agents=["claude-code", "copilot"])
    owners = {e.path: e.owner for e in lock.read(root).files}
    assert owners[f"{CLAUDE_SKILLS}/hello-exo/SKILL.md"] == "adapter:claude-code,copilot"
    assert owners[".claude/settings.json"] == "adapter:claude-code"
    assert owners["AGENTS.md"] == "engine"


def test_mcp_opcional(tmp_path: Path) -> None:
    root = tmp_path / "p"
    root.mkdir()
    project.sync(root, agents=["claude-code", "copilot"])
    assert not (root / ".mcp.json").exists()
    project.sync(root, mcp=True)
    servers = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    expected = {"type": "stdio", "command": _meta.NAME, "args": ["mcp"], "tools": ["*"]}
    assert servers[_meta.NAME] == expected
    assert config.load(root).config["mcp"]["enabled"] is True
    project.sync(root, mcp=False)
    assert not (root / ".mcp.json").exists()


def test_mcp_entry() -> None:
    assert "tools" not in mcp_entry(("claude-code",))
    assert mcp_entry(("claude-code", "copilot"))["tools"] == ["*"]


@pytest.mark.parametrize(
    ("targets", "expected"),
    [
        (("claude-code",), [CLAUDE_SKILLS]),
        (("copilot",), [CLAUDE_SKILLS]),
        (("claude-code", "copilot"), [CLAUDE_SKILLS]),
        (("claude-code", "cursor"), [CLAUDE_SKILLS, AGENTS_SKILLS]),
        (("generic",), [AGENTS_SKILLS]),
        (("codex",), [AGENTS_SKILLS]),
        ((), [AGENTS_SKILLS]),
    ],
)
def test_skills_dirs_adr_0007(targets: tuple[str, ...], expected: list[str]) -> None:
    assert skills_dirs(targets) == expected


def test_normalize_agents() -> None:
    assert project.normalize_agents([]) == ("generic",)
    assert project.normalize_agents(["copilot", "claude-code", "copilot"]) == ("copilot", "claude-code")
    assert project.normalize_agents(["generic", "cursor"]) == ("cursor",)
    with pytest.raises(ProjectError, match="unknown agent"):
        project.normalize_agents(["windsurf"])


def test_pack_inexistente_es_error_de_proyecto(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match="does not exist"):
        project.sync(tmp_path, packs=["fantasma"])


def test_nota_para_gemini(tmp_path: Path) -> None:
    result = project.sync(tmp_path, agents=["gemini"])
    assert any("context" in note and "GEMINI.md" in note for note in result.notes)
    assert (tmp_path / AGENTS_SKILLS / "hello-exo" / "SKILL.md").is_file()


def test_adaptadores_son_puros(tmp_path: Path) -> None:
    root = tmp_path / "p"
    root.mkdir()
    bundle = build_bundle(content.content_root(), ["core", "sdd"])
    ctx = Context(root, bundle, ("claude-code", "copilot"), config.defaults())
    ops = adapters.plan_all(ctx)
    assert list(root.iterdir()) == []
    kinds = {type(op) for op in ops}
    assert {MergeBlock, MergeListItem} <= kinds
    assert MergeKey not in kinds
