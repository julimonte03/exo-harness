"""Criterio 2 de F7: degradación correcta de los packs opcionales (ADR-0016).

Para cada pack opcional del ciclo (`sdd.optional`) que existe en el contenido:

- **instalado:** cada skill suya que nombra el mapa fase → skills está en el bundle y en
  el registro de skills, así el agente la resuelve;
- **sin instalar:** no está, y el mapa que sí se instala (con `core`) tiene su fila de
  degradación con el pack real y un criterio inline, que el agente aplica diciendo la
  frase exacta de `phase_map.note`.

El test es genérico: cubre cada pack nuevo de F7 en cuanto aparece.
"""

from __future__ import annotations

import pytest

from exo import content, packs, phase_map, registry
from exo.installer.bundle import build_bundle

ROOT = content.content_root()
COLLECTION = packs.load_collection(ROOT)
BASE = ["core", "sdd"]
EXISTING = set(COLLECTION.packs)
OPTIONAL = sorted(set(COLLECTION.packs["sdd"].optional) & EXISTING)
MAP_NAME = phase_map.MAP_FILE.name


def _skills_of(pack: str) -> set[str]:
    return {skill.name for skill in COLLECTION.skills if skill.pack == pack}


def _registry(wanted: list[str]) -> str:
    order = packs.resolve(COLLECTION.packs, wanted)
    return registry.render([s for s in COLLECTION.skills if s.pack in order], base=ROOT)


def _installed_map(bundle) -> phase_map.PhaseMap:
    return phase_map.parse(bundle.shared[MAP_NAME].decode("utf-8"))


def test_hay_packs_opcionales_que_probar() -> None:
    assert OPTIONAL, "sdd.optional no nombra ningún pack existente"


@pytest.mark.parametrize("pack", OPTIONAL)
def test_criterio_2_con_el_pack_resuelve_y_sin_el_degrada(pack: str) -> None:
    mapped = sorted(_skills_of(pack) & set(_installed_map(build_bundle(ROOT, BASE)).mentions))
    with_pack = build_bundle(ROOT, [*BASE, pack])
    without = build_bundle(ROOT, BASE)
    installed = {s.name for s in with_pack.skills}
    missing = {s.name for s in without.skills}
    assert _skills_of(pack) <= installed
    registry_with, registry_without = _registry([*BASE, pack]), _registry(BASE)
    degradations = _installed_map(without).degradations
    for skill in mapped:
        assert skill not in missing, f"{skill} no debería instalarse sin {pack}"
        assert f"| {skill} | {pack} |" in registry_with
        assert f"| {skill} | {pack} |" not in registry_without
        row = degradations.get(skill)
        assert row is not None, f"{skill} no tiene fila de degradación en el mapa instalado"
        assert row.pack == pack and row.criteria, row
        assert phase_map.note(pack, skill) == (
            f"{pack}/{skill} not installed — applying inline criteria"
        )


def test_el_resolver_instalado_usa_la_misma_frase() -> None:
    """El agente lee la frase del contrato instalado, no del código."""
    bundle = build_bundle(ROOT, BASE)
    resolver = bundle.shared["skill-resolver.md"].decode("utf-8")
    assert "<pack>/<skill> not installed — applying inline criteria" in resolver
