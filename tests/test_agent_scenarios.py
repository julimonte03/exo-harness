"""Escenarios de la v1.0 con agentes reales (F8, criterios 1 a 3): Claude Code y Copilot CLI.

Marker `agent_e2e`: no corre en la suite normal. Cada caso:
1. copia el fixture a un repo nuevo e instala exo con el agente y los packs del escenario;
2. corre el agente con el pedido, que trae las respuestas por adelantado (modo automático,
   sin push ni PR);
3. verifica con el motor, no con la respuesta del agente: el change archivado, su tier,
   los artefactos y gates del tier, `exo speclint` y `exo check`; o, en la adopción,
   `exo discover status`.

Variables (todas opcionales):
- `EXO_SCENARIOS_AGENTS`: `claude-code,copilot` (por defecto, los dos; se saltea el que no esté);
- `EXO_SCENARIOS`: ids de escenarios separados por coma (por defecto, todos);
- `EXO_SCENARIOS_TIMEOUT`: segundos por corrida (por defecto 7200);
- `EXO_SCENARIOS_MAX_TURNS`: turnos de Claude Code (por defecto 400);
- `EXO_SCENARIOS_COPILOT_MODEL`: modelo de Copilot (por defecto, auto con el perfil
  `intelligence`);
- `EXO_SCENARIOS_REPORT`: JSONL con un registro por corrida (por defecto, en el basetemp).

Corrida: `pytest -m agent_e2e tests/test_agent_scenarios.py --basetemp <carpeta>` deja en
cada carpeta el proyecto, `stream.jsonl` y los datos aislados para revisarlos.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import _agents as agents
import _skill_evals as evals
from _git import init_repo
from exo.core import config
from exo.sdd import speclint

pytestmark = pytest.mark.agent_e2e

TIMEOUT = int(os.environ.get("EXO_SCENARIOS_TIMEOUT", "7200"))
MAX_TURNS = int(os.environ.get("EXO_SCENARIOS_MAX_TURNS", "400"))
COPILOT_MODEL = os.environ.get("EXO_SCENARIOS_COPILOT_MODEL") or None
TICKETS = ("--ticket-pattern", r"[A-Z][A-Z0-9]*-\d+", "--ticket-example", "PROJ-123")
AUTOMATIC = (
    "This is a non-interactive run: I approve every phase in advance, so work in automatic "
    'mode and do not wait for "Adjust anything or continue?". Still follow every rule of the '
    "SDD contracts (tier rules, delegation, fresh-context verify, records, the phase log). Go "
    "through all the phases the tier requires, up to and including sdd-archive. Commit the "
    "work in the project's git repository, but do not push and do not open a PR."
)
TIER_ARTIFACTS = {
    1: ("proposal.md", "fitness-assessment.json", "verify-record.md", "ai-usage-record.json"),
    3: (
        "proposal.md",
        "fitness-assessment.json",
        "spec.md",
        "design.md",
        "tasks.md",
        "test-spec.md",
        "verify-record.md",
        "ai-usage-record.json",
    ),
}


@dataclass(frozen=True)
class Scenario:
    id: str
    fixture: str
    packs: tuple[str, ...]
    prompt: str
    python: bool  # el agente puede correr python (los tests del proyecto)
    tier: int | None = None  # el tier mínimo esperado; None en la adopción
    exact_tier: bool = False
    init: tuple[str, ...] = ()


SCENARIOS = (
    Scenario(
        id="tier1",
        fixture="toy-python",
        packs=("core", "sdd", "quality", "security"),
        prompt=(
            "/sdd-new Add a `--version` option to the CLI that prints `toy-todo 0.1.0` and "
            f"exits with code 0.\n\n{AUTOMATIC} At the end, report the tier and why, every "
            "phase you ran and where it ran, the artifacts, and the output of `exo check`."
        ),
        python=True,
        tier=1,
        exact_tier=True,
    ),
    Scenario(
        id="tier3",
        fixture="toy-python",
        packs=("core", "sdd", "quality", "security"),
        prompt=(
            "/sdd-new Store the tasks in a SQLite database instead of the JSON file, and "
            "migrate an existing tasks.json automatically the first time, without losing tasks "
            "or their done state.\n\nThe ticket for this change is PROJ-42 (I confirm it); it "
            f"has no epic. {AUTOMATIC} At the end, report the tier and the evidence for each "
            "dimension, every phase you ran and where it ran, the artifacts, and the output of "
            "`exo check`."
        ),
        python=True,
        tier=3,
        init=TICKETS,
    ),
    Scenario(
        id="adopt-quick",
        fixture="py-invoices",
        packs=("core", "sdd", "quality", "security", "design", "discovery"),
        prompt=(
            "/exo-adopt Adopt this existing project: it is an invoicing API that already has "
            "code and tests, and nobody has written its specs.\n\nThis is a non-interactive "
            "run, so here are my answers in advance: use depth quick; I approve the wiki "
            "sections and the recovered ADRs you propose (write them); for R6, do the adoption "
            "gap analysis and write the backlog, but do not validate any capability and do not "
            "create any change. Do not run the project's build or tests. Follow every rule of "
            "the project and of the discovery contract, including the extraction in the "
            "re-extractor subagent and the audit in the re-auditor subagent. Do not commit "
            "anything. At the end, report the units, every stage you ran and where, the "
            "capabilities with their audit precision, and the output of `exo discover status`."
        ),
        python=False,
    ),
)


def _selected(env_var: str, every: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.environ.get(env_var, "")
    wanted = tuple(x.strip() for x in raw.split(",") if x.strip())
    return tuple(x for x in every if x in wanted) if wanted else every


CASES = [
    pytest.param(agent, scenario, id=f"{agent}-{scenario.id}")
    for agent in _selected("EXO_SCENARIOS_AGENTS", agents.AGENTS)
    for scenario in SCENARIOS
    if scenario.id in _selected("EXO_SCENARIOS", tuple(s.id for s in SCENARIOS))
]


def _exo(project: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "exo", *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _json(done: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        data = json.loads(done.stdout)
    except ValueError:
        return {"_unparsed": done.stdout[-2000:], "_stderr": done.stderr[-2000:]}
    return data if isinstance(data, dict) else {"_unparsed": data}


def _project(scenario: Scenario, agent: str, root: Path, env: dict[str, str]) -> Path:
    project = init_repo(root / "project", fixture=scenario.fixture)
    init = [
        "init",
        "--agents",
        agent,
        "--packs",
        ",".join(scenario.packs),
        "--yes",
        *scenario.init,
    ]
    done = _exo(project, env, *init)
    assert done.returncode == 0, done.stdout + done.stderr
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore: adopt exo"],
        cwd=project,
        env=env,
        check=True,
        capture_output=True,
    )
    return project


def _run_agent(
    agent: str, scenario: Scenario, project: Path, root: Path, env: dict[str, str]
) -> tuple[agents.AgentRun, list[str]]:
    failed: list[str] = []
    usage_file = root / "copilot-usage.json"
    if agent == "claude-code":
        claude = shutil.which("claude")
        if claude is None:
            pytest.skip("requires Claude Code (claude)")
        command = agents.claude_command(
            claude, scenario.prompt, python=scenario.python, max_turns=MAX_TURNS
        )
        parse = agents.parse_claude
    else:
        launcher = agents.copilot_launcher(shutil.which("copilot"), os.environ)
        if launcher is None:
            pytest.skip("requires GitHub Copilot CLI (copilot)")
        home = agents.copilot_home(root / "copilot-home", os.environ, agents.home_dir(os.environ))
        env = agents.copilot_env(env, home, COPILOT_MODEL)
        command = agents.copilot_command(
            launcher,
            scenario.prompt,
            python=scenario.python,
            usage=usage_file,
            logs=root / "copilot-logs",
            model=COPILOT_MODEL,
        )
        parse = agents.parse_copilot
    try:
        done = subprocess.run(
            command,
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            check=False,
        )
        stdout = done.stdout
        (root / "stderr.txt").write_text(done.stderr or "", encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout or ""
        stdout = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        failed.append(f"timed out after {TIMEOUT} s (EXO_SCENARIOS_TIMEOUT)")
    (root / "stream.jsonl").write_text(stdout, encoding="utf-8")
    run = parse(stdout.splitlines())
    if agent == "copilot":
        run.usage = {**run.usage, **agents.read_usage(usage_file)}
    if run.error:
        failed.append(f"the agent ended with an error: {run.error}")
    return run, failed


def _archived(project: Path, env: dict[str, str]) -> list[dict[str, Any]]:
    listed = _json(_exo(project, env, "change", "list", "--json"))
    return [c for c in listed.get("changes", []) if c.get("archived")]


def check_cycle(
    scenario: Scenario, project: Path, env: dict[str, str]
) -> tuple[list[str], dict[str, Any]]:
    """Un ciclo SDD válido del tier esperado, verificado con el motor."""
    failed: list[str] = []
    archived = _archived(project, env)
    facts: dict[str, Any] = {"archived": [c["name"] for c in archived]}
    if len(archived) != 1:
        return [f"expected one archived change, found {facts['archived']}"], facts
    change = project / archived[0]["path"]
    try:
        tier = json.loads((change / "fitness-assessment.json").read_text(encoding="utf-8"))["tier"]
    except (OSError, ValueError, KeyError, TypeError):
        tier = None
    facts["tier"] = tier
    expected = scenario.tier or 0
    wrong = tier != expected if scenario.exact_tier else not isinstance(tier, int) or tier < expected
    if wrong:
        failed.append(f"tier {tier}, expected {'' if scenario.exact_tier else '>= '}{expected}")
    needed = TIER_ARTIFACTS[1 if (tier or expected) < 3 else 3]
    missing = [name for name in needed if not (change / name).is_file()]
    if missing:
        failed.append(f"missing artifacts: {missing}")
    if isinstance(tier, int) and tier >= 2:
        gates = config.load(project).config["governance"]["gates"].get(str(tier), [])
        # Como `exo check`: el contract_check vive en verify-record.md (sdd/check.py).
        absent = [
            g
            for g in gates
            if g != speclint.CONTRACT_GATE and not (change / "gates" / f"{g}.md").is_file()
        ]
        facts["gates"] = gates
        if absent:
            failed.append(f"missing gates for Tier {tier}: {absent}")
    lint = _exo(project, env, "speclint", str(change), "--json")
    facts["speclint_exit"] = lint.returncode
    if lint.returncode != 0:
        failed.append(f"exo speclint failed: {lint.stdout[-1500:]}")
    check = _json(_exo(project, env, "check", "--base", "main", "--json"))
    facts["check_ok"] = check.get("ok")
    if check.get("ok") is not True:
        failed.append(f"exo check --base main failed: {json.dumps(check)[:1500]}")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=project, capture_output=True, text=True, check=False
    )
    facts["uncommitted"] = status.stdout.splitlines()
    return failed, facts


def check_adoption(project: Path, env: dict[str, str]) -> tuple[list[str], dict[str, Any]]:
    """La adopción `quick` cerró sus unidades, auditó y no escribió fuera de lo permitido."""
    failed: list[str] = []
    status = _json(_exo(project, env, "discover", "status", "--json"))
    facts = {k: status.get(k) for k in ("depth", "units", "coverage", "outside_changes", "rounds")}
    facts["capabilities"] = status.get("capabilities")
    if status.get("depth") != "quick":
        failed.append(f"depth {status.get('depth')!r}, expected 'quick'")
    units = status.get("units") or {}
    if units.get("pending") or units.get("stale"):
        failed.append(f"units left: {units}")
    if status.get("outside_changes"):
        failed.append(f"writes outside the allowed paths: {status['outside_changes']}")
    if not status.get("coverage"):
        failed.append("coverage.md was not written (`exo discover coverage`)")
    if status.get("audit_missing"):
        failed.append(f"capabilities without an audit: {status['audit_missing']}")
    if not (status.get("capabilities") or {}).get("as-is"):
        failed.append("no as-is capability was recovered")
    return failed, facts


def _report(tmp_path_factory: pytest.TempPathFactory, entry: dict[str, Any]) -> None:
    target = os.environ.get("EXO_SCENARIOS_REPORT")
    path = Path(target) if target else tmp_path_factory.getbasetemp() / "agent-scenarios.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


@pytest.mark.parametrize(("agent", "scenario"), CASES)
def test_agent_scenario(
    agent: str, scenario: Scenario, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    env = evals.runner_env(data, os.environ)
    project = _project(scenario, agent, tmp_path, env)
    run, failed = _run_agent(agent, scenario, project, tmp_path, env)
    if scenario.tier is None:
        found, facts = check_adoption(project, env)
    else:
        found, facts = check_cycle(scenario, project, env)
    failed += found
    _report(
        tmp_path_factory,
        {
            "agent": agent,
            "scenario": scenario.id,
            "passed": not failed,
            "failed": failed,
            "facts": facts,
            "skills": run.used,
            "subagents": run.subagents,
            "commands": len(run.commands),
            "usage": run.usage,
            "error": run.error,
            "answer": run.answer[-3000:],
            "dir": str(tmp_path),
        },
    )
    assert not failed, "\n".join(failed)
