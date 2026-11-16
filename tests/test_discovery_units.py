"""R2 a R5: plan, unidades, muestra, cobertura y actualización (F6, ADR-0015).

Criterios 5 (solo lectura), 6 (reanudable) y 7 (incremental).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from _git import git, init_repo
from exo.discovery import coverage, inventory, pipeline, planner, sampler, store, units

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
AWS = "AKIA" + "Q" * 16


def _lines(n: int, prefix: str) -> str:
    return "".join(f"{prefix}_{i} = {i}\n" for i in range(n))


TREE = {
    "src/auth/__init__.py": "",
    "src/auth/login.py": "from auth.tokens import issue\n\n\ndef login(user):\n    return issue(user)\n",
    "src/auth/tokens.py": "def issue(user):\n    return 'token'\n",
    "src/billing/__init__.py": "",
    "src/billing/a_totals.py": _lines(450, "total"),
    "src/billing/b_taxes.py": _lines(450, "tax"),
    "src/billing/c_rounding.py": "from util.strings import clean\n" + _lines(10, "r"),
    "src/util/__init__.py": "",
    "src/util/strings.py": f"KEY = '{AWS}'\n\ndef clean(s):\n    return s.strip()\n",
    "tests/test_login.py": "from auth.login import login\n\n\ndef test_login():\n    assert login('a')\n",
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel, text in TREE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    if shutil.which("git"):
        init_repo(root)
    inventory.write(root)
    pipeline.structure(root)
    return root


def _ids(plan: dict) -> list[str]:
    return [u["id"] for u in plan["units"]]


def test_plan_ids_estables_partidos_entre_archivos_y_prioridad(repo: Path) -> None:
    plan, wrote = planner.write(repo)
    assert wrote is True
    assert _ids(plan) == ["src-auth", "src-billing-1", "src-billing-2", "src-util"]
    by_id = {u["id"]: u for u in plan["units"]}
    assert by_id["src-billing-1"]["files"] == ["src/billing/__init__.py", "src/billing/a_totals.py"]
    assert by_id["src-billing-2"]["files"] == [
        "src/billing/b_taxes.py",
        "src/billing/c_rounding.py",
    ]
    assert by_id["src-auth"]["criticality"] == ["auth", "login", "token"]
    assert by_id["src-auth"]["tests"] == ["tests/test_login.py"]
    assert all(u["detail"] == "full" for u in plan["units"])
    again, wrote = planner.write(repo)
    assert again == plan and wrote is False
    quick = planner.build(repo, "quick")
    expected = max(1, round(len(quick["units"]) * planner.QUICK_SHARE))
    assert [u["detail"] for u in quick["units"]].count("full") == expected
    assert quick["units"][0]["detail"] == "full" and quick["units"][0]["id"] == "src-auth"


def test_ids_con_colisiones_y_nombres_reservados() -> None:
    ids = planner.unit_ids(["src/a-b", "src/a/b", "con", "src/" + "x" * 80])
    assert ids["src/a-b"] != ids["src/a/b"]
    assert ids["src/a-b"].startswith("src-a-b-") and len(ids["src/a-b"]) == len("src-a-b-") + 6
    assert ids["con"].startswith("con-")
    assert len(ids["src/" + "x" * 80]) <= planner.MAX_ID
    assert planner.unit_ids(["src/a-b", "src/a/b"]) == {k: ids[k] for k in ("src/a-b", "src/a/b")}


def _doc(unit_id: str, claim: str) -> str:
    body = "\n".join(
        [f"# Unit: {unit_id}", ""]
        + [line for name in units.SECTIONS for line in (f"## {name}", "", "None.", "")]
    )
    return body.replace("## Responsibilities\n\nNone.", f"## Responsibilities\n\n- {claim}", 1)


def _write_doc(repo: Path, unit_id: str, claim: str) -> None:
    path = store.root(repo) / units.unit_doc(unit_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_doc(unit_id, claim), encoding="utf-8")


def test_next_marca_secretos_y_done_valida(repo: Path) -> None:
    planner.write(repo)
    [first] = units.next_units(repo)
    assert first["id"] == "src-auth" and first["status"] == "pending"
    assert first["document"].endswith("units/src-auth.md")
    util = [u for u in units.next_units(repo, count=10) if u["id"] == "src-util"][0]
    assert util["flags"]["src/util/strings.py"]["secret_lines"] == [1]
    with pytest.raises(units.UnitError, match="does not exist"):
        units.done(repo, "src-auth")
    bad = [
        ("Logs users in.", "without evidence"),
        ("Logs users in. [Code] src/util/strings.py:1", "not a file of this unit"),
        ("Logs users in. [Code] src/auth/login.py:99", "out of range"),
        (f"Uses the key {AWS}. [Code] src/auth/login.py:1", "a secret"),
    ]
    for claim, fragment in bad:
        _write_doc(repo, "src-auth", claim)
        with pytest.raises(units.UnitError, match=fragment):
            units.done(repo, "src-auth")
    _write_doc(repo, "src-auth", "Login issues a token for the user. [Code] src/auth/login.py:4-5")
    record = units.done(repo, "src-auth")
    assert set(record["files"]) == {
        "src/auth/__init__.py",
        "src/auth/login.py",
        "src/auth/tokens.py",
    }
    assert record["tests"] == {"tests/test_login.py": record["tests"]["tests/test_login.py"]}
    assert record["counts"]["code"] == 1


def test_criterio_6_retomar_no_rehace_lo_cerrado(repo: Path) -> None:
    planner.write(repo)
    _write_doc(repo, "src-auth", "Login issues a token. [Code] src/auth/login.py:4-5")
    units.done(repo, "src-auth")
    # Se corta a mitad de R3: una unidad cerrada y otra a medio escribir, sin cerrar.
    _write_doc(repo, "src-billing-1", "Totals. [Code] src/billing/a_totals.py:1")
    nexts = [u["id"] for u in units.next_units(repo, count=10)]
    assert "src-auth" not in nexts and nexts[0] == "src-billing-1"
    with pytest.raises(planner.PlanError, match="replan"):
        planner.write(repo, "deep")
    planner.write(repo, "deep", replan=True)
    assert "src-auth" not in [u["id"] for u in units.next_units(repo, count=10)]


def _cap(repo: Path, name: str, cited: str) -> None:
    path = repo / "specs" / "capabilities" / name / "spec.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Capability: {name}\n\nStatus: as-is\nSource: exo discover\n\n## Purpose\n\n{name}.\n\n"
        f"## Requirements\n\n### CAP-{name}-FR-1: Main rule\n\nIt does the thing. [Code] {cited}\n\n"
        f"### CAP-{name}-FR-2: Second rule\n\nIt also does this. [Inferred: low]\n",
        encoding="utf-8",
    )


def _close_all(repo: Path) -> None:
    plan = planner.load(repo)
    for item in plan["units"]:
        _write_doc(repo, item["id"], f"Does its job. [Code] {item['files'][-1]}:1")
        units.done(repo, item["id"])


def test_criterio_7_update_marca_solo_lo_afectado(repo: Path) -> None:
    planner.write(repo)
    _close_all(repo)
    _cap(repo, "auth", "src/auth/login.py:4")
    _cap(repo, "strings", "src/util/strings.py:3")
    assert pipeline.update(repo)["stale_units"] == {}
    (repo / "src/auth/login.py").write_text(
        TREE["src/auth/login.py"] + "# changed\n", encoding="utf-8"
    )
    report = pipeline.update(repo)
    assert report["stale_units"] == {"src-auth": ["src/auth/login.py"]}
    assert report["stale_capabilities"] == ["auth"]
    (repo / "src/auth/extra.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "src/auth/extra.py")  # el inventario ve solo lo versionado
    assert "src/auth/extra.py" in pipeline.update(repo)["new_files"]


def test_muestra_veredictos_y_cobertura(repo: Path) -> None:
    planner.write(repo)
    _close_all(repo)
    _cap(repo, "auth", "src/auth/login.py:4")
    _cap(repo, "strings", "src/util/strings.py:3")
    data = sampler.sample(repo, n=3)
    assert data["population"] == 4 and len(data["items"]) == 3
    assert {i["capability"] for i in data["items"]} == {"auth", "strings"}
    assert sampler.sample(repo, n=3) == data  # misma semilla, misma muestra
    other = sampler.sample(repo, n=3, seed=7)
    assert other["seed"] == 7
    sampler.sample(repo, n=4)
    with pytest.raises(sampler.AuditError, match="not in the sample"):
        sampler.record(repo, {"results": [{"id": "CAP-x-FR-9", "verdict": "correct"}]})
    results = {
        "results": [
            {"id": "CAP-auth-FR-1", "verdict": "correct"},
            {"id": "CAP-auth-FR-2", "verdict": "correct"},
            {"id": "CAP-strings-FR-1", "verdict": "incorrect", "note": "it trims only the left"},
            {"id": "CAP-strings-FR-2", "verdict": "unverifiable"},
        ]
    }
    sampler.record(repo, results)
    report, _ = coverage.write(repo)
    rows = {r["capability"]: r for r in report["precision"]}
    assert rows["auth"]["precision"] == 1.0 and rows["auth"]["flags"] == []
    assert (
        rows["strings"]["precision"] == 0.0
        and "below threshold: extract again" in rows["strings"]["flags"]
    )
    assert report["modules"] == {"total": 3, "covered": 3}
    assert report["requirements"] == {"total": 4, "with_evidence": 2}
    text = (store.root(repo) / coverage.FILENAME).read_text(encoding="utf-8")
    assert "| auth | 2 | 0 | 0 | 100.0 % | - |" in text


@needs_git
def test_criterio_5_solo_escribe_en_las_rutas_permitidas(repo: Path) -> None:
    planner.write(repo)
    _close_all(repo)
    _cap(repo, "auth", "src/auth/login.py:4")
    sampler.sample(repo)
    coverage.write(repo)
    (repo / ".exo" / "context.md").write_text("# Context\n", encoding="utf-8")
    adr = repo / "docs" / "adr" / "0001-recovered-token-login.md"
    adr.parent.mkdir(parents=True)
    adr.write_text("# 1. Token login\n", encoding="utf-8")
    assert pipeline.outside_changes(repo) == []
    (repo / "src/auth/login.py").write_text("changed = True\n", encoding="utf-8")
    (repo / "docs" / "adr" / "0002-new-decision.md").write_text("# 2\n", encoding="utf-8")
    assert pipeline.outside_changes(repo) == ["docs/adr/0002-new-decision.md", "src/auth/login.py"]
    status = pipeline.status(repo)
    assert status["units"] == {"pending": 0, "done": 3, "stale": 1}  # login.py cambió
    assert json.loads((store.root(repo) / "plan.json").read_text(encoding="utf-8"))["schema"] == 1


def test_los_comentarios_de_la_plantilla_no_son_afirmaciones(repo: Path) -> None:
    planner.write(repo)
    text = _doc("src-auth", "Login issues a token. [Code] src/auth/login.py:4-5")
    text = text.replace("## Entities\n", "## Entities\n\n<!--\n- An example claim without evidence\n-->\n", 1)
    path = store.root(repo) / units.unit_doc("src-auth")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    assert units.done(repo, "src-auth")["counts"]["claims"] == 1
