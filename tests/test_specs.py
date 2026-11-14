"""sdd/specs: specs vivas por capacidad, deltas por cambio y su integración (ADR-0013)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo.cli import main
from exo.core import snapshots
from exo.sdd import specs
from exo.sdd.specs import MergeError

DELTA = """# Spec: demo

## ADDED Requirements

### CAP-auth-FR-3: Sign in with SSO
The system SHALL let users sign in with the company SSO.

#### Scenario S-1: Happy path
- Given a user with an SSO account
- When they choose "Sign in with SSO"
- Then they land on the dashboard

### CAP-auth-NFR-1: Fast sign in
Sign in completes in under 1 s.

## MODIFIED Requirements

### CAP-auth-FR-1: Sign in with password
The system SHALL lock the account after 5 failed attempts.

#### Scenario S-2: Lockout
- Given a user who failed 4 times
- When they fail again
- Then the account is locked

## REMOVED Requirements

### CAP-auth-FR-2: Remember me
Reason: replaced by SSO sessions.
"""

AUTH = """# Capability: auth

## Purpose
Who can use the system and how they prove it.

## Requirements

### CAP-auth-FR-1: Sign in with password
The system SHALL let users sign in with email and password.

#### Scenario: Valid password
- Given a registered user
- When they enter the right password
- Then they are signed in

### CAP-auth-FR-2: Remember me
The system SHALL keep users signed in for 30 days if they ask.

#### Scenario: Remember me checked
- Given a user who checks "Remember me"
- When they come back after a day
- Then they are still signed in

## Notes
Free text   that the merge keeps byte for byte.
"""

AUTH_MERGED = """# Capability: auth

## Purpose
Who can use the system and how they prove it.

## Requirements

### CAP-auth-FR-1: Sign in with password
The system SHALL lock the account after 5 failed attempts.

#### Scenario: Lockout
- Given a user who failed 4 times
- When they fail again
- Then the account is locked

### CAP-auth-FR-3: Sign in with SSO
The system SHALL let users sign in with the company SSO.

#### Scenario: Happy path
- Given a user with an SSO account
- When they choose "Sign in with SSO"
- Then they land on the dashboard

### CAP-auth-NFR-1: Fast sign in
Sign in completes in under 1 s.

## Notes
Free text   that the merge keeps byte for byte.

## Removed Requirements

### CAP-auth-FR-2: Remember me
Removed by change `demo`.
Reason: replaced by SSO sessions.
"""

BILLING_DELTA = """# Spec: invoices

## ADDED Requirements

### CAP-billing-FR-1: Monthly invoice
The system SHALL send an invoice on the first day of each month.

