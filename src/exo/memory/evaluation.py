"""Experimento de memoria de F3 (`exo mem eval`): léxica contra híbrida, con métricas.

Corre sobre una base temporal (nunca la del usuario), con el dataset sintético de
`tests/memory_eval/` (80 memorias, 50 consultas etiquetadas).

**Métricas** (consultas con respuesta, salvo la última):

- Recall@5 y MRR@10, nDCG@10 con relevancia binaria; global y por tipo de
  consulta (exacta, paráfrasis, idioma cruzado).
- Falsos positivos en las consultas sin respuesta: el umbral τ es el percentil 10
  de la confianza del primer resultado en las consultas que sí aciertan, y cuenta
  como falso positivo una consulta sin respuesta cuyo primer resultado tiene
  confianza ≥ τ. La confianza es BM25 en la léxica y la similitud coseno en la
  semántica y en la híbrida (la del primer resultado fusionado).
- Latencia p50/p95 de búsqueda con 5 000 memorias (las 80 más distractores
  sintéticos), con el modelo ya cargado.
- Tamaño instalado (paquetes del extra más el modelo) y arranque en frío (abrir la
  base y hacer la primera búsqueda en un proceso nuevo).

**Regla de decisión** (congelada antes de correr; plan de F3, D-07): la híbrida
pasa a ser el default si, contra la léxica, (1) sube el Recall@5 global al menos
10 puntos, (2) no baja el Recall@5 de las consultas exactas más de 2 puntos y
(3) su p95 queda por debajo de 150 ms. Si pasan varias, gana la de mejor Recall@5
global; si empatan, la de menor tamaño instalado. Si no pasa ninguna, el default
sigue siendo la léxica.
"""

from __future__ import annotations

import importlib.metadata
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from exo import _meta, paths
from exo.memory import embeddings
from exo.memory.store import MemoryStore

KINDS = ("exact", "paraphrase", "cross")
NOTES = f"""## How to read the table

- **Latency:** p50 and p95 are measured with the database open and the model already loaded.
  That is the latency of the MCP server, which reuses the provider within the process, and of
  any repeated use.
- **Cost per CLI call:** each `{_meta.NAME} mem …` CLI call is a new process, so it opens the
  database and loads the model. That cost is the one in the "Cold start" column.
- **False positives:**
  - The threshold τ is calibrated on the same queries (10th percentile of the confidence of the
    hits) and **is not applied when searching**.
  - The column measures whether the top result of a query with no answer would have a
    confidence as high as that of a hit.
  - It does not measure whether the search returns nothing: the hybrid search returns results
    anyway.
  - Confidence is not comparable across configurations: BM25 for lexical, cosine for the others.
"""
PROJECT = "eval/acme-pagos"
LATENCY_SIZE = 5000
RECALL_GAIN = 0.10
EXACT_LOSS = 0.02
P95_LIMIT_MS = 150.0
_PACKAGES = {
    "lexical": (),
    "static": ("sqlite-vec", "model2vec"),
    "onnx": ("sqlite-vec", "fastembed"),
}


@dataclass(frozen=True)
class Config:
    name: str
    mode: str  # lexical | hybrid | semantic
    provider: str | None = None  # static | onnx | otro registrado
    model: str | None = None


@dataclass
class Row:
    config: Config
    recall5: float
    recall5_by_kind: dict[str, float]
    mrr10: float
    ndcg10: float
    fp_rate: float
    tau: float | None
    p50_ms: float | None = None
    p95_ms: float | None = None
    installed_mb: float | None = None
    cold_start_s: float | None = None
    misses: list[str] = field(default_factory=list)


# -- dataset -----------------------------------------------------------------------------


