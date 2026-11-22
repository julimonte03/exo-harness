"""Overlays de persona (D-17, ADR-0018): `exo persona set|show|clear` y los contratos."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from exo import _meta, paths, persona
from exo.cli import main

ROOT = Path(__file__).resolve().parents[1]
PERSONAS = ROOT / "content" / "packs" / "core" / "shared" / "personas"
BASE_RULES = ROOT / "content" / "rules" / "AGENTS.base.md"
SECTIONS = ("## Highlight", "## Your decisions", "## Judges first", "## Detail", "## Never")


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "datos"
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(folder))
    return folder


def _json(capsys: pytest.CaptureFixture[str]) -> dict:
    return json.loads(capsys.readouterr().out)


def _overlay(role: str) -> str:
    return f"{_meta.PROJECT_DIR}/shared/personas/{role}.md"


def test_sin_persona_show_dice_ninguna(
    data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["persona", "show", "--project", str(tmp_path), "--json"]) == 0
    assert _json(capsys) == {"schema": 1, "persona": None, "overlay": None, "installed": False}
    assert main(["persona", "show", "--project", str(tmp_path)]) == 0
    assert "no persona set" in capsys.readouterr().out
    assert not data_dir.exists()


def test_set_show_clear(data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["persona", "set", "qa"]) == 0
    assert "qa" in capsys.readouterr().out
    saved = json.loads((data_dir / persona.FILE_NAME).read_text(encoding="utf-8"))
    assert saved == {"schema": persona.SCHEMA, "persona": "qa"}

    assert main(["persona", "show", "--project", str(tmp_path), "--json"]) == 0
    assert _json(capsys) == {
        "schema": 1,
        "persona": "qa",
        "overlay": _overlay("qa"),
        "installed": False,
    }

    assert main(["persona", "clear"]) == 0
    assert "cleared" in capsys.readouterr().out
    assert not (data_dir / persona.FILE_NAME).exists()
    assert main(["persona", "clear"]) == 0
    assert "no persona was set" in capsys.readouterr().out


def test_show_dice_si_el_overlay_esta_instalado(
    data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["persona", "set", "tech-lead"]) == 0
    capsys.readouterr()
    assert main(["persona", "show", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "tech-lead" in out and "sync" in out  # no instalado: dice cómo arreglarlo

    overlay = tmp_path / _overlay("tech-lead")
    overlay.parent.mkdir(parents=True)
    overlay.write_bytes(b"# Persona overlay: tech-lead\n")
    assert main(["persona", "show", "--project", str(tmp_path), "--json"]) == 0
    assert _json(capsys)["installed"] is True


def test_init_instala_los_overlays_de_core(
    data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "proyecto"
    project.mkdir()
    assert main(["init", "--project", str(project), "--agents", "generic", "--yes"]) == 0
    for role in persona.ROLES:
        installed = project / _overlay(role)
        assert installed.read_bytes() == (PERSONAS / f"{role}.md").read_bytes()
    assert main(["persona", "set", "product"]) == 0
    capsys.readouterr()
    assert main(["persona", "show", "--project", str(project), "--json"]) == 0
    assert _json(capsys)["installed"] is True


def test_set_es_idempotente(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["persona", "set", "dev"]) == 0
    target = data_dir / persona.FILE_NAME
    before = target.stat().st_mtime_ns
    capsys.readouterr()
    assert main(["persona", "set", "dev"]) == 0
    assert "is already dev" in capsys.readouterr().out
    assert target.stat().st_mtime_ns == before


def test_rol_desconocido_es_error_de_uso(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["persona", "set", "admin"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "admin" in err and "tech-lead" in err
    assert not data_dir.exists()


@pytest.mark.parametrize(
    "raw",
    [
        b"{no es json",
        b'{"schema": 99, "persona": "qa"}',
        b'{"schema": 1, "persona": "admin"}',
        b'["qa"]',
    ],
)
def test_archivo_invalido_da_error_accionable(
    data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], raw: bytes
) -> None:
    data_dir.mkdir()
    (data_dir / persona.FILE_NAME).write_bytes(raw)
    assert main(["persona", "show", "--project", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "persona clear" in err
    # clear sirve justamente para salir de ese estado.
    assert main(["persona", "clear"]) == 0
    assert not (data_dir / persona.FILE_NAME).exists()


def test_cada_rol_tiene_su_overlay_y_nada_mas() -> None:
    files = sorted(path.stem for path in PERSONAS.glob("*.md"))
    assert files == sorted(persona.ROLES)


@pytest.mark.parametrize("role", persona.ROLES)
def test_overlay_corto_con_sus_secciones_y_sin_relajar(role: str) -> None:
    text = (PERSONAS / f"{role}.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= persona.MAX_OVERLAY_LINES
    assert lines[0] == f"# Persona overlay: {role}"
    for heading in SECTIONS:
        assert heading in lines, f"{role}: falta {heading}"
    never = text.split("## Never", 1)[1]
    # El overlay cambia qué se muestra y cómo, nunca qué se exige (ADR-0018).
    assert re.search(r"\brelax\b", never)
    assert "governance.roles" in text


def test_las_reglas_base_le_dicen_al_agente_como_leerlo() -> None:
    text = BASE_RULES.read_text(encoding="utf-8")
    assert "exo persona show --json" in text
    assert ".exo/shared/personas/<role>.md" in text
