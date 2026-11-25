"""Followups, `exo gate publish` y el host del repo (F5, D-30, ADR-0014)."""

from __future__ import annotations

import json
import os
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
    results = gates.publish(tmp_path, "add-login", approve=cfg["review"]["publish_command"])
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
    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    assert main([*argv, "--approve-command", cfg["review"]["publish_command"]]) == 1
    assert "code_review" in capsys.readouterr().err


# -- solo comandos aprobados en esta máquina (threat model, TM-21) ----------------------------


@pytest.fixture(autouse=True)
def _aprobaciones_por_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cada test arranca sin comandos aprobados."""
    from exo import paths

    monkeypatch.setenv(paths.ENV_DATA_DIR, str(tmp_path / "datos-usuario"))


def _marker_command(tmp_path: Path) -> tuple[str, Path]:
    marker = tmp_path / "corrio.txt"
    script = tmp_path / "marca.py"
    script.write_text(
        f"import pathlib\npathlib.Path({str(marker)!r}).write_text('si')\n", encoding="utf-8"
    )
    return f'"{Path(sys.executable).as_posix()}" "{script.as_posix()}"', marker


def test_un_comando_sin_aprobar_no_corre(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    command, marker = _marker_command(tmp_path)
    cfg = config.defaults()
    cfg["review"]["publish_command"] = command
    config.save(tmp_path, cfg)
    with pytest.raises(gates.CommandNotApproved, match="approve-command"):
        gates.publish(tmp_path, "add-login")
    assert not marker.exists()

    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    assert main(argv) == 1  # sin TTY no pregunta: se niega y dice cómo aprobarlo
    err = capsys.readouterr().err
    assert command in err and "--approve-command" in err
    assert not marker.exists()

    # El texto tiene que ser el de la config: la persona ve lo que aprueba (M-1, punto 4).
    assert main([*argv, "--approve-command", "otro comando"]) == 1
    assert "does not match" in capsys.readouterr().err and not marker.exists()
    assert main(argv) == 1  # y no quedó aprobado
    capsys.readouterr()
    assert main([*argv, "--approve-command", command]) == 0
    assert marker.exists()
    marker.unlink()
    assert main(argv) == 0  # ya aprobado en esta máquina
    assert marker.exists()

    marker.unlink()
    cfg["review"]["publish_command"] = command + " --otro"  # otro comando: otra aprobación
    config.save(tmp_path, cfg)
    assert main(argv) == 1
    assert not marker.exists()
    # --dry-run nunca ejecuta y no necesita aprobación.
    assert main([*argv, "--dry-run"]) == 0


@pytest.mark.parametrize(("answer", "code", "ran"), [("y", 0, True), ("n", 1, False)])
def test_en_una_terminal_pregunta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    answer: str,
    code: int,
    ran: bool,
) -> None:
    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    command, marker = _marker_command(tmp_path)
    cfg = config.defaults()
    cfg["review"]["publish_command"] = command
    config.save(tmp_path, cfg)
    asked: list[str] = []
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or answer)
    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    assert main(argv) == code
    assert marker.exists() is ran
    out = capsys.readouterr().out
    assert asked and command in out
    # Muestra también los archivos del proyecto que nombra el comando: la aprobación los cubre.
    assert "marca.py" in out.split(command, 1)[1]


def test_aprobaciones_ilegibles(tmp_path: Path) -> None:
    from exo import paths
    from exo.governance import approvals

    folder = Path(os.environ[paths.ENV_DATA_DIR])
    folder.mkdir(parents=True)
    (folder / approvals.FILE_NAME).write_text("{roto", encoding="utf-8")
    with pytest.raises(approvals.ApprovalError, match=approvals.FILE_NAME):
        approvals.check(tmp_path, "echo hola")


# -- la aprobación cubre el proyecto y los archivos que corre (F8R1-1) ------------------------


def _relative_marker(project_dir: Path) -> tuple[str, Path, Path]:
    """Un comando que corre un script del proyecto por su ruta relativa."""
    marker = project_dir / "corrio.txt"
    script = project_dir / "scripts" / "publicar.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        f"import pathlib\npathlib.Path({str(marker)!r}).write_text('si')\n", encoding="utf-8"
    )
    return f'"{Path(sys.executable).as_posix()}" scripts/publicar.py', marker, script


def _configure(project_dir: Path, command: str | None) -> None:
    cfg = config.defaults()
    cfg["review"]["publish_command"] = command
    config.save(project_dir, cfg)


def test_un_archivo_que_corre_el_comando_y_cambio_vuelve_a_pedir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    command, marker, script = _relative_marker(tmp_path)
    _configure(tmp_path, command)
    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    assert main(argv) == 1
    err = capsys.readouterr().err
    assert "scripts/publicar.py" in err  # sin TTY también dice qué cubre la aprobación
    assert main([*argv, "--approve-command", command]) == 0
    assert marker.exists()
    marker.unlink()
    assert main(argv) == 0  # sin cambios, no vuelve a preguntar
    assert marker.exists()
    marker.unlink()

    # La rama cambia el script: el texto del comando es el mismo, pero lo que corre no.
    script.write_text(script.read_text(encoding="utf-8") + "# otro\n", encoding="utf-8")
    capsys.readouterr()
    assert main(argv) == 1
    err = capsys.readouterr().err
    assert "changed" in err and "scripts/publicar.py" in err
    assert not marker.exists()
    assert main([*argv, "--approve-command", command]) == 0
    assert marker.exists()


def test_la_aprobacion_queda_atada_al_proyecto(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first, second = tmp_path / "uno", tmp_path / "dos"
    command, marker = _marker_command(tmp_path)  # el script queda fuera de los dos proyectos
    for root in (first, second):
        root.mkdir()
        _change(root, {"gates/code_review.md": gate("code_review")})
        _configure(root, command)
    publish = ["gate", "publish", "--change", "add-login", "--project"]
    assert main([*publish, str(first), "--approve-command", command]) == 0
    assert marker.exists()
    marker.unlink()
    capsys.readouterr()
    # El mismo texto en otro repo de la máquina no está aprobado.
    assert main([*publish, str(second)]) == 1
    assert str(second.resolve()) in capsys.readouterr().err
    assert not marker.exists()
    assert main([*publish, str(first)]) == 0


def test_lo_que_cubre_la_aprobacion(tmp_path: Path) -> None:
    from exo.governance import approvals

    for rel in ("scripts/publish-gate.sh", "body.md", "tools/run.py", "notes/a b.sh"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("echo\n", encoding="utf-8")
    (tmp_path / "carpeta").mkdir()
    outside = tmp_path.parent / f"{tmp_path.name}-afuera.sh"
    outside.write_text("echo\n", encoding="utf-8")
    command = (
        f'sh scripts/publish-gate.sh && "{(tmp_path / "tools" / "run.py").as_posix()}" '
        f"--body=body.md carpeta 'notes/a b.sh' {outside.as_posix()} missing.sh|cat"
    )
    covered = approvals.covered_files(tmp_path, command)
    assert sorted(covered) == ["body.md", "notes/a b.sh", "scripts/publish-gate.sh", "tools/run.py"]
    assert approvals.covered_files(tmp_path, "gh pr comment 1 --body-file x") == {}
    # Comillas sin cerrar: se parte por espacios.
    assert list(approvals.covered_files(tmp_path, "sh scripts/publish-gate.sh '")) == [
        "scripts/publish-gate.sh"
    ]


@pytest.mark.skipif(sys.platform != "win32", reason="rutas de cmd")
def test_lo_que_cubre_la_aprobacion_con_barras_de_windows(tmp_path: Path) -> None:
    from exo.governance import approvals

    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "publish.cmd").write_text("@echo off\n", encoding="utf-8")
    assert list(approvals.covered_files(tmp_path, r"cmd /c scripts\publish.cmd")) == [
        "scripts/publish.cmd"
    ]


def test_aprobaciones_de_una_version_anterior(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """El esquema 1 guardaba solo el SHA256 del texto: no dice para qué proyecto ni qué archivos,
    así que no alcanza. Se toma como no aprobado y se vuelve a pedir; al aprobar se reescribe."""
    import hashlib

    from exo import paths
    from exo.governance import approvals

    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    command, marker = _marker_command(tmp_path)
    _configure(tmp_path, command)
    folder = Path(os.environ[paths.ENV_DATA_DIR])
    folder.mkdir(parents=True)
    old = {
        "schema": 1,
        "commands": {
            hashlib.sha256(command.encode("utf-8")).hexdigest(): {
                "command": command,
                "approved_at": "2026-11-20T10:00:00+00:00",
            }
        },
    }
    (folder / approvals.FILE_NAME).write_text(json.dumps(old), encoding="utf-8")
    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    assert main(argv) == 1
    err = capsys.readouterr().err
    assert "earlier" in err and "--approve-command" in err
    assert not marker.exists()
    assert main([*argv, "--approve-command", command]) == 0
    assert marker.exists()
    saved = json.loads((folder / approvals.FILE_NAME).read_text(encoding="utf-8"))
    assert saved["schema"] == approvals.SCHEMA
    assert [e["command"] for e in saved["approvals"].values()] == [command]


def test_aprobaciones_de_un_exo_mas_nuevo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from exo import paths
    from exo.governance import approvals

    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    command, marker = _marker_command(tmp_path)
    _configure(tmp_path, command)
    folder = Path(os.environ[paths.ENV_DATA_DIR])
    folder.mkdir(parents=True)
    newer = b'{"schema": 99, "approvals": {}}'
    (folder / approvals.FILE_NAME).write_bytes(newer)
    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    for extra in ([], ["--approve-command", command]):
        assert main([*argv, *extra]) == 1
        err = capsys.readouterr().err
        assert "newer" in err and "upgrade exo" in err.lower()
        assert "delete" not in err
    assert (folder / approvals.FILE_NAME).read_bytes() == newer  # no se pisa
    assert not marker.exists()


def test_approve_command_sin_publish_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    assert main([*argv, "--approve-command", "sh publish.sh"]) == 1
    err = capsys.readouterr().err
    assert "None" not in err
    assert "review.publish_command is not set" in err


def test_gate_publish_lee_la_config_una_vez(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _change(tmp_path, {"gates/code_review.md": gate("code_review")})
    command, marker = _marker_command(tmp_path)
    _configure(tmp_path, command)
    callers: list[str] = []
    real = config.load

    def spy(project: Path) -> config.LoadResult:
        callers.append(sys._getframe(1).f_globals["__name__"])
        return real(project)

    monkeypatch.setattr(config, "load", spy)
    argv = ["gate", "publish", "--change", "add-login", "--project", str(tmp_path)]
    assert main([*argv, "--approve-command", command]) == 0
    assert marker.exists()
    # El texto que se compara es el que corre: una sola lectura, en gates.publish.
    assert callers.count("exo.governance.gates") == 1
    assert "exo.commands.gate" not in callers
    # gates.publish aprueba solo el texto que coincide con la config que leyó.
    with pytest.raises(gates.CommandMismatch, match="does not match"):
        gates.publish(tmp_path, "add-login", approve=command + " --otro")


def test_codeowners_suma_lo_que_corre_publish_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "publish-gate.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    cfg = config.defaults()
    cfg["governance"]["roles"]["tech_lead"] = ["@ana"]
    cfg["review"]["publish_command"] = "sh scripts/publish-gate.sh && sh scripts/missing.sh"
    config.save(tmp_path, cfg)
    assert main(["codeowners", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "/scripts/publish-gate.sh @ana" in out
    assert "missing.sh" not in out


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
