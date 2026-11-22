"""Followups, `exo gate publish` y el host del repo (F5, D-30, ADR-0014)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from exo.cli import main
from exo.core import config
from exo.governance import gates, hosts
from exo.installer import project
from exo.sdd import changes, observability
from test_check_f5 import gate
from test_speclint import VERIFY

FOLLOWUP = {
    "id": "JSEC-1",
    "judge": "judge-security",
    "rule": "A05:2025",
    "severity": "high",
    "summary": "User input reaches the SQL query unescaped",
    "location": "src/auth/login.py:42",
}


def _change(project_dir: Path, files: dict[str, str]) -> Path:
    created = changes.new_change(project_dir, "add-login")
    folder = project_dir / created.path
    for rel, text in files.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(text, encoding="utf-8")
    return folder


# -- followups --------------------------------------------------------------------------------


def test_followups_se_escriben_validados_y_sin_duplicar(tmp_path: Path) -> None:
    folder = _change(tmp_path, {})
    assert changes.add_followup(tmp_path, "add-login", FOLLOWUP).changed is True
    assert changes.add_followup(tmp_path, "add-login", FOLLOWUP).changed is False
    data = json.loads((folder / "followups.json").read_text(encoding="utf-8"))
    assert data == {"followups": [FOLLOWUP]}
    listed = observability.followups(tmp_path, "add-login", "open")
    assert [f["id"] for f in listed] == ["JSEC-1"]
    with pytest.raises(changes.ChangeError, match="JSEC-1 is already used"):
        changes.add_followup(tmp_path, "add-login", {**FOLLOWUP, "summary": "other"})


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"id": "SEC-1"}, "id"),
        ({"severity": "urgent"}, "severity"),
        ({"summary": ""}, "summary"),
    ],
)
def test_followup_invalido(tmp_path: Path, change: dict, fragment: str) -> None:
    _change(tmp_path, {})
    with pytest.raises(changes.ChangeError, match=fragment):
        changes.add_followup(tmp_path, "add-login", {**FOLLOWUP, **change})


def test_cli_followup(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _change(tmp_path, {})
    entry = tmp_path / "f.json"
    entry.write_text(json.dumps(FOLLOWUP), encoding="utf-8")
    assert (
        main(
            ["change", "record", "add-login", "--followup", f"@{entry}", "--project", str(tmp_path)]
        )
        == 0
    )
    assert "updated" in capsys.readouterr().out


# -- gates -----------------------------------------------------------------------------------


def test_criterio_4_un_texto_por_gate_con_su_marcador(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _change(
        tmp_path,
        {
            "verify-record.md": VERIFY,
            "gates/code_review.md": gate("code_review"),
            "gates/security_review.md": gate("security_review", "ESCALATED", "yes"),
        },
    )
    texts = gates.collect(tmp_path, "add-login")
    assert [t.name for t in texts] == ["code_review", "contract_check", "security_review"]
    for text in texts:
        assert text.body.count(text.marker) == 1
    assert (
        main(["gate", "publish", "--change", "add-login", "--dry-run", "--project", str(tmp_path)])
        == 0
    )
    out = capsys.readouterr().out
    for name in ("code_review", "contract_check", "security_review"):
        assert out.count(f"<!-- exo-gate:{name} -->") == 1
    assert "dry-run" in out


def test_criterio_4_el_comando_propio_se_llama_una_vez_por_gate(tmp_path: Path) -> None:
    _change(
        tmp_path,
        {
            "gates/code_review.md": gate("code_review"),
            "gates/threat_model.md": gate("threat_model"),
        },
    )
    log = tmp_path / "calls.log"
    script = tmp_path / "publish.py"
    script.write_text(
        "import os, pathlib\n"
        f"log = pathlib.Path({str(log)!r})\n"
        "body = pathlib.Path(os.environ['EXO_GATE_BODY']).read_text(encoding='utf-8')\n"
        "line = os.environ['EXO_GATE'] + '|' + os.environ['EXO_GATE_MARKER'] + '|' + str(os.environ['EXO_GATE_MARKER'] in body)\n"
        "log.write_text((log.read_text() if log.exists() else '') + line + '\\n')\n",
        encoding="utf-8",
    )
    cfg = config.defaults()
    cfg["review"]["publish_command"] = f'"{Path(sys.executable).as_posix()}" "{script.as_posix()}"'
    config.save(tmp_path, cfg)
    results = gates.publish(tmp_path, "add-login")
    assert [r.status for r in results] == ["sent", "sent"]
    lines = log.read_text().splitlines()
    assert lines == [
        "code_review|<!-- exo-gate:code_review -->|True",
        "threat_model|<!-- exo-gate:threat_model -->|True",
    ]
    assert gates.publish(tmp_path, "add-login", dry_run=True)[0].status == "printed"
    assert log.read_text().splitlines() == lines  # dry-run nunca ejecuta


def test_un_comando_que_falla_se_informa(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    cfg = config.defaults()
    cfg["review"]["publish_command"] = (
        f'"{Path(sys.executable).as_posix()}" -c "raise SystemExit(3)"'
    )
    config.save(tmp_path, cfg)
    assert main(["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]) == 1
    assert "code_review" in capsys.readouterr().err


def test_sin_comando_se_imprime(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    assert (
        main(["gate", "publish", "--change", "add-login", "--project", str(tmp_path), "--json"])
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["gates"][0]["status"] == "printed"
    assert "<!-- exo-gate:code_review -->" in payload["gates"][0]["body"]


def test_sin_gates_y_change_inexistente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _change(tmp_path, {})
    assert main(["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]) == 0
    assert "no gates" in capsys.readouterr().out
    assert main(["gate", "publish", "--change", "zz", "--project", str(tmp_path)]) == 1


# -- host del repo ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("remote", "host"),
    [
        ("https://github.com/acme/app.git", "github"),
        ("git@github.com:acme/app.git", "github"),
        ("https://dev.azure.com/acme/Payments/_git/app", "azure-devops"),
        ("git@ssh.dev.azure.com:v3/acme/Payments/app", "azure-devops"),
        ("https://acme.visualstudio.com/Payments/_git/app", "azure-devops"),
        ("https://gitlab.com/acme/app.git", "gitlab"),
        ("https://gitlab.acme.internal/team/app.git", "gitlab"),
        ("https://git.acme.internal/team/app.git", "other"),
        ("not a remote", None),
    ],
)
def test_host_desde_el_remoto(remote: str, host: str | None) -> None:
    assert hosts.from_remote(remote) == host


@pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
def test_init_guarda_el_host_detectado(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", "git@github.com:acme/app.git"],
        check=True,
    )
    assert main(["init", "--project", str(tmp_path), "--agents", "generic", "--yes"]) == 0
    assert config.load(tmp_path).config["review"]["host"] == "github"
    assert "publish_command" in capsys.readouterr().out
    cfg = config.load(tmp_path).config
    cfg["review"]["host"] = "other"
    config.save(tmp_path, cfg)
    project.sync(tmp_path)
    assert config.load(tmp_path).config["review"]["host"] == "other"  # la persona manda


def test_flags_de_revision(tmp_path: Path) -> None:
    assert (
        main(
            [
                "init",
                "--project",
                str(tmp_path),
                "--agents",
                "generic",
                "--yes",
                "--review-host",
                "gitlab",
                "--publish-command",
                "./publish.sh",
            ]
        )
        == 0
    )
    assert config.load(tmp_path).config["review"] == {
        "host": "gitlab",
        "publish_command": "./publish.sh",
    }


def test_un_followup_arreglado_deja_de_estar_abierto(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = _change(tmp_path, {})
    changes.add_followup(tmp_path, "add-login", FOLLOWUP)
    assert changes.fix_followup(tmp_path, "add-login", "JSEC-1").changed is True
    assert changes.fix_followup(tmp_path, "add-login", "JSEC-1").changed is False
    data = json.loads((folder / "followups.json").read_text(encoding="utf-8"))
    assert data == {"followups": [{**FOLLOWUP, "fixed": True}]}
    assert observability.followups(tmp_path, "add-login", "open") == []
    assert [f["id"] for f in observability.followups(tmp_path, "add-login", "fixed")] == ["JSEC-1"]
    assert observability.change_state(tmp_path, "add-login")["followups"] == {
        "open": 0,
        "fixed": 1,
        "dismissed": 0,
    }
    # Volver a mandar el hallazgo original no choca con el que ya está arreglado.
    assert changes.add_followup(tmp_path, "add-login", FOLLOWUP).changed is False
    with pytest.raises(changes.ChangeError, match="JSEC-9"):
        changes.fix_followup(tmp_path, "add-login", "JSEC-9")
    assert (
        main(["change", "record", "add-login", "--fixed", "JSEC-1", "--project", str(tmp_path)])
        == 0
    )
    assert "unchanged" in capsys.readouterr().out


def test_un_descarte_con_id_no_descarta_otros_de_la_misma_regla(tmp_path: Path) -> None:
    _change(tmp_path, {})
    changes.add_followup(tmp_path, "add-login", FOLLOWUP)
    changes.add_followup(
        tmp_path, "add-login", {**FOLLOWUP, "id": "JSEC-2", "location": "src/a.py:1"}
    )
    dismissal = {
        "id": "JSEC-1",
        "judge": "judge-security",
        "rule": FOLLOWUP["rule"],
        "reason": "false positive",
    }
    changes.update_record(tmp_path, "add-login", add=[("dismissed_followups", dismissal)])
    states = {f["id"]: f["status"] for f in observability.followups(tmp_path, "add-login", "all")}
    assert states == {"JSEC-1": "dismissed", "JSEC-2": "open"}


def test_cli_followups_fixed_y_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _change(tmp_path, {})
    entry = json.dumps(FOLLOWUP)
    assert (
        main(
            [
                "change",
                "record",
                "add-login",
                "--followup",
                entry,
                "--json",
                "--project",
                str(tmp_path),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["followups"]["changed"] is True
    assert (
        main(["change", "record", "add-login", "--fixed", "JSEC-1", "--project", str(tmp_path)])
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "change",
                "followups",
                "add-login",
                "--status",
                "fixed",
                "--project",
                str(tmp_path),
                "--json",
            ]
        )
        == 0
    )
    assert "JSEC-1" in capsys.readouterr().out
    # Si el registro falla, el followup tampoco se escribe.
    other = json.dumps({**FOLLOWUP, "id": "JSEC-2"})
    bad = ["change", "record", "add-login", "--followup", other, "--add", "skills_used", "123"]
    assert main([*bad, "--project", str(tmp_path)]) != 0
    data = json.loads((folder / "followups.json").read_text(encoding="utf-8"))
    assert [f["id"] for f in data["followups"]] == ["JSEC-1"]


def test_publish_rechaza_marcadores_que_no_coinciden(tmp_path: Path) -> None:
    _change(
        tmp_path,
        {
            "gates/security_review.md": gate("code_review"),
            "gates/code_review.md": gate("code_review"),
        },
    )
    with pytest.raises(gates.GateError, match="security_review"):
        gates.collect(tmp_path, "add-login")


def test_contract_check_no_lee_el_comentario_de_la_plantilla(tmp_path: Path) -> None:
    from exo.sdd import speclint

    text = VERIFY.replace(
        "Requires tech_lead approval: no",
        "<!--\nRequires tech_lead approval: yes | no\n-->\nRequires tech_lead approval: no",
    )
    assert "yes | no" in text
    path = tmp_path / "verify-record.md"
    path.write_text(text, encoding="utf-8")
    assert speclint.contract_gate(path).needs_approval is False


def test_gate_con_digitos_en_el_nombre(tmp_path: Path) -> None:
    from exo.sdd import speclint

    path = tmp_path / "gates" / "owasp_a01.md"
    path.parent.mkdir()
    path.write_text(gate("owasp_a01"), encoding="utf-8")
    assert speclint.lint_path(path).ok
    assert speclint.gate_info(path).name == "owasp_a01"
