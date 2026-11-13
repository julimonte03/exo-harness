"""Proveedor `onnx`: FastEmbed en CPU (extra `[vector]`). Carga solo archivos locales."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exo import _meta
from exo.memory.embeddings import ProviderError, model_path, promote, staged


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
            try:
                self._loaded = TextEmbedding(
                    model_name=self.model, cache_dir=str(path), local_files_only=True
                )
            except Exception as exc:  # noqa: BLE001 - archivos rotos dan errores de todo tipo
                raise ProviderError(
                    f"no se pudo cargar el modelo {self.model} de {path} ({exc}); bajalo de "
                    f"nuevo con `{_meta.NAME} mem model pull onnx`"
                ) from exc
        return self._loaded

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed(["dimensión"])[0])
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        try:
            return [[float(x) for x in row] for row in model.embed(list(texts))]
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"FastEmbed falló al calcular vectores ({exc})") from exc


def pull(model: str) -> Path:
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise _missing_extra() from exc
    path = model_path("onnx", model)
    partial = staged(path)
    TextEmbedding(model_name=model, cache_dir=str(partial))
    return promote(partial, path)
