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


def _discovery_bytes(repo: Path) -> dict[str, bytes]:
    root = store.root(repo)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@needs_git
def test_commitear_los_resultados_no_cambia_el_inventario(repo: Path) -> None:
    """H1: `.exo/discovery/`, las specs y un ADR recuperado commiteados no cambian R0 a R2."""
    planner.write(repo)
    inv = store.read_json(repo, inventory.FILENAME)
    assert inv is not None and inv["adr_dir_exists"] is False
    adr = repo / "docs" / "adr" / "0001-recovered-token-login.md"
    adr.parent.mkdir(parents=True)
    adr.write_text("# 1. Token login\n", encoding="utf-8", newline="\n")
    _cap(repo, "auth", "src/auth/login.py:4")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs: discovery")
    before = _discovery_bytes(repo)
    data, wrote = inventory.write(repo)
    assert wrote is False
    assert data["adr_dir_exists"] is False
    assert "engine" not in data["files"]["excluded"] and "specs" not in data["files"]["excluded"]
    assert pipeline.structure(repo)["written"] is False
    assert planner.write(repo)[1] is False
    assert _discovery_bytes(repo) == before


def _to_crlf(root: Path) -> None:
    """Simula un checkout de Windows con `core.autocrlf=true`: todo texto con CRLF."""
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            data = path.read_bytes().replace(b"\r\n", b"\n")
            path.write_bytes(data.replace(b"\n", b"\r\n"))


@needs_git
def test_un_checkout_con_crlf_da_lo_mismo_y_no_reescribe(repo: Path) -> None:
    """H2: la misma historia con CRLF da los mismos JSON, no reescribe y no bloquea `plan`."""
    planner.write(repo)
    _write_doc(repo, "src-auth", "Login issues a token. [Code] src/auth/login.py:4-5")
    units.done(repo, "src-auth")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs: discovery")
    git(repo, "config", "core.autocrlf", "true")
    lf = _discovery_bytes(repo)
    _to_crlf(repo)
    crlf = _discovery_bytes(repo)
    assert crlf != lf
    assert inventory.write(repo)[1] is False
    assert pipeline.structure(repo)["written"] is False
    assert planner.write(repo)[1] is False  # sin PlanError: el plan es el mismo
    assert _discovery_bytes(repo) == crlf
    assert pipeline.status(repo)["units"] == {"pending": 3, "done": 1, "stale": 0}


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


@needs_git
def test_un_replan_que_cambia_los_archivos_de_una_unidad_la_deja_stale(repo: Path) -> None:
    """H3: el conjunto de archivos y tests del plan distinto del registrado es `stale`."""
    from exo.discovery import files

    planner.write(repo)
    _close_all(repo)
    (repo / "src/auth/extra.py").write_text("x = 1\n", encoding="utf-8", newline="\n")
    git(repo, "add", "src/auth/extra.py")
    plan, _ = planner.write(repo, replan=True)
    by_id = {s.id: s for s in units.states(repo, plan, files.list_files(repo))}
    assert (by_id["src-auth"].status, by_id["src-auth"].changed) == ("stale", ["src/auth/extra.py"])
    assert by_id["src-util"].status == "done"
    [util] = [u for u in plan["units"] if u["id"] == "src-util"]
    util["files"].remove("src/util/__init__.py")  # un replan que lo sacó de la unidad
    by_id = {s.id: s for s in units.states(repo, plan, files.list_files(repo))}
    assert (by_id["src-util"].status, by_id["src-util"].changed) == (
        "stale",
        ["src/util/__init__.py"],
    )


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


def test_la_cobertura_ignora_una_auditoria_vieja_y_lo_avisa(repo: Path) -> None:
    """L1: otra semilla, o IDs que ya no están en la muestra, no cuentan."""
    planner.write(repo)
    _cap(repo, "auth", "src/auth/login.py:4")
    _cap(repo, "strings", "src/util/strings.py:3")
    sampler.sample(repo, n=4)
    ids = ["CAP-auth-FR-1", "CAP-auth-FR-2", "CAP-strings-FR-1", "CAP-strings-FR-2"]
    sampler.record(repo, {"results": [{"id": i, "verdict": "correct"} for i in ids]})
    assert coverage.build(repo)["warnings"] == []
    smaller = sampler.sample(repo, n=2)  # la misma semilla, otra muestra
    kept = {i["id"] for i in smaller["items"]}
    report = coverage.build(repo)
    assert sum(r["correct"] for r in report["precision"]) == len(kept)
    assert any("no longer in the sample" in w for w in report["warnings"])
    sampler.sample(repo, n=2, seed=7)
    report = coverage.build(repo)
    assert report["precision"] == []
    assert any("another sample" in w for w in report["warnings"])
    assert sorted(report["audit_missing"]) == sorted(
        i["id"] for i in store.read_json(repo, sampler.SAMPLE)["items"]
    )
    assert "another sample" in coverage.render(report)


