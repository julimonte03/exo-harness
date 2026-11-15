"""governance: git hooks por defecto (D-21, ADR-0014) y su lógica (`exo hook ...`).

Los tests de integración crean repos git temporales, instalan el motor con
`exo init` y corren git de verdad: los hooks llaman a este mismo `exo` por
`EXO_HOOK_CMD`, con el paquete en el `PYTHONPATH` absoluto.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import exo
from exo import _meta, doctor
from exo.cli import main
from exo.core import config
from exo.governance import githooks, hookrun
from exo.installer import project

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
AWS = "AKIA" + "Q" * 16
CARD = "4977777777777776"  # pasa Luhn; sintético
PATTERN = r"[A-Z][A-Z0-9]*-\d+"


# -- commit-msg (lógica) ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "feat: add login",
        "fix(auth): reject empty passwords",
        "feat(api)!: drop v1\n\nBREAKING CHANGE: v1 is gone",
        "feat(auth): add SSO\n\nWhy it exists.\n\nRefs: PROJ-123",
        "chore: bump deps\n\nRefs: PROJ-1, OPS-22",
        "Merge branch 'main' into feat/x",
        'Revert "feat: add login"',
        "fixup! feat: add login",
        "squash! feat: add login",
        "docs: explain hooks\n# Please enter the commit message\n# Lines starting with '#' are ignored",
    ],
)
def test_mensajes_validos(message: str) -> None:
    assert hookrun.check_message(message, pattern=PATTERN, example="PROJ-123").errors == []


@pytest.mark.parametrize(
    ("message", "fragment"),
    [
        ("update stuff", "Conventional Commits"),
        ("PROJ-123 feat(auth): add login", "Refs:"),
        ("Feat: add login", "Conventional Commits"),
        ("feat:add login", "Conventional Commits"),
        ("feat(auth): add login\n\nRefs: proj-12", "for example PROJ-123"),
        ("", "empty"),
    ],
)
def test_mensajes_invalidos(message: str, fragment: str) -> None:
    errors = hookrun.check_message(message, pattern=PATTERN, example="PROJ-123").errors
    assert any(fragment in e for e in errors), errors


def test_sin_patron_refs_es_libre_y_asunto_largo_solo_avisa() -> None:
    assert hookrun.check_message("feat: x\n\nRefs: anything", pattern=None, example=None).errors == []
    result = hookrun.check_message("feat: " + "x" * 80, pattern=None, example=None)
    assert result.errors == [] and any("72" in w for w in result.warnings)


# -- pre-push (lógica de las refs) -------------------------------------------------------------


def test_lineas_del_pre_push() -> None:
    zero = "0" * 40
    refs = hookrun.parse_push_lines(
        [f"refs/heads/feat/x {'a' * 40} refs/heads/feat/x {zero}", "", f"(delete) {zero} refs/heads/main {'b' * 40}"]
    )
    assert [(r.remote_branch, r.deleting, r.creating) for r in refs] == [("feat/x", False, True), ("main", True, False)]


# -- integración en repos git ------------------------------------------------------------------


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=check)


@pytest.fixture
def hook_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los hooks de los repos de prueba llaman a este `exo`, sin depender del PATH."""
    monkeypatch.setenv("EXO_HOOK_CMD", f"{Path(sys.executable).as_posix()} -m {_meta.NAME}")
    monkeypatch.setenv("PYTHONPATH", str(Path(exo.__file__).resolve().parents[1]))


@pytest.fixture
def repo(tmp_path: Path, hook_env: None) -> Path:
    root = tmp_path / "app"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    cfg = config.defaults()
    cfg["tickets"] = {"pattern": PATTERN, "example": "PROJ-123"}
    config.save(root, cfg)
    project.sync(root, agents=["generic"])
    return root


