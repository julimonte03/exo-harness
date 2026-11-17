"""Evals de skills con Claude Code real (F7, criterio 3, D-41). Fuera de la suite normal.

Correr con: `pytest -m agent_e2e tests/test_skill_evals.py --no-cov` (filtrar con `-k`).

Por cada caso de `tests/skill_evals/<skill>/evals.json`:

1. copia el fixture a una carpeta temporal, le da historia git y corre
   `exo init --agents claude-code --yes --packs …`, con los datos de usuario aislados
   (`EXO_DATA_DIR` y `EXO_MEMORY_DB` en la carpeta temporal) y el bin del intérprete de la
   suite primero en el PATH (el `exo` que corre el agente es el mismo); después del
   commit base pasa a una rama `feat/<skill>-eval` y aplica el `setup` (sus rutas no
   pueden salir del proyecto);
2. corre `claude -p <pedido> --output-format stream-json --verbose` con las tools de
   `TOOLS` (el workspace no es confiable, así que el `permissions.allow` del proyecto no
   cuenta) y aislado de la config de usuario de Claude Code: `--setting-sources
   project,local` (ni los settings, ni las skills, plugins, hooks o `CLAUDE.md` de
   usuario) y `--strict-mcp-config` sin `--mcp-config` (ningún servidor MCP);
3. lee qué skills cargó (`_skill_evals.parse_stream`) y verifica: `trigger` la carga,
   `no-trigger` no, `output` la carga y cumple sus chequeos.

Cada resultado se agrega como una línea JSON a `EXO_EVALS_REPORT` (o a
`skill-evals.jsonl` en la carpeta temporal base) para la revisión humana, con la versión
de Claude Code (`claude --version`) y las skills que el agente veía (`visible_skills`,
del evento `system`/`init` del stream): ahí se comprueba que no se coló nada de fuera de
exo y de Claude Code.
"""

from __future__ import annotations

import functools
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import _skill_evals as evals
from _git import init_repo

pytestmark = pytest.mark.agent_e2e

TOOLS = (
    "Bash(exo:*) Bash(git:*) Bash(ls:*) Bash(cat:*) Bash(mkdir:*) "
    "PowerShell(exo:*) PowerShell(git:*) "
    "Read Edit Write Grep Glob TodoWrite Task Agent Skill"
)
MAX_TURNS = int(os.environ.get("EXO_EVALS_MAX_TURNS", "40"))
TIMEOUT = int(os.environ.get("EXO_EVALS_TIMEOUT", "1800"))
CASES = evals.cases()


@functools.lru_cache(maxsize=1)
def _claude_version(claude: str) -> str:
    """`claude --version`, una vez por sesión, para el informe."""
    try:
        done = subprocess.run(
            [claude, "--version"], capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unknown ({exc})"
    return (done.stdout or done.stderr).strip() or f"unknown (exit {done.returncode})"


def _project(case: evals.Case, root: Path, env: dict[str, str]) -> Path:
    project = root / "project"
    if case.fixture == evals.EMPTY:
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Demo\n\nA new project.\n", encoding="utf-8")
        init_repo(project)
    else:
        init_repo(project, fixture=case.fixture)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "exo",
            "init",
            "--agents",
            "claude-code",
            "--yes",
            "--packs",
            ",".join(case.packs),
        ],
        cwd=project,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore: adopt exo"],
        cwd=project,
        env=env,
        check=True,
        capture_output=True,
    )
    # Fuera de `main`, que es rama protegida: una skill que escribe no frena a proponer una rama.
    subprocess.run(
        ["git", "switch", "-q", "-c", f"feat/{case.skill}-eval"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    files = case.setup.get("files", {})
    for rel, text in files.items():
        path = evals.setup_target(project, rel)  # falla si la ruta sale del proyecto
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    if files and case.setup.get("stage"):
        subprocess.run(["git", "add", "--", *files], cwd=project, check=True, capture_output=True)
    return project


def _report(tmp_path_factory: pytest.TempPathFactory, entry: dict) -> None:
    target = os.environ.get("EXO_EVALS_REPORT")
    path = Path(target) if target else tmp_path_factory.getbasetemp() / "skill-evals.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


@pytest.mark.skipif(shutil.which("claude") is None, reason="requiere Claude Code (claude)")
@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c.skill}-{c.id}")
def test_skill_eval(
    case: evals.Case, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    env = evals.runner_env(data, os.environ)
    project = _project(case, tmp_path, env)
    before = evals.snapshot(project)
    claude = shutil.which("claude") or "claude"
    command = evals.claude_command(claude, case.prompt, TOOLS, MAX_TURNS)
    failed: list[str] = []
    try:
        done = subprocess.run(
            command,
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            check=False,
        )
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout or ""
        stdout = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        code = None
        failed.append(f"timed out after {TIMEOUT} s (EXO_EVALS_TIMEOUT)")
    (tmp_path / "stream.jsonl").write_text(stdout, encoding="utf-8")
    run = evals.parse_stream(stdout.splitlines())
    after = evals.snapshot(project)
    written = evals.changed(before, after)
    deleted = evals.removed(before, after)
    used = case.skill in run.used
    if case.expect == "trigger" and not used:
        failed.append(f"{case.skill} was not loaded (loaded: {run.used or 'none'})")
    if case.expect == "no-trigger" and used:
        failed.append(f"{case.skill} was loaded and should not have been")
    if case.id == "output" and used:
        failed += evals.check_output(case, run, written, project, deleted)
    _report(
        tmp_path_factory,
        {
            "skill": case.skill,
            "case": case.id,
            "ok": not failed,
            "failed": failed,
            "used": run.used,
            "turns": run.turns,
            "error": run.error,
            "exit": code,
            "written": written,
            "deleted": deleted,
            "answer": run.answer,
            "review": case.review,
            "claude_version": _claude_version(claude),
            "visible_skills": run.visible,
            "stream": str(tmp_path / "stream.jsonl"),
        },
    )
    assert not failed, failed
