"""Git hooks del motor: qué se instala y cómo se activan (D-21, ADR-0014).

- **Por defecto**, tres scripts finos en `<carpeta del motor>/githooks/` que llaman
  a `exo hook <nombre>`, activados con `core.hooksPath`. Es por clon: cada uno corre
  `exo init` o `exo sync`, y `exo doctor` avisa si no están activos.
- **Con husky** (`.husky/`), se agrega un bloque a cada script de husky y no se
  toca `core.hooksPath`, que es de husky.
- **Con el framework pre-commit** (`.pre-commit-config.yaml`), el motor no edita su
  YAML: imprime el bloque a agregar y `exo doctor` verifica que esté.
- **Si `core.hooksPath` ya apunta a otro lado**, no se pisa: se avisa.

Los scripts son de POSIX `sh` (git para Windows los corre con su `sh`). Si `exo`
no está en el PATH, avisan y no bloquean: la CI, con `exo check`, es el gate real.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from exo import _meta
from exo.core import config
from exo.governance import git

HOOKS = ("commit-msg", "pre-commit", "pre-push")
FOLDER = f"{_meta.PROJECT_DIR}/githooks"
HOOKS_PATH = "core.hooksPath"
OVERRIDE = f"{_meta.ENV_PREFIX}HOOK_CMD"
HUSKY = ".husky"
PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"


@dataclass(frozen=True)
class Status:
    status: str  # ok | warn | info
    detail: str


def script(name: str) -> bytes:
    cli = _meta.NAME
    text = f"""#!/bin/sh
# {cli}: runs `{cli} hook {name}`. Turn the hooks off with governance.githooks: false
# in {_meta.PROJECT_DIR}/config.json. Skipping them with --no-verify is possible; CI still runs
# `{cli} check`.
project="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -n "${{{OVERRIDE}:-}}" ]; then
  exec ${OVERRIDE} hook {name} --project "$project" "$@"
fi
if command -v {cli} >/dev/null 2>&1; then
  exec {cli} hook {name} --project "$project" "$@"
fi
echo "{cli}: not found in PATH, so the {name} hook did not run; CI still runs {cli} check" >&2
exit 0
"""
    return text.encode("utf-8")


def husky_block(name: str) -> str:
    cli = _meta.NAME
    return (
        f'if [ -n "${{{OVERRIDE}:-}}" ]; then ${OVERRIDE} hook {name} "$@"; '
        f'elif command -v {cli} >/dev/null 2>&1; then {cli} hook {name} "$@"; fi'
    )


def pre_commit_snippet() -> str:
    cli = _meta.NAME
    return f"""  - repo: local
    hooks:
      - id: {cli}-pre-commit
        name: {cli} pre-commit
        entry: {cli} hook pre-commit
        language: system
        pass_filenames: false
      - id: {cli}-commit-msg
        name: {cli} commit-msg
        entry: {cli} hook commit-msg
        language: system
        stages: [commit-msg]"""


def mechanism(project: Path) -> str:
    """`husky`, `pre-commit` o `hooks-path` (los scripts del motor)."""
    if (Path(project) / HUSKY).is_dir():
        return "husky"
    if (Path(project) / PRE_COMMIT_CONFIG).is_file():
        return "pre-commit"
    return "hooks-path"


def enabled(cfg: dict) -> bool:
    return bool(cfg.get("governance", {}).get("githooks", True))


def expected_path(project: Path, top: Path) -> str:
    folder = (Path(project).resolve() / FOLDER).resolve()
    try:
        return folder.relative_to(top.resolve()).as_posix()
    except ValueError:
        return folder.as_posix()


def activate(project: Path) -> list[str]:
    """Activa los scripts del motor en este clon. Devuelve las notas para la persona."""
    project = Path(project)
    if mechanism(project) == "pre-commit":
        if f"{_meta.NAME} hook" in (project / PRE_COMMIT_CONFIG).read_text(errors="replace"):
            return []
        return [
            f"{PRE_COMMIT_CONFIG} manages the git hooks here, so the engine did not touch "
            f"{HOOKS_PATH}. Add this under `repos:` and run `pre-commit install --hook-type "
            f"pre-commit --hook-type commit-msg`:\n{pre_commit_snippet()}"
        ]
    if mechanism(project) == "husky":
        return []
    top = git.toplevel(project)
    if top is None:
        return [
            f"not a git repository: the git hooks are written in {FOLDER} but not active; "
            f"run `{_meta.NAME} sync` after `git init`"
        ]
    wanted = expected_path(project, top)
    current = git.config_get(project, HOOKS_PATH)
    if current == wanted:
        return []
    if current:
        return [
            f"{HOOKS_PATH} already points to {current}, so the engine did not change it. Add "
            f"`{_meta.NAME} hook <name>` to those hooks, or set governance.githooks to false"
        ]
    if not git.config_set(project, HOOKS_PATH, wanted):
        return [f"could not set {HOOKS_PATH}; run `git config {HOOKS_PATH} {wanted}`"]
    return [f"git hooks active in this clone ({HOOKS_PATH} = {wanted})"]


def deactivate(project: Path) -> bool:
    """Saca `core.hooksPath` si apunta a los hooks del motor. Devuelve si lo sacó."""
    top = git.toplevel(project)
    if top is None:
        return False
    if git.config_get(project, HOOKS_PATH) != expected_path(project, top):
        return False
    return git.config_unset(project, HOOKS_PATH)


def status(project: Path) -> Status:
    project = Path(project)
    if not enabled(config.load(project).config):
        return Status("info", "off (governance.githooks: false)")
    if git.toplevel(project) is None:
        return Status("info", "not a git repository")
    kind = mechanism(project)
    if kind == "husky":
        missing = [
            name
            for name in HOOKS
            if f"{_meta.NAME} hook {name}" not in _read(project / HUSKY / name)
        ]
        if missing:
            return Status(
                "warn",
                f"husky hooks without the engine: {', '.join(missing)}; run `{_meta.NAME} sync`",
            )
        return Status("ok", "through husky")
    if kind == "pre-commit":
        if f"{_meta.NAME} hook" in _read(project / PRE_COMMIT_CONFIG):
            return Status("ok", f"through {PRE_COMMIT_CONFIG}")
        return Status(
            "warn",
            f"{PRE_COMMIT_CONFIG} does not run `{_meta.NAME} hook`; "
            f"run `{_meta.NAME} sync` for the block to add",
        )
    top = git.toplevel(project)
    assert top is not None
    wanted = expected_path(project, top)
    current = git.config_get(project, HOOKS_PATH)
    if current != wanted:
        where = f"it points to {current}" if current else "it is not set"
        return Status(
            "warn", f"not active in this clone ({HOOKS_PATH}: {where}); run `{_meta.NAME} sync`"
        )
    missing = [name for name in HOOKS if not (project / FOLDER / name).is_file()]
    if missing:
        return Status("warn", f"missing hooks: {', '.join(missing)}; run `{_meta.NAME} sync`")
    if os.name != "nt":
        flat = [n for n in HOOKS if not (project / FOLDER / n).stat().st_mode & stat.S_IXUSR]
        if flat:
            return Status("warn", f"not executable: {', '.join(flat)}; run `{_meta.NAME} sync`")
    return Status("ok", f"{HOOKS_PATH} = {wanted}")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
