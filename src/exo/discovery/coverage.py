"""Cobertura y precisión de la ingeniería inversa (F6, ADR-0015).

- **Módulos cubiertos:** los que tienen todas sus unidades cerradas y al día.
- **FR con evidencia:** los requisitos de las specs con preámbulo que citan código o
  docs, no solo una inferencia.
- **Precisión por capacidad:** correctos sobre correctos más incorrectos de la
  auditoría. Los no verificables se informan aparte y, si pasan del 25 %, la
  capacidad queda marcada. Solo cuentan los veredictos de la muestra vigente: una
  auditoría con otra semilla, o de IDs que ya no están en `sample.json`, se ignora
  con un aviso.

Escribe `coverage.md` (en inglés, ADR-0011). Una capacidad con precisión por debajo
del umbral vuelve a la extracción (R3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exo.discovery import capabilities, graph, planner, sampler, store, units
from exo.discovery import files as files_mod
from exo.sdd import specs

FILENAME = "coverage.md"
THRESHOLD = 0.9
UNVERIFIABLE_FLAG = 0.25


def _verdicts(project: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """(veredictos de la muestra vigente, IDs sin auditar, avisos)."""
    sample = store.read_json(project, sampler.SAMPLE)
    audit = store.read_json(project, sampler.AUDIT)
    wanted = [i["id"] for i in sample["items"]] if sample else []
    if audit is None:
        return [], wanted, []
    warnings: list[str] = []
    if sample is None or audit.get("seed") != sample.get("seed"):
        seed = sample.get("seed") if sample else None
        warnings.append(
            f"{store.rel(sampler.AUDIT)} is from another sample (seed {audit.get('seed')!r}; "
            f"{store.rel(sampler.SAMPLE)} has seed {seed!r}): its verdicts were ignored, "
            "audit the current sample"
        )
        return [], wanted, warnings
    rows = [r for r in audit.get("results", []) if r["id"] in wanted]
    stale = sorted(r["id"] for r in audit.get("results", []) if r["id"] not in wanted)
    if stale:
        warnings.append(
            f"verdicts of requirements no longer in the sample were ignored: {', '.join(stale)}"
        )
    judged = {r["id"] for r in rows}
    return rows, [i for i in wanted if i not in judged], warnings


def _capability(requirement: str, known: dict[str, str]) -> str:
    """La capacidad de un FR: la de la población, o la de su ID (`CAP-<cap>-FR-n`)."""
    if requirement in known:
        return known[requirement]
    match = specs.REQUIREMENT_ID.fullmatch(requirement)
    return match.group(1) if match else "?"


def build(project: Path) -> dict[str, Any]:
    project = Path(project)
    plan = planner.load(project)
    fileset = files_mod.list_files(project)
    unit_states = {s.id: s.status for s in units.states(project, plan, fileset)}
    modules: dict[str, list[str]] = {}
    for item in plan["units"]:
        modules.setdefault(item["module"], []).append(unit_states[item["id"]])
    structure = store.read_json(project, graph.FILENAME)
    total_modules = len(structure["modules"]) if structure else len(modules)
    covered = sorted(m for m, sts in modules.items() if all(s == "done" for s in sts))
    spec_warnings: list[str] = []
    population = sampler.population(project, spec_warnings)
    blocks = {
        block.id: block
        for spec in capabilities.with_preamble(project)
        for block in spec.capability.requirements.values()
    }
    evidenced = sum(
        1
        for item in population
        if any(specs.FACTS.search(line) for line in blocks[item["id"]].lines)
    )
    rows, missing, warnings = _verdicts(project)
    warnings = spec_warnings + warnings
    by_id = {i["id"]: i["capability"] for i in population}
    per_capability: dict[str, dict[str, int]] = {}
    for row in rows:
        capability = _capability(row["id"], by_id)
        entry = per_capability.setdefault(
            capability, {"correct": 0, "incorrect": 0, "unverifiable": 0}
        )
        entry[row["verdict"]] += 1
    precision: list[dict[str, Any]] = []
    for capability, counts in sorted(per_capability.items()):
        judged = counts["correct"] + counts["incorrect"]
        total = judged + counts["unverifiable"]
        value = counts["correct"] / judged if judged else None
        flags = []
        if value is not None and value < THRESHOLD:
            flags.append("below threshold: extract again")
        if total and counts["unverifiable"] / total > UNVERIFIABLE_FLAG:
            flags.append("too many unverifiable claims")
        precision.append({"capability": capability, **counts, "precision": value, "flags": flags})
    return {
        "units": {
            "total": len(plan["units"]),
            "done": sum(1 for s in unit_states.values() if s == "done"),
            "stale": sum(1 for s in unit_states.values() if s == "stale"),
        },
        "modules": {"total": total_modules, "covered": len(covered)},
        "requirements": {"total": len(population), "with_evidence": evidenced},
        "precision": precision,
        "audit_missing": missing,
        "warnings": warnings,
    }


def _percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f} %" if whole else "n/a"


def render(data: dict[str, Any]) -> str:
    lines = [
        "# Discovery coverage",
        "",
        "Generated by the engine from the plan, the units and the audit; do not edit it.",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Units done | {data['units']['done']} of {data['units']['total']} "
        f"({data['units']['stale']} stale) |",
        f"| Modules covered | {data['modules']['covered']} of {data['modules']['total']} "
        f"({_percent(data['modules']['covered'], data['modules']['total'])}) |",
        f"| Requirements with evidence | {data['requirements']['with_evidence']} of "
        f"{data['requirements']['total']} "
        f"({_percent(data['requirements']['with_evidence'], data['requirements']['total'])}) |",
        "",
        "## Precision by capability",
        "",
    ]
    if not data["precision"]:
        lines.append("No audit results yet.")
    else:
        lines += [
            "| Capability | Correct | Incorrect | Unverifiable | Precision | Flags |",
            "|---|---|---|---|---|---|",
        ]
        for row in data["precision"]:
            value = "n/a" if row["precision"] is None else f"{100 * row['precision']:.1f} %"
            lines.append(
                f"| {row['capability']} | {row['correct']} | {row['incorrect']} | "
                f"{row['unverifiable']} | {value} | {'; '.join(row['flags']) or '-'} |"
            )
    if data["audit_missing"]:
        lines += ["", f"Not audited yet: {', '.join(data['audit_missing'])}."]
    for warning in data["warnings"]:
        lines += ["", f"Warning: {warning}."]
    return "\n".join(lines) + "\n"


def write(project: Path) -> tuple[dict[str, Any], bool]:
    data = build(project)
    return data, store.write_text(project, FILENAME, render(data))
