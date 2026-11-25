"""`exo update` y la actualización segura de un proyecto instalado (criterio 7 de F8).

El proyecto se instala con un contenido "viejo" sintético: el de `tests/_content.py`
más una skill `review` (que en la versión nueva pasa a `pre-commit-review`, como en
D-40) y una skill `legacy-notes` que la versión nueva ya no trae. El lock dice que lo
escribió exo 0.2.0 y la config está en el esquema 2. Después el contenido pasa a la
versión "nueva" y el motor dice ser 1.0.0.
"""

from __future__ import annotations

import builtins
import io
import json
import shutil
from pathlib import Path

import pytest

from _projects import tree
from exo import _meta, content, packs, paths
from exo.adapters import detect
from exo.cli import main
from exo.core import config, lock, snapshots
from exo.installer import engine, renames

HELLO = ".claude/skills/hello-exo"
REVIEW = ".claude/skills/review"
PCR = ".claude/skills/pre-commit-review"
LEGACY = ".claude/skills/legacy-notes"
FRESH = ".claude/skills/fresh-skill"


@pytest.fixture(autouse=True)
def _aislado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(detect, "detect", lambda project, env=None, which=None: [])
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(tmp_path / "datos-usuario"))
    monkeypatch.setattr("sys.stdin", io.StringIO(""))


def _skill(root: Path, name: str, body: str = "", pack: str = "core") -> None:
    path = root / "packs" / pack / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: >-\n  Test skill {name}. Use it when testing updates.\n"
        f"metadata:\n  {_meta.NAME}-pack: {pack}\n  {_meta.NAME}-execution: inline\n---\n\n"
        f"# {name}\n\n{body}\n",
        encoding="utf-8",
    )


def _to_new_version(root: Path) -> None:
    """El contenido de la versión nueva: un renombre, una baja, un cambio y una skill nueva."""
    shutil.rmtree(root / "packs" / "core" / "skills" / "review")
    shutil.rmtree(root / "packs" / "core" / "skills" / "legacy-notes")
    _skill(root, "pre-commit-review", "Review the staged diff.")
    _skill(root, "fresh-skill", "New in 1.0.0.")
    hello = root / "packs" / "core" / "skills" / "hello-exo"
    (hello / "SKILL.md").write_bytes((hello / "SKILL.md").read_bytes() + b"\nNew paragraph.\n")
    (hello / "references" / "guide.md").write_bytes(b"# Guide\n\nKeep it short, version 1.0.\n")