def load(dataset: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    memories = json.loads((dataset / "memories.json").read_text(encoding="utf-8"))["memories"]
    queries = json.loads((dataset / "queries.json").read_text(encoding="utf-8"))["queries"]
    known = {m["id"] for m in memories}
    for query in queries:
        unknown = set(query["relevant"]) - known
        if unknown:
            raise ValueError(f"{query['id']}: unknown memories {sorted(unknown)}")
    return memories, queries


_WORDS_ES = [
    "pago",
    "reembolso",
    "cuenta",
    "saldo",
    "comercio",
    "banco",
    "cliente",
    "factura",
    "tarjeta",
    "transferencia",
    "lote",
    "archivo",
    "reporte",
    "servicio",
    "cola",
    "evento",
    "alerta",
    "tablero",
    "usuario",
    "ambiente",
    "proceso",
    "configuración",
    "contrato",
    "despliegue",
    "prueba",
    "base",
    "índice",
    "consulta",
    "caché",
    "sesión",
    "permiso",
]
_WORDS_EN = [
    "payment",
    "refund",
    "account",
    "balance",
    "merchant",
    "bank",
    "customer",
    "invoice",
    "card",
    "transfer",
    "batch",
    "file",
    "report",
    "service",
    "queue",
    "event",
    "alert",
    "dashboard",
    "user",
    "environment",
    "process",
    "setting",
    "contract",
    "deploy",
    "test",
    "database",
    "index",
    "query",
    "cache",
    "session",
    "permission",
]
_VERBS = [
    "revisar",
    "ajustar",
    "migrar",
    "documentar",
    "limpiar",
    "renombrar",
    "check",
    "update",
    "move",
    "rename",
]


def distractors(count: int, seed: int = 42) -> list[dict[str, str]]:
    """Memorias de relleno, deterministas, para medir latencia con muchas filas."""
    rng = random.Random(seed)
    items = []
    for i in range(count):
        words = _WORDS_ES if i % 2 else _WORDS_EN
        sample = rng.sample(words, 6)
        title = f"{rng.choice(_VERBS)} {sample[0]} {sample[1]} {i}"
        content = (
            f"Nota {i}: {' '.join(sample[2:])} en el área {rng.randint(1, 40)}; "
            f"ticket OPS-{rng.randint(1000, 9999)}."
        )
        items.append({"title": title, "content": content, "type": "note"})
    return items


def _build(
    path: Path, memories: list[dict[str, Any]], config: Config, extra: int = 0
) -> dict[int, str]:
    """Base temporal con las memorias (más `extra` distractores). Devuelve id → clave."""
    keys: dict[int, str] = {}
    with MemoryStore(path, semantic=None) as store:
        for memory in memories:
            saved = store.save(
                project=PROJECT,
                title=memory["title"],
                content=memory["content"],
                type=memory["type"],
            )
            keys[saved.id] = memory["id"]
        for item in distractors(extra):
            store.save(project=PROJECT, **item)
        if config.mode != "lexical":
            store.reindex(provider=config.provider, model=config.model)
    return keys


# -- métricas ------------------------------------------------------------------------------


def recall_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant) if relevant else 0.0


def mrr_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return next((1.0 / i for i, key in enumerate(ranked[:k], 1) if key in relevant), 0.0)


def ndcg_at(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 1) for i, key in enumerate(ranked[:k], 1) if key in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def percentile(values: list[float], q: float) -> float:
    """Percentil por rango más cercano (q en 0..100)."""
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return ordered[rank - 1]


def _confidence(store: MemoryStore, query: str, mode: str, top_id: int, score: float) -> float:
    if mode == "lexical":
        return score
    if mode == "semantic":
        return score
    sims = {
        h.id: h.score for h in store.query(query, project=PROJECT, mode="semantic", limit=50).hits
    }
    return sims.get(top_id, 0.0)


def _quality(
    path: Path, queries: list[dict[str, Any]], keys: dict[int, str], config: Config
) -> Row:
    recalls: dict[str, list[float]] = {kind: [] for kind in KINDS}
    mrrs, ndcgs, hits_conf, none_conf, misses = [], [], [], [], []
    with MemoryStore(path) as store:
        for query in queries:
            result = store.query(query["query"], project=PROJECT, mode=config.mode, limit=10)
            ranked = [keys.get(h.id, "?") for h in result.hits]
            conf = (
                _confidence(
                    store, query["query"], config.mode, result.hits[0].id, result.hits[0].score
                )
                if result.hits
                else None
            )
            relevant = set(query["relevant"])
            if query["kind"] == "none":
                none_conf.append(conf)
                continue
            recalls[query["kind"]].append(recall_at(ranked, relevant, 5))
            mrrs.append(mrr_at(ranked, relevant, 10))
            ndcgs.append(ndcg_at(ranked, relevant, 10))
            if ranked and ranked[0] in relevant and conf is not None:
                hits_conf.append(conf)
            if recall_at(ranked, relevant, 5) == 0:
                misses.append(query["id"])
    tau = percentile(hits_conf, 10) if hits_conf else None
    false = sum(1 for c in none_conf if c is not None and tau is not None and c >= tau)
    every = [r for kind in KINDS for r in recalls[kind]]
    return Row(
        config=config,
        recall5=statistics.fmean(every),
        recall5_by_kind={kind: statistics.fmean(v) if v else 0.0 for kind, v in recalls.items()},
        mrr10=statistics.fmean(mrrs),
        ndcg10=statistics.fmean(ndcgs),
        fp_rate=false / len(none_conf) if none_conf else 0.0,
        tau=tau,
        misses=misses,
    )