def _commit(repo: Path, message: str, files: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    for rel, text in (files or {"README.md": f"{message}\n"}).items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        _git(repo, "add", rel)
    return _git(repo, "commit", "-q", "-m", message, check=False)


@needs_git
def test_init_instala_y_activa_los_hooks(repo: Path) -> None:
    folder = repo / _meta.PROJECT_DIR / "githooks"
    assert sorted(p.name for p in folder.iterdir()) == ["commit-msg", "pre-commit", "pre-push"]
    assert _git(repo, "config", "core.hooksPath").stdout.strip() == f"{_meta.PROJECT_DIR}/githooks"
    assert "githooks/* text eol=lf" in (repo / ".gitattributes").read_text(encoding="utf-8")
    raw = (folder / "pre-push").read_bytes()
    assert raw.startswith(b"#!/bin/sh\n") and b"\r\n" not in raw
    if os.name != "nt":
        assert (folder / "pre-push").stat().st_mode & stat.S_IXUSR
    assert githooks.status(repo).status == "ok"


@needs_git
def test_criterio_2_mensajes_de_commit(repo: Path) -> None:
    assert _commit(repo, "chore: adopt exo", {}).returncode == 0
    bad = _commit(repo, "update stuff")
    assert bad.returncode != 0 and "Conventional Commits" in bad.stderr + bad.stdout
    prefix = _commit(repo, "PROJ-1 feat: add x")
    assert prefix.returncode != 0
    assert _commit(repo, "feat: add x\n\nRefs: PROJ-1").returncode == 0
    assert _commit(repo, "feat: add y").returncode == 0  # sin ticket: la persona lo confirmó


@needs_git
def test_criterio_2_secretos_y_datos_en_el_stage(repo: Path) -> None:
    assert _commit(repo, "chore: adopt exo", {}).returncode == 0
    secret = _commit(repo, "feat: config", {"app.py": f"KEY = '{AWS}'\n"})
    assert secret.returncode != 0 and "aws-access-key" in secret.stderr + secret.stdout
    _git(repo, "reset", "-q")
    card = _commit(repo, "test: data", {"tests/fixtures/cards.txt": f"{CARD}\n"})
    assert card.returncode != 0 and "card" in card.stderr + card.stdout
    _git(repo, "reset", "-q")
    waiver = {"detector": "card", "path": "tests/fixtures/**", "reason": "synthetic", "approved_by": "ana", "expires": "2999-12-31"}
    (repo / _meta.PROJECT_DIR / "waivers.json").write_text(json.dumps({"schema": 1, "waivers": [waiver]}), encoding="utf-8")
    _git(repo, "add", f"{_meta.PROJECT_DIR}/waivers.json")
    assert _commit(repo, "test: data", {"tests/fixtures/cards.txt": f"{CARD}\n"}).returncode == 0
    env = _commit(repo, "chore: env", {".env": "DEBUG=1\n"})
    assert env.returncode != 0 and ".env" in env.stderr + env.stdout
    _git(repo, "reset", "-q")
    assert _commit(repo, "chore: env example", {".env.example": "DEBUG=1\n"}).returncode == 0


@needs_git
def test_criterio_2_push_a_rama_protegida_force_y_borrado(repo: Path, tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))
    assert _commit(repo, "chore: adopt exo", {}).returncode == 0
    to_main = _git(repo, "push", "-q", "origin", "main", check=False)
    assert to_main.returncode != 0 and "protected" in to_main.stderr
    _git(repo, "push", "-q", "--no-verify", "origin", "main")  # el remoto ya tiene main
    _git(repo, "checkout", "-q", "-b", "feat/x")
    assert _commit(repo, "feat: one").returncode == 0
    assert _git(repo, "push", "-q", "origin", "feat/x", check=False).returncode == 0
    _git(repo, "reset", "-q", "--hard", "HEAD~1")
    assert _commit(repo, "feat: other").returncode == 0
    forced = _git(repo, "push", "-q", "--force", "origin", "feat/x", check=False)
    assert forced.returncode != 0 and "force" in forced.stderr
    deleted = _git(repo, "push", "-q", "origin", ":main", check=False)
    assert deleted.returncode != 0 and "protected" in deleted.stderr


