"""`exo init/sync/status/add-agent/remove-agent/uninstall` (criterios 2, 3, 5, 6 y 7 de F2)."""

from __future__ import annotations

import builtins
import io
import json
import shutil
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


def test_criterio_2_init_por_cli_igual_al_golden(
    tmp_path: Path, golden, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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
    skill = root / ".claude" / "skills" / "memory-protocol" / "SKILL.md"
    original = skill.read_bytes()
    skill.write_bytes(b"editado a mano\n")
    capsys.readouterr()
    assert main(["sync", "--project", str(root)]) == 1
    out = capsys.readouterr().out
    assert "conflict: .claude/skills/memory-protocol/SKILL.md" in out
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
    assert (tmp_path / ".agents" / "skills" / "memory-protocol" / "SKILL.md").is_file()
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
    _answers(monkeypatch, "", "", r"[A-Z][A-Z0-9]*-\d+", "", "y")
    assert main(["init", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "[x] copilot" in out
    assert "About to apply" in out
    assert "#123" in out  # las sugerencias de ADR-0012
    cfg = config.load(tmp_path).config
    assert cfg["agents"] == ["copilot"]
    assert cfg["tickets"] == {"pattern": r"[A-Z][A-Z0-9]*-\d+", "example": "PROJ-123"}


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


def test_config_de_un_exo_mas_nuevo_pide_actualizar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F8R1-8: no es una config rota que haya que arreglar: la escribió un motor más nuevo."""
    _init(tmp_path)
    config.config_path(tmp_path).write_text('{"schema": 99}', encoding="utf-8")
    before = tree(tmp_path)
    capsys.readouterr()
    for argv in (["sync"], ["update"], ["init", "--yes"], ["add-agent", "cursor"]):
        assert main([*argv, "--project", str(tmp_path)]) == 1
        err = capsys.readouterr().err
        assert "config.json was written by a newer exo" in err, argv
        assert "upgrade exo" in err.lower() and "Fix it" not in err
    assert tree(tmp_path) == before
    # Los comandos que solo leen siguen con los defaults, y lo dicen sin contradecirse.
    warning = " ".join(config.load(tmp_path).warnings)
    assert "newer" in warning and "upgrade exo" in warning.lower()
    with pytest.raises(config.ConfigError, match="newer"):
        config.save(tmp_path, config.defaults())


def test_config_invalida_por_flags_no_escribe_nada(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _init(tmp_path, "--ticket-pattern", "(") == 2
    assert "not a valid regular expression" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_flags_de_tickets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _init(tmp_path, "--ticket-pattern", r"#\d+") == 0
    assert config.load(tmp_path).config["tickets"] == {"pattern": r"#\d+", "example": "#123"}
    assert _init(tmp_path, "--ticket-pattern", r"OPS-\d+", "--ticket-example", "OPS-7") == 0
    assert config.load(tmp_path).config["tickets"] == {"pattern": r"OPS-\d+", "example": "OPS-7"}
    assert _init(tmp_path, "--ticket-pattern", r"T\d+") == 0
    assert config.load(tmp_path).config["tickets"] == {"pattern": r"T\d+", "example": None}
    assert _init(tmp_path, "--ticket-pattern", "") == 0
    assert config.load(tmp_path).config["tickets"] == {"pattern": None, "example": None}
    capsys.readouterr()
    assert _init(tmp_path, "--ticket-example", "X-1") == 2
    assert "--ticket-pattern" in capsys.readouterr().err


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


def test_wizard_repregunta_el_patron_y_el_ejemplo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _answers(monkeypatch, "claude-code", "", "(", r"#\d+", "PROJ-1", "#9", "y")
    assert main(["init", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.count("invalid value") == 2
    assert config.load(tmp_path).config["tickets"] == {"pattern": r"#\d+", "example": "#9"}


def _romper_marcador(root: Path) -> None:
    agents = root / "AGENTS.md"
    end = f"<!-- END:{_meta.BLOCK_PREFIX}:core -->"
    agents.write_text(agents.read_text(encoding="utf-8").replace(end, ""), encoding="utf-8")


def test_force_informa_lo_que_no_pudo_resolver(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    _romper_marcador(tmp_path)
    skill = tmp_path / ".claude" / "skills" / "memory-protocol" / "SKILL.md"
    original = skill.read_bytes()
    skill.write_bytes(b"editado\n")
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path), "--force"]) == 1
    out = capsys.readouterr().out
    assert "forced: .claude/skills/memory-protocol/SKILL.md" in out
    assert "unresolved: AGENTS.md" in out
    assert skill.read_bytes() == original
    assert main(["uninstall", "--project", str(tmp_path), "--yes", "--force"]) == 1
    assert "unresolved: AGENTS.md" in capsys.readouterr().out
    assert (tmp_path / _meta.PROJECT_DIR / "lock.json").is_file()


def test_force_con_dry_run_muestra_lo_que_haria(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    skill = tmp_path / ".claude" / "skills" / "memory-protocol" / "SKILL.md"
    skill.write_bytes(b"editado\n")
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path), "--force", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "would force: .claude/skills/memory-protocol/SKILL.md" in out
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


def test_uninstall_conserva_lo_de_la_ingenieria_inversa(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """D-36: `discovery/` y `context.md` son conocimiento del proyecto, no instalación."""
    _init(tmp_path)
    motor = tmp_path / _meta.PROJECT_DIR
    (motor / "discovery" / "units").mkdir(parents=True)
    (motor / "discovery" / "plan.json").write_bytes(b"{}\n")
    (motor / "discovery" / "units" / "a.md").write_bytes(b"# Unit: a\n")
    (motor / "context.md").write_bytes(b"# Context\n")
    capsys.readouterr()
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "kept" in out and f"{_meta.PROJECT_DIR}/discovery" in out
    assert (motor / "discovery" / "units" / "a.md").read_bytes() == b"# Unit: a\n"
    assert (motor / "context.md").is_file()
    assert sorted(p.name for p in motor.iterdir()) == ["context.md", "discovery"]
    assert f"{_meta.PROJECT_DIR}/context.md" not in out.split("kept")[0]


def test_uninstall_conserva_la_marca_del_humano(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """F7R3-20: `brand.json` (ADR-0016, D-12) lo escribe la persona, no el motor."""
    _init(tmp_path)
    motor = tmp_path / _meta.PROJECT_DIR
    brand = b'{"colors": {"primary": "#123456"}}\n'
    (motor / "brand.json").write_bytes(brand)
    capsys.readouterr()
    assert main(["uninstall", "--project", str(tmp_path), "--yes", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kept"] == [f"{_meta.PROJECT_DIR}/brand.json"]
    assert f"{_meta.PROJECT_DIR}/brand.json" not in payload.get("also_removed", [])
    assert (motor / "brand.json").read_bytes() == brand
    assert [p.name for p in motor.iterdir()] == ["brand.json"]


def test_uninstall_avisa_que_conserva_la_marca(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    (tmp_path / _meta.PROJECT_DIR / "brand.json").write_bytes(b"{}\n")
    capsys.readouterr()
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 0
    line = next(x for x in capsys.readouterr().out.splitlines() if x.startswith("kept"))
    label, _, value = line.partition("): ")
    assert value == f"{_meta.PROJECT_DIR}/brand.json"
    assert "brand" in label, label  # la etiqueta no dice solo "discovery"


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


def test_salida_sin_notas_vacias_ni_lineas_repetidas(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Con el contenido sintético: con más de 30 archivos la salida resume en vez de listar."""
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
    assert (tmp_path / ".claude" / "skills" / "memory-protocol" / "SKILL.md").is_file()


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


HELLO = ".claude/skills/hello-exo"


def test_sync_informa_las_huerfanas_y_solo_las_borra_con_prune(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F8: una skill que el contenido ya no trae no se borra sin `--prune`."""
    _init(tmp_path)
    shutil.rmtree(synthetic_content / "packs" / "core" / "skills" / "hello-exo")
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert f"orphan\t{HELLO}/ (2 files)" in out
    assert f"`{_meta.NAME} sync --prune`" in out
    assert "remove\t" not in out
    assert (tmp_path / HELLO / "SKILL.md").is_file()
    assert "(your agents may still use them)" in out
    assert main(["sync", "--project", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["orphans"] == [f"{HELLO}/SKILL.md", f"{HELLO}/references/guide.md"]
    assert payload["changed"] is False
    assert main(["sync", "--project", str(tmp_path), "--prune", "--dry-run"]) == 0
    assert f"remove\t{HELLO}/SKILL.md" in capsys.readouterr().out
    assert (tmp_path / HELLO / "SKILL.md").is_file()
    assert main(["sync", "--project", str(tmp_path), "--prune"]) == 0
    assert "snapshot before the changes" in capsys.readouterr().out
    assert not (tmp_path / HELLO).exists()
    assert main(["sync", "--project", str(tmp_path)]) == 0
    assert "orphan" not in capsys.readouterr().out


def test_un_pack_que_se_saca_de_la_config_se_borra_sin_prune(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Lo que la persona deja de pedir no es una huérfana: se da de baja como siempre."""
    _init(tmp_path, "--packs", "core,sdd")
    assert (tmp_path / ".claude" / "skills" / "demo-phase" / "SKILL.md").is_file()
    cfg = config.load(tmp_path).config
    cfg["packs"] = ["core"]
    config.save(tmp_path, cfg)
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path)]) == 0
    assert "orphan" not in capsys.readouterr().out
    assert not (tmp_path / ".claude" / "skills" / "demo-phase").exists()
    assert not (tmp_path / ".claude" / "agents" / "demo-explorer.md").exists()
    assert (tmp_path / HELLO / "SKILL.md").is_file()


def test_init_con_menos_packs_los_saca_sin_prune(tmp_path: Path, synthetic_content: Path) -> None:
    _init(tmp_path, "--packs", "core,sdd")
    assert _init(tmp_path, "--packs", "core") == 0
    assert not (tmp_path / ".claude" / "skills" / "demo-phase").exists()


def test_remove_agent_no_borra_huerfanas_ajenas(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`remove-agent` borra lo del agente; una huérfana del contenido sigue esperando `--prune`."""
    _init(tmp_path)
    assert main(["add-agent", "cursor", "--project", str(tmp_path)]) == 0
    shutil.rmtree(synthetic_content / "packs" / "core" / "skills" / "hello-exo")
    capsys.readouterr()
    assert main(["remove-agent", "cursor", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert not (tmp_path / ".agents" / "skills" / "demo-phase").exists()
    # hello-exo ya no está en el contenido: es huérfana también en la carpeta de cursor.
    assert sorted(p.name for p in (tmp_path / ".agents" / "skills").iterdir()) == ["hello-exo"]
    assert (tmp_path / HELLO / "SKILL.md").is_file()
    assert f"orphan\t{HELLO}/ (2 files)" in out
    assert "orphan\t.agents/skills/hello-exo/ (2 files)" in out
    # F8R1-15: ningún agente que queda lee `.agents/skills/`: no "may still use them".
    [line] = [line for line in out.splitlines() if line.startswith("orphaned:")]
    assert "2 of them are in .agents/skills/, which no agent of this project reads" in line
    shutil.rmtree(tmp_path / HELLO)
    assert main(["sync", "--project", str(tmp_path)]) == 0
    [line] = [line for line in capsys.readouterr().out.splitlines() if line.startswith("orphaned:")]
    assert "no agent of this project reads .agents/skills/" in line
    assert "may still use" not in line


def test_force_dry_run_con_algo_sin_resolver_no_dice_que_aplico(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(tmp_path)
    _romper_marcador(tmp_path)
    capsys.readouterr()
    assert main(["sync", "--project", str(tmp_path), "--force", "--dry-run"]) == 1
    out = capsys.readouterr().out
    assert "the rest would be applied" in out
    assert "the rest was applied" not in out
