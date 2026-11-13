"""Proveedor `onnx`: FastEmbed en CPU (extra `[vector]`). Carga solo archivos locales."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exo import _meta
from exo.memory.embeddings import ProviderError, model_path


def _missing_extra() -> ProviderError:
    return ProviderError(f"falta el extra [vector]: pip install {_meta.DIST_NAME}[vector]")


class OnnxProvider:
    name = "onnx"

    def __init__(self, model: str) -> None:
        self.model = model
        self._loaded: Any = None
        self._dim: int | None = None

    def _load(self) -> Any:
        if self._loaded is None:
            path = model_path(self.name, self.model)
            if not path.is_dir():
                raise ProviderError(
                    f"falta el modelo {self.model}; bajalo con `{_meta.NAME} mem model pull onnx`"
                )
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise _missing_extra() from exc
            self._loaded = TextEmbedding(
                model_name=self.model, cache_dir=str(path), local_files_only=True
            )
        return self._loaded

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed(["dimensión"])[0])
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in row] for row in self._load().embed(list(texts))]


def pull(model: str) -> Path:
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise _missing_extra() from exc
    path = model_path("onnx", model)
    path.mkdir(parents=True, exist_ok=True)
    TextEmbedding(model_name=model, cache_dir=str(path))
    return path
