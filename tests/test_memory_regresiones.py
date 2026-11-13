"""Regresiones de la revisión final de F3 (un test por hallazgo)."""

from __future__ import annotations

import io
import json
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from _memory_fakes import FakeProvider
from exo import paths
from exo.cli import main
from exo.memory import db, embeddings, exchange, projects
from exo.memory.store import MemoryStore, MemoryStoreError, NotFoundError
from exo.tools import registry
from exo.tools.validation import InputError

P = "github.com/acme/api"


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setitem(embeddings.FACTORIES, "fake", lambda model, allow_remote: provider)
    return provider


# -- 1. --content - en UTF-8 ------------------------------------------------------------


def _stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(data), encoding="cp1252"))


def test_contenido_por_stdin_en_utf8(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "decisión → usar ñandú ✓\n"
    _stdin(monkeypatch, text.encode("utf-8"))
    assert main(["mem", "save", "--project", P, "--title", "t", "--content", "-", "--json"]) == 0
    obs_id = json.loads(capsys.readouterr().out)["id"]
    with MemoryStore() as store:
        assert store.get(obs_id).content == text


def test_contenido_por_stdin_que_no_es_utf8_no_corta(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"caf\xe9 con leche")
    assert main(["mem", "save", "--project", P, "--title", "t", "--content", "-", "--json"]) == 0
    with MemoryStore() as store:
        assert store.list(P)[0].content.startswith("caf")


# -- 2. remotos con acentos -----------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="sin git")
def test_remoto_con_acentos(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    remote = "https://dev.azure.com/Org/ÁREA Pagos/_git/Repo"
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", remote], check=True)
    assert projects.detect(repo).name == "dev.azure.com/org/área pagos/repo"


def test_git_sin_salida_no_rompe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        returncode = 1
        stdout = None

    monkeypatch.setattr(projects.subprocess, "run", lambda *a, **k: Result())
    assert projects._git_remote(tmp_path) is None


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        ("https://dev.azure.com/acme/_git/api", "dev.azure.com/acme/api/api"),
        ("https://acme.visualstudio.com/_git/api", "dev.azure.com/acme/api/api"),
    ],
)
def test_forma_corta_de_azure(remote: str, expected: str) -> None:
    assert projects.normalize_remote(remote) == expected


# -- 3. Ollama local sin proxy -----------------------------------------------------------------


