"""Índice semántico derivado, búsqueda híbrida con RRF y reindex (criterios 3 y 7 de F3)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from _memory_fakes import FakeProvider
from exo.memory import backends, embeddings, fusion
from exo.memory.backends.python import PythonBackend, cosine_distance, pack
from exo.memory.index import SemanticIndex
from exo.memory.store import MemoryStore, MemoryStoreError

P = "github.com/acme/api"


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setitem(embeddings.FACTORIES, "fake", lambda model, allow_remote: provider)
    return provider


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "memory.db"


def _corpus(store: MemoryStore) -> dict[str, int]:
    docs = {
        "colas": ("Elegimos colas para pagos", "Los pagos se procesan con colas y reintentos."),
        "coche": ("Seguro del coche", "La póliza cubre el coche de la empresa."),
        "lento": ("Endpoint lento", "El listado de clientes demora 3 s en producción."),
        "otro": ("Otro proyecto", "colas en otro lado"),
    }
    ids = {}
    for key, (title, content) in docs.items():
        project = "local/otro" if key == "otro" else P
        ids[key] = store.save(project=project, title=title, content=content).id
    return ids


# -- RRF y backend ----------------------------------------------------------------------


def test_rrf() -> None:
    fused = fusion.rrf([[1, 2, 3], [3, 1]])
    assert [item for item, _ in fused] == [1, 3, 2]
    assert fused[0][1] == pytest.approx(1 / 61 + 1 / 62)
    weighted = fusion.rrf([[1, 2], [2, 1]], weights=[1.0, 3.0])
    assert [item for item, _ in weighted] == [2, 1]
    assert fusion.rrf([]) == []
    with pytest.raises(ValueError):
        fusion.rrf([[1]], weights=[1.0, 2.0])


def test_distancia_coseno_en_python() -> None:
    assert cosine_distance(pack([1.0, 0.0]), pack([1.0, 0.0])) == pytest.approx(0.0)
    assert cosine_distance(pack([1.0, 0.0]), pack([0.0, 1.0])) == pytest.approx(1.0)
    assert cosine_distance(pack([0.0, 0.0]), pack([1.0, 0.0])) == 1.0
    assert cosine_distance(pack([1.0]), pack([1.0, 0.0])) is None


def test_sin_sqlite_vec_se_usa_el_backend_de_python(monkeypatch: pytest.MonkeyPatch) -> None:
    from exo.memory.backends import sqlite_vec

    monkeypatch.setattr(sqlite_vec, "available", lambda: False)
    assert backends.create().name == "python"
    assert backends.create("python").name == "python"


# -- reindex y modos ---------------------------------------------------------------------


def test_sin_indice_auto_es_lexico_y_semantico_pide_reindex(path: Path) -> None:
    with MemoryStore(path) as store:
        _corpus(store)
        result = store.query("colas", project=P)
        assert result.mode == "lexical"
        with pytest.raises(MemoryStoreError, match="reindex"):
            store.query("colas", mode="semantic")
        assert store.stats().semantic is None


def test_reindex_crea_el_indice_y_auto_pasa_a_hibrido(path: Path, fake: FakeProvider) -> None:
    with MemoryStore(path) as store:
        _corpus(store)
        result = store.reindex(provider="fake")
        assert (result.vectors, result.provider, result.model, result.dim) == (4, "fake", "v1", 32)
    with MemoryStore(path) as store:
        assert store.semantic is not None
        stats = store.stats().semantic
        assert (stats["provider"], stats["dim"], stats["missing_vectors"]) == ("fake", 32, 0)
        hybrid = store.query("mensajeria", project=P)
        assert hybrid.mode == "hybrid"
        assert hybrid.hits[0].title == "Elegimos colas para pagos"
        assert store.query("mensajeria", project=P, mode="lexical").hits == []


def test_la_semantica_filtra_antes_de_rankear(path: Path, fake: FakeProvider) -> None:
    with MemoryStore(path) as store:
        _corpus(store)
        store.reindex(provider="fake")
        hits = store.query("colas", project="local/otro", mode="semantic").hits
        assert [h.title for h in hits][:1] == ["Otro proyecto"]
        assert all(h.project in ("local/otro", "") for h in hits)
        assert store.query("demora", project=P, mode="semantic").hits[0].title == "Endpoint lento"


def test_guardar_calcula_el_vector_y_avisa_similares(path: Path, fake: FakeProvider) -> None:
    with MemoryStore(path) as store:
        store.reindex(provider="fake")
        first = store.save(project=P, title="Usamos colas", content="colas para pagos y cobros")
        assert first.similar == []
        second = store.save(project=P, title="Usamos colas", content="colas para pagos y cobros!")
        assert [h.id for h in second.similar] == [first.id]
        assert second.similar[0].score >= 0.8
        assert store.semantic.missing(store.conn) == 0
        store.delete(first.id)
        count = store.conn.execute("SELECT count(*) FROM observation_vectors").fetchone()[0]
        assert count == 1


def test_el_resumen_y_lo_importado_tienen_vector(
    path: Path, fake: FakeProvider, tmp_path: Path
) -> None:
    from exo.memory import exchange

    with MemoryStore(tmp_path / "origen.db") as source:
        source.save(project=P, title="Importada", content="sobre colas")
        data = exchange.export(source)
    with MemoryStore(path) as store:
        store.reindex(provider="fake")
        store.session_summary(P, "Quedó lenta la búsqueda")
        exchange.import_(store, data)
        assert store.semantic.missing(store.conn) == 0
        assert store.query("demora", project=P, mode="semantic").hits[0].type == "session-summary"


def test_si_el_proveedor_falla_se_guarda_igual(path: Path, fake: FakeProvider) -> None:
    with MemoryStore(path) as store:
        store.reindex(provider="fake")
        fake.fail = True
        saved = store.save(project=P, title="Sin vector", content="igual se guarda")
        assert store.get(saved.id).title == "Sin vector"
        assert "reindex" in store.semantic_note
        result = store.query("guarda", project=P)
        assert (result.mode, [h.title for h in result.hits]) == ("lexical", ["Sin vector"])
        assert "no disponible" in result.note
        with pytest.raises(MemoryStoreError):
            store.query("guarda", project=P, mode="hybrid")
        fake.fail = False
        assert store.fill_vectors() == 1


def test_dimension_distinta_exige_reindex(path: Path, fake: FakeProvider) -> None:
    with MemoryStore(path) as store:
        _corpus(store)
        store.reindex(provider="fake")
    conn = sqlite3.connect(path)
    conn.execute("UPDATE meta SET value = '99' WHERE key = 'embedding_dim'")
    conn.commit()
    conn.close()
    with MemoryStore(path) as store:
        result = store.query("colas", project=P)
        assert result.mode == "lexical" and "reindex" in result.note
        assert store.reindex().dim == 32
        assert store.query("colas", project=P).mode == "hybrid"


def test_criterio_3_reindex_da_los_mismos_resultados(path: Path, fake: FakeProvider) -> None:
    queries = ["colas", "mensajeria", "coche", "auto", "demora clientes", "pagos"]
    with MemoryStore(path) as store:
        _corpus(store)
        store.reindex(provider="fake")
        before = {q: [h.id for h in store.search(q, project=P)] for q in queries}
        store.conn.execute("DELETE FROM observation_vectors")
        store.conn.execute("DELETE FROM observations_fts")
        result = store.reindex()
        assert (result.fts, result.vectors) == (4, 4)
        after = {q: [h.id for h in store.search(q, project=P)] for q in queries}
    assert after == before
    assert any(before.values())


def test_reindex_none_apaga_lo_semantico(path: Path, fake: FakeProvider) -> None:
    with MemoryStore(path) as store:
        _corpus(store)
        store.reindex(provider="fake")
        assert store.reindex(provider="none").vectors == 0
        assert store.query("colas").mode == "lexical"
    with MemoryStore(path) as store:
        assert store.semantic is None and store.stats().semantic is None


def test_local_sin_extras_es_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings, "installed", lambda provider: False)
    assert embeddings.resolve("local") == "none"
    monkeypatch.setattr(embeddings, "installed", lambda provider: provider == "onnx")
    assert embeddings.resolve("local") == "onnx"
    assert embeddings.resolve("static") == "static"
    monkeypatch.setattr(embeddings, "installed", lambda provider: True)
    assert embeddings.resolve("local") == "onnx"


def test_criterio_7_proveedor_remoto_sin_permiso_falla(path: Path) -> None:
    with MemoryStore(path) as store:
        with pytest.raises(embeddings.ProviderError, match="remoto"):
            store.reindex(provider="openai-compatible")
        assert store.stats().semantic is None
    with pytest.raises(embeddings.ProviderError, match="desconocido"):
        embeddings.create("none")


def test_indice_explicito_con_backend_de_python(path: Path) -> None:
    provider = FakeProvider()
    with MemoryStore(path, semantic=SemanticIndex(provider, PythonBackend())) as store:
        saved = store.save(project=P, title="Coche", content="seguro del coche")
        assert store.query("auto", project=P, mode="semantic").hits[0].id == saved.id
