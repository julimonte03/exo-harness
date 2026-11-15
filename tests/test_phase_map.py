"""phase_map: lectura del mapa fase → skills (`packs/sdd/shared/phase-skill-map.md`, §6.4)."""

from __future__ import annotations

from pathlib import Path

from exo import phase_map

MAP = """# Phase → skill map

Intro with `not-a-skill-mention` outside the map.

## Map

| Phase | Required | Conditional | Judges |
|---|---|---|---|
| design | `alpha` | hard to reverse → `beta-skill` | `judge-x` |
| apply | `alpha`, `gamma` | — | — |

<!-- `commented-out` -->

```
| code | `in-code` | — | — |
```

## Inline criteria for skills not installed

| Skill | Pack | Inline criteria when missing |
|---|---|---|
| `beta-skill` | design | Write a short record. |
| `judge-x` | quality |  |
"""


def test_menciones_del_mapa() -> None:
    parsed = phase_map.parse(MAP)
    assert set(parsed.mentions) == {"alpha", "beta-skill", "judge-x", "gamma"}
    assert parsed.mentions["alpha"] == 9


def test_degradaciones() -> None:
    parsed = phase_map.parse(MAP)
    assert set(parsed.degradations) == {"beta-skill", "judge-x"}
    beta = parsed.degradations["beta-skill"]
    assert (beta.pack, beta.criteria, beta.line) == ("design", "Write a short record.", 22)
    assert parsed.degradations["judge-x"].criteria == ""


def test_nota_de_degradacion() -> None:
    assert phase_map.note("security", "threat-modeling") == (
        "security/threat-modeling not installed — applying inline criteria"
    )


def test_load(tmp_path: Path) -> None:
    assert phase_map.load(tmp_path) is None
    path = tmp_path / phase_map.MAP_FILE
    path.parent.mkdir(parents=True)
    path.write_text(MAP, encoding="utf-8")
    loaded = phase_map.load(tmp_path)
    assert loaded is not None and "alpha" in loaded.mentions


def test_filas_del_mapa_con_sus_required() -> None:
    parsed = phase_map.parse(MAP)
    assert parsed.required == {"design": ("alpha",), "apply": ("alpha", "gamma")}