#### Scenario S-1: First day
- Given an active customer
- When the month starts
- Then they get an invoice
"""


def _write(path: Path, text: str, *, newline: str = "\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return path


def _project(tmp_path: Path, delta: str = DELTA, *, auth: str | None = AUTH, change: str = "demo") -> Path:
    if auth is not None:
        _write(tmp_path / "specs" / "capabilities" / "auth" / "spec.md", auth)
    _write(tmp_path / "specs" / change / "spec.md", delta)
    _write(tmp_path / "specs" / change / "proposal.md", "# Proposal\n")
    return tmp_path


def _auth(project: Path) -> str:
    return (project / "specs" / "capabilities" / "auth" / "spec.md").read_bytes().decode("utf-8")


def _problems(items: list[specs.Problem]) -> list[str]:
    return [p.message for p in items]


# -- formato del delta ----------------------------------------------------------


def test_delta_valido() -> None:
    delta = specs.parse_delta(DELTA)
    assert delta.problems == ()
    assert [b.id for b in delta.added] == ["CAP-auth-FR-3", "CAP-auth-NFR-1"]
    assert [b.id for b in delta.modified] == ["CAP-auth-FR-1"]
    assert [b.id for b in delta.removed] == ["CAP-auth-FR-2"]
    assert delta.scenarios == {"S-1": 8, "S-2": 21}
    assert delta.ids()["CAP-auth-FR-1"] == 18


def test_las_secciones_son_opcionales() -> None:
    assert specs.parse_delta(BILLING_DELTA).problems == ()


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("## ADDED Requirements", "## Requirements", "unknown section '## Requirements'"),
        ("### CAP-auth-FR-3:", "### FR-3:", "malformed requirement ID: FR-3"),
        ("### CAP-auth-FR-3:", "### CAP-Auth-FR-3:", "malformed requirement ID: CAP-Auth-FR-3"),
        ("### CAP-auth-FR-3:", "### CAP-auth-FR-03:", "malformed requirement ID: CAP-auth-FR-03"),
        ("### CAP-auth-NFR-1:", "### CAP-auth-FR-3:", "CAP-auth-FR-3 appears twice"),
        ("#### Scenario S-2: Lockout", "#### Scenario S-1: Lockout", "S-1 appears twice"),
        ("#### Scenario S-2: Lockout", "#### Scenario: Lockout", "scenario without an S-n ID"),
        ("#### Scenario S-2: Lockout", "#### Lockout", "unexpected heading"),
        ("- Then the account is locked\n", "", "S-2 has no Then"),
        ("- Given a user with an SSO account\n", "", "S-1 has no Given"),
        ("The system SHALL let users sign in with the company SSO.\n", "", "CAP-auth-FR-3 has no requirement text"),
        ("Reason: replaced by SSO sessions.\n", "Gone.\n", "needs a 'Reason:"),
    ],
)
def test_reglas_del_delta(old: str, new: str, fragment: str) -> None:
    text = DELTA.replace(old, new, 1)
    assert text != DELTA
    messages = _problems(list(specs.parse_delta(text).problems))
    assert any(fragment in m for m in messages), messages


def test_fr_sin_escenarios_y_nfr_sin_escenarios() -> None:
    text = DELTA.replace(
        "#### Scenario S-2: Lockout\n- Given a user who failed 4 times\n- When they fail again\n- Then the account is locked\n",
        "",
    )
    messages = _problems(list(specs.parse_delta(text).problems))
    assert "CAP-auth-FR-1 has no scenarios" in messages
    assert not any("NFR-1" in m for m in messages)


def test_delta_sin_requisitos() -> None:
    messages = _problems(list(specs.parse_delta("# Spec: x\n\n## ADDED Requirements\n\nNothing yet.\n").problems))
    assert any("has no requirements" in m for m in messages)


def test_comentarios_y_codigo_no_cuentan() -> None:
    text = DELTA.replace(
        "## REMOVED Requirements",
        "<!--\n### CAP-<capability>-FR-<n>: <title>\n-->\n```\n### CAP-auth-FR-9: in code\n```\n\n## REMOVED Requirements",
    )
    delta = specs.parse_delta(text)
    assert delta.problems == ()
    assert "CAP-auth-FR-9" not in delta.ids()


def test_problemas_con_numero_de_linea() -> None:
    text = DELTA.replace("### CAP-auth-NFR-1:", "### CAP-auth-FR-3:")
    problem = next(p for p in specs.parse_delta(text).problems if "twice" in p.message)
    assert problem.line == 13


# -- formato de la spec de capacidad ----------------------------------------------


def test_capacidad_valida() -> None:
    cap = specs.parse_capability(AUTH, "auth")
    assert cap.problems == ()
    assert list(cap.requirements) == ["CAP-auth-FR-1", "CAP-auth-FR-2"]
    assert cap.removed == {}


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("### CAP-auth-FR-2:", "### CAP-billing-FR-2:", "belongs to capability billing"),
        ("### CAP-auth-FR-2:", "### CAP-auth-FR-1:", "CAP-auth-FR-1 appears twice"),
        ("#### Scenario: Valid password", "#### Scenario S-1: Valid password", "belong to change deltas"),
        ("- When they come back after a day\n", "", "has no When"),
    ],
)
def test_reglas_de_la_capacidad(old: str, new: str, fragment: str) -> None:
    messages = _problems(list(specs.parse_capability(AUTH.replace(old, new, 1), "auth").problems))
    assert any(fragment in m for m in messages), messages


def test_requisito_y_lapida_con_el_mismo_id() -> None:
    text = AUTH + "\n## Removed Requirements\n\n### CAP-auth-FR-2: Remember me\nRemoved by change `x`.\n"
    messages = _problems(list(specs.parse_capability(text, "auth").problems))
    assert any("CAP-auth-FR-2 appears twice" in m for m in messages)


# -- integración (criterio 3 de F4) --------------------------------------------------


def test_criterio_3_merge_produce_el_resultado_esperado(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = specs.merge(project, "demo")
    assert _auth(project) == AUTH_MERGED
    [cap] = result.capabilities
    assert (cap.name, cap.action, cap.path) == ("auth", "update", "specs/capabilities/auth/spec.md")
    assert [(op.id, op.action, op.status) for op in cap.ops] == [
        ("CAP-auth-FR-3", "add", "applied"),
        ("CAP-auth-NFR-1", "add", "applied"),
        ("CAP-auth-FR-1", "modify", "applied"),
        ("CAP-auth-FR-2", "remove", "applied"),
    ]
    assert result.written is True
    assert specs.parse_capability(_auth(project), "auth").problems == ()


def test_criterio_3_merge_es_idempotente(tmp_path: Path) -> None:
    project = _project(tmp_path)
    specs.merge(project, "demo")
    snaps = snapshots.list_snapshots(project)
    again = specs.merge(project, "demo")
    assert again.written is False
    assert again.snapshot is None
    assert {op.status for op in again.capabilities[0].ops} == {"already"}
    assert again.capabilities[0].action == "unchanged"
    assert snapshots.list_snapshots(project) == snaps
    assert _auth(project) == AUTH_MERGED


_REMOVED_SECTION = "## REMOVED Requirements\n\n### CAP-auth-FR-2: Remember me\nReason: replaced by SSO sessions.\n"


@pytest.mark.parametrize(
    ("replacements", "fragment"),
    [
        ([("### CAP-auth-FR-1:", "### CAP-auth-FR-7:")], "CAP-auth-FR-7 does not exist"),
        ([("### CAP-auth-FR-2:", "### CAP-auth-FR-8:")], "CAP-auth-FR-8 does not exist"),
        (
            [(_REMOVED_SECTION, ""), ("### CAP-auth-FR-3: Sign in with SSO", "### CAP-auth-FR-2: Sign in with SSO")],
            "CAP-auth-FR-2 already exists",
        ),
    ],
)
def test_criterio_3_merge_falla_con_referencias_invalidas_y_no_escribe(
    tmp_path: Path, replacements: list[tuple[str, str]], fragment: str
) -> None:
    """Un error en una capacidad frena todo: la otra (billing, válida) tampoco se escribe."""
    delta = DELTA
    for old, new in replacements:
        assert old in delta
        delta = delta.replace(old, new, 1)
    project = _project(tmp_path, _with_billing(delta))
    with pytest.raises(MergeError) as info:
        specs.merge(project, "demo")
    assert any(fragment in m for m in info.value.problems), info.value.problems
    assert _auth(project) == AUTH
    assert not (project / "specs" / "capabilities" / "billing").exists()
    assert snapshots.list_snapshots(project) == []


def test_modificar_una_capacidad_inexistente(tmp_path: Path) -> None:
    delta = DELTA.replace("CAP-auth-", "CAP-pay-")
    project = _project(tmp_path, delta)
    with pytest.raises(MergeError) as info:
        specs.merge(project, "demo")
    assert any("capability pay does not exist" in m for m in info.value.problems)


def test_un_id_borrado_no_se_reusa(tmp_path: Path) -> None:
    project = _project(tmp_path)
    specs.merge(project, "demo")
    reuse = BILLING_DELTA.replace("CAP-billing-FR-1", "CAP-auth-FR-2")
    _write(project / "specs" / "otro" / "spec.md", reuse)
    with pytest.raises(MergeError) as info:
        specs.merge(project, "otro")
    assert any("was removed" in m and "new number" in m for m in info.value.problems)
    modify = DELTA.split("## MODIFIED")[0].replace("## ADDED", "## MODIFIED").replace("CAP-auth-FR-3", "CAP-auth-FR-2")
    _write(project / "specs" / "otro" / "spec.md", modify)
    with pytest.raises(MergeError) as info:
        specs.merge(project, "otro")
    assert any("CAP-auth-FR-2 was removed" in m for m in info.value.problems)


def _with_billing(delta: str) -> str:
    """Suma al delta un ADDED de otra capacidad (billing), con un escenario S-3."""
    block = BILLING_DELTA.split("## ADDED Requirements\n\n", 1)[1].rstrip("\n")
    block = block.replace("#### Scenario S-1: First day", "#### Scenario S-3: First day")
    return delta.replace("### CAP-auth-NFR-1: Fast sign in", block + "\n\n### CAP-auth-NFR-1: Fast sign in")


def test_capacidad_nueva_y_varias_capacidades(tmp_path: Path) -> None:
    project = _project(tmp_path, _with_billing(DELTA))
    result = specs.merge(project, "demo")
    assert [(c.name, c.action) for c in result.capabilities] == [("auth", "update"), ("billing", "create")]
    billing = (project / "specs" / "capabilities" / "billing" / "spec.md").read_text(encoding="utf-8")
    assert billing.startswith("# Capability: billing\n\n## Purpose\n")
    assert "#### Scenario: First day" in billing
    assert billing.endswith("- Then they get an invoice\n")
    assert any("billing" in note and "Purpose" in note for note in result.notes)


def test_crlf_y_bytes_fuera_de_los_bloques(tmp_path: Path) -> None:
    project = _project(tmp_path, auth=None)
    _write(project / "specs" / "capabilities" / "auth" / "spec.md", AUTH, newline="\r\n")
    specs.merge(project, "demo")
    raw = (project / "specs" / "capabilities" / "auth" / "spec.md").read_bytes()
    assert raw == AUTH_MERGED.replace("\n", "\r\n").encode("utf-8")


def test_snapshot_antes_de_escribir(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = specs.merge(project, "demo")
    assert result.snapshot is not None
    [snap] = snapshots.list_snapshots(project)
    archive = snapshots.read_archive(snap.path.read_bytes())
    assert archive.files["specs/capabilities/auth/spec.md"][0] == AUTH.encode("utf-8")


def test_dry_run_no_escribe(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = specs.merge(project, "demo", dry_run=True)
    assert result.written is False
    assert result.capabilities[0].action == "update"
    assert _auth(project) == AUTH
    assert snapshots.list_snapshots(project) == []


def test_change_sin_delta(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "specs" / "demo" / "spec.md").unlink()
    result = specs.merge(project, "demo")
    assert result.capabilities == []
    assert result.written is False
    assert any("no spec.md" in note for note in result.notes)


def test_delta_con_errores_de_formato(tmp_path: Path) -> None:
    project = _project(tmp_path, DELTA.replace("### CAP-auth-FR-3:", "### FR-3:"))
    with pytest.raises(MergeError) as info:
        specs.merge(project, "demo")
    assert any("malformed requirement ID" in m for m in info.value.problems)


def test_change_inexistente(tmp_path: Path) -> None:
    with pytest.raises(MergeError, match="no-existe"):
        specs.merge(_project(tmp_path), "no-existe")


def test_listar_capacidades(tmp_path: Path) -> None:
    project = _project(tmp_path)
    specs.merge(project, "demo")
    [info] = specs.list_capabilities(project)
    assert (info.name, info.path) == ("auth", "specs/capabilities/auth/spec.md")
    assert (info.functional, info.non_functional, info.removed, info.problems) == (2, 1, 1, 0)


# -- CLI ------------------------------------------------------------------------------


def test_cli_specs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = _project(tmp_path)
    assert main(["specs", "merge", "demo", "--project", str(project), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "would update specs/capabilities/auth/spec.md" in out
    assert _auth(project) == AUTH
    assert main(["specs", "merge", "demo", "--project", str(project), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["written"] is True
    assert payload["capabilities"][0]["ops"][0] == {"id": "CAP-auth-FR-3", "action": "add", "status": "applied"}
    assert main(["specs", "merge", "demo", "--project", str(project)]) == 0
    assert "unchanged" in capsys.readouterr().out
    assert main(["specs", "list", "--project", str(project)]) == 0
    assert "auth" in capsys.readouterr().out
    assert main(["specs", "list", "--project", str(project), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["capabilities"][0]["name"] == "auth"


def test_cli_specs_merge_con_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = _project(tmp_path, DELTA.replace("### CAP-auth-FR-1:", "### CAP-auth-FR-7:"))
    assert main(["specs", "merge", "demo", "--project", str(project)]) == 1
    err = capsys.readouterr().err
    assert "CAP-auth-FR-7 does not exist" in err
