"""Git hooks del motor: qué se instala y cómo se activan (D-21, ADR-0014).

- **Por defecto**, tres scripts finos en `<carpeta del motor>/githooks/` que llaman
  a `exo hook <nombre>`, activados con `core.hooksPath`. Es por clon: cada uno corre
  `exo init` o `exo sync`, y `exo doctor` avisa si no están activos.
- **Con husky** (`.husky/`, husky 9), se agrega un bloque a cada script de husky
  y no se toca `core.hooksPath`, que es de husky; `exo doctor` verifica que apunte a
  husky (si no, falta `npm install`).
- **Con el framework pre-commit** (`.pre-commit-config.yaml`), el motor no edita su
  YAML: imprime el bloque a agregar (los tres hooks) y `exo doctor` verifica que esté
  y que `pre-commit install` haya corrido.
- **Si `core.hooksPath` ya apunta a otro lado**, en cualquier scope (local, global o
  del sistema), no se pisa: se avisa.
- **Si el clon ya tiene hooks propios en `.git/hooks`** (git-lfs, Gerrit), activar
  `core.hooksPath` los apagaría: no se activa y se avisa.

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
        stages: [commit-msg]
      - id: {cli}-pre-push
        name: {cli} pre-push
        entry: {cli} hook pre-push
        language: system
        pass_filenames: false
        stages: [pre-push]"""


PRE_COMMIT_INSTALL = (
    "pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push"
)


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
            f"{HOOKS_PATH}. Add this under `repos:` and run `{PRE_COMMIT_INSTALL}`:\n"
            f"{pre_commit_snippet()}"
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
    found = git.config_get_any(project, HOOKS_PATH)
    if found is not None:
        scope, current = found
        if current == wanted:
            return []
        return [
            f"{HOOKS_PATH} is already set to {current} ({scope} config), so the engine did not "
            f"change it and its hooks are not active. Add `{_meta.NAME} hook <name>` to those "
            "hooks, or set governance.githooks to false"
        ]
    own = own_hooks(project)
    if own:
        return [
            f"this clone has its own hooks in {_hooks_label(project, top)} ({', '.join(own)}, "
            f"for example git-lfs); setting {HOOKS_PATH} would stop them, so the engine did not "
            f"activate its hooks. Add `{_meta.NAME} hook <name>` to those hooks, or move them "
            f"away and run `{_meta.NAME} sync`"
        ]
    if not git.config_set(project, HOOKS_PATH, wanted):
        return [f"could not set {HOOKS_PATH}; run `git config {HOOKS_PATH} {wanted}`"]
    return [f"git hooks active in this clone ({HOOKS_PATH} = {wanted})"]


def _hooks_dir(project: Path) -> Path | None:
    result = git.run(project, "rev-parse", "--git-common-dir")
    if not result.ok or not result.out.strip():
        return None
    common = Path(result.out.strip())
    return (common if common.is_absolute() else Path(project) / common) / "hooks"


def _hooks_label(project: Path, top: Path) -> str:
    folder = _hooks_dir(project)
    if folder is None:
        return ".git/hooks"
    try:
        return folder.resolve().relative_to(top.resolve()).as_posix()
    except ValueError:
        return folder.as_posix()


def own_hooks(project: Path) -> list[str]:
    """Hooks que el clon ya tiene en `.git/hooks` (sin los `.sample` de git)."""
    folder = _hooks_dir(project)
    if folder is None or not folder.is_dir():
        return []
    return sorted(
        p.name for p in folder.iterdir() if p.is_file() and not p.name.endswith(".sample")
    )


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
        found = git.config_get_any(project, HOOKS_PATH)
        if found is None or found[1].rstrip("/") not in (HUSKY, f"{HUSKY}/_"):
            where = f"it points to {found[1]}" if found else "it is not set"
            return Status(
                "warn",
                f"husky is not active in this clone ({HOOKS_PATH}: {where}); run `npm install` "
                "or `npx husky`",
            )
        return Status("ok", "through husky")
    if kind == "pre-commit":
        text = _read(project / PRE_COMMIT_CONFIG)
        absent = [name for name in HOOKS if f"{_meta.NAME} hook {name}" not in text]
        if absent:
            return Status(
                "warn",
                f"{PRE_COMMIT_CONFIG} does not run `{_meta.NAME} hook` for {', '.join(absent)}; "
                f"run `{_meta.NAME} sync` for the block to add",
            )
        folder = _hooks_dir(project)
        found = git.config_get_any(project, HOOKS_PATH)
        if found is not None:
            folder = Path(found[1]) if Path(found[1]).is_absolute() else project / found[1]
        idle = [
            name for name in HOOKS if folder is None or "pre-commit" not in _read(folder / name)
        ]
        if idle:
            return Status(
                "warn",
                f"pre-commit is not installed for {', '.join(idle)}; run `{PRE_COMMIT_INSTALL}`",
            )
        return Status("ok", f"through {PRE_COMMIT_CONFIG}")
    top = git.toplevel(project)
    assert top is not None
    wanted = expected_path(project, top)
    found = git.config_get_any(project, HOOKS_PATH)
    current = found[1] if found else None
    if current != wanted:
        if found is not None:
            where = f"it points to {current} ({found[0]} config)"
        elif own_hooks(project):
            return Status(
                "warn",
                f"not active: {_hooks_label(project, top)} has its own hooks "
                f"({', '.join(own_hooks(project))}); add `{_meta.NAME} hook <name>` to them",
            )
        else:
            where = "it is not set"
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
