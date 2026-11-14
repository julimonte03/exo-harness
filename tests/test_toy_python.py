"""El fixture `tests/fixtures/repos/toy-python/` del checklist del ciclo SDD (F4, tarea 9).

Es el único fixture versionado como carpeta (los demás se arman en código, ver
`_projects.py`): el checklist lo copia a una carpeta temporal y adopta el motor
ahí. Por eso no puede traer archivos de agente, y sus tests tienen que pasar.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from exo import _meta
from exo.installer import project

TOY = Path(__file__).resolve().parent / "fixtures" / "repos" / "toy-python"


def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "toy-python"
    shutil.copytree(
        TOY, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tasks.json")
    )
    return target


def test_no_trae_archivos_de_agente_ni_del_motor() -> None:
    names = {p.relative_to(TOY).parts[0] for p in TOY.rglob("*")}
    for forbidden in (
        "AGENTS.md",
        "CLAUDE.md",
        ".claude",
        ".github",
        ".agents",
        _meta.PROJECT_DIR,
        "specs",
    ):
        assert forbidden not in names


def test_sus_tests_pasan(tmp_path: Path) -> None:
    copy = _copy(tmp_path)
    env = {k: v for k, v in os.environ.items() if not k.startswith("COV_")}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:cov"],
        cwd=copy,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "5 passed" in result.stdout


def test_se_adopta_sin_conflictos(tmp_path: Path) -> None:
    copy = _copy(tmp_path)
    result = project.sync(copy, agents=["claude-code"])
    assert result.engine.conflicts == []
    assert (copy / ".claude" / "skills" / "sdd-new" / "SKILL.md").is_file()
    assert (copy / _meta.PROJECT_DIR / "shared" / "sdd-phase-common.md").is_file()
