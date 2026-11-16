"""`exo discover ...` y la tool `discovery_status` (F6, ADR-0015, ADR-0005)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from _git import init_repo
from exo import _meta
from exo.cli import main
from exo.discovery import store, units
from exo.tools import registry

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    tree = {
        "pyproject.toml": "[project]\nname = 'app'\ndependencies = ['fastapi']\n",
        "src/app/__init__.py": "",
        "src/app/auth.py": "def login(user):\n    return user\n",
        "src/app/billing/__init__.py": "",
        "src/app/billing/totals.py": "from app.auth import login\n\n\ndef total(lines):\n    return sum(lines)\n",
    }
    for rel, text in tree.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    if shutil.which("git"):
        init_repo(root)
    return root


def _json(capsys: pytest.CaptureFixture[str], argv: list[str], code: int = 0) -> dict:
    assert main(argv) == code
    return json.loads(capsys.readouterr().out)


def _doc(unit_id: str, claim: str) -> str:
    sections = "\n".join(f"## {name}\n\nNone.\n" for name in units.SECTIONS)
    text = f"# Unit: {unit_id}\n\n{sections}"
    return text.replace("## Responsibilities\n\nNone.", f"## Responsibilities\n\n- {claim}", 1)


def test_el_recorrido_completo_por_cli(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = ["--project", str(repo), "--json"]
    data = _json(capsys, ["discover", "inventory", *p])
    assert "fastapi" in data["frameworks"]
    data = _json(capsys, ["discover", "structure", *p])
    assert data["modules"] == 2 and data["edges"] == 1
    data = _json(capsys, ["discover", "plan", "--depth", "standard", *p])
    assert [u["id"] for u in data["units"]] == ["src-app", "src-app-billing"]
    status = _json(capsys, ["discover", "status", *p])
    assert status["units"] == {"pending": 2, "done": 0, "stale": 0, "skipped": 0}
    nxt = _json(capsys, ["discover", "next", "--count", "2", *p])
    assert [u["id"] for u in nxt["units"]] == ["src-app", "src-app-billing"]
    doc = store.root(repo) / units.unit_doc("src-app")
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        _doc("src-app", "Login returns the user. [Code] src/app/auth.py:1-2"), encoding="utf-8"
    )
    data = _json(capsys, ["discover", "done", "src-app", *p])
    assert data["id"] == "src-app"
    status = _json(capsys, ["discover", "status", *p])
    assert status["units"] == {"pending": 1, "done": 1, "stale": 0, "skipped": 0}
    assert status["outside_changes"] == [] or status["outside_changes"] is None


def test_done_informa_cada_error_y_sale_con_1(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = ["--project", str(repo)]
    for step in ("inventory", "structure", "plan"):
        assert main(["discover", step, *p]) == 0
    capsys.readouterr()
    doc = store.root(repo) / units.unit_doc("src-app")
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(_doc("src-app", "No evidence here."), encoding="utf-8")
    assert main(["discover", "done", "src-app", *p]) == 1
    err = capsys.readouterr().err
    assert "without evidence" in err


def test_plan_sin_replan_y_audit_desde_archivo(
    repo: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    p = ["--project", str(repo)]
    for step in ("inventory", "structure", "plan"):
        assert main(["discover", step, *p]) == 0
    doc = store.root(repo) / units.unit_doc("src-app")
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(_doc("src-app", "Login. [Code] src/app/auth.py:1"), encoding="utf-8")
    assert main(["discover", "done", "src-app", *p]) == 0
    capsys.readouterr()
    assert main(["discover", "plan", "--depth", "deep", *p]) == 1
    assert "--replan" in capsys.readouterr().err
    assert main(["discover", "plan", "--depth", "deep", "--replan", *p]) == 0
    capsys.readouterr()
    assert main(["discover", "sample", *p]) == 1
    assert "no as-is specs" in capsys.readouterr().err
    results = tmp_path / "results.json"
    results.write_text('{"results": []}', encoding="utf-8")
    assert main(["discover", "audit", f"@{results}", *p]) == 1


def test_la_tool_discovery_status_es_de_solo_lectura_y_tiene_cli(repo: Path) -> None:
    tool = registry.get("discovery_status")
    assert tool is not None and tool.cli == ("discover", "status")
    result = registry.call("discovery_status", {}, registry.Context(repo))
    assert result["units"] is None
    assert not (repo / _meta.PROJECT_DIR / store.FOLDER).exists()
