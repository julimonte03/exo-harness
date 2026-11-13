"""Proveedores de embeddings reales y backend sqlite-vec (D-08; criterio 7 de F3).

Sin red: Ollama y el compatible con OpenAI se prueban contra un servidor HTTP local
falso. Los modelos de model2vec y FastEmbed se prueban solo si ya están bajados
con `exo mem model pull` (si no, se saltean).
"""

from __future__ import annotations

import json
import random
import sqlite3
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from exo import paths
from exo.memory import embeddings
from exo.memory.backends import python as pybackend
from exo.memory.backends import sqlite_vec
from exo.memory.embeddings import ProviderError, http
from exo.memory.store import MemoryStore

P = "github.com/acme/api"


class _Handler(BaseHTTPRequestHandler):
    replies: list[tuple[int, object]] = []
    seen: list[tuple[str, dict, dict]] = []

    def do_POST(self) -> None:  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.seen.append((self.path, dict(self.headers), body))
        status, payload = self.replies.pop(0) if self.replies else (200, {})
        if callable(payload):
            payload = payload(body)
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def server() -> Iterator[tuple[str, type[_Handler]]]:
    handler = type("H", (_Handler,), {"replies": [], "seen": []})
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", handler
    httpd.shutdown()


def _vectors(n: int, dim: int = 4) -> list[list[float]]:
    return [[float(i + j) for j in range(dim)] for i in range(n)]


# -- Ollama y OpenAI-compatible ----------------------------------------------------------


def test_ollama_local(server, monkeypatch: pytest.MonkeyPatch) -> None:
    url, handler = server
    monkeypatch.setenv("OLLAMA_HOST", url)
    handler.replies = [(200, lambda body: {"embeddings": _vectors(len(body["input"]))})] * 2
    provider = embeddings.create("ollama", "bge-m3")
    assert provider.embed(["a", "b"]) == _vectors(2)
    assert provider.dim == 4
    path, _, body = handler.seen[0]
    assert (path, body["model"]) == ("/api/embed", "bge-m3")


def test_ollama_en_otro_host_es_remoto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.empresa.com:11434")
    with pytest.raises(ProviderError, match="no es esta máquina"):
        embeddings.create("ollama")
    assert embeddings.create("ollama", allow_remote=True).url == "http://ollama.empresa.com:11434"


def test_openai_compatible_con_permiso(server, monkeypatch: pytest.MonkeyPatch) -> None:
    url, handler = server
    monkeypatch.setenv(http.ENV_URL, url + "/v1")
    monkeypatch.setenv(http.ENV_KEY, "clave-de-prueba")
    handler.replies = [
        (200, lambda body: {"data": [{"embedding": v} for v in _vectors(len(body["input"]))]})
    ]
    provider = embeddings.create("openai-compatible", allow_remote=True)
    assert provider.embed(["x"]) == _vectors(1)
    path, headers, body = handler.seen[0]
    assert (path, headers["Authorization"], body["model"]) == (
        "/v1/embeddings",
        "Bearer clave-de-prueba",
        "text-embedding-3-small",
    )


def test_openai_compatible_sin_clave_o_sin_permiso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(http.ENV_KEY, raising=False)
    with pytest.raises(ProviderError, match=http.ENV_KEY):
        embeddings.create("openai-compatible", allow_remote=True).embed(["x"])
    with pytest.raises(ProviderError, match="remoto"):
        http.OpenAICompatibleProvider(None)


@pytest.mark.parametrize(
    ("reply", "fragment"),
    [
        ((500, {"error": "boom"}), "500"),
        ((200, {"embeddings": [[1.0]]}), "1 vectores"),
        ((200, {"embeddings": [["x"]] * 2}), "inválidos"),
    ],
)
def test_errores_http(server, monkeypatch: pytest.MonkeyPatch, reply, fragment: str) -> None:
    url, handler = server
    monkeypatch.setenv("OLLAMA_HOST", url)
    handler.replies = [reply]
    with pytest.raises(ProviderError, match=fragment):
        embeddings.create("ollama").embed(["a", "b"])


