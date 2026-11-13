"""`exo init/sync/status/add-agent/remove-agent/uninstall` (criterios 2, 3, 5, 6 y 7 de F2)."""

from __future__ import annotations

import builtins
import io
import json
from pathlib import Path

import pytest

from _projects import FIXTURES, tree
from exo import _meta, paths
from exo.adapters import detect
from exo.adapters.detect import Detection
from exo.cli import main
from exo.core import config, snapshots

AGENTS = "claude-code,copilot"


@pytest.fixture(autouse=True)
def _aislado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Las pruebas corren dentro de un agente real: la detección y la carpeta de
    # datos no pueden depender del entorno de la máquina.
    monkeypatch.setattr(detect, "detect", lambda project, env=None, which=None: [])
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(tmp_path / "datos-usuario"))
    monkeypatch.setattr("sys.stdin", io.StringIO(""))


def _init(root: Path, *extra: str) -> int:
    return main(["init", "--project", str(root), "--agents", AGENTS, "--yes", *extra])


def _outside_motor(files: dict[str, bytes]) -> dict[str, bytes]:
    return {k: v for k, v in files.items() if not k.startswith(_meta.PROJECT_DIR)}


def test_criterio_2_init_por_cli_igual_al_golden(tmp_path: Path, golden, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "p"
    root.mkdir()
    assert _init(root) == 0
    out = capsys.readouterr().out
    assert "done:" in out
    golden("claude-copilot__vacio", tree(root))


def test_criterio_3_sync_sin_cambios(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "p"
    root.mkdir()
    _init(root)
    snaps = snapshots.list_snapshots(root)
    capsys.readouterr()
    assert main(["sync", "--project", str(root)]) == 0
    assert "no changes" in capsys.readouterr().out
    assert main(["init", "--project", str(root), "--yes"]) == 0
    assert "no changes" in capsys.readouterr().out
    assert snapshots.list_snapshots(root) == snaps


def test_criterio_5_conflicto_y_force(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "p"
    root.mkdir()
    _init(root)
    skill = root / ".claude" / "skills" / "hello-exo" / "SKILL.md"
    original = skill.read_bytes()
    skill.write_bytes(b"editado a mano\n")
    capsys.readouterr()
    assert main(["sync", "--project", str(root)]) == 1
    out = capsys.readouterr().out
    assert "conflict: .claude/skills/hello-exo/SKILL.md" in out
    assert "nothing was written" in out
    assert skill.read_bytes() == b"editado a mano\n"
    assert main(["sync", "--project", str(root), "--force"]) == 0
    assert "snapshot before the changes" in capsys.readouterr().out
    assert skill.read_bytes() == original


@pytest.mark.parametrize("fixture", sorted(FIXTURES))
def test_criterio_6_init_y_uninstall_dejan_el_proyecto_igual(tmp_path: Path, fixture: str, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "p"
    FIXTURES[fixture](root)
    original = tree(root)
    extra = ["--mcp"] if fixture in ("mcp-jsonc", "settings-compacto") else []
    assert _init(root, *extra) == 0
    assert tree(root) != original
    assert main(["uninstall", "--project", str(root), "--yes"]) == 0
    assert tree(root) == original
    assert not (root / _meta.PROJECT_DIR).exists()
    backups = list((paths.user_data_dir() / "uninstall-backups").iterdir())
    assert len(backups) == 1
    archive = snapshots.read_archive(backups[0].read_bytes())
    assert f"{_meta.PROJECT_DIR}/config.json" in archive.files
    assert "safety backup" in capsys.readouterr().out


def test_criterio_7_add_agent_cursor_solo_agrega_lo_de_cursor(tmp_path: Path) -> None:
    root = tmp_path / "p"
    FIXTURES["agents-humano"](root)
    _init(root)
    before = tree(root)
    assert main(["add-agent", "cursor", "--project", str(root)]) == 0
    after = tree(root)
    added = sorted(set(after) - set(before))
    assert added and all(path.startswith(".agents/skills/") for path in added)
    changed = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    assert changed == [f"{_meta.PROJECT_DIR}/config.json", f"{_meta.PROJECT_DIR}/lock.json"]
    assert config.load(root).config["agents"] == ["claude-code", "copilot", "cursor"]
    assert main(["remove-agent", "cursor", "--project", str(root)]) == 0
    assert tree(root) == before


def test_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "p"
    root.mkdir()
    assert main(["status", "--project", str(root)]) == 0
    assert "not installed" in capsys.readouterr().out
    _init(root)
    (root / ".claude" / "agents" / "sdd-judge.md").write_bytes(b"tocado")
    capsys.readouterr()
    assert main(["status", "--project", str(root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["installed"] is True
    assert payload["agents"] == ["claude-code", "copilot"]
    assert payload["drift"] == [{"path": ".claude/agents/sdd-judge.md", "kind": "mirror", "status": "modified"}]
    assert main(["status", "--project", str(root)]) == 0
    assert "manual change: .claude/agents/sdd-judge.md" in capsys.readouterr().out


def test_init_detecta_agentes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found = [Detection("claude-code", 3, ("env var CLAUDECODE",)), Detection("codex", 1, ("executable codex",))]
    monkeypatch.setattr(detect, "detect", lambda project, env=None, which=None: found)
    assert main(["init", "--project", str(tmp_path), "--yes"]) == 0
    assert config.load(tmp_path).config["agents"] == ["claude-code"]


def test_init_sin_agentes_detectados_instala_la_base(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init", "--project", str(tmp_path), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "generic base" in out
    assert (tmp_path / ".agents" / "skills" / "hello-exo" / "SKILL.md").is_file()
    assert config.load(tmp_path).config["agents"] == ["generic"]


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def _answers(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    pending = iter(answers)
    monkeypatch.setattr("sys.stdin", _Tty(""))
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(pending))


def test_wizard_interactivo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    found = [Detection("copilot", 2, ("file .github/copilot-instructions.md",))]
    monkeypatch.setattr(detect, "detect", lambda project, env=None, which=None: found)
    _answers(monkeypatch, "", "", "jira", "PROJ", "y")
    assert main(["init", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "[x] copilot" in out
    assert "About to apply" in out
    cfg = config.load(tmp_path).config
    assert cfg["agents"] == ["copilot"]
    assert cfg["tracker"] == {"type": "jira", "prefix": "PROJ", "prefixes": []}


def test_wizard_cancelado_no_escribe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _answers(monkeypatch, "claude-code", "core", "", "n")
    assert main(["init", "--project", str(tmp_path)]) == 1
    assert "cancelled" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_dry_run_y_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _init(tmp_path, "--dry-run") == 0
    assert "dry-run" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []
    assert _init(tmp_path, "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["applied"] is True
    assert payload["agents"] == ["claude-code", "copilot"]
    assert {a["action"] for a in payload["actions"]} == {"create"}


@pytest.mark.parametrize(
    ("argv", "code", "fragment"),
    [
        (["sync"], 1, "not installed"),
        (["add-agent", "cursor"], 1, "not installed"),
        (["init", "--agents", "windsurf", "--yes"], 1, "unknown agent"),
        (["init", "--packs", "fantasma", "--yes", "--agents", "generic"], 1, "fantasma"),
        (["uninstall"], 2, "--yes"),
    ],
)
def test_errores(tmp_path: Path, capsys: pytest.CaptureFixture[str], argv: list[str], code: int, fragment: str) -> None:
    assert main([*argv, "--project", str(tmp_path)]) == code
    assert fragment in capsys.readouterr().err


def test_remove_agent_que_no_esta(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    assert main(["remove-agent", "cursor", "--project", str(tmp_path)]) == 1
    assert "is not one of the project agents" in capsys.readouterr().err


def test_uninstall_con_conflicto_no_borra_nada(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    (tmp_path / ".claude" / "agents" / "sdd-judge.md").write_bytes(b"tocado")
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 1
    assert (tmp_path / _meta.PROJECT_DIR / "lock.json").exists()
    assert main(["uninstall", "--project", str(tmp_path), "--yes", "--force"]) == 0
    assert not (tmp_path / _meta.PROJECT_DIR).exists()


@pytest.mark.parametrize(
    "broken",
    ['{"agents": ["claude-code"], // comentario\n}', '{"schema": 99}', '{"schema": 1, "agents": "claude-code"}'],
    ids=["jsonc", "esquema-futuro", "campo-invalido"],
)
def test_config_rota_aborta_sin_tocar_nada(tmp_path: Path, broken: str, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    config.config_path(tmp_path).write_text(broken, encoding="utf-8")
    before = tree(tmp_path)
    capsys.readouterr()
    for argv in (["sync"], ["add-agent", "cursor"], ["init", "--yes"]):
        assert main([*argv, "--project", str(tmp_path)]) == 1
        assert "config.json" in capsys.readouterr().err
    assert tree(tmp_path) == before


def test_config_invalida_por_flags_no_escribe_nada(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _init(tmp_path, "--tracker", "jira", "--prefix", "proj") == 1
    assert "tracker.prefix" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_sync_no_reescribe_la_config_del_humano(tmp_path: Path) -> None:
    _init(tmp_path)
    path = config.config_path(tmp_path)
    compact = json.dumps(json.loads(path.read_text(encoding="utf-8"))).encode()
    path.write_bytes(compact)
    assert main(["sync", "--project", str(tmp_path)]) == 0
    assert main(["init", "--project", str(tmp_path), "--yes"]) == 0
    assert path.read_bytes() == compact


def test_la_config_y_el_lock_van_en_el_snapshot(tmp_path: Path) -> None:
    _init(tmp_path)
    motor = tmp_path / _meta.PROJECT_DIR
    before = {name: (motor / name).read_bytes() for name in ("config.json", "lock.json")}
    assert main(["add-agent", "cursor", "--project", str(tmp_path)]) == 0
    newest = snapshots.list_snapshots(tmp_path)[-1]
    archive = snapshots.read_archive(newest.path.read_bytes())
    for name, data in before.items():
        assert archive.files[f"{_meta.PROJECT_DIR}/{name}"][0] == data


def test_wizard_normaliza_y_repregunta_el_tracker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _answers(monkeypatch, "claude-code", "", "Trello", "Jira", "1x", "proj", "y")
    assert main(["init", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.count("invalid value") == 2
    assert config.load(tmp_path).config["tracker"] == {"type": "jira", "prefix": "PROJ", "prefixes": []}


def _romper_marcador(root: Path) -> None:
    agents = root / "AGENTS.md"
    end = f"<!-- END:{_meta.BLOCK_PREFIX}:core -->"
    agents.write_text(agents.read_text(encoding="utf-8").replace(end, ""), encoding="utf-8")


def test_force_informa_lo_que_no_pudo_resolver(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    _romper_marcador(tmp_path)
    skill = tmp_path / ".claude" / "skills" / "hello-exo" / "SKILL.md"
    original = skill.read_bytes()
    skill.write_bytes(b"editado\n")
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path), "--force"]) == 1
    out = capsys.readouterr().out
    assert "forced: .claude/skills/hello-exo/SKILL.md" in out
    assert "unresolved: AGENTS.md" in out
    assert skill.read_bytes() == original
    assert main(["uninstall", "--project", str(tmp_path), "--yes", "--force"]) == 1
    assert "unresolved: AGENTS.md" in capsys.readouterr().out
    assert (tmp_path / _meta.PROJECT_DIR / "lock.json").is_file()


def test_force_con_dry_run_muestra_lo_que_haria(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    skill = tmp_path / ".claude" / "skills" / "hello-exo" / "SKILL.md"
    skill.write_bytes(b"editado\n")
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path), "--force", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "would force: .claude/skills/hello-exo/SKILL.md" in out
    assert skill.read_bytes() == b"editado\n"


def test_uninstall_avisa_lo_del_humano_en_la_carpeta_del_motor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    notes = tmp_path / _meta.PROJECT_DIR / "notas.md"
    notes.write_bytes(b"mis notas\n")
    capsys.readouterr()
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 0
    out = capsys.readouterr().out
    assert f"{_meta.PROJECT_DIR}/notas.md" in out
    backup = next((paths.user_data_dir() / "uninstall-backups").iterdir())
    assert snapshots.read_archive(backup.read_bytes()).files[f"{_meta.PROJECT_DIR}/notas.md"][0] == b"mis notas\n"


def test_uninstall_dos_veces(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 0
    capsys.readouterr()
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 0
    assert "nothing to do" in capsys.readouterr().out


def test_init_no_interactivo_informa_las_detecciones_debiles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    found = [Detection("claude-code", 3, ("env var CLAUDECODE",)), Detection("codex", 1, ("executable codex",))]
    monkeypatch.setattr(detect, "detect", lambda project, env=None, which=None: found)
    assert main(["init", "--project", str(tmp_path), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "detected: claude-code (env var CLAUDECODE)" in out
    assert "unconfirmed: codex (executable codex)" in out
    assert f"{_meta.NAME} add-agent codex" in out


def test_salida_sin_notas_vacias_ni_lineas_repetidas(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    assert "notes" not in capsys.readouterr().out
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 0
    assert capsys.readouterr().out.count("remove\t.claude/settings.json") == 1


def test_sin_config_pero_con_lock_usa_lo_del_lock(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init", "--project", str(tmp_path), "--agents", "claude-code", "--yes"]) == 0
    config.config_path(tmp_path).unlink()
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "remove" not in out
    assert "using the agents and packs from the lock" in out
    assert main(["init", "--project", str(tmp_path), "--yes", "--dry-run"]) == 0
    assert "remove" not in capsys.readouterr().out
    assert main(["add-agent", "copilot", "--project", str(tmp_path)]) == 0
    assert config.load(tmp_path).config["agents"] == ["claude-code", "copilot"]
    assert (tmp_path / ".claude" / "skills" / "hello-exo" / "SKILL.md").is_file()


def test_uninstall_no_lista_archivos_del_motor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    capsys.readouterr()
    assert main(["uninstall", "--project", str(tmp_path), "--yes", "--dry-run"]) == 0
    assert "also removed" not in capsys.readouterr().out


def test_uninstall_json_sin_instalar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["uninstall", "--project", str(tmp_path), "--yes", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["installed"] is False


def test_remove_agent_con_config_rota_explica_la_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    config.config_path(tmp_path).write_text("{ roto", encoding="utf-8")
    capsys.readouterr()
    assert main(["remove-agent", "copilot", "--project", str(tmp_path)]) == 1
    assert "config.json cannot be used" in capsys.readouterr().err


def test_lock_corrupto_da_error_sin_traceback(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    (tmp_path / _meta.PROJECT_DIR / "lock.json").write_text("{ roto", encoding="utf-8")
    capsys.readouterr()
    for argv in (["sync"], ["add-agent", "cursor"]):
        assert main([*argv, "--project", str(tmp_path)]) == 1
        assert "lock.json" in capsys.readouterr().err


def test_force_dry_run_con_algo_sin_resolver_no_dice_que_aplico(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    _romper_marcador(tmp_path)
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path), "--force", "--dry-run"]) == 1
    out = capsys.readouterr().out
    assert "the rest would be applied" in out
    assert "the rest was applied" not in out