def test_la_evidencia_de_la_cobertura_y_la_capacidad_de_un_id_con_guiones(repo: Path) -> None:
    """L9: `[Code]` sin ruta no es evidencia; `CAP-user-accounts-FR-1` es de `user-accounts`."""
    planner.write(repo)
    _cap(repo, "user-accounts", "src/auth/login.py:4")
    path = repo / "specs" / "capabilities" / "user-accounts" / "spec.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("It also does this. [Inferred: low]", "See [Code] there. [Inferred: low]"),
        encoding="utf-8",
    )
    assert coverage.build(repo)["requirements"] == {"total": 2, "with_evidence": 1}
    sampler.sample(repo, n=2)
    sampler.record(repo, {"results": [{"id": "CAP-user-accounts-FR-1", "verdict": "correct"}]})
    path.unlink()  # la spec se borró después de auditar: el ID ya no está en la población
    [row] = coverage.build(repo)["precision"]
    assert row["capability"] == "user-accounts"


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


@needs_git
def test_cambios_fuera_renames_rutas_ancladas_y_sin_lock(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M1, L3 y M9: el origen de un rename cuenta, el patrón se ancla a la raíz y no se
    toma el lock del índice."""
    from exo.governance import git as git_mod

    planner.write(repo)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs: discovery")
    assert pipeline.outside_changes(repo) == []
    git(repo, "mv", "src/util/strings.py", ".exo/discovery/strings.py")
    assert pipeline.outside_changes(repo) == ["src/util/strings.py"]
    git(repo, "mv", ".exo/discovery/strings.py", "src/util/strings.py")
    nested = repo / "src" / ".exo" / "context.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Context\n", encoding="utf-8")
    deeper = repo / "docs" / "adr" / "old" / "0001-recovered-x.md"
    deeper.parent.mkdir(parents=True)
    deeper.write_text("# 1\n", encoding="utf-8")
    assert pipeline.outside_changes(repo) == [
        "docs/adr/old/0001-recovered-x.md",
        "src/.exo/context.md",
    ]
    calls: list[tuple[str, ...]] = []
    real = git_mod.run

    def spy(project: Path, *args: str, **kwargs: object) -> git_mod.Run:
        calls.append(args)
        return real(project, *args, **kwargs)

    monkeypatch.setattr(git_mod, "run", spy)
    pipeline.outside_changes(repo)
    [status_call] = [c for c in calls if "status" in c]
    assert status_call.index("--no-optional-locks") < status_call.index("status")


@needs_git
def test_si_git_falla_status_lo_dice(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """L8: None solo sin git; una falla de git va a `outside_changes_error`."""
    from exo.cli import main
    from exo.governance import git as git_mod

    planner.write(repo)
    real = git_mod.run

    def failing(project: Path, *args: str, **kwargs: object) -> git_mod.Run:
        if "status" in args:
            return git_mod.Run(False, "", "timed out after 30 seconds")
        return real(project, *args, **kwargs)

    monkeypatch.setattr(git_mod, "run", failing)
    payload = pipeline.status(repo)
    assert payload["outside_changes"] is None
    assert "timed out" in payload["outside_changes_error"]
    assert main(["discover", "status", "--project", str(repo)]) == 0
    assert "timed out" in capsys.readouterr().out
    monkeypatch.setattr(git_mod, "run", real)
    assert pipeline.status(repo)["outside_changes_error"] is None


def test_sin_git_no_hay_cambios_fuera_ni_error(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    payload = pipeline.status(tmp_path)
    assert payload["outside_changes"] is None and payload["outside_changes_error"] is None


def test_los_comentarios_de_la_plantilla_no_son_afirmaciones(repo: Path) -> None:
    planner.write(repo)
    text = _doc("src-auth", "Login issues a token. [Code] src/auth/login.py:4-5")
    text = text.replace(
        "## Entities\n", "## Entities\n\n<!--\n- An example claim without evidence\n-->\n", 1
    )
    path = store.root(repo) / units.unit_doc("src-auth")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    assert units.done(repo, "src-auth")["counts"]["claims"] == 1


def _write_text_doc(repo: Path, unit_id: str, text: str) -> None:
    path = store.root(repo) / units.unit_doc(unit_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_done_cuenta_todas_las_vinetas_y_rechaza_el_texto_suelto(repo: Path) -> None:
    """M5: `-`, `*`, `+` y `1.` son afirmaciones; otra línea no vacía es un error."""
    planner.write(repo)
    claims = (
        "- Login issues a token. [Code] src/auth/login.py:4-5\n"
        "* It checks the user. [Code] src/auth/login.py:4\n"
        "+ Tokens are strings. [Code] src/auth/tokens.py:1-2\n"
        "1. It has no rate limit. [Inferred: low]\n"
    )
    text = _doc("src-auth", "PLACEHOLDER").replace("- PLACEHOLDER", claims.rstrip("\n"))
    text = text.replace("## Integrations\n\nNone.", "## Integrations\n\nNot extracted: summary.")
    _write_text_doc(repo, "src-auth", text)
    record = units.done(repo, "src-auth")
    assert record["counts"] == {"claims": 4, "code": 3, "doc": 0, "inferred": 1}
    bad = [
        ("Login issues a token. [Code] src/auth/login.py:4", "as a bullet"),
        ("+ Login issues a token.", "without evidence"),
        ("1. Login issues a token.", "without evidence"),
    ]
    for line, fragment in bad:
        text = _doc("src-auth", "PLACEHOLDER").replace("- PLACEHOLDER", line)
        _write_text_doc(repo, "src-auth", text)
        with pytest.raises(units.UnitError, match=fragment):
            units.done(repo, "src-auth")


@needs_git
def test_done_exige_un_hecho_en_detalle_full_y_rechaza_doc_de_credenciales(repo: Path) -> None:
    """M5 y L4: en `full`, al menos un [Code] o [Doc]; un [Doc] a credenciales es error."""
    (repo / ".env").write_text("TOKEN=never-read\n", encoding="utf-8")
    (repo / "README.md").write_text("# App\n", encoding="utf-8")
    git(repo, "add", ".env", "README.md")
    plan, _ = planner.write(repo, "quick")
    by_detail = {u["detail"]: u["id"] for u in plan["units"]}
    full, summary = by_detail["full"], by_detail["summary"]
    _write_doc(repo, full, "It does something. [Inferred: high]")
    with pytest.raises(units.UnitError, match=r"\[Code\] path:line or \[Doc\] path"):
        units.done(repo, full)
    _write_doc(repo, full, "It reads its config. [Doc] .env")
    with pytest.raises(units.UnitError, match="credentials file"):
        units.done(repo, full)
    _write_doc(repo, full, "It is documented. [Doc] README.md")
    assert units.done(repo, full)["counts"]["doc"] == 1
    _write_doc(repo, summary, "It does something. [Inferred: high]")
    assert units.done(repo, summary)["counts"]["inferred"] == 1


def test_reabrir_unidades_por_id_o_por_capacidad(repo: Path) -> None:
    planner.write(repo)
    _close_all(repo)
    _cap(repo, "auth", "src/auth/login.py:4")
    assert units.reopen(repo, ["src-util"]) == ["src-util"]
    assert [u["id"] for u in units.next_units(repo, count=10)] == ["src-util"]
    assert units.reopen(repo, capability="auth") == ["src-auth"]
    assert {u["id"] for u in units.next_units(repo, count=10)} == {"src-auth", "src-util"}
    with pytest.raises(units.UnitError, match="not a unit"):
        units.reopen(repo, ["nope"])
    with pytest.raises(units.UnitError, match="cites no file"):
        units.reopen(repo, capability="ghost")


JAVA = "src/main/java/com/example"


@needs_git
def test_un_archivo_java_en_latin_1_no_rompe_nada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """H4: inventario, grafo y `next` lo leen con reemplazos y avisan; nunca un traceback."""
    from exo.cli import main
    from exo.discovery import graph

    root = tmp_path / "lib"
    app = (
        "package com.example;\nimport com.example.util.Texto;\n// Autor: José Núñez\n"
        "public class App {\n  public static void main(String[] a) {}\n}\n"
    )
    tree = {
        f"{JAVA}/App.java": app.encode("latin-1"),
        f"{JAVA}/util/Texto.java": b"package com.example.util;\npublic class Texto {}\n",
    }
    for rel, data in tree.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    init_repo(root)
    inv = inventory.build(root)
    assert {e["path"]: e["kinds"] for e in inv["entrypoints"]} == {
        f"{JAVA}/App.java": ["java-main"]
    }
    assert any(f"{JAVA}/App.java" in w and "not UTF-8" in w for w in inv["warnings"])
    structure = graph.build(root)
    assert {(e["from"], e["to"]) for e in structure["edges"]} == {(JAVA, f"{JAVA}/util")}
    assert any(f"{JAVA}/App.java" in w for w in structure["warnings"])
    for step in ("inventory", "structure", "plan"):
        assert main(["discover", step, "--project", str(root)]) == 0
    err = capsys.readouterr().err
    assert f"{JAVA}/App.java" in err
    assert "save it" not in err and "Set-Content" not in err  # nada que modificar en el proyecto
    [unit] = [u for u in units.next_units(root, count=10) if f"{JAVA}/App.java" in u["files"]]
    assert "not UTF-8" in unit["flags"][f"{JAVA}/App.java"]["warnings"][0]
    assert main(["discover", "next", "--count", "5", "--project", str(root)]) == 0


def test_un_json_o_un_documento_de_unidad_que_no_es_utf8_da_un_error_claro(repo: Path) -> None:
    """H4: `read_json` da DiscoveryError y `done` da UnitError, no un ValueError suelto."""
    planner.write(repo)
    path = store.root(repo) / units.unit_doc("src-auth")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_doc("src-auth", "Login, José. [Code] src/auth/login.py:4").encode("latin-1"))
    with pytest.raises(units.UnitError, match="not UTF-8"):
        units.done(repo, "src-auth")
    (store.root(repo) / planner.FILENAME).write_bytes(
        '{"schema": 1, "x": "José"}'.encode("latin-1")
    )
    with pytest.raises(store.DiscoveryError, match="not UTF-8"):
        planner.load(repo)
