"""Proveedor `static`: model2vec (extra `[static]`). Embeddings estáticos, sin red neuronal
al consultar: muy livianos en CPU. Carga solo desde la carpeta local del modelo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exo import _meta
from exo.memory.embeddings import ProviderError, model_path, promote, staged


def _missing_extra() -> ProviderError:
    return ProviderError(f"missing the [static] extra: pip install {_meta.DIST_NAME}[static]")


class StaticProvider:
    name = "static"

    def __init__(self, model: str) -> None:
        self.model = model
        self._loaded: Any = None

    def _load(self) -> Any:
        if self._loaded is None:
            path = model_path(self.name, self.model)
            if not path.is_dir():
                raise ProviderError(
                    f"model {self.model} is missing; download it with "
                    f"`{_meta.NAME} mem model pull static`"
                )
            try:
                from model2vec import StaticModel
            except ImportError as exc:
                raise _missing_extra() from exc
            try:
                self._loaded = StaticModel.from_pretrained(str(path), force_download=False)
            except Exception as exc:  # noqa: BLE001 - archivos rotos dan errores de todo tipo
                raise ProviderError(
                    f"could not load model {self.model} from {path} ({exc}); download it "
                    f"again with `{_meta.NAME} mem model pull static`"
                ) from exc
        return self._loaded

    @property
    def dim(self) -> int:
        return int(self._load().dim)

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        try:
            vectors = model.encode(list(texts), use_multiprocessing=False)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"model2vec failed to compute vectors ({exc})") from exc
        return [[float(x) for x in row] for row in vectors]


def pull(model: str) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise _missing_extra() from exc
    path = model_path("static", model)
    partial = staged(path)
    # Solo lo que usa model2vec: algunos repos traen además una copia ONNX del mismo tamaño.
    snapshot_download(
        repo_id=model,
        local_dir=str(partial),
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
    )
    return promote(partial, path)
