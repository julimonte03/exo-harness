"""Proveedor de embeddings falso y determinista para los tests (sin modelos ni red).

Hashea cada token a una de 32 dimensiones; los sinónimos de `SYNONYMS` caen en la
misma, así una consulta sin palabras en común puede encontrar por "significado".
"""

from __future__ import annotations

import hashlib

from exo.memory.store import tokens

SYNONYMS = {
    "coche": "vehiculo",
    "auto": "vehiculo",
    "car": "vehiculo",
    "cola": "queue",
    "colas": "queue",
    "queues": "queue",
    "mensajeria": "queue",
    "lento": "slow",
    "lenta": "slow",
    "demora": "slow",
    "latency": "slow",
}


class FakeProvider:
    name = "fake"

    def __init__(self, model: str | None = None, dim: int = 32) -> None:
        self.model = model or "v1"
        self._dim = dim
        self.calls = 0
        self.fail = False

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.fail:
            from exo.memory.embeddings import ProviderError

            raise ProviderError("el modelo falso falló")
        self.calls += 1
        vectors = []
        for text in texts:
            vector = [0.0] * self._dim
            for token in tokens(text):
                token = SYNONYMS.get(token, token)
                vector[int(hashlib.md5(token.encode()).hexdigest(), 16) % self._dim] += 1.0
            vectors.append(vector)
        return vectors
