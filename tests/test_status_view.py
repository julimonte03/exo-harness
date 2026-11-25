"""`exo status` enriquecido (F8): la vista de terminal del proyecto y de sus changes."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from _git import init_repo
from exo import _meta, paths, status_view
from exo.cli import main
from exo.sdd import changes
from test_check_f5 import gate

FOLLOWUP = {
    "id": "JSEC-1",
    "judge": "judge-security",
    "rule": "CWE-89, A05:2025 Injection",
    "severity": "high",
    "summary": "User input reaches the SQL query unescaped",
    "location": "src/auth/login.py:42",
}
ESC = "\x1b["


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(tmp_path / "datos"))
    root = tmp_path / "p"
    root.mkdir()
    init_repo(root)
    argv = ["init", "--project", str(root), "--agents", "claude-code", "--packs", "core,sdd", "--yes"]
    assert main(argv) == 0
    return root


def _status(root: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> str:
    capsys.readouterr()
    assert main(["status", "--project", str(root), *extra]) == 0
    return capsys.readouterr().out


def test_proyecto_sin_changes(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = _status(project, capsys)
    assert ESC not in out  # capsys no es una TTY: sin colores
    lines = out.splitlines()
    assert "agents: claude-code" in lines
    assert "packs: core, sdd" in lines
    assert f"engine: {_meta.VERSION} (lock written by {_meta.VERSION})" in lines
    assert any(line.startswith("hooks: ok") for line in lines)
    assert f"persona: none (`{_meta.NAME} persona set <role>`)" in lines
    assert "no manual changes to generated files" in lines
    assert "changes: none active" in lines


def test_changes_con_gates_y_followups(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    created = changes.new_change(project, "add-login")
    gates = project / created.path / "gates"
    gates.mkdir()
    (gates / "code_review.md").write_text(gate("code_review"), encoding="utf-8")
    (gates / "security_review.md").write_text(
        gate("security_review", "ESCALATED", "yes"), encoding="utf-8"
    )
    changes.add_followup(project, "add-login", FOLLOWUP)
    assert main(["persona", "set", "tech-lead"]) == 0
    (project / ".claude" / "agents" / "sdd-judge.md").write_bytes(b"tocado")

    out = _status(project, capsys)
    assert "persona: tech-lead" in out
    assert "manual change: .claude/agents/sdd-judge.md (mirror): modified" in out
    assert "changes: 1 active" in out
    [row] = [line for line in out.splitlines() if "add-login" in line]
    assert "Tier 4 (unclassified)" in row  # sin fitness-assessment.json
    assert "next: risk" in row
    detail = out.split(row, 1)[1]
    assert "gates: code_review APPROVED, security_review ESCALATED (needs tech_lead)" in detail
    assert "followups: 1 open" in detail


def test_persona_ilegible_no_corta_la_vista(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F8R1-14: un `persona.json` que no se puede leer se muestra como aviso."""
    from exo import persona

    persona.file_path().mkdir(parents=True)  # una carpeta: leerla da OSError
    out = _status(project, capsys)
    [line] = [line for line in out.splitlines() if line.startswith("persona:")]
    assert "warning" in line and persona.FILE_NAME in line