def _old_install(root: Path, content_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _skill(content_root, "review", "Review the staged diff.")
    _skill(content_root, "legacy-notes", "Gone in 1.0.0.")
    root.mkdir()
    assert main(["init", "--project", str(root), "--agents", "claude-code", "--yes"]) == 0
    data = lock.read(root)
    data.engine_version = "0.2.0"
    lock.write(root, data)
    cfg = json.loads(config.config_path(root).read_text(encoding="utf-8"))
    cfg["schema"] = 2
    cfg["governance"]["dpa_profile"] = "legacy"  # lo saca la migración al esquema 3
    config.config_path(root).write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    _to_new_version(content_root)
    monkeypatch.setattr(_meta, "VERSION", "1.0.0")


@pytest.fixture
def old_project(
    tmp_path: Path, synthetic_content: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    root = tmp_path / "p"
    _old_install(root, synthetic_content, monkeypatch)
    (root / HELLO / "SKILL.md").write_bytes(b"# hello-exo\n\nOur team version.\n")
    return root


def _schema_on_disk(root: Path) -> int:
    return json.loads(config.config_path(root).read_text(encoding="utf-8"))["schema"]


# -- criterio 7 ----------------------------------------------------------------------------


def test_criterio_7_update_de_0_2_0_a_1_0_0(
    old_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = old_project
    edited = (root / HELLO / "SKILL.md").read_bytes()
    before = tree(root)
    capsys.readouterr()

    # 1. Vista previa: muestra el plan y no escribe nada.
    assert main(["update", "--project", str(root)]) == 1
    out = capsys.readouterr().out
    assert "engine: 0.2.0 -> 1.0.0" in out
    assert "config: schema 2 -> 3 (saved with --apply)" in out
    assert f"  {PCR}/ (1 file, renamed from {REVIEW}/)" in out
    assert f"  {FRESH}/ (1 file)" in out
    assert f"  {HELLO}/" not in out.split("modified:")[1].split("removed:")[0]
    assert f"  {REVIEW}/ (1 file, renamed to {PCR}/)" in out
    assert f"  {LEGACY}/ (1 file)" in out
    assert f"kept: {HELLO}/SKILL.md (mirror): modified by hand since the last install" in out
    # El resto de la skill tampoco se toca: una skill a medias no es ni la vieja ni la nueva.
    assert f"kept: {HELLO}/ (1 file, {engine.HELD})" in out
    assert f"preview: nothing was written; apply it with `{_meta.NAME} update --apply`" in out
    assert tree(root) == before

    # 2. --apply: actualiza, preserva lo editado y no borra las huérfanas.
    assert main(["update", "--project", str(root), "--apply"]) == 1
    out = capsys.readouterr().out
    assert "snapshot before the changes" in out
    assert f"kept your edits in 1 file; overwrite them with `{_meta.NAME} update --apply --force`" in out
    assert f"delete them with `{_meta.NAME} update --apply --prune`" in out
    assert (root / HELLO / "SKILL.md").read_bytes() == edited
    assert b"version 1.0" not in (root / HELLO / "references" / "guide.md").read_bytes()
    assert (root / PCR / "SKILL.md").is_file() and (root / FRESH / "SKILL.md").is_file()
    assert (root / REVIEW / "SKILL.md").is_file() and (root / LEGACY / "SKILL.md").is_file()
    assert lock.read(root).engine_version == "1.0.0"
    assert _schema_on_disk(root) == 3
    newest = snapshots.list_snapshots(root)[-1]
    archive = snapshots.read_archive(newest.path.read_bytes())
    assert json.loads(archive.files[f"{_meta.PROJECT_DIR}/config.json"][0])["schema"] == 2

    # 3. --prune: borra las huérfanas; lo editado sigue intacto.
    assert main(["update", "--project", str(root), "--apply", "--prune"]) == 1
    out = capsys.readouterr().out
    assert f"  {REVIEW}/ (1 file, renamed to {PCR}/)" in out.split("removed:")[1]
    assert not (root / REVIEW).exists() and not (root / LEGACY).exists()
    assert (root / HELLO / "SKILL.md").read_bytes() == edited

    # 4. --force: pisa lo editado, con snapshot antes.
    assert main(["update", "--project", str(root), "--apply", "--force"]) == 0
    assert b"New paragraph." in (root / HELLO / "SKILL.md").read_bytes()
    assert b"version 1.0" in (root / HELLO / "references" / "guide.md").read_bytes()
    newest = snapshots.list_snapshots(root)[-1]
    archive = snapshots.read_archive(newest.path.read_bytes())
    assert archive.files[f"{HELLO}/SKILL.md"][0] == edited
    capsys.readouterr()
    assert main(["update", "--project", str(root)]) == 0
    assert f"up to date: nothing to change for {_meta.NAME} 1.0.0" in capsys.readouterr().out


def test_criterio_7_json_con_la_misma_informacion(
    old_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()
    assert main(["update", "--project", str(old_project), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert (payload["from_version"], payload["to_version"]) == ("0.2.0", "1.0.0")
    assert payload["applied"] is False
    assert payload["new"] == [f"{FRESH}/SKILL.md", f"{PCR}/SKILL.md"]
    assert f"{HELLO}/references/guide.md" not in payload["modified"]
    held = [a for a in payload["actions"] if a["action"] == "skip" and a["detail"] == engine.HELD]
    assert [a["path"] for a in held] == [f"{HELLO}/references/guide.md"]
    assert payload["orphans"] == [f"{LEGACY}/SKILL.md", f"{REVIEW}/SKILL.md"]
    assert payload["renamed"] == {f"{REVIEW}/SKILL.md": f"{PCR}/SKILL.md"}
    assert payload["removed"] == []
    assert [c["path"] for c in payload["conflicts"]] == [f"{HELLO}/SKILL.md"]
    assert payload["config_migration"] == {"from": 2, "to": 3, "saved": False}


def test_criterio_7_sin_tty_nunca_pregunta_ni_borra(
    old_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_input(prompt: str = "") -> str:
        raise AssertionError("asked without a TTY")

    monkeypatch.setattr(builtins, "input", no_input)
    main(["update", "--project", str(old_project), "--apply"])
    assert (old_project / REVIEW / "SKILL.md").is_file()


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.mark.parametrize(("answer", "deleted"), [("y", True), ("", False), ("n", False)])
def test_criterio_7_en_una_terminal_pregunta_antes_de_borrar(
    old_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    answer: str,
    deleted: bool,
) -> None:
    asked: list[str] = []
    monkeypatch.setattr("sys.stdin", _Tty(""))
    monkeypatch.setattr(builtins, "input", lambda prompt="": asked.append(prompt) or answer)
    main(["update", "--project", str(old_project), "--apply"])
    out = capsys.readouterr().out
    assert len(asked) == 1 and "[y/N]" in asked[0]
    assert f"  {REVIEW}/ (1 file, renamed to {PCR}/)" in out
    assert (old_project / REVIEW).exists() is not deleted
    assert (old_project / LEGACY).exists() is not deleted
    assert (old_project / PCR / "SKILL.md").is_file()


# -- más casos -----------------------------------------------------------------------------


def test_sin_instalar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["update", "--project", str(tmp_path)]) == 1
    assert "not installed" in capsys.readouterr().err


def test_un_lock_de_un_motor_mas_nuevo_no_se_lleva_hacia_atras(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["init", "--project", str(tmp_path), "--agents", "claude-code", "--yes"]) == 0
    data = lock.read(tmp_path)
    data.engine_version = "9.0.0"
    lock.write(tmp_path, data)
    capsys.readouterr()
    assert main(["update", "--project", str(tmp_path), "--apply"]) == 1
    err = capsys.readouterr().err
    assert f"written by {_meta.NAME} 9.0.0" in err and f"upgrade {_meta.NAME}" in err.lower()
    assert lock.read(tmp_path).engine_version == "9.0.0"
    assert main(["update", "--project", str(tmp_path), "--apply", "--force"]) == 0
    assert lock.read(tmp_path).engine_version == _meta.VERSION


@pytest.mark.parametrize(
    "argv",
    [
        ["sync"],
        ["sync", "--dry-run"],
        ["add-agent", "copilot"],
        ["remove-agent", "claude-code"],
        ["init", "--yes"],
    ],
)
def test_ningun_comando_lleva_hacia_atras_un_lock_mas_nuevo(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """F8R1-2: `sync`, `init`, `add-agent` y `remove-agent` también se niegan sin `--force`."""
    assert main(["init", "--project", str(tmp_path), "--agents", "claude-code", "--yes"]) == 0
    data = lock.read(tmp_path)
    data.engine_version = "9.0.0"
    lock.write(tmp_path, data)
    before = tree(tmp_path)
    capsys.readouterr()
    assert main([*argv, "--project", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert f"written by {_meta.NAME} 9.0.0" in err and f"upgrade {_meta.NAME}" in err.lower()
    assert tree(tmp_path) == before
    if "--dry-run" not in argv:
        assert main([*argv, "--project", str(tmp_path), "--force"]) == 0
        assert lock.read(tmp_path).engine_version == _meta.VERSION


def test_una_skill_que_choca_se_conserva_entera(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F8R1-3: la persona tiene una skill propia con el nombre de una que trae la versión
    nueva. Su `SKILL.md` no se pisa, y tampoco se escribe nada más dentro de su carpeta."""
    root = tmp_path / "p"
    root.mkdir()
    assert main(["init", "--project", str(root), "--agents", "claude-code", "--yes"]) == 0
    mine = root / ".claude" / "skills" / "fresh"
    mine.mkdir(parents=True)
    (mine / "SKILL.md").write_text("# my skill\n", encoding="utf-8")
    _skill(synthetic_content, "fresh", "The engine's version.")
    guide = synthetic_content / "packs" / "core" / "skills" / "fresh" / "references" / "guide.md"
    guide.parent.mkdir()
    guide.write_text("# engine guide\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["update", "--project", str(root), "--apply"]) == 1
    out = capsys.readouterr().out
    assert "unresolved: .claude/skills/fresh/SKILL.md" in out
    assert f"kept: .claude/skills/fresh/ (1 file, {engine.HELD})" in out
    assert (mine / "SKILL.md").read_text(encoding="utf-8") == "# my skill\n"
    assert not (mine / "references").exists()
    assert not any(e.path.startswith(".claude/skills/fresh/") for e in lock.read(root).files)
    # Con --force tampoco: el archivo de la persona no lo resuelve --force.
    assert main(["sync", "--project", str(root), "--force"]) == 1
    assert f"kept: .claude/skills/fresh/ (1 file, {engine.HELD})" in capsys.readouterr().out
    assert not (mine / "references").exists()


def test_uninstall_no_mira_la_version_del_lock(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["init", "--project", str(tmp_path), "--agents", "claude-code", "--yes"]) == 0
    data = lock.read(tmp_path)
    data.engine_version = "9.0.0"
    lock.write(tmp_path, data)
    assert main(["uninstall", "--project", str(tmp_path), "--yes"]) == 0
    assert not (tmp_path / _meta.PROJECT_DIR / lock.FILENAME).exists()


def test_sin_cambios_no_escribe_ni_crea_snapshot(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["init", "--project", str(tmp_path), "--agents", "claude-code", "--yes"]) == 0
    before, snaps = tree(tmp_path), snapshots.list_snapshots(tmp_path)
    capsys.readouterr()
    assert main(["update", "--project", str(tmp_path), "--apply"]) == 0
    out = capsys.readouterr().out
    assert f"engine: {_meta.VERSION} (the lock is already at this version)" in out
    assert "no changes" in out
    assert tree(tmp_path) == before
    assert snapshots.list_snapshots(tmp_path) == snaps


def test_sync_no_guarda_la_config_migrada_pero_avisa(
    old_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()
    main(["sync", "--project", str(old_project), "--force"])
    out = capsys.readouterr().out
    assert _schema_on_disk(old_project) == 2
    assert f"`{_meta.NAME} update --apply`" in out


def test_sync_muestra_el_renombre_conocido(
    old_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()
    main(["sync", "--project", str(old_project), "--force"])
    out = capsys.readouterr().out
    assert f"orphan\t{REVIEW}/ (1 file, renamed to {PCR}/)" in out
    assert (old_project / REVIEW / "SKILL.md").is_file()


def test_rename_path_por_segmento() -> None:
    table = {"review": "pre-commit-review", "old-agent": "new-agent"}
    assert renames.rename_path(".claude/skills/review/SKILL.md", table) == f"{PCR}/SKILL.md"
    assert renames.rename_path(".claude/agents/old-agent.md", table) == ".claude/agents/new-agent.md"
    assert renames.rename_path(".claude/skills/reviewer/SKILL.md", table) is None
    assert renames.rename_path(".claude/skills/x/review-notes.md", table) is None
    assert renames.find([f"{REVIEW}/SKILL.md"], {f"{PCR}/other.md"}, table) == {}


def test_la_tabla_de_renombres_coincide_con_el_contenido() -> None:
    """Cada nombre nuevo existe en el contenido real y el viejo ya no."""
    collection = packs.load_collection(content.content_root())
    names = {s.name for s in collection.skills} | {a.name for a in collection.subagents}
    for old, new in renames.RENAMED.items():
        assert new in names, new
        assert old not in names, old
