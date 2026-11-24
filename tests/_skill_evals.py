"""Evals de skills (F7, criterio 3, D-41, ADR-0016): formato, carga y chequeos.

Cada skill evaluada tiene `tests/skill_evals/<skill>/evals.json`:

```json
{
  "skill": "accessibility-audit",
  "fixture": "node-shop",
  "packs": ["core", "sdd", "frontend"],
  "cases": [
    {"id": "trigger", "expect": "trigger", "prompt": "..."},
    {"id": "no-trigger", "expect": "no-trigger", "prompt": "..."},
    {"id": "output", "expect": "trigger", "prompt": "...",
     "checks": {"answer_contains": ["WCAG"], "answer_matches": ["2\\.2"],
                "files_written": ["docs/*.md"],
                "file_contains": {"docs/*.md": ["^## Verdict"]},
                "files_unchanged": ["src/*"]},
     "review": "What a person checks by hand in the answer."}
  ]
}
```

- `fixture`: una carpeta de `tests/fixtures/repos/`, o `empty` (un repo con un README).
  Un caso puede cambiarla con su propio `fixture`.
- `setup` (opcional, en el caso o arriba): `{"files": {"ruta": "texto"}, "stage": true}`.
  Los archivos se escriben **después** del commit base, sin commitear: así hay un diff
  que revisar o artefactos de un change. Con `stage`, además se agregan al índice. Las
  rutas son relativas al proyecto, con `/`, y no pueden salir de él (ni `..`, ni una
  ruta absoluta o con unidad, en Windows ni en POSIX). El `setup` de un caso
  **reemplaza** entero al de arriba (no se combinan): un caso que necesita los archivos
  de arriba y uno más los repite todos.
- `packs`: los que instala `exo init` (más sus `requires`). Tiene que incluir el pack de
  la skill: sin él la skill no se instala y el caso no mide nada. Un caso puede
  cambiarlos con sus propios `packs`, con la misma regla.
- Los pedidos de `trigger` y `no-trigger` no nombran la skill: miden si el agente la
  elige por su `description`.
- `output` es un `trigger` con chequeos sobre la respuesta final y los archivos; necesita
  al menos uno que mida algo (cualquiera menos `files_unchanged`, que solo prohíbe):
  - `answer_contains`: textos que la respuesta contiene (sin distinguir mayúsculas);
  - `answer_matches`: regex que la respuesta cumple;
  - `files_written`: globs; algún archivo que la corrida creó o modificó coincide con cada uno;
  - `file_contains`: `{"<glob>": ["<regex>", ...]}`; algún archivo escrito que coincide con
    el glob contiene cada regex (todas en el mismo archivo);
  - `files_unchanged`: globs que la corrida no puede haber creado, modificado ni borrado.

  Las regex se buscan con `re.IGNORECASE | re.MULTILINE`. Los globs son de `fnmatch`
  sobre la ruta relativa con `/` (`*` también cruza carpetas).
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent / "skill_evals"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "repos"
EMPTY = "empty"
CASE_IDS = ("trigger", "no-trigger", "output")
EXPECT = {"trigger": "trigger", "no-trigger": "no-trigger", "output": "trigger"}
# Los chequeos que miden algo que la skill hizo; `files_unchanged` solo prohíbe.
POSITIVE_CHECKS = ("answer_contains", "answer_matches", "files_written", "file_contains")
CHECKS = (*POSITIVE_CHECKS, "files_unchanged")
_LIST_CHECKS = ("answer_contains", "answer_matches", "files_written", "files_unchanged")
_FLAGS = re.IGNORECASE | re.MULTILINE
# Aíslan la corrida de la config de usuario de Claude Code (settings, skills, plugins, hooks,
# CLAUDE.md) y de todo servidor MCP que no venga de `--mcp-config` (no se pasa ninguno).
ISOLATION_FLAGS = ("--setting-sources", "project,local", "--strict-mcp-config")

# Las skills de prioridad 1 y 2 de F7 (F7-packs.md): cada una tiene sus tres casos.
PRIORITY_1 = (
    "reasons-canvas-author",
    "prompt-spec-review",
    "prompt-code-sync",
    "context-anchoring",
    "sdd-onboard",
    "judge-product",
    "judge-business",
    "judge-frontend",
    "judge-team",
    "excellence-committee",
    "review-4r",
    "product-discovery",
    "accessibility-audit",
    "parallel-dispatch",
    "chained-pr",
)
PRIORITY_2 = (
    "backend-and-api",
    "backend-engineering",
    "java-build-resolver",
    "java-coding-standards",
    "java-reviewer",
    "jpa-patterns",
    "security-scan-jkp",
    "springboot-patterns",
    "springboot-security",
    "springboot-verification",
    "python-patterns",
    "python-reviewer",
    "frontend-design",
    "frontend-engineering",
    "frontend-patterns",
    "playwright",
    "react-patterns",
    "react-testing",
    "security-scan-node",
    "tailwind-4",
    "typescript-reviewer",
    "typescript",
    "zod",
)
REQUIRED = PRIORITY_1 + PRIORITY_2


@dataclass(frozen=True)
class Case:
    skill: str
    id: str
    expect: str
    prompt: str
    fixture: str
    packs: tuple[str, ...]
    checks: dict[str, Any] = field(default_factory=dict)
    review: str = ""
    setup: dict[str, Any] = field(default_factory=dict)


def load(skill_dir: Path) -> dict[str, Any]:
    return json.loads((skill_dir / "evals.json").read_text(encoding="utf-8"))


def problems(data: Any, folder: str, skills: Mapping[str, str], packs: set[str]) -> list[str]:
    """Lo que está mal en un `evals.json` (vacío si está bien).

    `skills`: cada skill del contenido -> su pack.
    """
    if not isinstance(data, dict):
        return ["evals.json must be a JSON object"]
    found: list[str] = []
    skill = data.get("skill")
    if skill != folder:
        found.append(f"skill is {skill!r} but the folder is {folder!r}")
    if skill not in skills:
        found.append(f"{skill!r} is not a skill of the content")
    pack_of = skills.get(skill) if isinstance(skill, str) else None
    found += _fixture_problems(data.get("fixture"))
    found += _packs_problems(data.get("packs"), packs, str(skill), pack_of)
    if "setup" in data:
        found += _setup_problems(data["setup"])
    cases = data.get("cases")
    if not isinstance(cases, list):
        return [*found, "cases must be a list"]
    ids = [c.get("id") for c in cases if isinstance(c, dict)]
    if sorted(ids, key=str) != sorted(CASE_IDS):
        found.append(f"cases must be exactly {', '.join(CASE_IDS)} (got {ids})")
    for case in cases:
        if isinstance(case, dict):
            found += _case_problems(case, str(skill), packs, pack_of)
    return found


def _packs_problems(wanted: Any, packs: set[str], skill: str, pack_of: str | None) -> list[str]:
    if not isinstance(wanted, list) or not wanted or not all(isinstance(p, str) for p in wanted):
        return ["packs must be a non-empty list"]
    found = [f"unknown pack {p!r}" for p in wanted if p not in packs]
    if pack_of is not None and pack_of not in wanted:
        found.append(f"packs must include {pack_of!r}, the pack of {skill}")
    return found


def unsafe_path(rel: Any) -> bool:
    """¿La ruta de un archivo de `setup` no es relativa al proyecto, portable y adentro?

    Se mira con las reglas de Windows y de POSIX: `C:/x`, `C:x`, una barra inicial, un
    recurso de red y `..` escapan en Windows aunque en POSIX parezcan relativas. Se exige
    `/` como separador (con barra invertida la misma ruta es otra en POSIX) y nada de `:`
    (los streams de NTFS).
    """
    if not isinstance(rel, str) or not rel or "\\" in rel or ":" in rel or rel.endswith("/"):
        return True
    win, posix = PureWindowsPath(rel), PurePosixPath(rel)
    if win.drive or win.root or posix.root or not posix.parts:
        return True
    return ".." in posix.parts or ".." in win.parts


def setup_target(project: Path, rel: str) -> Path:
    """Dónde escribe el runner un archivo de `setup`: falla si la ruta sale del proyecto,
    también a través de un link."""
    if unsafe_path(rel):
        raise ValueError(f"setup.files: {rel!r} must be a relative path inside the project")
    root = Path(project).resolve()
    target = (root / rel).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"setup.files: {rel!r} resolves outside the project ({target})")
    return target


def _setup_problems(setup: Any) -> list[str]:
    if not isinstance(setup, dict) or set(setup) - {"files", "stage"}:
        return ["setup must be an object with files and, optionally, stage"]
    files = setup.get("files")
    if not isinstance(files, dict) or not files:
        return ["setup.files must map relative paths to their text"]
    found = [
        f"setup.files: {rel!r} must be a relative path inside the project, with /"
        for rel in files
        if unsafe_path(rel)
    ]
    found += [
        f"setup.files: {rel!r} must be text"
        for rel, text in files.items()
        if not isinstance(text, str)
    ]
    if not isinstance(setup.get("stage", False), bool):
        found.append("setup.stage must be true or false")
    return found


def _fixture_problems(fixture: Any) -> list[str]:
    if fixture == EMPTY:
        return []
    if not isinstance(fixture, str) or not (FIXTURES_DIR / fixture).is_dir():
        return [f"fixture {fixture!r} is not {EMPTY!r} nor a folder of tests/fixtures/repos"]
    return []


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value)


def _case_problems(
    case: dict[str, Any], skill: str, packs: set[str], pack_of: str | None
) -> list[str]:
    found: list[str] = []
    case_id = case.get("id")
    if case.get("expect") != EXPECT.get(str(case_id)):
        found.append(f"{case_id}: expect must be {EXPECT.get(str(case_id))!r}")
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or len(prompt.split()) < 4:
        found.append(f"{case_id}: the prompt must be a sentence")
    elif case_id in ("trigger", "no-trigger") and skill.lower() in prompt.lower():
        found.append(f"{case_id}: the prompt names the skill; it must pick it by its description")
    if "fixture" in case:
        found += [f"{case_id}: {p}" for p in _fixture_problems(case["fixture"])]
    if "packs" in case:
        found += [f"{case_id}: {p}" for p in _packs_problems(case["packs"], packs, skill, pack_of)]
    if "setup" in case:
        found += [f"{case_id}: {p}" for p in _setup_problems(case["setup"])]
    checks = case.get("checks", {})
    if case_id == "output":
        if not isinstance(checks, dict) or not any(checks.get(k) for k in POSITIVE_CHECKS):
            found.append(f"output: checks needs one of {', '.join(POSITIVE_CHECKS)}")
        if not str(case.get("review", "")).strip():
            found.append("output: review must say what a person checks")
    if not isinstance(checks, dict):
        return [*found, f"{case_id}: checks must be an object"]
    found += [f"{case_id}: unknown check {k!r}" for k in checks if k not in CHECKS]
    found += [
        f"{case_id}: {key} must be a list of non-empty strings"
        for key in _LIST_CHECKS
        if key in checks and not _strings(checks[key])
    ]
    patterns = list(checks["answer_matches"]) if _strings(checks.get("answer_matches")) else []
    contains = checks.get("file_contains", {})
    if not isinstance(contains, dict) or not all(
        isinstance(glob, str) and glob and _strings(regexes) and regexes
        for glob, regexes in contains.items()
    ):
        found.append(f"{case_id}: file_contains must map a glob to a non-empty list of regexes")
    else:
        patterns += [p for regexes in contains.values() for p in regexes]
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            found.append(f"{case_id}: bad regex {pattern!r} ({exc})")
    return found


def cases() -> list[Case]:
    """Todos los casos de todas las skills evaluadas, en orden."""
    found: list[Case] = []
    for folder in (
        sorted(p for p in EVALS_DIR.iterdir() if p.is_dir()) if EVALS_DIR.is_dir() else []
    ):
        data = load(folder)
        for case in data["cases"]:
            found.append(
                Case(
                    skill=data["skill"],
                    id=case["id"],
                    expect=case["expect"],
                    prompt=case["prompt"],
                    fixture=case.get("fixture", data["fixture"]),
                    packs=tuple(case.get("packs", data["packs"])),
                    checks=case.get("checks", {}),
                    review=case.get("review", ""),
                    # El del caso reemplaza al de arriba: no se combinan.
                    setup=case.get("setup", data.get("setup", {})),
                )
            )
    return found


# -- la corrida de Claude Code -----------------------------------------------------------------


def claude_command(claude: str, prompt: str, tools: str, max_turns: int) -> list[str]:
    """`claude -p` con salida stream-json, las tools permitidas y aislado de la config de
    usuario (`ISOLATION_FLAGS`)."""
    return [
        claude,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        *ISOLATION_FLAGS,
        "--allowedTools",
        tools,
        # `Bash(git:*)` cubre git push: el agente nunca publica (threat model, M-17).
        "--disallowedTools",
        "Bash(git push:*) PowerShell(git push:*)",
        "--max-turns",
        str(max_turns),
    ]


def runner_env(data: Path, base: Mapping[str, str]) -> dict[str, str]:
    """El entorno de una corrida: los datos de usuario de exo en `data` y el bin del
    intérprete de la suite primero en el PATH, así el `exo` que corre el agente es este."""
    env = dict(base)
    env["EXO_DATA_DIR"] = str(data)
    env["EXO_MEMORY_DB"] = str(Path(data) / "memory.db")
    # Un `git config --global` del agente escribe acá y no en el de la persona (M-17); la
    # identidad de los commits es la del repo de prueba (`_git.init_repo`).
    gitconfig = Path(data) / "gitconfig"
    gitconfig.parent.mkdir(parents=True, exist_ok=True)
    if not gitconfig.exists():
        gitconfig.write_text("", encoding="utf-8")
    env["GIT_CONFIG_GLOBAL"] = str(gitconfig)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    key = "PATH"
    if os.name == "nt":  # en Windows la variable puede llamarse `Path`
        key = next((k for k in env if k.upper() == "PATH"), "PATH")
    current = env.get(key, "")
    env[key] = str(Path(sys.executable).parent) + (os.pathsep + current if current else "")
    return env


# -- lectura de la salida stream-json de Claude Code ------------------------------------------


@dataclass
class Run:
    used: list[str] = field(default_factory=list)  # skills cargadas, en orden
    answer: str = ""
    turns: int | None = None
    error: str | None = None
    # Las skills que el agente veía (evento `system`/`init`); None si el stream no lo trae.
    visible: list[str] | None = None


def parse_stream(lines: list[str]) -> Run:
    """Las skills que cargó el agente y su respuesta final, de `--output-format stream-json`.

    Una skill cuenta como cargada si el agente la invocó con la tool `Skill`, o si leyó su
    `SKILL.md` (un agente que sigue el registro de skills la abre con `Read`). Del evento
    `system`/`init` se guardan las skills visibles, para auditar el aislamiento.
    """
    run = Run()
    for raw in lines:
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            skills = event.get("skills")
            if isinstance(skills, list):
                run.visible = [str(s) for s in skills]
            continue
        if event.get("type") == "result":
            run.answer = str(event.get("result") or "")
            run.turns = event.get("num_turns")
            if event.get("is_error"):
                run.error = str(event.get("subtype") or "error")
            continue
        message = event.get("message")
        blocks = message.get("content") if isinstance(message, dict) else None
        for block in blocks if isinstance(blocks, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = _skill_of(block.get("name"), block.get("input") or {})
            if name and name not in run.used:
                run.used.append(name)
    return run


_SKILL_FILE = re.compile(r"(?:^|[\\/])skills[\\/]([a-z0-9-]+)[\\/]SKILL\.md$")


def _skill_of(tool: Any, args: Any) -> str | None:
    if not isinstance(args, dict):
        return None
    if tool == "Skill":
        value = args.get("skill") or args.get("command") or args.get("name")
        return str(value).split(":")[-1].lstrip("/") if value else None
    if tool == "Read":
        match = _SKILL_FILE.search(str(args.get("file_path", "")))
        return match.group(1) if match else None
    return None


def snapshot(project: Path) -> dict[str, int]:
    """Ruta -> (tamaño, mtime) de los archivos del proyecto, sin `.git`."""
    found: dict[str, int] = {}
    for path in project.rglob("*"):
        rel = path.relative_to(project).as_posix()
        if path.is_file() and not rel.startswith(".git/"):
            stat = path.stat()
            found[rel] = hash((stat.st_size, stat.st_mtime_ns))
    return found


def changed(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """Los archivos que la corrida creó o modificó."""
    return sorted(rel for rel, sig in after.items() if before.get(rel) != sig)


def removed(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """Los archivos que la corrida borró."""
    return sorted(rel for rel in before if rel not in after)


def _text(project: Path, rel: str) -> str:
    try:
        return (project / rel).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def check_output(
    case: Case,
    run: Run,
    written: list[str],
    project: Path | None = None,
    deleted: Sequence[str] = (),
) -> list[str]:
    """Los chequeos de `output` que no se cumplen.

    `written`: lo que la corrida creó o modificó; `deleted`: lo que borró; `project`: la
    carpeta donde leer los archivos escritos (la necesita `file_contains`).
    """
    failed: list[str] = []
    answer = run.answer.lower()
    for text in case.checks.get("answer_contains", []):
        if text.lower() not in answer:
            failed.append(f"the answer does not contain {text!r}")
    for pattern in case.checks.get("answer_matches", []):
        if not re.search(pattern, run.answer, _FLAGS):
            failed.append(f"the answer does not match {pattern!r}")
    for pattern in case.checks.get("files_written", []):
        if not any(fnmatch.fnmatchcase(rel, pattern) for rel in written):
            failed.append(f"no written file matches {pattern!r}")
    contains: dict[str, list[str]] = case.checks.get("file_contains", {})
    if contains and project is None:
        raise ValueError("file_contains needs the project folder to read the written files")
    for glob, regexes in contains.items():
        candidates = [rel for rel in written if fnmatch.fnmatchcase(rel, glob)]
        if not candidates:
            failed.append(f"no written file matches {glob!r}")
            continue
        closest: tuple[str, list[str]] | None = None
        for rel in candidates:
            text = _text(Path(project or "."), rel)
            missing = [r for r in regexes if not re.search(r, text, _FLAGS)]
            if closest is None or len(missing) < len(closest[1]):
                closest = (rel, missing)
            if not missing:
                break
        if closest and closest[1]:
            failed.append(
                f"no written file matching {glob!r} matches all its regexes: the closest, "
                f"{closest[0]}, misses {closest[1]}"
            )
    touched = [*written, *deleted]
    for glob in case.checks.get("files_unchanged", []):
        hit = [rel for rel in touched if fnmatch.fnmatchcase(rel, glob)]
        if hit:
            failed.append(f"{', '.join(hit)} changed, but files_unchanged has {glob!r}")
    return failed
