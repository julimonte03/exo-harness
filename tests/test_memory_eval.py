"""Experimento de memoria (criterio 5 de F3): dataset, métricas, regla de decisión y arnés."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _memory_fakes import FakeProvider
from exo.cli import main
from exo.memory import embeddings, evaluation
from exo.memory.evaluation import Config, Row

DATASET = Path(__file__).resolve().parent / "memory_eval"


def test_dataset_cumple_el_plan() -> None:
    memories, queries = evaluation.load(DATASET)
    assert len(memories) == 80 and len({m["id"] for m in memories}) == 80
    kinds = [q["kind"] for q in queries]
    assert (
        kinds.count("exact"),
        kinds.count("paraphrase"),
        kinds.count("cross"),
        kinds.count("none"),
    ) == (15, 20, 10, 5)
    assert {m["lang"] for m in memories} == {"es", "en"}
    assert all(q["relevant"] == [] for q in queries if q["kind"] == "none")
    assert all(q["relevant"] for q in queries if q["kind"] != "none")


def test_load_rechaza_relevantes_inexistentes(tmp_path: Path) -> None:
    (tmp_path / "memories.json").write_text(
        json.dumps({"memories": [{"id": "m1"}]}), encoding="utf-8"
    )
    (tmp_path / "queries.json").write_text(
        json.dumps({"queries": [{"id": "q1", "relevant": ["m9"]}]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="m9"):
        evaluation.load(tmp_path)


def test_metricas() -> None:
    ranked = ["a", "b", "c", "d", "e", "f"]
    assert evaluation.recall_at(ranked, {"b", "z"}, 5) == 0.5
    assert evaluation.recall_at(ranked, set(), 5) == 0.0
    assert evaluation.mrr_at(ranked, {"c"}, 10) == pytest.approx(1 / 3)
    assert evaluation.mrr_at(ranked, {"z"}, 10) == 0.0
    assert evaluation.ndcg_at(["x", "a"], {"a"}, 10) == pytest.approx(1 / 1.5849625)
    assert evaluation.ndcg_at(ranked, {"a"}, 10) == 1.0
    assert evaluation.percentile([5.0, 1.0, 3.0, 2.0, 4.0], 50) == 3.0
    assert evaluation.percentile([1.0, 2.0], 95) == 2.0


def _row(name: str, mode: str, recall: float, exact: float, p95: float, size: float = 0.0) -> Row:
    return Row(
        config=Config(name, mode),
        recall5=recall,
        recall5_by_kind={"exact": exact, "paraphrase": 0.0, "cross": 0.0},
        mrr10=0.0,
        ndcg10=0.0,
        fp_rate=0.0,
        tau=None,
        p95_ms=p95,
        installed_mb=size,
    )


def test_regla_de_decision() -> None:
    lexical = _row("lexical", "lexical", 0.50, 1.00, 5)
    winner, reasons = evaluation.decide(
        [
            lexical,
            _row("hybrid-a", "hybrid", 0.70, 0.99, 40, 600),
            _row("hybrid-b", "hybrid", 0.70, 1.00, 30, 300),
        ]
    )
    assert winner == "hybrid-b"
    assert all(": passes" in r for r in reasons)
    assert evaluation.decide([lexical, _row("h", "hybrid", 0.59, 1.0, 10)])[0] == "lexical"
    assert evaluation.decide([lexical, _row("h", "hybrid", 0.80, 0.97, 10)])[0] == "lexical"
    winner, reasons = evaluation.decide([lexical, _row("h", "hybrid", 0.80, 1.0, 151)])
    assert winner == "lexical" and "fails" in reasons[0]


def test_distractores_deterministas() -> None:
    assert evaluation.distractors(5) == evaluation.distractors(5)
    assert len({d["title"] for d in evaluation.distractors(200)}) == 200


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        embeddings.FACTORIES, "fake", lambda model, allow_remote: FakeProvider(model)
    )


def test_evaluate_con_proveedor_falso(fake: None) -> None:
    report = evaluation.evaluate(
        DATASET, evaluation.default_configs(["fake"]), latency_size=120, measure_cost=False
    )
    names = [r["config"]["name"] for r in report["rows"]]
    assert names == ["lexical", "hybrid-fake", "semantic-fake"]
    lexical = report["rows"][0]
    assert lexical["recall5_by_kind"]["exact"] == 1.0
    assert all(r["p95_ms"] is not None for r in report["rows"])
    assert report["winner"] in names
    text = evaluation.render(report)
    assert "| lexical |" in text and "Rule" not in text and "**Result:**" in text


def test_cli_eval(fake: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "docs" / "memory.md"
    code = main(
        [
            "mem",
            "eval",
            "--dataset",
            str(DATASET),
            "--providers",
            "fake",
            "--latency-size",
            "100",
            "--skip-cost",
            "--output",
            str(out),
        ]
    )
    assert code == 0
    assert out.read_text(encoding="utf-8").startswith("# Memory experiment")
    assert "hybrid-fake" in capsys.readouterr().out


def test_costos_de_la_lexica() -> None:
    assert evaluation.installed_mb(Config("lexical", "lexical")) == 0.0
