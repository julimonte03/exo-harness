"""sdd/observability: changes, épicas, archivo, fase derivada, followups y AI Usage Record."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import _meta
from exo.core import config, fsutil
from exo.sdd import observability
from exo.sdd.observability import ObservabilityError


def _touch(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tree(project: Path, specs: str = "specs") -> Path:
    root = project / specs
    _touch(root / "PROJ-1-login" / "proposal.md")
    _touch(root / "PROJ-1-login" / "spec.md")
    epic = root / "PROJ-10" / "PROJ-11-pagos"
    for name in ("fitness-assessment.json", "proposal.md", "spec.md", "design.md"):
        _touch(epic / name)
    _touch(epic / "tasks.md", "- [x] paso 1\n- [ ] paso 2\n")
    _touch(
        epic / "ai-usage-record.json",
        json.dumps(
            {
                "attribution_schema_version": 2,
                "change_name": "PROJ-11-pagos",
                "jira_key": "PROJ-11",
                "capabilities_used": [{"name": "sdd-new", "type": "skill", "activation": "explicit"}],
                "dismissed_followups": [
                    {"judge": "judge-security", "rule": "S-SQL", "reason": "falso positivo"},
                    {"id": "J2-003", "judge": "judge-code-reviewer", "rule": "R-1", "reason": "aceptado"},
                ],
            }
        ),
    )
    _touch(
        epic / "followups.json",
        json.dumps(
            {
                "followups": [
                    {"id": "J1-001", "judge": "judge-security", "rule": "S-SQL", "severity": "high", "summary": "a"},
                    {"id": "J1-002", "judge": "judge-security", "rule": "S-XSS", "severity": "medium", "summary": "b"},
                    {"id": "J2-003", "judge": "judge-code-reviewer", "rule": "R-2", "severity": "low", "summary": "c"},
                ]
            }
        ),
    )
    # Un change recién creado tiene al menos un artefacto; una carpeta vacía no es un change.
    _touch(root / "nuevo" / "followups.json", "[]")
    (root / "vacia").mkdir()
    _touch(root / "solo-tasks" / "tasks.md", "- [ ] pendiente\n")
    _touch(root / "capabilities" / "auth" / "spec.md")
    _touch(root / "archive" / "2026-01-15-viejo" / "proposal.md")
    _touch(root / "archive" / "2026-01-15-viejo" / "verify-record.md")
    _touch(root / "archive" / "PROJ-10" / "2026-02-01-PROJ-12-otro" / "proposal.md")
    _touch(root / "archive" / "sin-fecha" / "proposal.md")
    _touch(root / ".oculto" / "proposal.md")
    _touch(root / "_borrador" / "proposal.md")
    _touch(root / "LEEME.md")
    return root


def _by_name(project: Path) -> dict[str, observability.Change]:
    return {c.name: c for c in observability.find_changes(project)}


def test_epicas_por_estructura_con_cualquier_patron(tmp_path: Path) -> None:
    """ADR-0012/D-26: la épica es la carpeta sin artefactos que contiene changes, sin regex de Jira."""
    root = tmp_path / "specs"
    _touch(root / "AB-100" / "AB-101-alta" / "proposal.md")
    _touch(root / "100" / "101-baja" / "ai-usage-record.json", "{}")
    _touch(root / "PROJ-5" / "proposal.md")  # parece una épica, pero tiene artefactos: es un change
    (root / "100" / "102-vacio").mkdir()  # vacía: no es un change
    _touch(root / "archive" / "AB-100" / "2026-03-01-AB-103-viejo" / "proposal.md")
    changes = _by_name(tmp_path)
    assert changes["AB-101-alta"].epic == "AB-100"
    assert changes["101-baja"].epic == "100"
    assert "102-vacio" not in changes
    assert changes["PROJ-5"].epic is None
    assert (changes["AB-103-viejo"].epic, changes["AB-103-viejo"].archived) == ("AB-100", True)


def test_detecta_changes_epicas_y_archivo(tmp_path: Path) -> None:
    _tree(tmp_path)
    changes = _by_name(tmp_path)
    assert sorted(changes) == ["PROJ-1-login", "PROJ-11-pagos", "PROJ-12-otro", "nuevo", "sin-fecha", "solo-tasks", "viejo"]
    pagos = changes["PROJ-11-pagos"]
    assert (pagos.epic, pagos.archived, pagos.archived_on) == ("PROJ-10", False, None)
    assert pagos.path == "specs/PROJ-10/PROJ-11-pagos"
    otro = changes["PROJ-12-otro"]
    assert (otro.epic, otro.archived, otro.archived_on) == ("PROJ-10", True, "2026-02-01")
    assert changes["viejo"].archived_on == "2026-01-15"
    assert changes["sin-fecha"].archived_on is None


@pytest.mark.parametrize(
    ("name", "phase"),
    [
        ("PROJ-1-login", "spec"),
        ("PROJ-11-pagos", "apply"),
        ("solo-tasks", "tasks"),
        ("nuevo", "new"),
        ("viejo", "archived"),
    ],
)
def test_fase_derivada(tmp_path: Path, name: str, phase: str) -> None:
    _tree(tmp_path)
    assert _by_name(tmp_path)[name].phase == phase


def test_artefactos_presentes_en_orden(tmp_path: Path) -> None:
    _tree(tmp_path)
    assert _by_name(tmp_path)["PROJ-11-pagos"].artifacts == (
        "fitness-assessment.json",
        "proposal.md",
        "spec.md",
        "design.md",
        "tasks.md",
        "ai-usage-record.json",
        "followups.json",
    )


def test_sin_archivados(tmp_path: Path) -> None:
    _tree(tmp_path)
    names = {c.name for c in observability.find_changes(tmp_path, include_archived=False)}
    assert names == {"PROJ-1-login", "PROJ-11-pagos", "nuevo", "solo-tasks"}


def test_specs_dir_de_la_config(tmp_path: Path) -> None:
    cfg = config.defaults()
    cfg["specs_dir"] = "docs/specs"
    config.save(tmp_path, cfg)
    _tree(tmp_path, "docs/specs")
    assert "PROJ-1-login" in _by_name(tmp_path)
    assert _by_name(tmp_path)["PROJ-1-login"].path == "docs/specs/PROJ-1-login"


def test_sin_carpeta_de_specs(tmp_path: Path) -> None:
    assert observability.find_changes(tmp_path) == []


def test_change_state_proyecta_ticket_y_atribucion(tmp_path: Path) -> None:
    _tree(tmp_path)
    state = observability.change_state(tmp_path, "PROJ-11-pagos")
    assert state["ticket_key"] == "PROJ-11"
    assert state["attribution_schema_version"] == 2
    assert state["phase"] == "apply"
    assert state["followups"] == {"open": 1, "fixed": 0, "dismissed": 2}
    assert state["warnings"] == []
    empty = observability.change_state(tmp_path, "PROJ-1-login")
    assert (empty["ticket_key"], empty["attribution_schema_version"]) == (None, None)
    assert empty["followups"] == {"open": 0, "fixed": 0, "dismissed": 0}


def test_followups_por_estado(tmp_path: Path) -> None:
    _tree(tmp_path)
    open_ = observability.followups(tmp_path, "PROJ-11-pagos", "open")
    assert [f["id"] for f in open_] == ["J1-002"]
    dismissed = observability.followups(tmp_path, "PROJ-11-pagos", "dismissed")
    assert [(f["id"], f["dismissal"]) for f in dismissed] == [("J1-001", "falso positivo"), ("J2-003", "aceptado")]
    every = observability.followups(tmp_path, "PROJ-11-pagos", "all")
    assert [f["status"] for f in every] == ["dismissed", "open", "dismissed"]
    with pytest.raises(ObservabilityError, match="status"):
        observability.followups(tmp_path, "PROJ-11-pagos", "cerrados")


def test_ai_usage_record(tmp_path: Path) -> None:
    _tree(tmp_path)
    payload = observability.ai_usage_record(tmp_path, "PROJ-11-pagos")
    assert payload["record"]["change_name"] == "PROJ-11-pagos"
    assert payload["ticket_key"] == "PROJ-11"
    missing = observability.ai_usage_record(tmp_path, "nuevo")
    assert missing == {"record": None, "ticket_key": None, "attribution_schema_version": None, "warnings": []}


def test_ticket_key_tiene_prioridad_sobre_jira_key(tmp_path: Path) -> None:
    _touch(tmp_path / "specs" / "c" / "ai-usage-record.json", json.dumps({"ticket_key": "GH-5", "jira_key": "X-1"}))
    assert observability.ai_usage_record(tmp_path, "c")["ticket_key"] == "GH-5"


def test_json_ilegible_se_tolera_con_advertencia(tmp_path: Path) -> None:
    _touch(tmp_path / "specs" / "c" / "ai-usage-record.json", "{ roto")
    _touch(tmp_path / "specs" / "c" / "followups.json", "[1, 2")
    state = observability.change_state(tmp_path, "c")
    assert state["followups"] == {"open": 0, "fixed": 0, "dismissed": 0}
    assert len(state["warnings"]) == 2
    assert all("unreadable" in w for w in state["warnings"])


def test_followups_como_lista_y_entradas_invalidas(tmp_path: Path) -> None:
    _touch(tmp_path / "specs" / "c" / "followups.json", json.dumps([{"id": "J1-1", "judge": "j", "rule": "r"}, "basura"]))
    assert [f["id"] for f in observability.followups(tmp_path, "c", "all")] == ["J1-1"]


def test_change_inexistente_o_ambiguo(tmp_path: Path) -> None:
    _tree(tmp_path)
    with pytest.raises(ObservabilityError, match="does not exist"):
        observability.change_state(tmp_path, "fantasma")
    _touch(tmp_path / "specs" / "PROJ-20" / "nuevo" / "proposal.md")
    with pytest.raises(ObservabilityError, match="ambiguous"):
        observability.change_state(tmp_path, "nuevo")


def test_activo_tiene_prioridad_sobre_archivado(tmp_path: Path) -> None:
    _touch(tmp_path / "specs" / "dup" / "proposal.md")
    _touch(tmp_path / "specs" / "archive" / "2026-01-01-dup" / "proposal.md")
    assert observability.change_state(tmp_path, "dup")["archived"] is False


def test_es_de_solo_lectura(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = {p: fsutil.sha256_file(p) for p in root.rglob("*") if p.is_file()}
    observability.find_changes(tmp_path)
    for name in ("PROJ-11-pagos", "viejo", "nuevo"):
        observability.change_state(tmp_path, name)
        observability.followups(tmp_path, name, "all")
        observability.ai_usage_record(tmp_path, name)
    after = {p: fsutil.sha256_file(p) for p in root.rglob("*") if p.is_file()}
    assert after == before
    assert not (tmp_path / _meta.PROJECT_DIR).exists()


# -- robustez (revisión F1) ---------------------------------------------------


def test_tasks_no_utf8_no_rompe_el_listado(tmp_path: Path) -> None:
    folder = tmp_path / "specs" / "c"
    folder.mkdir(parents=True)
    (folder / "tasks.md").write_bytes(b"- [x] hecho \xff\xfe\n")
    assert _by_name(tmp_path)["c"].phase == "apply"


def test_dismissed_followups_que_no_es_lista(tmp_path: Path) -> None:
    _touch(tmp_path / "specs" / "c" / "ai-usage-record.json", json.dumps({"dismissed_followups": {"x": 1}}))
    _touch(tmp_path / "specs" / "c" / "followups.json", json.dumps([{"id": "J1-1", "judge": "j", "rule": "r"}]))
    state = observability.change_state(tmp_path, "c")
    assert state["followups"] == {"open": 1, "fixed": 0, "dismissed": 0}
    assert any("dismissed_followups" in w for w in state["warnings"])


def test_specs_que_sale_del_proyecto_por_un_link_no_se_lee(tmp_path: Path, make_dir_link) -> None:
    outside = tmp_path / "afuera"
    _touch(outside / "secreto" / "proposal.md")
    project = tmp_path / "proyecto"
    project.mkdir()
    make_dir_link(project / "specs", outside)
    assert observability.find_changes(project) == []


def test_change_state_incluye_el_tier(tmp_path: Path) -> None:
    """Sin fitness-assessment.json legible el tier es 3 (§6.3); el contrato de estado lo usa."""
    _tree(tmp_path)
    login = observability.change_state(tmp_path, "PROJ-1-login")
    assert (login["tier"], login["tier_source"]) == (3, "missing")
    pagos = observability.change_state(tmp_path, "PROJ-11-pagos")  # el archivo dice "x"
    assert (pagos["tier"], pagos["tier_source"]) == (3, "unreadable")
    folder = tmp_path / "specs" / "PROJ-10" / "PROJ-11-pagos"
    (folder / "fitness-assessment.json").write_text(json.dumps({"tier": 2}), encoding="utf-8")
    pagos = observability.change_state(tmp_path, "PROJ-11-pagos")
    assert (pagos["tier"], pagos["tier_source"]) == (2, "assessment")
    # Un 4 de la 1.0 se lee como 3 (D-52); uno fuera de rango sigue siendo ilegible.
    (folder / "fitness-assessment.json").write_text(json.dumps({"tier": 4}), encoding="utf-8")
    pagos = observability.change_state(tmp_path, "PROJ-11-pagos")
    assert (pagos["tier"], pagos["tier_source"]) == (3, "assessment")
    (folder / "fitness-assessment.json").write_text(json.dumps({"tier": 5}), encoding="utf-8")
    pagos = observability.change_state(tmp_path, "PROJ-11-pagos")
    assert (pagos["tier"], pagos["tier_source"]) == (3, "unreadable")
