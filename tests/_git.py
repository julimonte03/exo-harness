"""Repos git para los tests de ingeniería inversa (F6), con historia determinista.

`init_repo` copia un fixture a una carpeta temporal y le da una historia de commits
con fechas y autores fijos, así las métricas de churn y ownership no dependen del
reloj ni de quién corre los tests.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "repos"


def git(repo: Path, *args: str, env: Mapping[str, str] | None = None) -> str:
    """Corre git en `repo` y devuelve stdout sin el salto final. Falla si git falla."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env={**os.environ, **(env or {})},
    )
    return done.stdout.rstrip("\n")


@dataclass(frozen=True)
class Commit:
    """Un commit sintético: `files` son rutas relativas a reemplazar o crear."""

    when: str  # ISO 8601, por ejemplo "2026-01-15T10:00:00+00:00"
    author: str
    message: str
    files: Mapping[str, str] = field(default_factory=dict)


def _author_env(commit: Commit) -> dict[str, str]:
    email = commit.author.lower().replace(" ", ".") + "@example.com"
    return {
        "GIT_AUTHOR_NAME": commit.author,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_AUTHOR_DATE": commit.when,
        "GIT_COMMITTER_NAME": commit.author,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_COMMITTER_DATE": commit.when,
    }


def init_repo(
    target: Path,
    *,
    fixture: str | None = None,
    history: Iterable[Commit] = (),
    base_when: str = "2026-01-01T09:00:00+00:00",
    base_author: str = "Ana Base",
) -> Path:
    """Repo nuevo en `target`: el fixture (si hay) en un primer commit, y después `history`."""
    target.mkdir(parents=True, exist_ok=True)
    if fixture is not None:
        shutil.copytree(FIXTURES / fixture, target, dirs_exist_ok=True)
    git(target, "init", "-q", "-b", "main")
    git(target, "config", "user.email", "tests@example.com")
    git(target, "config", "user.name", "Tests")
    git(target, "config", "core.autocrlf", "false")
    base = Commit(base_when, base_author, "chore: base")
    git(target, "add", "-A")
    git(target, "commit", "-q", "--allow-empty", "-m", base.message, env=_author_env(base))
    for commit in history:
        for rel, text in commit.files.items():
            path = target / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        git(target, "add", "-A")
        git(target, "commit", "-q", "--allow-empty", "-m", commit.message, env=_author_env(commit))
    return target
