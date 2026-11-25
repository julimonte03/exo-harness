"""Proveedores de embeddings (D-08). Cada uno importa su dependencia de forma diferida.

- `none`: sin búsqueda semántica.
- `onnx`: FastEmbed en CPU (extra `[vector]`). El default de `local` desde el
  experimento de F3 (ADR-0010).
- `static`: model2vec (extra `[static]`), embeddings estáticos.
- `ollama`: HTTP a un Ollama local.
- `openai-compatible`: HTTP a un servicio remoto. Manda el texto de las
  memorias afuera, así que exige habilitarlo explícitamente (invariante 11).

Los modelos de `static` y `onnx` se bajan **solo** con `exo mem model pull`
(ADR-0009) a la carpeta de modelos del usuario; al usarlos, nunca se descargan.
La configuración (proveedor, modelo, dimensión) vive en la base de la memoria,
porque es una por usuario.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from exo import _meta, paths
from exo.memory.model import MemoryStoreError

PROVIDERS = ("none", "static", "onnx", "ollama", "openai-compatible")
REMOTE = ("openai-compatible",)
DEFAULT_MODELS = {
    "static": "minishlab/potion-multilingual-128M",
    "onnx": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
}
# Paquete que necesita cada proveedor local, para resolver `local` sin importarlos.
_PACKAGES = {"static": "model2vec", "onnx": "fastembed"}
LOCAL_ORDER = ("onnx", "static")


class ProviderError(MemoryStoreError):
    """El proveedor no se puede usar: falta el extra, el modelo o el permiso."""


class EmbeddingProvider(Protocol):
    name: str
    model: str

    @property
    def dim(self) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


Factory = Callable[[str | None, bool], EmbeddingProvider]


def models_dir() -> Path:
    return paths.user_data_dir() / "models"


def model_path(provider: str, model: str) -> Path:
    """Carpeta local de un modelo bajado con `model pull`."""
    return models_dir() / provider / model.replace("/", "--")


def installed(provider: str) -> bool:
    package = _PACKAGES.get(provider)
    return package is not None and importlib.util.find_spec(package) is not None


def resolve(name: str) -> str:
    """`local` es el mejor proveedor local instalado según el experimento de F3 (ADR-0010):
    `onnx`, después `static`, si no `none`."""
    if name != "local":
        return name
    return next((p for p in LOCAL_ORDER if installed(p)), "none")


def _static(model: str | None, allow_remote: bool) -> EmbeddingProvider:
    from exo.memory.embeddings.static import StaticProvider

    return StaticProvider(model or DEFAULT_MODELS["static"])


def _onnx(model: str | None, allow_remote: bool) -> EmbeddingProvider:
    from exo.memory.embeddings.onnx import OnnxProvider

    return OnnxProvider(model or DEFAULT_MODELS["onnx"])


def _ollama(model: str | None, allow_remote: bool) -> EmbeddingProvider:
    from exo.memory.embeddings.http import OllamaProvider

    return OllamaProvider(model, allow_remote=allow_remote)


def _openai(model: str | None, allow_remote: bool) -> EmbeddingProvider:
    from exo.memory.embeddings.http import OpenAICompatibleProvider

    return OpenAICompatibleProvider(model, allow_remote=allow_remote)


FACTORIES: dict[str, Factory] = {
    "static": _static,
    "onnx": _onnx,
    "ollama": _ollama,
    "openai-compatible": _openai,
}


def check_remote(name: str, allow_remote: bool) -> None:
    if name in REMOTE and not allow_remote:
        raise ProviderError(
            f"provider {name} sends the memory text to a remote service; "
            f"it is disabled unless you ask for it explicitly (--allow-remote in "
            f"`{_meta.NAME} mem reindex`)"
        )


# Proveedores locales ya creados en este proceso: el servidor MCP carga el modelo una vez.
_CACHE: dict[tuple[str, str], EmbeddingProvider] = {}


def create(name: str, model: str | None = None, *, allow_remote: bool = False) -> EmbeddingProvider:
    """Proveedor listo para usar (carga el modelo recién en el primer `embed`). Los locales
    se reutilizan dentro del proceso."""
    name = resolve(name)
    if name == "none" or name not in FACTORIES:
        raise ProviderError(f"unknown or empty embeddings provider: {name!r}")
    check_remote(name, allow_remote)
    if name in DEFAULT_MODELS:
        key = (name, model or DEFAULT_MODELS[name])
        if key not in _CACHE:
            _CACHE[key] = FACTORIES[name](model, allow_remote)
        return _CACHE[key]
    return FACTORIES[name](model, allow_remote)


def staged(target: Path) -> Path:
    """Carpeta temporal al lado de `target` para bajar un modelo; ver `promote`."""
    partial = target.with_name(target.name + ".partial")
    if partial.exists():
        import shutil

        shutil.rmtree(partial)
    # La carpeta de datos tiene la memoria: si falta, se crea privada (TM-27, F8R1-9).
    paths.private_dir(partial.parent)
    return partial


def promote(partial: Path, target: Path) -> Path:
    """Reemplaza `target` por la descarga completa: un corte deja el modelo anterior o nada."""
    import shutil

    old = target.with_name(target.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if target.exists():
        target.rename(old)
    partial.rename(target)
    if old.exists():
        shutil.rmtree(old)
    _CACHE.clear()
    return target


def pull(provider: str, model: str | None = None) -> tuple[str, str, Path]:
    """Baja un modelo local a la carpeta de modelos. Devuelve (proveedor, modelo, carpeta)."""
    provider = resolve(provider)
    if provider == "ollama":
        raise ProviderError("Ollama models are downloaded with `ollama pull <model>`")
    if provider not in DEFAULT_MODELS:
        raise ProviderError(f"provider {provider!r} has no models to download")
    model = model or DEFAULT_MODELS[provider]
    if provider == "static":
        from exo.memory.embeddings.static import pull as download
    else:
        from exo.memory.embeddings.onnx import pull as download
    return provider, model, download(model)


def list_models() -> list[tuple[str, str, Path]]:
    """Modelos bajados: (proveedor, modelo, carpeta)."""
    found = []
    for provider in sorted(DEFAULT_MODELS):
        folder = models_dir() / provider
        if folder.is_dir():
            for path in sorted(p for p in folder.iterdir() if p.is_dir()):
                if path.suffix in (".partial", ".old"):
                    continue
                found.append((provider, path.name.replace("--", "/"), path))
    return found