def _latency(
    path: Path, queries: list[dict[str, Any]], config: Config, reps: int = 3
) -> tuple[float, float]:
    times = []
    with MemoryStore(path) as store:
        store.query("calentamiento", project=PROJECT, mode=config.mode)
        for _ in range(reps):
            for query in queries:
                start = time.perf_counter()
                store.query(query["query"], project=PROJECT, mode=config.mode, limit=10)
                times.append((time.perf_counter() - start) * 1000)
    return percentile(times, 50), percentile(times, 95)


def _dist_size(name: str) -> int:
    try:
        dist = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return 0
    total = 0
    for item in dist.files or []:
        located = Path(str(dist.locate_file(item)))
        if located.is_file():
            total += located.stat().st_size
    return total


def _closure(names: tuple[str, ...]) -> set[str]:
    seen: set[str] = set()
    pending = list(names)
    while pending:
        name = pending.pop().lower().replace("_", "-")
        if name in seen:
            continue
        seen.add(name)
        try:
            requires = importlib.metadata.requires(name) or []
        except importlib.metadata.PackageNotFoundError:
            continue
        for requirement in requires:
            if "extra ==" in requirement:
                continue
            match = re.match(r"[A-Za-z0-9._-]+", requirement)
            if match:
                pending.append(match.group(0))
    return seen


def installed_mb(config: Config) -> float:
    packages = _PACKAGES.get(config.provider or "lexical", ())
    total = sum(_dist_size(name) for name in _closure(packages)) if packages else 0
    if config.provider in embeddings.DEFAULT_MODELS:
        model = config.model or embeddings.DEFAULT_MODELS[config.provider]
        folder = embeddings.model_path(config.provider, model)
        total += sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
    return total / 1e6


def cold_start_s(path: Path, config: Config, runs: int = 3) -> float:
    code = (
        "import time\n"
        "t = time.perf_counter()\n"
        "from exo.memory.store import MemoryStore\n"
        "with MemoryStore() as s:\n"
        f"    s.query('pagos duplicados', project={PROJECT!r}, mode={config.mode!r})\n"
        "print(time.perf_counter() - t)\n"
    )
    env = {**os.environ, paths.ENV_MEMORY_DB: str(path)}
    samples = []
    for _ in range(runs):
        out = subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
        )
        samples.append(float(out.stdout.strip().splitlines()[-1]))
    return statistics.median(samples)


# -- decisión y reporte -------------------------------------------------------------------


def decide(rows: list[Row]) -> tuple[str, list[str]]:
    """Aplica la regla congelada. Devuelve (configuración ganadora, razones)."""
    lexical = next(r for r in rows if r.config.mode == "lexical")
    reasons, passing = [], []
    for row in rows:
        if row.config.mode != "hybrid":
            continue
        gain = row.recall5 - lexical.recall5
        loss = lexical.recall5_by_kind["exact"] - row.recall5_by_kind["exact"]
        checks = {
            f"global Recall@5 +{gain * 100:.1f} pts (needs ≥ {RECALL_GAIN * 100:.0f})": gain
            >= RECALL_GAIN - 1e-9,
            f"exact −{max(loss, 0) * 100:.1f} pts (needs ≤ {EXACT_LOSS * 100:.0f})": loss
            <= EXACT_LOSS + 1e-9,
            f"p95 {row.p95_ms:.1f} ms (needs < {P95_LIMIT_MS:.0f})": row.p95_ms is not None
            and row.p95_ms < P95_LIMIT_MS,
        }
        verdict = "passes" if all(checks.values()) else "fails"
        detail = "; ".join(f"{text}: {'yes' if ok else 'no'}" for text, ok in checks.items())
        reasons.append(f"{row.config.name}: {verdict} ({detail})")
        if all(checks.values()):
            passing.append(row)
    if not passing:
        return lexical.config.name, reasons
    best = min(passing, key=lambda r: (-r.recall5, r.installed_mb or 0.0))
    return best.config.name, reasons


