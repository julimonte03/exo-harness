"""R1, churn y ownership (F6, ADR-0015): ventana anclada, sin emails, determinista."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from _git import Commit, git, init_repo
from exo.discovery import git_metrics

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")


def test_parse_log_con_binarios_y_rutas_con_espacios() -> None:
    out = "\x1eabc\x1f1700000000\x1fAna B\x00\n2\t1\tsrc/a b.py\x00-\t-\tlogo.png\x00\x1edef\x1f1700000100\x1fBruno\x00\n"
    changes = git_metrics.parse_log(out)
    assert [(c.commit, c.author, c.path, c.churn) for c in changes] == [
        ("abc", "Ana B", "src/a b.py", 3),
        ("abc", "Ana B", "logo.png", 0),
    ]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src" / "billing").mkdir(parents=True)
    (root / "src" / "old").mkdir(parents=True)
    # Con LF explícito: en Windows, write_text escribiría CRLF y git contaría cambiada la línea.
    for rel, text in {
        "src/billing/totals.py": "a = 1\n",
        "src/billing/taxes.py": "t = 1\n",
        "src/old/legacy.py": "x = 1\n",
    }.items():
        (root / rel).write_text(text, encoding="utf-8", newline="\n")
    return init_repo(
        root,
        base_when="2024-06-01T09:00:00+00:00",
        history=[
            Commit(
                "2026-02-01T10:00:00+00:00",
                "Bruno Dev",
                "feat: totals",
                {"src/billing/totals.py": "a = 1\nb = 2\n"},
            ),
            Commit(
                "2026-03-01T10:00:00+00:00",
                "Carla Dev",
                "feat: taxes",
                {"src/billing/taxes.py": "t = 2\n"},
            ),
            Commit(
                "2026-03-15T10:00:00+00:00",
                "Bruno Dev",
                "fix: totals",
                {"src/billing/totals.py": "a = 1\nb = 3\nc = 4\n"},
            ),
        ],
    )


@needs_git
def test_churn_en_la_ventana_y_ownership_sin_emails(repo: Path) -> None:
    hotspots, ownership = git_metrics.build(repo)
    files = {f["path"]: f for f in hotspots["files"]}
    # La base (2024-06-01) cae fuera de la ventana de 365 días que termina el 2026-03-15.
    assert "src/old/legacy.py" not in files
    assert files["src/billing/totals.py"]["commits"] == 2
    assert files["src/billing/totals.py"]["churn"] == 1 + 3
    assert files["src/billing/taxes.py"]["commits"] == 1
    [billing] = [m for m in hotspots["modules"] if m["path"] == "src/billing"]
    assert billing["commits"] == 3
    owners = {m["path"]: m["authors"] for m in ownership["modules"]}
    assert owners["src/billing"][0] == {"name": "Bruno Dev", "commits": 2}
    assert {a["name"] for a in owners["src/billing"]} == {"Ana Base", "Bruno Dev", "Carla Dev"}
    assert owners["src/old"] == [{"name": "Ana Base", "commits": 1}]
    assert "@" not in repr(ownership)


@needs_git
def test_commitear_los_resultados_no_mueve_la_ventana(repo: Path) -> None:
    first, wrote = git_metrics.write(repo)
    assert wrote is True
    git(repo, "add", "-A")
    git(
        repo,
        "commit",
        "-q",
        "-m",
        "chore: discovery",
        env={
            "GIT_AUTHOR_DATE": "2026-09-01T10:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-09-01T10:00:00+00:00",
        },
    )
    second, wrote = git_metrics.write(repo)
    assert second == first
    assert wrote is False


def test_sin_git_avisa(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    hotspots, ownership = git_metrics.build(tmp_path)
    assert hotspots["files"] == [] and ownership["modules"] == []
    assert any("not a git repository" in w for w in hotspots["warnings"])
