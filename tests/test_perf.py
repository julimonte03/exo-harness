"""Metas de rendimiento de F8 (marker `perf`; corre en la suite normal y en la CI).

Las metas (`docs/plan/fases/F8-endurecimiento-y-distribucion.md`, Rendimiento):
- `exo init` en menos de 10 s;
- `exo sync` sin cambios en menos de 1 s;
- `exo discover inventory` sobre 50 mil líneas en menos de 30 s, y `structure`, el paso
  siguiente de la adopción, con el mismo presupuesto;
- la búsqueda de memoria según ADR-0010: p95 por debajo de 150 ms con 5 000 memorias. Se
  mide la léxica, la que anda sin extras y la que usa la CI normal.

Cómo se mide:
- Los comandos corren en un proceso nuevo (`python -m exo`), como los usa una persona o
  un agente: cuenta la importación del CLI. A cada corrida se le resta el arranque del
  intérprete solo (`python -c pass`), medido justo antes: es de la máquina y no del
  motor. En un Windows con antivirus pasa de medio segundo; en un runner de Linux son
  milisegundos.
- Cuenta la mejor de varias corridas: la mínima es la que menos ruido tiene, y la primera
  lectura de archivos recién escritos la frena el antivirus. Si ninguna baja del límite,
  se reintenta hasta `MAX_RUNS`: una máquina ocupada con otra cosa no es el motor.
- El test falla recién con el doble de la meta, para no dar falsos rojos en una CI
  lenta. Entre la meta y el doble avisa con un `PerfWarning`, que sale en el resumen.
  Los números salen siempre en la salida del test: `pytest -m perf --no-cov -rP`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

import _synthetic_repo
import exo
from exo import _meta, paths
from exo.memory import evaluation
from exo.memory.store import MemoryStore, now

pytestmark = [
    pytest.mark.perf,
    pytest.mark.skipif(shutil.which("git") is None, reason="requiere git"),
]

SRC = Path(exo.__file__).resolve().parents[1]
DATASET = Path(__file__).resolve().parent / "memory_eval"
AGENTS = "claude-code,copilot"
RUNS = 2
MAX_RUNS = 5
MARGIN = 2.0  # se falla con el doble de la meta
TARGETS = {"init": 10.0, "sync": 1.0, "inventory": 30.0, "structure": 30.0, "search_p95_ms": 150.0}


class PerfWarning(UserWarning):
    """Una medición pasó la meta, pero no el doble: se avisa y no se falla."""


def check(what: str, cost: float, target: float, unit: str = "s", detail: str = "") -> None:
    """Falla con `MARGIN` veces la meta y avisa entre la meta y ese margen."""
    message = f"{what}: {cost:.2f} {unit} (meta < {target:g} {unit}{detail})"
    print(message)
    assert cost < MARGIN * target, message
    if cost >= target:
        warnings.warn(PerfWarning(message), stacklevel=2)


def _env() -> dict[str, str]:
    """El entorno del test (datos aislados) con el `exo` que se está probando primero."""
    current = os.environ.get("PYTHONPATH")
    return {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(SRC), current]))}


def timed(*args: str) -> tuple[float, str]:
    """(segundos, stdout) de `python <args>` en un proceso nuevo. Falla si el comando falla."""
    start = time.perf_counter()
    done = subprocess.run(
        [sys.executable, *args],
        env=_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - start
    assert done.returncode == 0, (
        f"{args} salió con {done.returncode}:\n{done.stdout}\n{done.stderr}"
    )
    return elapsed, done.stdout


@dataclass(frozen=True)
class Measurement:
    cost: float  # segundos del motor: lo medido menos el arranque del intérprete
    wall: float
    interpreter: float
    out: str  # stdout de la última corrida

    @property
    def detail(self) -> str:
        return f"; medido {self.wall:.2f} s, menos {self.interpreter:.2f} s del intérprete"


def measure(argv: Callable[[int], list[str]], target: float) -> Measurement:
    """La mejor de `RUNS` corridas de `exo <argv(n)>`, cada una pareada con el arranque del
    intérprete. Mientras ninguna baje de `MARGIN` veces la meta, reintenta hasta
    `MAX_RUNS`. `argv` recibe el número de corrida (`init` necesita una copia nueva)."""
    best: Measurement | None = None
    for run in range(MAX_RUNS):
        args = ["-m", _meta.NAME, *argv(run)]
        interpreter, _ = timed("-c", "pass")
        wall, out = timed(*args)
        if best is None or wall - interpreter < best.cost:
            best = Measurement(wall - interpreter, wall, interpreter, out)
        if run + 1 >= RUNS and best.cost < MARGIN * target:
            break
    assert best is not None
    return Measurement(best.cost, best.wall, best.interpreter, out)


def _copy(repo: Path, target: Path) -> Path:
    """Una copia del repo sin lo que escribió el motor (discovery escribe en su carpeta)."""
    shutil.copytree(repo, target, ignore=shutil.ignore_patterns(_meta.PROJECT_DIR))
    return target


@pytest.fixture(scope="module")
def repo50k(tmp_path_factory: pytest.TempPathFactory) -> Iterator[_synthetic_repo.SyntheticRepo]:
    # El fixture de módulo corre antes que el aislamiento por test de conftest: la config
    # global de git del dev no puede cambiar el repo.
    with pytest.MonkeyPatch.context() as patch:
        gitconfig = tmp_path_factory.mktemp("git-global-perf") / "gitconfig"
        gitconfig.write_text("", encoding="utf-8")
        patch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
        patch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        repo = _synthetic_repo.build(tmp_path_factory.mktemp("perf") / "shop")
    assert repo.lines >= 50_000, f"el repo sintético tiene {repo.lines} líneas"
    yield repo


def test_init_menos_de_10s(repo50k: _synthetic_repo.SyntheticRepo, tmp_path: Path) -> None:
    def argv(run: int) -> list[str]:  # cada corrida sobre una copia nueva: si no, es un sync
        target = _copy(repo50k.root, tmp_path / f"p{run}")
        return ["init", "--project", str(target), "--agents", AGENTS, "--yes"]

    found = measure(argv, TARGETS["init"])
    assert "done:" in found.out
    check(
        "exo init (repo de 50 mil líneas, dos agentes)",
        found.cost,
        TARGETS["init"],
        detail=found.detail,
    )


def test_sync_sin_cambios_menos_de_1s(
    repo50k: _synthetic_repo.SyntheticRepo, tmp_path: Path
) -> None:
    target = _copy(repo50k.root, tmp_path / "p")
    timed("-m", _meta.NAME, "init", "--project", str(target), "--agents", AGENTS, "--yes")
    found = measure(lambda _run: ["sync", "--project", str(target)], TARGETS["sync"])
    assert "no changes" in found.out
    check("exo sync sin cambios", found.cost, TARGETS["sync"], detail=found.detail)


def test_discover_inventory_50k_lineas_menos_de_30s(
    repo50k: _synthetic_repo.SyntheticRepo,
) -> None:
    project = str(repo50k.root)
    found = measure(
        lambda _run: ["discover", "inventory", "--project", project, "--json"],
        TARGETS["inventory"],
    )
    data = json.loads(found.out)
    lines = sum(data["languages"][name]["lines"] for name in ("python", "typescript", "java"))
    assert lines >= 50_000 and data["entrypoints"]
    check(
        "exo discover inventory (50 mil líneas)",
        found.cost,
        TARGETS["inventory"],
        detail=found.detail,
    )


def test_discover_structure_50k_lineas_menos_de_30s(
    repo50k: _synthetic_repo.SyntheticRepo,
) -> None:
    project = str(repo50k.root)
    found = measure(
        lambda _run: ["discover", "structure", "--project", project, "--json"],
        TARGETS["structure"],
    )
    data = json.loads(found.out)
    assert data["modules"] >= 3 * len(_synthetic_repo.AREAS) and data["edges"] > 0
    check(
        "exo discover structure (50 mil líneas)",
        found.cost,
        TARGETS["structure"],
        detail=found.detail,
    )


def test_busqueda_lexica_p95_menos_de_150ms_con_5000_memorias(tmp_path: Path) -> None:
    """Como `exo mem eval` (ADR-0010): la base abierta, las 50 consultas tres veces."""
    memories, queries = evaluation.load(DATASET)
    stamp = now()
    rows = [
        (evaluation.PROJECT, "project", m["type"], m["title"], m["content"], None, stamp, stamp)
        for m in [*memories, *evaluation.distractors(evaluation.LATENCY_SIZE - len(memories))]
    ]
    times = []
    with MemoryStore(tmp_path / "memoria.db", semantic=None) as store:
        assert store.import_rows(rows)["created"] == evaluation.LATENCY_SIZE
        store.query("calentamiento", project=evaluation.PROJECT, mode="lexical")
        for _ in range(3):
            for query in queries:
                start = time.perf_counter()
                store.query(query["query"], project=evaluation.PROJECT, mode="lexical", limit=10)
                times.append((time.perf_counter() - start) * 1000)
    check(
        f"búsqueda léxica, p95 con {evaluation.LATENCY_SIZE} memorias",
        evaluation.percentile(times, 95),
        TARGETS["search_p95_ms"],
        unit="ms",
    )


def test_el_repo_sintetico_es_determinista_y_mezcla_tres_lenguajes() -> None:
    tree = _synthetic_repo.files(50_000)
    assert tree == _synthetic_repo.files(50_000)
    lines: dict[str, int] = {}
    for rel, text in tree.items():
        suffix = Path(rel).suffix
        lines[suffix] = lines.get(suffix, 0) + text.count("\n")
    assert sum(lines[s] for s in (".py", ".ts", ".java")) >= 50_000
    assert all(lines[s] >= 10_000 for s in (".py", ".ts", ".java")), lines


def test_check_avisa_entre_la_meta_y_el_doble_y_falla_despues() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        check("rápido", 0.5, 1.0)
        check("lento", 1.5, 1.0)
    assert [str(w.message) for w in caught] == ["lento: 1.50 s (meta < 1 s)"]
    assert all(issubclass(w.category, PerfWarning) for w in caught)
    with pytest.raises(AssertionError, match="muy lento: 2.00 s"):
        check("muy lento", 2.0, 1.0)


def test_measure_reintenta_solo_mientras_no_baja_del_doble(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Una máquina ocupada un rato no da un rojo: se reintenta hasta `MAX_RUNS`."""
    walls = iter([9.0, 9.0, 1.5, 0.8])  # segundos del comando, corrida por corrida
    calls: list[tuple[str, ...]] = []

    def fake(*args: str) -> tuple[float, str]:
        calls.append(args)
        return (0.5, "") if args == ("-c", "pass") else (next(walls), f"run {len(calls)}")

    monkeypatch.setattr(sys.modules[__name__], "timed", fake)
    found = measure(lambda run: ["sync", str(run)], 1.0)
    assert (found.cost, found.wall, found.interpreter) == (1.0, 1.5, 0.5)
    assert [c[-1] for c in calls if c != ("-c", "pass")] == ["0", "1", "2"]
    assert found.out == "run 6"
    walls = iter([0.6, 0.7, 9.0])
    calls.clear()
    assert measure(lambda run: ["sync"], 1.0).cost == pytest.approx(0.1)
    assert len(calls) == 2 * RUNS


def test_el_entorno_del_proceso_hijo_usa_este_exo_y_los_datos_aislados() -> None:
    env = _env()
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(SRC)
    assert env[paths.ENV_DATA_DIR] == os.environ[paths.ENV_DATA_DIR]
