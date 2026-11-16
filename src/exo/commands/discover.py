"""`exo discover ...`: la ingeniería inversa por CLI (F6, ADR-0015, ADR-0005).

`status` es una tool de solo lectura (también por MCP, si está habilitado) y se
registra en `commands/tools.py`. El resto escribe en `<carpeta del motor>/discovery/`
y por eso no son tools, igual que `exo change new|record`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from exo import _meta
from exo.commands._output import emit_json, error, usage_error
from exo.core import fsutil
from exo.discovery import (
    capabilities,
    coverage,
    inventory,
    pipeline,
    planner,
    sampler,
    store,
    units,
)

_ERRORS = (
    store.DiscoveryError,
    planner.PlanError,
    units.UnitError,
    sampler.AuditError,
    capabilities.CapabilityError,
    OSError,
)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--json", action="store_true", help="JSON output")


def register_actions(actions: argparse._SubParsersAction) -> None:
    inv = actions.add_parser(
        "inventory", help="R0: languages, manifests, frameworks, entrypoints, tests, CI"
    )
    _common(inv)
    inv.set_defaults(handler=_inventory)
    struct = actions.add_parser("structure", help="R1: modules, import graph, churn, ownership")
    _common(struct)
    struct.set_defaults(handler=_structure)
    plan = actions.add_parser("plan", help="R2: bounded work units, priority and estimate")
    plan.add_argument("--depth", choices=planner.DEPTHS, help="default: discovery.depth")
    plan.add_argument(
        "--replan", action="store_true", help="rebuild a plan that already has closed units"
    )
    _common(plan)
    plan.set_defaults(handler=_plan)
    nxt = actions.add_parser("next", help="R3: the next units to extract, by priority")
    nxt.add_argument("--count", type=int, default=1, help="how many units (to run in parallel)")
    _common(nxt)
    nxt.set_defaults(handler=_next)
    done = actions.add_parser("done", help="R3: validate a unit's extraction and close it")
    done.add_argument("unit", help="unit id, as `next` gives it")
    _common(done)
    done.set_defaults(handler=_done)
    skip = actions.add_parser(
        "skip", help="R3: take out of the loop a unit that cannot be closed, with the reason"
    )
    skip.add_argument("unit", help="unit id, as `next` gives it")
    skip.add_argument("--reason", required=True, help="why it cannot be closed (committed)")
    _common(skip)
    skip.set_defaults(handler=_skip)
    reopen = actions.add_parser(
        "reopen",
        help="R5: send closed or skipped units back to extraction (a capability below threshold)",
    )
    reopen.add_argument("units", nargs="*", help="unit ids")
    reopen.add_argument("--capability", help="the units whose files the capability's FRs cite")
    _common(reopen)
    reopen.set_defaults(handler=_reopen)
    syn = actions.add_parser(
        "synthesized",
        help="R4: validate the capability specs just written and record the code they cite",
    )
    syn.add_argument("capabilities", nargs="+", help="capability names")
    _common(syn)
    syn.set_defaults(handler=_synthesized)
    sample = actions.add_parser("sample", help="R5: pick the requirements to audit")
    sample.add_argument("--n", type=int, default=sampler.DEFAULT_N, help="sample size")
    sample.add_argument("--seed", type=int, help="default: derived from the specs")
    _common(sample)
    sample.set_defaults(handler=_sample)
    audit = actions.add_parser("audit", help="R5: record the auditor's verdicts")
    audit.add_argument("results", help='JSON {"results": [{"id", "verdict", "note"}]}, or @<file>')
    _common(audit)
    audit.set_defaults(handler=_audit)
    cov = actions.add_parser("coverage", help="R5: module coverage, evidence and precision")
    _common(cov)
    cov.set_defaults(handler=_coverage)
    update = actions.add_parser(
        "update", help="recompute R0 and R1 and report stale units and capabilities"
    )
    _common(update)
    update.set_defaults(handler=_update)


def status_lines(result: dict[str, Any]) -> list[str]:
    """La salida humana de `discover status` (la tool `discovery_status`)."""
    lines: list[str] = []
    steps = ", ".join(name for name, ran in result["steps"].items() if ran) or "none"
    lines.append(f"steps that ran: {steps}")
    if result.get("units") is not None:
        counts = result["units"]
        lines.append(
            f"units: {counts['done']} done, {counts['pending']} pending, "
            f"{counts['stale']} stale, {counts['skipped']} skipped (depth {result['depth']})"
        )
        if result["next"]:
            lines.append(f"next: {', '.join(result['next'])}")
        for item in result["skipped"]:
            changed = (
                f" (its files changed: {', '.join(item['changed'])})" if item["changed"] else ""
            )
            lines.append(f"skipped {item['id']}: {item['reason']}{changed}")
        lines += [f"orphan unit record (not in the plan): {o}" for o in result["orphans"]]
    outside = result.get("outside_changes")
    if outside:
        lines.append("changes outside the paths discovery may write:")
        lines += [f"  {path}" for path in outside]
    if result.get("outside_changes_error"):
        lines.append(
            "could not check for changes outside the paths discovery may write: "
            f"{result['outside_changes_error']}"
        )
    lines += [f"warning: {warning}" for warning in result.get("warnings", [])]
    return lines


def _fail(exc: Exception) -> int:
    lines = str(exc).split("\n")
    if len(lines) == 1:
        return error(lines[0])
    for line in lines:
        print(f"  {line}", file=sys.stderr)
    return error(f"{len(lines)} problems; fix them and run it again")


def _inventory(args: argparse.Namespace) -> int:
    try:
        data, wrote = inventory.write(args.project)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(data)
        return 0
    print(f"{store.rel(inventory.FILENAME)}: " + ("updated" if wrote else "unchanged"))
    langs = ", ".join(f"{k} ({v['lines']} lines)" for k, v in data["languages"].items())
    print(f"languages: {langs or 'none'}")
    print(f"frameworks: {', '.join(data['frameworks']) or 'none'}")
    print(f"entrypoints: {len(data['entrypoints'])}, test files: {len(data['tests']['files'])}")
    for warning in data["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _structure(args: argparse.Namespace) -> int:
    try:
        data = pipeline.structure(args.project)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(data)
        return 0
    print(f"{data['modules']} modules, {data['edges']} edges")
    for warning in data["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _plan(args: argparse.Namespace) -> int:
    try:
        data, wrote = planner.write(args.project, args.depth, replan=args.replan)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(data)
        return 0
    totals = data["totals"]
    print(f"{store.rel(planner.FILENAME)}: " + ("updated" if wrote else "unchanged"))
    print(
        f"depth {data['depth']}: {totals['units']} units ({totals['detailed']} in detail), "
        f"{totals['lines']} lines, about {totals['estimate_tokens']} tokens"
    )
    for item in data["units"][:5]:
        print(f"  {item['id']}\t{item['lines']} lines\tpriority {item['priority']}")
    return 0


def _next(args: argparse.Namespace) -> int:
    if args.count < 1:
        return usage_error("--count must be 1 or more")
    try:
        found = units.next_units(args.project, args.count)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json({"units": found})
        return 0
    if not found:
        print("every unit is closed and up to date")
    for item in found:
        print(f"{item['id']}\t{item['status']}\t{len(item['files'])} files\t{item['document']}")
    return 0


def _done(args: argparse.Namespace) -> int:
    try:
        record = units.done(args.project, args.unit)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(record)
    else:
        counts = record["counts"]
        print(f"{args.unit} closed: {counts['claims']} claims ({counts['inferred']} inferred)")
    return 0


def _skip(args: argparse.Namespace) -> int:
    try:
        record = units.skip(args.project, args.unit, args.reason)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(record)
    else:
        print(
            f"{args.unit} skipped: {record['skipped']} "
            f"(`{_meta.NAME} discover reopen {args.unit}` brings it back)"
        )
    return 0


def _reopen(args: argparse.Namespace) -> int:
    if not args.units and args.capability is None:
        return usage_error("pass unit ids or --capability <name>")
    try:
        reopened = units.reopen(args.project, args.units, capability=args.capability)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json({"reopened": reopened})
    else:
        print(f"reopened: {', '.join(reopened) or 'none (they were not closed)'}")
    return 0


def _synthesized(args: argparse.Namespace) -> int:
    try:
        records = capabilities.synthesized(args.project, args.capabilities)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json({"capabilities": records})
        return 0
    for record in records:
        print(
            f"{record['capability']}: recorded (round {record['rounds']}, "
            f"{len(record['files'])} cited files)"
        )
    return 0


def _sample(args: argparse.Namespace) -> int:
    if args.n < 1:
        return usage_error("--n must be 1 or more")
    try:
        data = sampler.sample(args.project, args.n, args.seed)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(data)
        return 0
    print(f"seed {data['seed']}: {len(data['items'])} of {data['population']} requirements")
    for item in data["items"]:
        print(f"  {item['id']}\t{item['spec']}:{item['line']}")
    _warn(data["warnings"])
    return 0


def _warn(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)


def _load(raw: str) -> Any:
    text = fsutil.read_text_auto(Path(raw[1:])) if raw.startswith("@") else raw
    return json.loads(text)


def _audit(args: argparse.Namespace) -> int:
    try:
        results = _load(args.results)
    except (OSError, ValueError) as exc:  # ValueError: no es UTF-8, o no es JSON
        return usage_error(f"cannot read the results: {exc}")
    try:
        data = sampler.record(args.project, results)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(data)
        return 0
    print(f"{len(data['results'])} verdicts recorded")
    if data["missing"]:
        print(f"not audited yet: {', '.join(data['missing'])}")
    return 0


def _coverage(args: argparse.Namespace) -> int:
    try:
        data, _ = coverage.write(args.project)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(data)
        return 0
    print(coverage.render(data), end="")
    return 0


def _update(args: argparse.Namespace) -> int:
    try:
        data = pipeline.update(args.project)
    except _ERRORS as exc:
        return _fail(exc)
    if args.json:
        emit_json(data)
        return 0
    if not any(value for key, value in data.items() if key != "warnings"):
        print("nothing changed since the units were closed")
    for unit_id, changed in data["stale_units"].items():
        print(f"stale unit {unit_id}: {', '.join(changed)}")
    for unit_id, changed in data["changed_skipped_units"].items():
        print(
            f"skipped unit {unit_id} changed: {', '.join(changed)} (it stays skipped; "
            f"`{_meta.NAME} discover reopen {unit_id}` sends it back to extraction)"
        )
    for name in data["stale_capabilities"]:
        print(
            f"stale capability {name}: code it cites changed; extract its units again, "
            f"synthesize it and run `{_meta.NAME} discover synthesized {name}`"
        )
    for name in data["unrecorded_capabilities"]:
        print(
            f"capability {name} has no synthesis record: run "
            f"`{_meta.NAME} discover synthesized {name}` once its spec is written"
        )
    for path in data["new_files"]:
        print(f"new file without a unit: {path} (run `{_meta.NAME} discover plan --replan`)")
    for path in data["deleted_files"]:
        print(f"deleted file: {path}")
    _warn(data["warnings"])
    return 0
