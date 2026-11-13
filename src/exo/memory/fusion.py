"""Reciprocal Rank Fusion (Cormack, Clarke y Büttcher, 2009).

`score(d) = Σ peso_i / (k + rango_i(d))`, con rangos desde 1. k = 60 es el valor
del paper y del plan de F3. Los filtros (proyecto, scope, tipo) ya vienen
aplicados en cada ranking: la fusión no filtra.
"""

from __future__ import annotations

from collections.abc import Sequence

K = 60


def rrf(
    rankings: Sequence[Sequence[int]],
    *,
    k: int = K,
    weights: Sequence[float] | None = None,
) -> list[tuple[int, float]]:
    """Fusiona rankings de ids (el mejor primero). Empates: gana el mejor rango en el primer
    ranking que lo tenga, y después el id menor, para que el orden sea determinista."""
    if weights is not None and len(weights) != len(rankings):
        raise ValueError("hace falta un peso por ranking")
    scores: dict[int, float] = {}
    first_seen: dict[int, tuple[int, int]] = {}
    for index, ranking in enumerate(rankings):
        weight = 1.0 if weights is None else weights[index]
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + weight / (k + rank)
            first_seen.setdefault(item, (index, rank))
    return sorted(scores.items(), key=lambda pair: (-pair[1], first_seen[pair[0]], pair[0]))
