"""Criterio 2 de F6: el inventario y el grafo coinciden con la verdad conocida de cada fixture.

La verdad conocida vive afuera del fixture (`tests/fixtures/ground-truth/`), y el fixture
se copia a una carpeta temporal con su propia historia git (ADR-0015).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import _ground_truth
import exo
from _git import Commit, git, init_repo
from exo import _meta
from exo.discovery import graph, inventory, planner, store

FIXTURES = _ground_truth.fixtures()
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
STEPS = ("inventory", "structure", "plan")


@pytest.fixture(scope="module", params=FIXTURES)
def analyzed(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> tuple[dict, dict, dict]:
    name = request.param
    root = tmp_path_factory.mktemp(name) / name
    init_repo(root, fixture=name)
    return _ground_truth.load(name), inventory.build(root), graph.build(root)


@needs_git
def test_criterio_2_inventario(analyzed: tuple[dict, dict, dict]) -> None:
    truth, inv, _ = analyzed
    assert set(truth["languages"]) <= set(inv["languages"])
    assert set(truth["frameworks"]) <= set(inv["frameworks"]), set(truth["frameworks"]) - set(
        inv["frameworks"]
    )
    assert {e["path"] for e in inv["entrypoints"]} == set(truth["entrypoints"])
    assert set(inv["tests"]["files"]) == set(truth["test_files"])
    for key in ("ci", "migrations", "api_contracts", "infrastructure", "sensitive_files"):
        assert set(inv[key]) == set(truth[key]), key


@needs_git
def test_criterio_2_modulos_y_aristas(analyzed: tuple[dict, dict, dict]) -> None:
    truth, _, structure = analyzed
    assert {m["path"] for m in structure["modules"]} == set(truth["modules"])
    edges = {(e["from"], e["to"]) for e in structure["edges"]}
    expected = {tuple(edge) for edge in truth["edges"]}
    assert edges == expected, {"missing": expected - edges, "extra": edges - expected}


def _history(name: str) -> list[Commit]:
    """Dos commits de otros autores sobre un entrypoint, para que churn y ownership tengan datos."""
    entry = _ground_truth.load(name)["entrypoints"][0]
    text = (_ground_truth.ROOT.parent / "repos" / name / entry).read_text(encoding="utf-8")
    mark = "#" if entry.endswith(".py") else "//"
    return [
        Commit("2026-02-01T10:00:00+00:00", "Bea Dos", "fix: one", {entry: f"{text}{mark} one\n"}),
        Commit(
            "2026-03-01T10:00:00+00:00", "Ciro Tres", "fix: two", {entry: f"{text}{mark} two\n"}
        ),
    ]


def _run_steps(root: Path, seed: str) -> dict[str, bytes]:
    """R0 a R2 por CLI en un subproceso con `PYTHONHASHSEED=seed`: los archivos de discovery."""
    src = str(Path(exo.__file__).resolve().parents[1])
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": src}
    for step in STEPS:
        subprocess.run(
            [sys.executable, "-m", _meta.NAME, "discover", step, "--project", str(root), "--json"],
            check=True,
            env=env,
            capture_output=True,
        )
    folder = store.root(root)
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()
    }


@needs_git
@pytest.mark.parametrize("name", FIXTURES)
def test_criterio_1_r0_a_r2_deterministas_y_estables_al_commitear(
    name: str, tmp_path: Path
) -> None:
    """`inventory`, `structure` y `plan` dan los mismos bytes con otro PYTHONHASHSEED, y
    commitear los resultados y correrlos otra vez no cambia nada (ADR-0015)."""
    root = tmp_path / name
    init_repo(root, fixture=name, history=_history(name))
    first = _run_steps(root, "1")
    assert {
        inventory.FILENAME,
        graph.FILENAME,
        planner.FILENAME,
        "module-graph.mmd",
        "hotspots.json",
        "ownership.json",
    } <= set(first)
    shutil.rmtree(store.root(root))
    assert _run_steps(root, "4242") == first
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "docs(discovery): R0 to R2")
    assert _run_steps(root, "77") == first
    assert git(root, "status", "--porcelain") == ""


def test_la_verdad_conocida_es_consistente() -> None:
    for name in FIXTURES:
        truth = _ground_truth.load(name)
        root = _ground_truth.ROOT.parent / "repos" / name
        listed = [
            p for key in ("entrypoints", "test_files", "ci", "migrations") for p in truth[key]
        ]
        listed += [p for cap in truth["capabilities"] for p in cap["key_files"]]
        missing = [p for p in listed if not (root / p).is_file()]
        assert missing == [], (name, missing)
        modules = set(truth["modules"])
        assert all(a in modules and b in modules for a, b in truth["edges"]), name