def evaluate(
    dataset: Path,
    configs: list[Config],
    *,
    latency_size: int = LATENCY_SIZE,
    measure_cost: bool = True,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    memories, queries = load(dataset)
    say = progress or (lambda _text: None)
    rows: list[Row] = []
    with tempfile.TemporaryDirectory(prefix=f"{_meta.NAME}-eval-") as tmp:
        for config in configs:
            say(f"{config.name}: database with {len(memories)} memories")
            small = Path(tmp) / f"{config.name}-small.db"
            keys = _build(small, memories, config)
            row = _quality(small, queries, keys, config)
            say(f"{config.name}: latency with {latency_size} memories")
            big = Path(tmp) / f"{config.name}-big.db"
            _build(big, memories, config, extra=max(latency_size - len(memories), 0))
            row.p50_ms, row.p95_ms = _latency(big, queries, config)
            if measure_cost:
                row.installed_mb = installed_mb(config)
                row.cold_start_s = cold_start_s(big, config)
            rows.append(row)
    winner, reasons = decide(rows)
    return {
        "date": date.today().isoformat(),
        "engine_version": _meta.VERSION,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "memories": len(memories),
        "queries": {kind: sum(q["kind"] == kind for q in queries) for kind in (*KINDS, "none")},
        "latency_size": latency_size,
        "rows": [{**asdict(r), "config": asdict(r.config)} for r in rows],
        "winner": winner,
        "reasons": reasons,
    }


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}"


def _num(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def render(report: dict[str, Any]) -> str:
    """Tabla de métricas en Markdown para `docs/evals/memory-<fecha>.md`."""
    lines = [
        f"# Memory experiment — {report['date']}",
        "",
        f"Engine {report['engine_version']}, Python {report['python']} ({report['platform']}). "
        f"Synthetic dataset: {report['memories']} memories; queries: "
        + ", ".join(f"{n} {kind}" for kind, n in report["queries"].items())
        + f". Latency with {report['latency_size']} memories.",
        "",
        "| Configuration | Recall@5 | exact | paraphrase | cross | MRR@10 | nDCG@10 "
        "| FP with no answer | p50 ms | p95 ms | Installed MB | Cold start s |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        kinds = row["recall5_by_kind"]
        lines.append(
            f"| {row['config']['name']} | {_pct(row['recall5'])} | {_pct(kinds['exact'])} | "
            f"{_pct(kinds['paraphrase'])} | {_pct(kinds['cross'])} | {_num(row['mrr10'], 3)} | "
            f"{_num(row['ndcg10'], 3)} | {_pct(row['fp_rate'])} | {_num(row['p50_ms'])} | "
            f"{_num(row['p95_ms'])} | {_num(row['installed_mb'], 0)} | "
            f"{_num(row['cold_start_s'], 2)} |"
        )
    lines += ["", "## Decision (rule frozen before the run)", ""]
    lines += [f"- {reason}" for reason in report["reasons"]]
    lines += ["", f"**Result:** {report['winner']}.", ""]
    lines += [NOTES, "## Queries with no hit in the top 5", ""]
    for row in report["rows"]:
        lines.append(f"- {row['config']['name']}: {', '.join(row['misses']) or '-'}")
    return "\n".join(lines) + "\n"


def default_configs(providers: list[str]) -> list[Config]:
    configs = [Config("lexical", "lexical")]
    for provider in providers:
        model = embeddings.DEFAULT_MODELS.get(provider)
        configs.append(Config(f"hybrid-{provider}", "hybrid", provider, model))
        configs.append(Config(f"semantic-{provider}", "semantic", provider, model))
    return configs
