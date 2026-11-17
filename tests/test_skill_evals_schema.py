"""Evals de skills (F7, criterio 3): el formato, la cobertura y la lectura de la salida.

Corre en la suite normal. Las corridas con Claude Code real están en
`test_skill_evals.py` (`agent_e2e`).
"""

from __future__ import annotations

import json

import pytest

import _skill_evals as evals
from exo import content, packs

COLLECTION = packs.load_collection(content.content_root())
SKILLS = {skill.name for skill in COLLECTION.skills}
FOLDERS = (
    sorted(p for p in evals.EVALS_DIR.iterdir() if p.is_dir()) if evals.EVALS_DIR.is_dir() else []
)


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_cada_evals_json_es_valido(folder) -> None:
    found = evals.problems(evals.load(folder), folder.name, SKILLS, set(COLLECTION.packs))
    assert found == [], found


def test_criterio_3_las_skills_de_prioridad_1_y_2_tienen_sus_tres_casos() -> None:
    """Toda skill de prioridad 1 o 2 que ya existe tiene su evals.json."""
    present = {p.name for p in FOLDERS}
    missing = [s for s in evals.REQUIRED if s in SKILLS and s not in present]
    assert missing == [], missing


def test_la_lista_de_prioridades_no_tiene_repetidas() -> None:
    assert len(set(evals.REQUIRED)) == len(evals.REQUIRED) == 38


def _event(**fields) -> str:
    return json.dumps(fields)


def _tool(name: str, args: dict) -> str:
    content_ = [{"type": "tool_use", "id": "t1", "name": name, "input": args}]
    return _event(type="assistant", message={"content": content_})


def test_parse_stream_ve_la_tool_skill_y_la_lectura_del_skill_md() -> None:
    lines = [
        _event(type="system", subtype="init"),
        _tool("Skill", {"skill": "accessibility-audit"}),
        _tool("Read", {"file_path": "C:\\p\\.claude\\skills\\judge-product\\SKILL.md"}),
        _tool("Read", {"file_path": "/p/.claude/skills/zod/references/x.md"}),
        _tool("Skill", {"skill": "accessibility-audit"}),
        "not json",
        _event(type="result", subtype="success", result="Done: WCAG 2.2 AA.", num_turns=4),
    ]
    run = evals.parse_stream(lines)
    assert run.used == ["accessibility-audit", "judge-product"]
    assert run.answer == "Done: WCAG 2.2 AA." and run.turns == 4 and run.error is None


def test_parse_stream_marca_el_error() -> None:
    run = evals.parse_stream([_event(type="result", subtype="error_max_turns", is_error=True)])
    assert run.error == "error_max_turns"


def test_check_output() -> None:
    case = evals.Case(
        skill="x",
        id="output",
        expect="trigger",
        prompt="audit the form please",
        fixture="empty",
        packs=("core",),
        checks={
            "answer_contains": ["wcag"],
            "answer_matches": [r"2\.2"],
            "files_written": ["docs/*.md"],
        },
    )
    run = evals.Run(answer="Checked against WCAG 2.2 AA.")
    assert evals.check_output(case, run, ["docs/a11y.md"]) == []
    failed = evals.check_output(case, evals.Run(answer="ok"), [])
    assert len(failed) == 3


def test_setup_valido_y_rutas_que_escapan() -> None:
    assert evals._setup_problems({"files": {"src/a.py": "x = 1\n"}, "stage": True}) == []
    found = evals._setup_problems({"files": {"../evil.py": "x", "/abs.py": "y", "ok.py": 3}})
    assert len(found) == 3, found
    assert evals._setup_problems({"files": {}}) and evals._setup_problems({"other": 1})


def test_problems_rechaza_lo_que_no_mide_nada() -> None:
    data = {
        "skill": "zod",
        "fixture": "nope",
        "packs": ["core", "ghost"],
        "cases": [
            {"id": "trigger", "expect": "trigger", "prompt": "use zod to validate this input"},
            {"id": "no-trigger", "expect": "trigger", "prompt": "short"},
            {"id": "output", "expect": "trigger", "prompt": "validate this payload at the edge"},
        ],
    }
    found = evals.problems(data, "zod", {"zod"}, {"core"})
    joined = " | ".join(found)
    for fragment in (
        "fixture",
        "ghost",
        "names the skill",
        "no-trigger: expect",
        "sentence",
        "checks needs",
        "review",
    ):
        assert fragment in joined, (fragment, found)
