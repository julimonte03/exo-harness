"""sdd/changes: crear un change, actualizar su AI Usage Record y registrar su tier."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from exo.cli import main
from exo.core import config
from exo.sdd import changes, fitness, record
from exo.sdd.changes import ChangeError

NOW = datetime(2026, 11, 14, 10, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 11, 14, 11, 0, 0, tzinfo=timezone.utc)
LOW = {dimension: 0 for dimension in fitness.DIMENSIONS}


def _tickets(project: Path, pattern: str | None, example: str | None = None) -> None:
    cfg = config.defaults()
    cfg["tickets"] = {"pattern": pattern, "example": example}
    config.save(project, cfg)


def _record(project: Path, path: str) -> dict:
    return json.loads((project / path / record.FILENAME).read_text(encoding="utf-8"))


# -- exo change new ------------------------------------------------------------------


def test_nuevo_sin_ticket(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", purpose="Let users sign in.", now=NOW)
    assert (created.name, created.path, created.epic) == ("add-login", "specs/add-login", None)
    data = _record(tmp_path, created.path)
    assert data == {
        "attribution_schema_version": 1,
        "change_name": "add-login",
        "ticket_key": None,
        "epic_key": None,
        "purpose": "Let users sign in.",
        "capabilities_used": [{"name": "exo change new", "type": "command", "activation": "requested"}],
        "updated_at": "2026-11-14T10:00:00Z",
    }
    assert record.validate(data) == []


@pytest.mark.parametrize(
    ("pattern", "ticket", "epic", "path"),
    [
        (r"[A-Z][A-Z0-9]*-\d+", "PROJ-123", None, "specs/PROJ-123-add-login"),
        (r"#\d+", "#123", "#100", "specs/100/123-add-login"),
        (r"AB#\d+", "AB#123", "AB#100", "specs/AB-100/AB-123-add-login"),
    ],
)
def test_nuevo_con_ticket_normalizado(tmp_path: Path, pattern: str, ticket: str, epic: str | None, path: str) -> None:
    _tickets(tmp_path, pattern)
    created = changes.new_change(tmp_path, "add-login", ticket=ticket, epic=epic, now=NOW)
    assert created.path == path
    data = _record(tmp_path, path)
    assert (data["ticket_key"], data["epic_key"]) == (ticket, epic)
    assert data["change_name"] == path.rsplit("/", 1)[1]


def test_ticket_que_no_cumple_el_patron(tmp_path: Path) -> None:
    _tickets(tmp_path, r"[A-Z][A-Z0-9]*-\d+", "PROJ-123")
    with pytest.raises(ChangeError, match="for example PROJ-123"):
        changes.new_change(tmp_path, "add-login", ticket="proj-1")
    assert not (tmp_path / "specs").exists()


def test_ticket_sin_patron_en_el_proyecto(tmp_path: Path) -> None:
    with pytest.raises(ChangeError, match="no ticket pattern"):
        changes.new_change(tmp_path, "add-login", ticket="PROJ-1")


def test_nombre_repetido_en_cualquier_epica(tmp_path: Path) -> None:
    _tickets(tmp_path, r"#\d+")
    changes.new_change(tmp_path, "add-login", epic="#7", now=NOW)
    with pytest.raises(ChangeError, match="already exists"):
        changes.new_change(tmp_path, "add-login")


def test_una_epica_no_puede_ser_un_change(tmp_path: Path) -> None:
    _tickets(tmp_path, r"[A-Z]+-\d+")
    changes.new_change(tmp_path, "add-login", ticket="PROJ-1", now=NOW)
    (tmp_path / "specs" / "PROJ-9").mkdir()
    (tmp_path / "specs" / "PROJ-9" / "proposal.md").write_text("x\n", encoding="utf-8")
    with pytest.raises(ChangeError, match="is a change"):
        changes.new_change(tmp_path, "other", epic="PROJ-9")


@pytest.mark.parametrize("slug", ["Add-Login", "archive", "a b"])
def test_slug_invalido(tmp_path: Path, slug: str) -> None:
    with pytest.raises(ChangeError):
        changes.new_change(tmp_path, slug)


# -- exo change record ---------------------------------------------------------------


def test_record_agrega_sin_duplicar_y_es_idempotente(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    entry = {"name": "sdd-new", "type": "skill", "activation": "requested"}
    first = changes.update_record(tmp_path, "add-login", add=[("capabilities_used", entry)], now=LATER)
    assert first.changed is True
    data = _record(tmp_path, created.path)
    assert data["capabilities_used"][-1] == entry
    assert data["updated_at"] == "2026-11-14T11:00:00Z"
    raw = (tmp_path / created.path / record.FILENAME).read_bytes()
    again = changes.update_record(
        tmp_path,
        "add-login",
        add=[("capabilities_used", {**entry, "activation": "auto"}), ("skills_used", "sdd-new")],
        now=NOW,
    )
    assert again.changed is True
    data = _record(tmp_path, created.path)
    assert sum(1 for c in data["capabilities_used"] if c["name"] == "sdd-new") == 1
    assert data["skills_used"] == ["sdd-new"]
    raw = (tmp_path / created.path / record.FILENAME).read_bytes()
    third = changes.update_record(tmp_path, "add-login", add=[("skills_used", "sdd-new")], now=LATER)
    assert third.changed is False
    assert (tmp_path / created.path / record.FILENAME).read_bytes() == raw


def test_record_set_purpose(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    changes.update_record(tmp_path, "add-login", set_=[("purpose", "Sign in.")], now=LATER)
    assert _record(tmp_path, created.path)["purpose"] == "Sign in."


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [
        ({"add": [("purpose", "x")]}, "purpose is not a list field"),
        ({"set_": [("change_name", "otro")]}, "change_name cannot be set"),
        ({"add": [("capabilities_used", {"name": "x", "type": "skill", "activation": "explicit"})]}, "activation"),
        ({"add": [("inventado", 1)]}, "inventado is not a list field"),
    ],
)
def test_record_invalido_no_escribe(tmp_path: Path, kwargs: dict, fragment: str) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    raw = (tmp_path / created.path / record.FILENAME).read_bytes()
    with pytest.raises(ChangeError, match=fragment):
        changes.update_record(tmp_path, "add-login", now=LATER, **kwargs)
    assert (tmp_path / created.path / record.FILENAME).read_bytes() == raw


def test_record_sin_archivo(tmp_path: Path) -> None:
    (tmp_path / "specs" / "a-mano").mkdir(parents=True)
    (tmp_path / "specs" / "a-mano" / "proposal.md").write_text("x\n", encoding="utf-8")
    with pytest.raises(ChangeError, match="exo change new"):
        changes.update_record(tmp_path, "a-mano", add=[("skills_used", "x")])


# -- fitness-assessment.json (criterio 7) ---------------------------------------------


def _assessment(project: Path, path: str) -> dict:
    return json.loads((project / path / changes.ASSESSMENT).read_text(encoding="utf-8"))


def test_primera_clasificacion(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    result = changes.record_assessment(tmp_path, "add-login", LOW, now=NOW)
    assert (result.tier, result.previous, result.comparison, result.written) == (1, None, "initial", True)
    data = _assessment(tmp_path, created.path)
    assert data["tier"] == 1 and data["ceremony"] == "minimal"
    assert data["history"] == [{"tier": 1, "rule": data["rule"], "at": "2026-11-14T10:00:00Z", "change": "initial"}]
    assert changes.read_tier(tmp_path / created.path) == 1


def test_misma_evidencia_no_reescribe(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    changes.record_assessment(tmp_path, "add-login", LOW, now=NOW)
    raw = (tmp_path / created.path / changes.ASSESSMENT).read_bytes()
    again = changes.record_assessment(tmp_path, "add-login", LOW, now=LATER)
    assert (again.comparison, again.written) == ("same", False)
    assert (tmp_path / created.path / changes.ASSESSMENT).read_bytes() == raw


def test_criterio_7_evidencia_faltante_da_tier_4(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    result = changes.record_assessment(tmp_path, "add-login", {"blast_radius": 0}, now=NOW)
    assert result.tier == 4
    assert _assessment(tmp_path, created.path)["rule"] == "FM-00"


def test_criterio_7_upgrade_automatico_y_downgrade_con_confirmacion_literal(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    changes.record_assessment(tmp_path, "add-login", LOW, now=NOW)
    high = {**LOW, "security_data_sensitivity": 3}
    up = changes.record_assessment(tmp_path, "add-login", high, now=LATER)
    assert (up.previous, up.comparison, up.written) == (1, "upgrade", True)
    assert up.tier > 1
    raw = (tmp_path / created.path / changes.ASSESSMENT).read_bytes()
    with pytest.raises(ChangeError, match="--confirm-downgrade"):
        changes.record_assessment(tmp_path, "add-login", LOW, now=LATER)
    with pytest.raises(ChangeError, match="--confirm-downgrade"):
        changes.record_assessment(tmp_path, "add-login", LOW, confirm_downgrade="   ", now=LATER)
    assert (tmp_path / created.path / changes.ASSESSMENT).read_bytes() == raw
    words = "Sí, bajalo a Tier 1: no toca datos personales."
    down = changes.record_assessment(tmp_path, "add-login", LOW, confirm_downgrade=words, now=LATER)
    assert (down.comparison, down.tier) == ("downgrade", 1)
    last = _assessment(tmp_path, created.path)["history"][-1]
    assert last["change"] == "downgrade" and last["confirmation"] == words


def test_criterio_7_tier_ilegible_cuenta_como_4(tmp_path: Path) -> None:
    created = changes.new_change(tmp_path, "add-login", now=NOW)
    (tmp_path / created.path / changes.ASSESSMENT).write_text("{ roto", encoding="utf-8")
    assert changes.read_tier(tmp_path / created.path) is None
    assert changes.effective_tier(tmp_path / created.path) == 4
    with pytest.raises(ChangeError, match="--confirm-downgrade"):
        changes.record_assessment(tmp_path, "add-login", LOW, now=LATER)


# -- CLI --------------------------------------------------------------------------------


def test_cli_change_new_record_y_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = str(tmp_path)
    assert main(["change", "new", "add-login", "--purpose", "Sign in.", "--project", project, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "add-login" and payload["path"] == "specs/add-login"
    assert main(["change", "new", "add-login", "--project", project]) == 1
    assert "already exists" in capsys.readouterr().err
    entry = json.dumps({"name": "sdd-new", "type": "skill", "activation": "requested"})
    assert main(["change", "record", "add-login", "--add", "capabilities_used", entry, "--project", project]) == 0
    assert "updated" in capsys.readouterr().out
    assert main(["change", "record", "add-login", "--add", "skills_used", "no es json", "--project", project]) == 2
    assert "JSON" in capsys.readouterr().err
    assert main(["change", "status", "--project", project, "--json"]) == 0
    states = json.loads(capsys.readouterr().out)["changes"]
    assert [s["name"] for s in states] == ["add-login"]
    assert main(["change", "status", "add-login", "--project", project, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["name"] == "add-login"


def test_cli_fitness_con_change(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = str(tmp_path)
    assert main(["change", "new", "add-login", "--project", project]) == 0
    evidence = json.dumps(LOW)
    assert main(["fitness", "classify", "--evidence-json", evidence, "--change", "add-login", "--project", project]) == 0
    assert "Tier 1" in capsys.readouterr().out
    high = json.dumps({**LOW, "security_data_sensitivity": 3})
    assert main(["fitness", "classify", "--evidence-json", high, "--change", "add-login", "--project", project]) == 0
    capsys.readouterr()
    assert main(["fitness", "classify", "--evidence-json", evidence, "--change", "add-login", "--project", project]) == 1
    assert "--confirm-downgrade" in capsys.readouterr().err
    assert main([
        "fitness", "classify", "--evidence-json", evidence, "--change", "add-login",
        "--confirm-downgrade", "ok, Tier 1", "--project", project, "--json",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tier"] == 1 and payload["assessment"]["comparison"] == "downgrade"
    assert main(["fitness", "classify", "--evidence-json", evidence, "--confirm-downgrade", "x"]) == 2


def test_cli_json_desde_archivo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """En PowerShell 5.1 las comillas del JSON se pierden: el JSON puede venir de un archivo."""
    project = str(tmp_path)
    assert main(["change", "new", "add-login", "--project", project]) == 0
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(LOW), encoding="utf-8")
    capsys.readouterr()
    assert main(["fitness", "classify", "--evidence-file", str(evidence), "--change", "add-login", "--project", project, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tier"] == 1
    entry = tmp_path / "entry.json"
    entry.write_text(json.dumps({"name": "sdd-new", "type": "skill", "activation": "requested"}), encoding="utf-8")
    assert main(["change", "record", "add-login", "--add", "capabilities_used", f"@{entry}", "--project", project]) == 0
    record_data = json.loads((tmp_path / "specs" / "add-login" / record.FILENAME).read_text(encoding="utf-8"))
    assert record_data["capabilities_used"][-1]["name"] == "sdd-new"
    assert main(["change", "record", "add-login", "--add", "skills_used", f"@{tmp_path / 'no-existe.json'}", "--project", project]) == 2
    assert "no-existe.json" in capsys.readouterr().err
    assert main(["fitness", "classify", "--evidence-file", str(tmp_path / "no.json")]) == 2
    assert main(["fitness", "classify", "--evidence-json", "{}", "--evidence-file", str(evidence)]) == 2
