"""memory/projects: detección del proyecto desde `git remote origin`, normalizado."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from exo.memory import projects

AZ = "dev.azure.com/acme/pagos/api"


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        ("https://github.com/Acme/Api.git", "github.com/acme/api"),
        ("https://user:token@github.com/acme/api", "github.com/acme/api"),
        ("git@github.com:acme/api.git", "github.com/acme/api"),
        ("ssh://git@github.com:2222/acme/api.git/", "github.com/acme/api"),
        ("https://gitlab.example.com/grupo/sub/api.git", "gitlab.example.com/grupo/sub/api"),
        ("https://dev.azure.com/acme/pagos/_git/api", AZ),
        ("https://acme@dev.azure.com/acme/pagos/_git/api", AZ),
        ("git@ssh.dev.azure.com:v3/acme/pagos/api", AZ),
        ("https://acme.visualstudio.com/pagos/_git/api", AZ),
        ("https://acme.visualstudio.com/DefaultCollection/pagos/_git/api", AZ),
        ("acme@vs-ssh.visualstudio.com:v3/acme/pagos/api", AZ),
        ("https://dev.azure.com/acme/Mi%20Proyecto/_git/api", "dev.azure.com/acme/mi proyecto/api"),
        ("  https://github.com/acme/api  ", "github.com/acme/api"),
    ],
)
def test_normalizacion_del_remoto(remote: str, expected: str) -> None:
    assert projects.normalize_remote(remote) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "no es una url",
        "https://",
        "C:" + chr(92) + "repos" + chr(92) + "api",
        "/srv/git/api.git",
        "file:///srv/git/api.git",
    ],
)
def test_remoto_que_no_se_puede_normalizar(bad: str) -> None:
    assert projects.normalize_remote(bad) is None


def test_sin_git_usa_la_carpeta(tmp_path: Path) -> None:
    folder = tmp_path / "Mi-Servicio"
    folder.mkdir()
    found = projects.detect(folder)
    assert (found.name, found.source, found.remote) == ("local/mi-servicio", "folder", None)


def test_lee_el_remoto_de_git_config_sin_ejecutar_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "config").write_text(
        '[core]\n\tbare = false\n[remote "origin"]\n\turl = git@ssh.dev.azure.com:v3/acme/pagos/api\n',
        encoding="utf-8",
    )
    (repo / "src" / "modulo").mkdir(parents=True)
    monkeypatch.setattr(projects, "_git_remote", lambda root: None)
    found = projects.detect(repo / "src" / "modulo")
    assert (found.name, found.source, found.path) == (AZ, "git-remote", repo)


def test_repo_sin_origin_usa_la_carpeta_del_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "Repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "config").write_text("[core]\n\tbare = false\n", encoding="utf-8")
    monkeypatch.setattr(projects, "_git_remote", lambda root: None)
    found = projects.detect(repo)
    assert (found.name, found.source) == ("local/repo", "folder")


@pytest.mark.skipif(shutil.which("git") is None, reason="sin git")
def test_con_git_real(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/Acme/Api.git"],
        check=True,
    )
    assert projects.detect(repo).name == "github.com/acme/api"
