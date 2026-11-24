"""Consistencia del contenido del ciclo SDD (F4, tarea 8 y criterios 1 y 2).

Port de `test_phase_skill_map_consistency` del reporte (§10.4), con lo que F4
define: toda skill que nombra el mapa fase → skills existe o pertenece a un
pack que todavía no existe y declara cómo degrada; las skills de fase dicen
dónde corren como manda el contrato común (sección G); los subagentes tienen
las tools de su rol.
"""

from __future__ import annotations

import json
import re

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
    "skill-reviewer",
    "context-config-audit",
)
# Fase -> skill de fase.
PHASE_SKILL = {
    "risk": "risk-tiering",
    "new": "sdd-new",
    "init": "sdd-init",
    "status": "sdd-status",
    "explore": "sdd-explore",
    "propose": "sdd-propose",
    "spec": "sdd-spec",
    "design": "sdd-design",
    "tasks": "sdd-tasks",
    "apply": "sdd-apply",
    "verify": "sdd-verify",
    "archive": "sdd-archive",
}
_TABLE_ROW = re.compile(r"^\s*\|([^|]+)\|([^|]+)\|")
_AGENT = re.compile(r"`(sdd-[a-z-]+)`")


def _who_runs() -> dict[str, tuple[str, str | None]]:
    """La tabla "Who runs each phase" de la sección G: fase -> (dónde corre, subagente)."""
    text = (ROOT / "packs" / "core" / "shared" / "sdd-phase-common.md").read_text(encoding="utf-8")
    table = text.split("**Who runs each phase:**", 1)[1].split("\n\n", 2)[1]
    found: dict[str, tuple[str, str | None]] = {}
    for line in table.splitlines():
        row = _TABLE_ROW.match(line)
        if not row or set(row.group(1).strip()) <= {"-"} or row.group(1).strip() == "Phase":
            continue
        where = row.group(2).strip()
        agent = _AGENT.search(where)
        inline = where.startswith(("inline", "the orchestrator"))
        for phase in (p.strip() for p in row.group(1).split(",")):
            if phase in PHASE_SKILL:
                found[phase] = (
                    ("inline", None) if inline or not agent else ("subagent", agent.group(1))
                )
    return found


PHASES = {PHASE_SKILL[phase]: where for phase, where in _who_runs().items()}
ORCHESTRATION = ("sdd-orchestrator", "sdd-continue", "sdd-ff")
TOOLS = {
    "sdd-explorer": {"Read", "Grep", "Glob"},
    # Bash y PowerShell: en Copilot CLI sobre Windows, Bash solo no da shell (F8, TM-40).
    "sdd-implementer": {"Read", "Grep", "Glob", "Edit", "Write", "Bash", "PowerShell"},
    "sdd-verifier": {"Read", "Grep", "Glob", "Bash", "PowerShell"},
    "sdd-judge": {"Read", "Grep", "Glob"},
    # Pack discovery (F6): solo lectura; devuelven texto y el orquestador escribe.
    "re-extractor": {"Read", "Grep", "Glob"},
    "re-auditor": {"Read", "Grep", "Glob"},
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


def test_criterio_2_las_degradaciones_son_de_packs_opcionales() -> None:
    """Cada fila tiene criterio y un pack declarado por `sdd` (F4).

    Desde F5 una fila puede ser de una skill que existe, si vive en un pack opcional:
    un proyecto sin ese pack degrada con el criterio inline. La fila tiene que nombrar
    el pack real de la skill, y una skill de `core` o `sdd` (que siempre se instalan
    con el ciclo) no puede tener fila.
    """
    assert MAP is not None
    sdd = COLLECTION.packs["sdd"]
    always = set(packs.resolve(COLLECTION.packs, ["sdd"]))
    for item in MAP.degradations.values():
        assert item.criteria, f"{item.skill} no tiene criterio inline"
        assert item.pack in ("core", "sdd", *sdd.optional), (
            f"{item.skill}: pack {item.pack} sin declarar"
        )
        skill = SKILLS.get(item.skill)
        if skill is None:
            continue
        assert skill.pack == item.pack, (
            f"{item.skill} vive en el pack {skill.pack}, no en {item.pack}"
        )
        assert skill.pack not in always, (
            f"{item.skill} es de {skill.pack}, que siempre se instala con sdd: sacala de la tabla"
        )


def test_las_skills_de_packs_opcionales_del_mapa_degradan() -> None:
    """Toda skill de un pack opcional que nombra el mapa tiene su criterio inline (F5)."""
    assert MAP is not None
    always = set(packs.resolve(COLLECTION.packs, ["sdd"]))
    missing = sorted(
        m
        for m in MAP.mentions
        if m in SKILLS and SKILLS[m].pack not in always and m not in MAP.degradations
    )
    assert missing == [], f"skills de packs opcionales sin criterio inline: {missing}"


def test_la_tabla_de_la_seccion_g_cubre_todas_las_fases() -> None:
    assert set(PHASES) == set(PHASE_SKILL.values())
    assert PHASES["sdd-apply"] == ("subagent", "sdd-implementer")
    assert PHASES["risk-tiering"] == ("inline", None)


@pytest.mark.parametrize(
    "phase", sorted(p for p in (MAP.required if MAP else {}) if p in PHASE_SKILL)
)
def test_cada_skill_de_fase_nombra_las_required_de_su_fila(phase: str) -> None:
    """Si el mapa exige una skill en una fase, la skill de esa fase la tiene que cargar."""
    assert MAP is not None
    skill = PHASE_SKILL[phase]
    body = (SKILLS[skill].path / packs.SKILL_FILE).read_text(encoding="utf-8")
    for required in MAP.required[phase]:
        if required != skill:
            assert f"`{required}`" in body or f"skill:{required}" in body, (
                f"{skill} no nombra {required}"
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
