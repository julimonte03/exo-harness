"""Consistencia del contenido del ciclo SDD (F4, tarea 8 y criterios 1 y 2).

Port de `test_phase_skill_map_consistency` del reporte (§10.4), con lo que F4
define: toda skill que nombra el mapa fase → skills existe o pertenece a un
pack que todavía no existe y declara cómo degrada; las skills de fase dicen
dónde corren como manda el contrato común (sección G); los subagentes tienen
las tools de su rol.
"""

from __future__ import annotations

import json

import pytest

from exo import _meta, content, packs, phase_map
from exo.core import frontmatter

ROOT = content.content_root()
COLLECTION = packs.load_collection(ROOT)
SKILLS = {s.name: s for s in COLLECTION.skills}
MAP = phase_map.load(ROOT)
SHARED = f"{_meta.PROJECT_DIR}/shared"

CORE = (
    "memory-protocol",
    "context-retrieval",
    "ai-usage-record",
    "test-strategy",
    "code-generation",
    "branch-pr",
    "work-unit-commits",
    "project-onboarding",
)
# Skill de fase -> (dónde corre, subagente) según la tabla de la sección G del contrato común.
PHASES = {
    "risk-tiering": ("inline", None),
    "sdd-new": ("inline", None),
    "sdd-init": ("inline", None),
    "sdd-status": ("inline", None),
    "sdd-explore": ("subagent", "sdd-explorer"),
    "sdd-propose": ("inline", None),
    "sdd-spec": ("inline", None),
    "sdd-design": ("inline", None),
    "sdd-tasks": ("inline", None),
    "sdd-apply": ("subagent", "sdd-implementer"),
    "sdd-verify": ("subagent", "sdd-verifier"),
    "sdd-archive": ("inline", None),
}
ORCHESTRATION = ("sdd-orchestrator", "sdd-continue", "sdd-ff")
TOOLS = {
    "sdd-explorer": {"Read", "Grep", "Glob"},
    "sdd-implementer": {"Read", "Grep", "Glob", "Edit", "Write", "Bash"},
    "sdd-verifier": {"Read", "Grep", "Glob", "Bash"},
    "sdd-judge": {"Read", "Grep", "Glob"},
}


def _meta_of(name: str) -> dict[str, str]:
    return dict(SKILLS[name].metadata)


def test_criterio_1_skills_de_la_fase() -> None:
    assert {n for n in CORE if SKILLS.get(n) and SKILLS[n].pack == "core"} == set(CORE)
    sdd = (*PHASES, *ORCHESTRATION)
    assert {n for n in sdd if SKILLS.get(n) and SKILLS[n].pack == "sdd"} == set(sdd)
    assert "hello-exo" not in SKILLS


def test_criterio_2_toda_skill_del_mapa_existe_o_degrada() -> None:
    assert MAP is not None and MAP.mentions
    missing = sorted(m for m in MAP.mentions if m not in SKILLS and m not in MAP.degradations)
    assert missing == [], f"mencionadas sin skill ni degradación declarada: {missing}"


def test_criterio_2_las_degradaciones_son_de_skills_que_faltan() -> None:
    """Si una skill ya existe, su fila de degradación sobra; cada fila tiene criterio y pack declarado."""
    assert MAP is not None
    sdd = COLLECTION.packs["sdd"]
    for item in MAP.degradations.values():
        assert item.skill not in SKILLS, (
            f"{item.skill} ya existe: sacala de la tabla de degradaciones"
        )
        assert item.criteria, f"{item.skill} no tiene criterio inline"
        assert item.pack in ("core", "sdd", *sdd.optional), (
            f"{item.skill}: pack {item.pack} sin declarar"
        )


def test_criterio_2_las_skills_requeridas_del_ciclo_existen() -> None:
    """Las Required del mapa que entregan F4 tienen que existir (no pueden degradar)."""
    assert MAP is not None
    for name in (
        "risk-tiering",
        "context-retrieval",
        "test-strategy",
        "code-generation",
        "work-unit-commits",
        "branch-pr",
    ):
        assert name in MAP.mentions and name in SKILLS


@pytest.mark.parametrize("name", sorted(PHASES))
def test_las_skills_de_fase_corren_donde_dice_el_contrato(name: str) -> None:
    execution, subagent = PHASES[name]
    meta = _meta_of(name)
    assert meta.get("exo-execution") == execution
    assert meta.get("exo-subagent") == subagent
    if subagent:
        assert subagent in {a.name for a in COLLECTION.subagents}


@pytest.mark.parametrize("name", sorted((*PHASES, *ORCHESTRATION)))
def test_las_skills_del_ciclo_siguen_el_contrato_comun(name: str) -> None:
    body = (SKILLS[name].path / packs.SKILL_FILE).read_text(encoding="utf-8")
    assert f"{SHARED}/sdd-phase-common.md" in body
    assert body.count("\n") <= 500


@pytest.mark.parametrize("name", sorted(TOOLS))
def test_los_subagentes_tienen_las_tools_de_su_rol(name: str) -> None:
    agent = next(a for a in COLLECTION.subagents if a.name == name)
    data, _ = frontmatter.parse(agent.path.read_text(encoding="utf-8"), strict=True)
    tools = {t.strip() for t in str(data.get("tools", "")).split(",") if t.strip()}
    assert tools == TOOLS[name]
    assert "skeleton" not in agent.path.read_text(encoding="utf-8").lower()


def test_el_esquema_del_registro_se_instala_con_sdd() -> None:
    from exo.installer.bundle import build_bundle

    shared = build_bundle(ROOT, ["sdd"]).shared
    assert "schemas/ai-usage-record.schema.json" in shared
    assert json.loads(shared["schemas/ai-usage-record.schema.json"])["required"]
    for name in (
        "phase-skill-map.md",
        "sdd-phase-common.md",
        "skill-resolver.md",
        "agent-capabilities.md",
    ):
        assert name in shared