@needs_git
def test_husky_recibe_bloques_y_no_se_toca_hooks_path(tmp_path: Path, hook_env: None) -> None:
    root = tmp_path / "app"
    (root / ".husky").mkdir(parents=True)
    (root / ".husky" / "pre-commit").write_text("npm test\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "core.hooksPath", ".husky/_")
    result = project.sync(root, agents=["generic"])
    assert _git(root, "config", "core.hooksPath").stdout.strip() == ".husky/_"
    text = (root / ".husky" / "pre-commit").read_text(encoding="utf-8")
    assert text.startswith("npm test\n") and f"{_meta.NAME} hook pre-commit" in text
    assert (root / ".husky" / "commit-msg").is_file()
    assert not (root / _meta.PROJECT_DIR / "githooks").exists()
    assert any("husky" in note for note in result.notes)


@needs_git
def test_framework_pre_commit_recibe_instrucciones(tmp_path: Path, hook_env: None) -> None:
    root = tmp_path / "app"
    root.mkdir()
    (root / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    result = project.sync(root, agents=["generic"])
    assert _git(root, "config", "core.hooksPath", check=False).stdout.strip() == ""
    assert any(f"entry: {_meta.NAME} hook pre-commit" in note for note in result.notes)
    assert githooks.status(root).status == "warn"


@needs_git
def test_apagarlos_y_desinstalar_revierte_hooks_path(repo: Path) -> None:
    cfg = config.load(repo).config
    cfg["governance"]["githooks"] = False
    config.save(repo, cfg)
    project.sync(repo)
    assert _git(repo, "config", "core.hooksPath", check=False).stdout.strip() == ""
    assert not (repo / _meta.PROJECT_DIR / "githooks").exists()
    cfg["governance"]["githooks"] = True
    config.save(repo, cfg)
    project.sync(repo)
    assert _git(repo, "config", "core.hooksPath").stdout.strip() == f"{_meta.PROJECT_DIR}/githooks"
    project.uninstall(repo)
    assert _git(repo, "config", "core.hooksPath", check=False).stdout.strip() == ""


@needs_git
def test_otro_hooks_path_no_se_pisa(tmp_path: Path, hook_env: None) -> None:
    root = tmp_path / "app"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "core.hooksPath", "tools/hooks")
    result = project.sync(root, agents=["generic"])
    assert _git(root, "config", "core.hooksPath").stdout.strip() == "tools/hooks"
    assert any("tools/hooks" in note for note in result.notes)


def test_fuera_de_git_se_escriben_pero_no_se_activan(tmp_path: Path) -> None:
    result = project.sync(tmp_path, agents=["generic"])
    assert (tmp_path / _meta.PROJECT_DIR / "githooks" / "pre-commit").is_file()
    assert any("not a git repository" in note for note in result.notes)
    assert githooks.status(tmp_path).status == "info"


@needs_git
def test_doctor_y_el_bit_de_ejecucion(repo: Path) -> None:
    check = next(c for c in doctor.run_checks(repo) if c.name == "githooks")
    assert check.status == "ok"
    _git(repo, "config", "--unset", "core.hooksPath")
    check = next(c for c in doctor.run_checks(repo) if c.name == "githooks")
    assert check.status == "warn" and f"{_meta.NAME} sync" in check.detail
    if os.name != "nt":
        hook = repo / _meta.PROJECT_DIR / "githooks" / "pre-commit"
        hook.chmod(0o644)
        result = project.sync(repo)
        assert hook.stat().st_mode & stat.S_IXUSR
        assert any(a.reason == "executable bit" for a in result.engine.actions)


def test_cli_hook_commit_msg(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    message = tmp_path / "MSG"
    message.write_text("bad message\n", encoding="utf-8")
    assert main(["hook", "commit-msg", str(message), "--project", str(tmp_path)]) == 1
    assert "Conventional Commits" in capsys.readouterr().err
    message.write_text("fix: good one\n", encoding="utf-8")
    assert main(["hook", "commit-msg", str(message), "--project", str(tmp_path)]) == 0
