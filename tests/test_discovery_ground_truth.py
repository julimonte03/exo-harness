"""Criterio 2 de F6: el inventario y el grafo coinciden con la verdad conocida de cada fixture.

La verdad conocida vive afuera del fixture (`tests/fixtures/ground-truth/`), y el fixture
se copia a una carpeta temporal con su propia historia git (ADR-0015).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import _ground_truth
from _git import init_repo
from exo.discovery import graph, inventory

FIXTURES = _ground_truth.fixtures()
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")


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