def test_ollama_sin_servidor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    with pytest.raises(ProviderError, match="no se pudo conectar"):
        embeddings.create("ollama").embed(["a"])


# -- modelos locales ---------------------------------------------------------------------


def test_sin_modelo_bajado_pide_model_pull() -> None:
    for name in ("static", "onnx"):
        provider = embeddings.create(name)
        with pytest.raises(ProviderError, match="model pull"):
            provider.embed(["x"])


def test_pull_de_ollama_o_remoto() -> None:
    with pytest.raises(ProviderError, match="ollama pull"):
        embeddings.pull("ollama")
    with pytest.raises(ProviderError, match="no tiene modelos"):
        embeddings.pull("openai-compatible")


def test_pull_y_list_models_sin_red(monkeypatch: pytest.MonkeyPatch) -> None:
    from exo.memory.embeddings import static

    def fake_pull(model: str) -> Path:
        path = embeddings.model_path("static", model)
        path.mkdir(parents=True)
        return path

    monkeypatch.setattr(static, "pull", fake_pull)
    provider, model, path = embeddings.pull("static")
    assert (provider, model) == ("static", embeddings.DEFAULT_MODELS["static"])
    assert path.is_relative_to(paths.user_data_dir())
    assert embeddings.list_models() == [("static", model, path)]


def _real_models_dir() -> Path:
    """La carpeta real de modelos (los tests aíslan la de datos, pero los modelos pesan)."""
    import os
    import sys

    base = os.environ.get("LOCALAPPDATA") if sys.platform == "win32" else None
    if sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    elif sys.platform != "win32":
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    from exo import _meta

    return Path(base or "") / _meta.USER_DIR_NAME / "models"


@pytest.mark.parametrize("provider", ["static", "onnx"])
def test_modelo_real_si_esta_bajado(
    provider: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    model = embeddings.DEFAULT_MODELS[provider]
    real = _real_models_dir()
    if not (real / provider / model.replace("/", "--")).is_dir() or not embeddings.installed(
        provider
    ):
        pytest.skip(f"modelo {provider} no bajado (exo mem model pull {provider})")
    monkeypatch.setattr(embeddings, "models_dir", lambda: real)
    with MemoryStore(tmp_path / "m.db") as store:
        store.save(
            project=P, title="Colas de mensajería", content="Los pagos se encolan y se reintentan."
        )
        store.save(project=P, title="Seguro del auto", content="La póliza cubre el vehículo.")
        result = store.reindex(provider=provider)
        assert result.vectors == 2 and result.dim > 0
        hits = store.query("message queue retries", project=P, mode="semantic").hits
        assert hits[0].title == "Colas de mensajería"


# -- sqlite-vec --------------------------------------------------------------------------


@pytest.mark.skipif(not sqlite_vec.available(), reason="sin sqlite-vec")
def test_sqlite_vec_y_python_dan_la_misma_distancia() -> None:
    rng = random.Random(7)
    conn = sqlite3.connect(":memory:")
    sqlite_vec.SqliteVecBackend().prepare(conn)
    pybackend.PythonBackend().prepare(conn)
    for _ in range(20):
        a = pybackend.pack([rng.uniform(-1, 1) for _ in range(16)])
        b = pybackend.pack([rng.uniform(-1, 1) for _ in range(16)])
        c_vec, c_py = conn.execute(
            "SELECT vec_distance_cosine(?, ?), exo_cosine_distance(?, ?)", (a, b, a, b)
        ).fetchone()
        assert c_vec == pytest.approx(c_py, abs=1e-5)
    conn.close()


def test_sqlite_vec_no_disponible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlite_vec, "installed", lambda: False)
    assert sqlite_vec.available() is False
