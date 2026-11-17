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
                "files_written": ["docs/*.md"]},
     "review": "What a person checks by hand in the answer."}
  ]
}
```

- `fixture`: una carpeta de `tests/fixtures/repos/`, o `empty` (un repo con un README).
  Un caso puede cambiarla con su propio `fixture`.
- `setup` (opcional, en el caso o arriba): `{"files": {"ruta": "texto"}, "stage": true}`.
  Los archivos se escriben **después** del commit base, sin commitear: así hay un diff
  que revisar o artefactos de un change. Con `stage`, además se agregan al índice.
- `packs`: los que instala `exo init` (más sus `requires`).
- Los pedidos de `trigger` y `no-trigger` no nombran la skill: miden si el agente la
  elige por su `description`.
- `output` es un `trigger` con chequeos sobre la respuesta final y los archivos.
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent / "skill_evals"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "repos"
EMPTY = "empty"
CASE_IDS = ("trigger", "no-trigger", "output")
EXPECT = {"trigger": "trigger", "no-trigger": "no-trigger", "output": "trigger"}
CHECKS = ("answer_contains", "answer_matches", "files_written")

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
    checks: dict[str, list[str]] = field(default_factory=dict)
    review: str = ""
    setup: dict[str, Any] = field(default_factory=dict)


def load(skill_dir: Path) -> dict[str, Any]:
    return json.loads((skill_dir / "evals.json").read_text(encoding="utf-8"))


def problems(data: Any, folder: str, skills: set[str], packs: set[str]) -> list[str]:
    """Lo que está mal en un `evals.json` (vacío si está bien)."""
    if not isinstance(data, dict):
        return ["evals.json must be a JSON object"]
    found: list[str] = []
    skill = data.get("skill")
    if skill != folder:
        found.append(f"skill is {skill!r} but the folder is {folder!r}")
    if skill not in skills:
        found.append(f"{skill!r} is not a skill of the content")
    found += _fixture_problems(data.get("fixture"))
    wanted = data.get("packs")
    if not isinstance(wanted, list) or not wanted:
        found.append("packs must be a non-empty list")
    else:
        found += [f"unknown pack {p!r}" for p in wanted if p not in packs]
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
            found += _case_problems(case, str(skill))
    return found


def _setup_problems(setup: Any) -> list[str]:
    if not isinstance(setup, dict) or set(setup) - {"files", "stage"}:
        return ["setup must be an object with files and, optionally, stage"]
    files = setup.get("files")
    if not isinstance(files, dict) or not files:
        return ["setup.files must map relative paths to their text"]
    found = [
        f"setup.files: {rel!r} must be a relative path inside the project"
        for rel in files
        if not isinstance(rel, str) or rel.startswith(("/", "\\")) or ".." in rel.split("/")
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


def _case_problems(case: dict[str, Any], skill: str) -> list[str]:
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
    if "setup" in case:
        found += [f"{case_id}: {p}" for p in _setup_problems(case["setup"])]
    checks = case.get("checks", {})
    if case_id == "output":
        if not isinstance(checks, dict) or not any(checks.get(k) for k in CHECKS):
            found.append(f"output: checks needs one of {', '.join(CHECKS)}")
        if not str(case.get("review", "")).strip():
            found.append("output: review must say what a person checks")
    if isinstance(checks, dict):
        found += [f"{case_id}: unknown check {k!r}" for k in checks if k not in CHECKS]
        for pattern in checks.get("answer_matches", []):
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
                    setup=case.get("setup", data.get("setup", {})),
                )
            )
    return found


# -- lectura de la salida stream-json de Claude Code ------------------------------------------


@dataclass
class Run:
    used: list[str] = field(default_factory=list)  # skills cargadas, en orden
    answer: str = ""
    turns: int | None = None
    error: str | None = None


def parse_stream(lines: list[str]) -> Run:
    """Las skills que cargó el agente y su respuesta final, de `--output-format stream-json`.

    Una skill cuenta como cargada si el agente la invocó con la tool `Skill`, o si leyó su
    `SKILL.md` (un agente que sigue el registro de skills la abre con `Read`).
    """
    run = Run()
    for raw in lines:
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(event, dict):
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


def check_output(case: Case, run: Run, written: list[str]) -> list[str]:
    """Los chequeos de `output` que no se cumplen (`written`: lo que la corrida escribió)."""
    failed: list[str] = []
    answer = run.answer.lower()
    for text in case.checks.get("answer_contains", []):
        if text.lower() not in answer:
            failed.append(f"the answer does not contain {text!r}")
    for pattern in case.checks.get("answer_matches", []):
        if not re.search(pattern, run.answer, re.IGNORECASE | re.MULTILINE):
            failed.append(f"the answer does not match {pattern!r}")
    for pattern in case.checks.get("files_written", []):
        if not any(fnmatch.fnmatchcase(rel, pattern) for rel in written):
            failed.append(f"no written file matches {pattern!r}")
    return failed
