"""El escaneo del diff no se esquiva (revisión de cierre de F5).

El parser lee `git diff -U0` respetando los contadores de cada hunk, con flags que
ignoran la config del dev, y los errores de git no pasan como "nada que escanear".
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from exo.core import config
from exo.governance import git, hookrun
from exo.sdd import check

AWS = "AKIA" + "Q" * 16
ZERO = "0" * 40
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")


# -- parser ---------------------------------------------------------------------------------


def test_el_parser_respeta_los_contadores_del_hunk() -> None:
    text = "\n".join(
        [
            "diff --git a/app.py b/app.py",
            "--- a/app.py",
            "+++ b/app.py",
            "@@ -0,0 +1,3 @@",
            "+++ b/otro.py",  # contenido: la línea agregada es "++ b/otro.py"
            f"+KEY = '{AWS}'",
            "+--- x",
            "diff --git a/b.txt b/b.txt",
            "--- a/b.txt",
            "+++ b/b.txt",
            "@@ -1 +1 @@",
            "-viejo",
            "\\ No newline at end of file",
            "+nuevo",
            "\\ No newline at end of file",
        ]
    )
    found = git.parse_added(text)
    assert found == {
        "app.py": [(1, "++ b/otro.py"), (2, f"KEY = '{AWS}'"), (3, "--- x")],
        "b.txt": [(1, "nuevo")],
    }


@pytest.mark.parametrize(
    ("header", "path"),
    [
        ('+++ "b/a\\"b.txt"', 'a"b.txt'),
        ('+++ "b/tab\\tname.txt"', "tab\tname.txt"),
        ('+++ "b/caf\\303\\251.txt"', "café.txt"),
        ("+++ b/my file.txt\t", "my file.txt"),
        ("+++ /dev/null", None),
    ],
)
def test_nombres_entrecomillados_y_con_espacios(header: str, path: str | None) -> None:
    text = f"diff --git a/x b/x\n{header}\n@@ -0,0 +1 @@\n+hola"
    found = git.parse_added(text)
    assert found == ({path: [(1, "hola")]} if path else {})


# -- con git ----------------------------------------------------------------------------------


def _git(repo: Path, *args: str, stdin: str | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "r"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "T")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "chore: base")
    return root


def _staged_kinds(repo: Path) -> list[str]:
    result = hookrun.pre_commit(repo)
    return [e for e in result.errors if "aws-access-key" in e]


@needs_git
def test_una_linea_que_empieza_con_mas_mas_no_corta_el_escaneo(repo: Path) -> None:
    (repo / "app.py").write_text(f"++ b/otro.py\nKEY = '{AWS}'\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    errors = _staged_kinds(repo)
    assert len(errors) == 1 and errors[0].startswith("app.py:2:")


@needs_git
def test_gitattributes_binary_no_esconde_el_secreto(repo: Path) -> None:
    (repo / ".gitattributes").write_text("*.json -diff\n", encoding="utf-8")
    (repo / "config.json").write_text(f'{{"key": "{AWS}"}}\n', encoding="utf-8")
    _git(repo, "add", "-A")
    assert any(e.startswith("config.json:1:") for e in _staged_kinds(repo))


@needs_git
@pytest.mark.parametrize("option", ["diff.noprefix=true", "diff.mnemonicPrefix=true"])
def test_la_config_de_diff_del_dev_no_apaga_el_escaneo(repo: Path, option: str) -> None:
    key, value = option.split("=")
    _git(repo, "config", key, value)
    (repo / "app.py").write_text(f"KEY = '{AWS}'\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    assert _staged_kinds(repo)


@needs_git
def test_un_nombre_que_git_entrecomilla_se_escanea(repo: Path) -> None:
    blob = _git(repo, "hash-object", "-w", "--stdin", stdin=f"KEY = '{AWS}'\n")
    _git(
        repo,
        "-c",
        "core.protectNTFS=false",
        "update-index",
        "--add",
        "--cacheinfo",
        f'100644,{blob},a"b.txt',
    )
    errors = _staged_kinds(repo)
    assert errors and errors[0].startswith('a"b.txt:1:')


@needs_git
def test_si_git_falla_el_hook_bloquea_y_check_da_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "app.py").write_text("ok = 1\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    real = git.run

    def broken(project: Path, *args: str, stdin: bytes | None = None) -> git.Run:
        if args and args[0] == "diff":
            return git.Run(False, "", "fatal: simulated failure")
        return real(project, *args, stdin=stdin)

    monkeypatch.setattr(git, "run", broken)
    result = hookrun.pre_commit(repo)
    assert any("simulated failure" in e for e in result.errors)
    outcome = check.check(repo, base="main")
    assert not outcome.ok
    assert any("simulated failure" in f.message for f in outcome.diff)


@needs_git
@pytest.mark.parametrize("persistence", ["memory", "none"])
def test_base_escanea_el_diff_con_cualquier_persistencia(repo: Path, persistence: str) -> None:
    cfg = config.defaults()
    cfg["sdd"]["persistence"] = persistence
    config.save(repo, cfg)
    _git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "app.py").write_text(f"KEY = '{AWS}'\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: app")
    outcome = check.check(repo, base="main")
    assert not outcome.ok
    assert any("aws-access-key" in f.message for f in outcome.diff)


@needs_git
def test_base_y_change_juntos_escanean_el_diff(repo: Path) -> None:
    from exo.sdd import changes

    _git(repo, "checkout", "-q", "-b", "feat/x")
    changes.new_change(repo, "algo")
    (repo / "app.py").write_text(f"KEY = '{AWS}'\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: app")
    outcome = check.check(repo, base="main", names=["algo"])
    assert any("aws-access-key" in f.message for f in outcome.diff)


# -- pre-push: lo que se empuja ----------------------------------------------------------------


def _push_line(ref: str, local: str, remote: str) -> list[str]:
    return [f"refs/heads/{ref} {local} refs/heads/{ref} {remote}"]


@needs_git
def test_pre_push_de_una_rama_nueva_escanea_sus_commits(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "app.py").write_text(f"KEY = '{AWS}'\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: app")
    local = _git(repo, "rev-parse", "HEAD")
    result = hookrun.pre_push(repo, "origin", _push_line("feat/x", local, ZERO))
    assert any("aws-access-key" in e for e in result.errors)


@needs_git
def test_pre_push_mira_el_commit_empujado_y_no_el_arbol(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "app.py").write_text(f"KEY = '{AWS}'\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: app")
    pushed = _git(repo, "rev-parse", "HEAD")
    # El secreto se borra del árbol sin commitear, y hay un archivo sin trackear con otro.
    (repo / "app.py").write_text("KEY = None\n", encoding="utf-8")
    (repo / "scratch.txt").write_text(f"{AWS}\n", encoding="utf-8")
    result = hookrun.pre_push(repo, "origin", _push_line("feat/x", pushed, base))
    errors = [e for e in result.errors if "aws-access-key" in e]
    assert errors and all("scratch.txt" not in e for e in errors)
    # Empujar otra rama estando parado en main también escanea esa rama.
    _git(repo, "stash", "-q", "--include-untracked")
    _git(repo, "checkout", "-q", "main")
    result = hookrun.pre_push(repo, "origin", _push_line("feat/x", pushed, base))
    assert any("aws-access-key" in e for e in result.errors)


@needs_git
def test_pre_push_limpio_pasa(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "app.py").write_text("ok = 1\n", encoding="utf-8")
    (repo / "scratch.txt").write_text(f"{AWS}\n", encoding="utf-8")  # sin trackear: no se empuja
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "feat: app")
    local = _git(repo, "rev-parse", "HEAD")
    assert hookrun.pre_push(repo, "origin", _push_line("feat/x", local, base)).errors == []
    assert hookrun.pre_push(repo, "origin", _push_line("feat/x", local, ZERO)).errors == []