class _Recorder(BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.hits.append(self.path)
        data = json.dumps({"embeddings": [[1.0, 0.0]]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


def _serve(handler: type[BaseHTTPRequestHandler]) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_ollama_local_no_pasa_por_el_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    ollama = _serve(type("Ollama", (_Recorder,), {"hits": []}))
    proxy = _serve(type("Proxy", (_Recorder,), {"hits": []}))
    try:
        monkeypatch.setenv("OLLAMA_HOST", f"http://127.0.0.1:{ollama.server_port}")
        for name in ("HTTP_PROXY", "http_proxy"):
            monkeypatch.setenv(name, f"http://127.0.0.1:{proxy.server_port}")
        for name in ("NO_PROXY", "no_proxy"):
            monkeypatch.delenv(name, raising=False)
        assert embeddings.create("ollama").embed(["texto de la memoria"]) == [[1.0, 0.0]]
        assert ollama.RequestHandlerClass.hits == ["/api/embed"]
        assert proxy.RequestHandlerClass.hits == []
    finally:
        ollama.shutdown()
        proxy.shutdown()


def test_ollama_en_0000_es_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0:11434")
    provider = embeddings.create("ollama")
    assert provider.url == "http://127.0.0.1:11434" and provider.local


# -- 4. otro proceso cambia el índice ------------------------------------------------------------


def test_reindex_con_otra_dimension_desde_otro_proceso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(
        embeddings.FACTORIES, "fake32", lambda model, allow_remote: FakeProvider(model, dim=32)
    )
    monkeypatch.setitem(
        embeddings.FACTORIES, "fake16", lambda model, allow_remote: FakeProvider(model, dim=16)
    )
    path = tmp_path / "m.db"
    with MemoryStore(path) as setup:
        setup.save(project=P, title="Colas", content="colas para pagos")
        setup.reindex(provider="fake32")
    a = MemoryStore(path)
    try:
        with MemoryStore(path) as b:
            b.reindex(provider="fake16")
        saved = a.save(project=P, title="Nueva", content="mensajeria nueva")
        assert a.get(saved.id).title == "Nueva"
        assert "reindex" in a.semantic_note
        assert a.query("colas", project=P).hits
        assert a.semantic.missing(a.conn) >= 1
    finally:
        a.close()
    with MemoryStore(path) as fresh:
        assert fresh.query("mensajeria", project=P).mode == "hybrid"
        assert fresh.semantic.missing(fresh.conn) == 1


# -- 5. modelo roto o a medio bajar ---------------------------------------------------------------


@pytest.mark.parametrize("provider", ["onnx", "static"])
def test_modelo_roto_no_impide_guardar_ni_buscar(
    provider: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not embeddings.installed(provider):
        pytest.skip(f"sin el extra de {provider}")
    monkeypatch.setattr(embeddings, "models_dir", lambda: tmp_path / "models")
    folder = embeddings.model_path(provider, embeddings.DEFAULT_MODELS[provider])
    folder.mkdir(parents=True)
    (folder / "config.json").write_text("{ roto", encoding="utf-8")
    (folder / "model.safetensors").write_bytes(b"basura")
    path = tmp_path / "m.db"
    with MemoryStore(path) as store:
        store.save(project=P, title="Antes", content="guardada antes")
        conn = store.conn
        for key, value in (
            ("embedding_provider", provider),
            ("embedding_model", embeddings.DEFAULT_MODELS[provider]),
            ("embedding_dim", "8"),
        ):
            db.set_meta(conn, key, value)
    context = registry.Context(tmp_path, memory_db=path)
    saved = registry.call(
        "mem_save", {"project": P, "title": "Después", "content": "con el modelo roto"}, context
    )
    assert saved["action"] == "created"
    found = registry.call("mem_search", {"project": P, "query": "modelo roto"}, context)
    assert found["mode"] == "lexical" and found["results"][0]["title"] == "Después"


def test_pull_cortado_no_deja_un_modelo_a_medias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("huggingface_hub")
    import huggingface_hub

    def broken(repo_id: str, local_dir: str, **kwargs: object) -> str:
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        (Path(local_dir) / "config.json").write_text("{}", encoding="utf-8")
        raise OSError("se cortó la red")

    monkeypatch.setattr(huggingface_hub, "snapshot_download", broken)
    monkeypatch.setattr(embeddings, "models_dir", lambda: tmp_path / "models")
    with pytest.raises(OSError, match="se cortó"):
        embeddings.pull("static")
    assert not embeddings.model_path("static", embeddings.DEFAULT_MODELS["static"]).exists()
    assert embeddings.list_models() == []


# -- 6. fechas del import -----------------------------------------------------------------------


def test_import_compara_fechas_de_verdad(tmp_path: Path) -> None:
    with MemoryStore(tmp_path / "m.db") as store:
        rows = [
            (
                P,
                "project",
                "note",
                "Perfil",
                "local",
                "project/profile",
                "2026-11-14T01:00:00.000000+00:00",
                "2026-11-14T01:00:00.000000+00:00",
            )
        ]
        store.import_rows(rows)

        def payload(content: str, stamp: str) -> dict:
            return {
                "format": exchange.FORMAT,
                "schema": 1,
                "observations": [
                    {
                        "project": P,
                        "title": "Perfil",
                        "content": content,
                        "topic_key": "project/profile",
                        "created_at": stamp,
                        "updated_at": stamp,
                    }
                ],
            }

        assert (
            exchange.import_(store, payload("más viejo", "2026-11-14T09:30:00+09:00")).skipped == 1
        )
        assert (
            exchange.import_(store, payload("más nuevo", "2026-11-13T23:00:00-03:00")).updated == 1
        )
        obs = store.list(P)[0]
        assert (obs.content, obs.updated_at) == ("más nuevo", "2026-11-14T02:00:00.000000+00:00")
        assert exchange.import_(store, payload("sin zona", "2027-01-01")).updated == 1
        assert store.list(P)[0].updated_at == "2027-01-01T00:00:00.000000+00:00"


def test_import_con_tipos_que_no_son_texto(tmp_path: Path) -> None:
    data = {
        "format": exchange.FORMAT,
        "schema": 1,
        "observations": [{"project": P, "title": "t", "content": "c", "type": 3}],
    }
    with MemoryStore(tmp_path / "m.db") as store, pytest.raises(MemoryStoreError, match="type"):
        exchange.import_(store, data)


# -- 7. repos sin remoto con la misma carpeta ------------------------------------------------------


def test_repos_sin_remoto_con_la_misma_carpeta_no_comparten_memoria(tmp_path: Path) -> None:
    a, b = tmp_path / "a" / "api", tmp_path / "b" / "api"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    registry.call("mem_save", {"title": "De A", "content": "solo de a"}, registry.Context(a))
    in_b = registry.call("mem_context", {}, registry.Context(b))
    assert in_b["project"].startswith("local/api-") and "De A" not in in_b["context"]
    assert registry.call("mem_detect_project", {}, registry.Context(a))["name"] == "local/api"
    assert registry.call("mem_detect_project", {}, registry.Context(b))["name"] == in_b["project"]


# -- 8. proveedores reutilizados en el proceso -------------------------------------------------------


def test_los_proveedores_locales_se_reutilizan() -> None:
    assert embeddings.create("onnx") is embeddings.create("onnx")
    assert embeddings.create("onnx") is not embeddings.create("onnx", "otro/modelo")


# -- menores ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("word", ["Straße", "ﬁnance", "m²", "naïve"])
def test_fts5_tokeniza_la_consulta_igual_que_el_indice(tmp_path: Path, word: str) -> None:
    with MemoryStore(tmp_path / "m.db") as store:
        store.save(project=P, title="Texto raro", content=f"la palabra {word} está acá")
        assert [h.title for h in store.search(word, project=P)] == ["Texto raro"]


def test_consulta_enorme_es_rapida(tmp_path: Path) -> None:
    with MemoryStore(tmp_path / "m.db") as store:
        store.save(project=P, title="t", content="palabra1")
        start = time.perf_counter()
        store.search(" ".join(f"palabra{i}" for i in range(30_000)), project=P)
        assert time.perf_counter() - start < 3


def test_reindex_local_sin_extras_es_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake: FakeProvider
) -> None:
    monkeypatch.setattr(embeddings, "installed", lambda provider: False)
    with MemoryStore(tmp_path / "m.db") as store:
        store.save(project=P, title="t", content="c")
        store.reindex(provider="fake")
        with pytest.raises(embeddings.ProviderError, match="no local provider"):
            store.reindex(provider="local")
        assert store.stats().semantic["provider"] == "fake"


def test_si_sqlite_vec_no_carga_se_usa_el_backend_de_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake: FakeProvider
) -> None:
    from exo.memory.backends import sqlite_vec

    def broken(self, conn: sqlite3.Connection) -> None:
        raise MemoryStoreError("no se pudo cargar sqlite-vec (prueba)")

    monkeypatch.setattr(sqlite_vec, "available", lambda: True)
    monkeypatch.setattr(sqlite_vec.SqliteVecBackend, "prepare", broken)
    with MemoryStore(tmp_path / "m.db") as store:
        store.save(project=P, title="Coche", content="seguro del coche")
        store.reindex(provider="fake")
        assert store.semantic.backend.name == "python"
        assert store.query("auto", project=P, mode="semantic").hits


def test_save_muestra_los_parecidos(fake: FakeProvider, capsys: pytest.CaptureFixture[str]) -> None:
    with MemoryStore() as store:
        store.reindex(provider="fake")
    main(["mem", "save", "--project", P, "--title", "Colas", "--content", "colas para pagos"])
    capsys.readouterr()
    main(["mem", "save", "--project", P, "--title", "Colas", "--content", "colas para pagos!"])
    out = capsys.readouterr().out
    assert "similar: #1 Colas" in out


def test_salida_a_un_pipe_en_utf8(tmp_path: Path) -> None:
    env = {**__import__("os").environ, paths.ENV_MEMORY_DB: str(tmp_path / "m.db")}
    with MemoryStore(tmp_path / "m.db") as store:
        store.save(project=P, title="Flecha", content="antes → después ≥ ✓")
    out = subprocess.run(
        [sys.executable, "-m", "exo", "mem", "get", "1"], env=env, capture_output=True, check=True
    ).stdout
    assert "antes → después ≥ ✓".encode() in out


def test_ids_enormes_y_sesion_inexistente(tmp_path: Path) -> None:
    context = registry.Context(tmp_path, memory_db=tmp_path / "m.db")
    with pytest.raises(InputError, match="between"):
        registry.call("mem_get", {"id": 2**70}, context)
    with pytest.raises(InputError, match=r"session \d+ not found"):
        registry.call(
            "mem_save", {"project": P, "title": "t", "content": "c", "session_id": 99}, context
        )
    with MemoryStore(tmp_path / "m.db") as store, pytest.raises(NotFoundError):
        store.save(project=P, title="t", content="c", session_id=99)


def test_el_resumen_se_embebe_con_su_titulo(tmp_path: Path, fake: FakeProvider) -> None:
    with MemoryStore(tmp_path / "m.db") as store:
        store.reindex(provider="fake")
        result = store.session_summary(P, "quedó pendiente el retry")
        before = store.conn.execute(
            "SELECT embedding FROM observation_vectors WHERE id = ?", (result.observation_id,)
        ).fetchone()[0]
        store.reindex()
        after = store.conn.execute(
            "SELECT embedding FROM observation_vectors WHERE id = ?", (result.observation_id,)
        ).fetchone()[0]
        assert before == after


def test_merge_no_duplica_contenido_identico(tmp_path: Path) -> None:
    with MemoryStore(tmp_path / "m.db") as store:
        store.save(project="old/api", title="Gotcha", content="UTC siempre")
        store.save(project=P, title="Gotcha", content="UTC siempre")
        assert store.projects_merge("old/api", P).conflicts == 1
        assert len(store.list(P)) == 1


def test_abrir_no_toma_el_lock_de_escritura(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "m.db"
    with MemoryStore(path) as store:
        store.save(project=P, title="t", content="lectura")
    monkeypatch.setattr(db, "BUSY_TIMEOUT_MS", 200)
    writer = sqlite3.connect(path, isolation_level=None)
    writer.execute("BEGIN IMMEDIATE")
    try:
        with MemoryStore(path) as reader:
            assert [h.title for h in reader.search("lectura", project=P)] == ["t"]
    finally:
        writer.execute("ROLLBACK")
        writer.close()


def test_semantica_respeta_limit_mayor_a_la_profundidad(tmp_path: Path, fake: FakeProvider) -> None:
    with MemoryStore(tmp_path / "m.db") as store:
        for i in range(70):
            store.save(project=P, title=f"colas {i}", content="colas")
        store.reindex(provider="fake")
        assert len(store.query("colas", project=P, mode="semantic", limit=70).hits) == 70


def test_doctor_avisa_si_falta_el_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    from exo import doctor

    MemoryStore().close()
    conn = sqlite3.connect(paths.memory_db_path())
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [("embedding_provider", "onnx"), ("embedding_model", embeddings.DEFAULT_MODELS["onnx"])],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(embeddings, "installed", lambda provider: False)
    check = {c.name: c for c in doctor.run_checks(Path("."))}["memory-semantic"]
    assert check.status == "warn" and "[vector]" in check.detail
