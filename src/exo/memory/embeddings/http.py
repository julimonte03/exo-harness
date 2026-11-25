"""Proveedores por HTTP, con stdlib: Ollama local y servicios compatibles con OpenAI.

Invariante 11: nada sale de la máquina sin permiso. Ollama en localhost no
cuenta como remoto; en otro host, sí. `openai-compatible` siempre es remoto.
La clave de API sale de una variable de entorno, nunca de la base.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit

from exo import _meta
from exo.memory.embeddings import ProviderError

TIMEOUT = 60
ENV_URL = f"{_meta.ENV_PREFIX}EMBEDDINGS_URL"
ENV_KEY = f"{_meta.ENV_PREFIX}EMBEDDINGS_API_KEY"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Un 3xx queda como HTTPError: urllib reenvía `Authorization` al destino de una
    redirección, así que la clave y el texto nunca van a otra dirección (threat model,
    TM-29)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]  # noqa: ANN001
        return None


# Sin proxies: para un servicio local, un proxy del sistema (HTTP_PROXY o el del registro de
# Windows) sacaría el texto de las memorias de la máquina (invariante 11), y con
# `openai-compatible` por http, también la API key en claro (F8R1-4).
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
_REMOTE = urllib.request.build_opener(_NoRedirect)


def _post(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    *,
    direct: bool = False,
) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        opener = _DIRECT.open if direct else _REMOTE.open
        with opener(request, timeout=TIMEOUT) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            target = exc.headers.get("Location", "?") if exc.headers else "?"
            raise ProviderError(
                f"{url} answered with a redirect ({exc.code}) to {target}; redirects are not "
                "followed, so the key and the memory text never reach another address: point "
                "the URL at the final address"
            ) from exc
        raise ProviderError(f"{url} returned {exc.code}: {exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f"could not connect to {url} ({exc})") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError(f"{url} did not return JSON ({exc})") from exc


def _vectors(raw: Any, url: str, count: int) -> list[list[float]]:
    if not isinstance(raw, list) or len(raw) != count:
        raise ProviderError(f"{url} returned {len(raw) if isinstance(raw, list) else 0} vectors")
    try:
        return [[float(x) for x in vector] for vector in raw]
    except (TypeError, ValueError) as exc:
        raise ProviderError(f"{url} returned invalid vectors") from exc


class _Http:
    name = "http"
    model = ""

    def __init__(self) -> None:
        self._dim: int | None = None

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed(["dimensión"])[0])
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - abstracto
        raise NotImplementedError


class OllamaProvider(_Http):
    name = "ollama"
    DEFAULT_MODEL = "bge-m3"  # multilingüe

    def __init__(self, model: str | None, *, allow_remote: bool = False) -> None:
        super().__init__()
        self.model = model or self.DEFAULT_MODEL
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        url = host if "://" in host else f"http://{host}"
        # 0.0.0.0 es la dirección en la que escucha Ollama; los clientes van a 127.0.0.1.
        self.url = url.replace("//0.0.0.0", "//127.0.0.1", 1)
        self.local = (urlsplit(self.url).hostname or "") in _LOCAL_HOSTS
        if not self.local and not allow_remote:
            raise ProviderError(
                f"OLLAMA_HOST points to {self.url}, which is not this machine: the memory text "
                f"would leave it. Use a local Ollama or pass --allow-remote"
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.url.rstrip('/')}/api/embed"
        data = _post(url, {"model": self.model, "input": list(texts)}, direct=self.local)
        return _vectors(data.get("embeddings") if isinstance(data, dict) else None, url, len(texts))


class OpenAICompatibleProvider(_Http):
    name = "openai-compatible"
    DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self, model: str | None, *, allow_remote: bool = False) -> None:
        super().__init__()
        if not allow_remote:  # create() ya lo valida; esto cubre el uso directo
            raise ProviderError("openai-compatible is remote: it needs --allow-remote")
        self.model = model or self.DEFAULT_MODEL
        self.url = os.environ.get(ENV_URL, "https://api.openai.com/v1")
        parts = urlsplit(self.url)
        self.local = (parts.hostname or "") in _LOCAL_HOSTS
        local = parts.scheme == "http" and self.local
        if parts.scheme != "https" and not local:
            # La clave viaja en cada pedido: en claro, cualquiera en el camino la lee.
            raise ProviderError(
                f"{ENV_URL} must be an https:// URL (http:// only for this machine): {self.url}"
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        key = os.environ.get(ENV_KEY)
        if not key:
            raise ProviderError(f"missing API key: set the {ENV_KEY} variable")
        url = f"{self.url.rstrip('/')}/embeddings"
        data = _post(
            url,
            {"model": self.model, "input": list(texts)},
            {"Authorization": f"Bearer {key}"},
            direct=self.local,  # en esta máquina, nunca por un proxy
        )
        items = data.get("data") if isinstance(data, dict) else None
        raw = [item.get("embedding") for item in items] if isinstance(items, list) else None
        return _vectors(raw, url, len(texts))