def test_lock_de_otra_version_sugiere_update(
    project: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    written = _meta.VERSION
    monkeypatch.setattr(_meta, "VERSION", "9.9.9")
    out = _status(project, capsys)
    assert f"engine: 9.9.9 (lock written by {written}; run `{_meta.NAME} update`)" in out


def test_lock_de_un_motor_mas_nuevo_pide_actualizar_el_motor(
    project: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """F8R1-5: `exo update` lo rechaza; como `exo doctor`, hay que actualizar exo."""
    written = _meta.VERSION
    monkeypatch.setattr(_meta, "VERSION", "0.0.1")
    out = _status(project, capsys)
    assert f"engine: 0.0.1 (lock written by {written}; upgrade {_meta.NAME})" in out
    assert "run `" not in out.split("engine:", 1)[1].splitlines()[0]


def test_json_sin_cambios(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    payload = json.loads(_status(project, capsys, "--json"))
    assert sorted(payload) == sorted(
        [
            "schema",
            "installed",
            "agents",
            "packs",
            "engine_version",
            "lock_version",
            "files",
            "drift",
            "warnings",
        ]
    )


def test_sin_instalar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["status", "--project", str(tmp_path)]) == 0
    assert capsys.readouterr().out == f"the engine is not installed; run `{_meta.NAME} init`\n"


class _Stream(io.StringIO):
    def __init__(self, tty: bool) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


@pytest.mark.parametrize(
    ("tty", "env", "expected"),
    [
        (True, {}, True),
        (False, {}, False),
        (True, {"NO_COLOR": "1"}, False),
        (True, {"NO_COLOR": ""}, True),  # no-color.org: vacía no cuenta
        (True, {"TERM": "dumb"}, False),
    ],
)
def test_colores_solo_en_tty_y_sin_no_color(tty: bool, env: dict, expected: bool) -> None:
    assert status_view.use_color(_Stream(tty), env, windows=False) is expected


@pytest.mark.parametrize("vt", [True, False])
def test_en_windows_colores_solo_si_la_consola_acepta_ansi(
    monkeypatch: pytest.MonkeyPatch, vt: bool
) -> None:
    """F8R1-6: conhost muestra los códigos ANSI como basura si no se activa el modo VT."""
    asked: list[object] = []
    monkeypatch.setattr(status_view, "_enable_vt", lambda stream: asked.append(stream) or vt)
    stream = _Stream(True)
    assert status_view.use_color(stream, {}, windows=True) is vt
    assert asked == [stream]
    assert status_view.use_color(_Stream(False), {}, windows=True) is False
    assert len(asked) == 1  # sin TTY ni se intenta


class _Kernel32:
    """Lo que `_enable_vt` usa de kernel32: GetConsoleMode y SetConsoleMode."""

    def __init__(self, mode: int | None, settable: bool = True) -> None:
        self.mode, self.settable, self.set_to = mode, settable, None

    def GetConsoleMode(self, handle: int, ref: object) -> int:  # noqa: N802
        if self.mode is None:
            return 0  # no es una consola
        ref._obj.value = self.mode  # type: ignore[attr-defined]
        return 1

    def SetConsoleMode(self, handle: int, mode: int) -> int:  # noqa: N802
        self.set_to = mode
        return 1 if self.settable else 0


class _Console(io.StringIO):
    def fileno(self) -> int:
        return 1


@pytest.mark.parametrize(
    ("kernel32", "expected", "set_to"),
    [
        (_Kernel32(0x0003), True, 0x0007),  # se activa
        (_Kernel32(0x0007), True, None),  # ya estaba activo
        (_Kernel32(0x0003, settable=False), False, 0x0007),  # consola vieja: sin color
        (_Kernel32(None), False, None),  # no es una consola
    ],
)
def test_activar_el_modo_vt(kernel32: _Kernel32, expected: bool, set_to: int | None) -> None:
    handles: list[int] = []
    got = status_view._enable_vt(
        _Console(), kernel32=kernel32, get_handle=lambda fd: handles.append(fd) or 42
    )
    assert got is expected
    assert kernel32.set_to == set_to and handles == [1]
    assert status_view._enable_vt(io.StringIO(), kernel32=kernel32, get_handle=int) is False


def test_con_colores_marca_el_estado(project: Path) -> None:
    view = status_view.gather(project)
    plain = status_view.render(view, status_view.Style(color=False))
    colored = status_view.render(view, status_view.Style(color=True))
    assert not any(ESC in line for line in plain)
    assert any(ESC in line for line in colored)
    strip = status_view.Style.strip
    assert [strip(line) for line in colored] == plain
