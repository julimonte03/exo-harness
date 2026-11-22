"""memory/store: fuente de verdad en SQLite, upsert por topic_key y búsqueda léxica."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from exo import paths
from exo.memory import db
from exo.memory.store import MemoryStore, MemoryStoreError, NotFoundError

P = "dev.azure.com/acme/pagos/api"


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    with MemoryStore(tmp_path / "memory.db") as opened:
        yield opened


@pytest.fixture(params=[True, False], ids=["fts5", "like"])
def any_store(request: pytest.FixtureRequest, tmp_path: Path) -> MemoryStore:
    with MemoryStore(tmp_path / "memory.db", fts=request.param) as opened:
        yield opened


def _save(store: MemoryStore, title: str, content: str, **kwargs) -> int:
    kwargs.setdefault("project", P)
    return store.save(title=title, content=content, **kwargs).id


# -- ruta y esquema ---------------------------------------------------------------------


def test_ruta_por_defecto_y_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert paths.memory_db_path() == paths.user_data_dir() / "memory.db"
    monkeypatch.setenv(paths.ENV_MEMORY_DB, str(tmp_path / "otra" / "m.db"))
    assert paths.memory_db_path() == tmp_path / "otra" / "m.db"
    with MemoryStore() as store:
        assert store.path == tmp_path / "otra" / "m.db"
    assert (tmp_path / "otra" / "m.db").is_file()


def test_wal_y_version_de_esquema(store: MemoryStore) -> None:
    conn = sqlite3.connect(store.path)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    version = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0]
    assert int(version) == db.SCHEMA_VERSION
    conn.close()


def test_esquema_mas_nuevo_da_error_claro(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    MemoryStore(path).close()
    conn = sqlite3.connect(path)
    conn.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    conn.commit()
    conn.close()
    with pytest.raises(MemoryStoreError, match="schema 99"):
        MemoryStore(path)


def test_un_paso_de_migracion_inyectado_corre_una_vez_y_conserva_los_datos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F8: el mecanismo de migraciones de la memoria, con un esquema 2 de prueba."""
    path = tmp_path / "memory.db"
    with MemoryStore(path) as store:
        saved = _save(store, "Antes de migrar", "Dato del esquema 1.")
    calls: list[int] = []

    def v1_to_v2(conn: sqlite3.Connection) -> None:
        calls.append(1)
        conn.execute("ALTER TABLE observations ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")

    monkeypatch.setattr(db, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(db, "MIGRATIONS", {1: v1_to_v2})
    with MemoryStore(path) as store:
        assert store.get(saved).title == "Antes de migrar"
    with MemoryStore(path) as store:
        assert store.stats().schema_version == 2
    assert calls == [1]
    conn = sqlite3.connect(path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(observations)")]
    conn.close()
    assert "pinned" in columns


def test_un_paso_que_falla_deja_la_base_como_estaba(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "memory.db"
    MemoryStore(path).close()

    def broken(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE pinned (id INTEGER)")
        raise sqlite3.OperationalError("disco lleno")

    monkeypatch.setattr(db, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(db, "MIGRATIONS", {1: broken})
    with pytest.raises(sqlite3.OperationalError, match="disco lleno"):
        MemoryStore(path)
    conn = sqlite3.connect(path)
    version = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0]
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
    conn.close()
    assert version == "1"
    assert "pinned" not in tables


# -- guardar y leer ---------------------------------------------------------------------


def test_save_y_get(store: MemoryStore) -> None:
    result = store.save(
        project=P, title="Usar UUIDv7", content="Las claves nuevas son UUIDv7.", type="decision"
    )
    assert result.action == "created"
    obs = store.get(result.id)
    assert (obs.project, obs.type, obs.title, obs.scope, obs.revision) == (
        P,
        "decision",
        "Usar UUIDv7",
        "project",
        1,
    )
    assert obs.created_at == obs.updated_at
    assert obs.content_hash


def test_upsert_por_topic_key(store: MemoryStore) -> None:
    first = store.save(project=P, title="Perfil", content="v1", topic_key="project/profile")
    same = store.save(project=P, title="Perfil", content="v1", topic_key="project/profile")
    assert (same.id, same.action) == (first.id, "unchanged")
    updated = store.save(project=P, title="Perfil", content="v2", topic_key="project/profile")
    assert (updated.id, updated.action) == (first.id, "updated")
    obs = store.get(first.id)
    assert (obs.content, obs.revision) == ("v2", 2)
    other = store.save(
        project="local/otro", title="Perfil", content="v1", topic_key="project/profile"
    )
    assert other.id != first.id


def test_sin_topic_key_no_duplica_contenido_identico(store: MemoryStore) -> None:
    a = store.save(project=P, title="Gotcha", content="El job corre en UTC.")
    b = store.save(project=P, title="Gotcha", content="El job corre en UTC.")
    assert (b.id, b.action) == (a.id, "unchanged")
    c = store.save(project=P, title="Gotcha", content="El job corre en hora local.")
    assert c.id != a.id


def test_scope_personal_se_ve_desde_cualquier_proyecto(any_store: MemoryStore) -> None:
    _save(any_store, "Preferencia", "Prefiero respuestas cortas con ejemplos.", scope="personal")
    obs = any_store.list(project="local/otro")
    assert [(o.title, o.scope, o.project) for o in obs] == [("Preferencia", "personal", "")]
    assert [h.title for h in any_store.search("respuestas cortas", project=P)] == ["Preferencia"]
    assert any_store.search("respuestas cortas", project=P, scope="project") == []


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [
        ({"title": " "}, "title"),
        ({"content": ""}, "content"),
        ({"scope": "equipo"}, "scope"),
        ({"type": "Decisión!"}, "type"),
        ({"topic_key": "../afuera"}, "topic_key"),
        ({"topic_key": "/absoluta"}, "topic_key"),
        ({"project": ""}, "project"),
        ({"title": "x" * 201}, "title"),
    ],
)
def test_validaciones(store: MemoryStore, kwargs: dict, fragment: str) -> None:
    base = {"project": P, "title": "t", "content": "c"}
    with pytest.raises(MemoryStoreError, match=fragment):
        store.save(**{**base, **kwargs})


def test_get_y_delete(store: MemoryStore) -> None:
    obs_id = _save(store, "Bug", "NPE al cerrar.")
    assert store.delete(obs_id) is True
    assert store.delete(obs_id) is False
    with pytest.raises(NotFoundError, match=str(obs_id)):
        store.get(obs_id)
    assert store.search("NPE") == []


def test_list_ordena_por_recientes_y_filtra(store: MemoryStore) -> None:
    ids = [_save(store, f"t{i}", f"c{i}", type="bugfix" if i % 2 else "decision") for i in range(5)]
    assert [o.id for o in store.list(project=P)] == list(reversed(ids))
    assert [o.id for o in store.list(project=P, type="bugfix")] == [ids[3], ids[1]]
    assert [o.id for o in store.list(project=P, limit=2, offset=1)] == [ids[3], ids[2]]
    assert store.list(project="local/otro") == []


# -- búsqueda -------------------------------------------------------------------------


def test_busqueda_por_identificador_exacto(any_store: MemoryStore) -> None:
    _save(any_store, "Timeout en pagos", "PROJ-1234: el gateway corta a los 30 s.")
    _save(any_store, "Otro ticket", "PROJ-1235 no tiene relación.")
    hits = any_store.search("PROJ-1234")
    assert hits[0].title == "Timeout en pagos"


def test_busqueda_sin_acentos_y_por_varias_palabras(any_store: MemoryStore) -> None:
    _save(any_store, "Migración de esquema", "Las migraciones corren antes del deploy.")
    _save(any_store, "Logs", "Los logs van a stderr.")
    assert [h.title for h in any_store.search("migracion")] == ["Migración de esquema"]
    hits = any_store.search("deploy de logs")
    assert {h.title for h in hits} == {"Migración de esquema", "Logs"}


def test_busqueda_filtra_antes_de_rankear(any_store: MemoryStore) -> None:
    for i in range(15):
        _save(any_store, f"cache {i}", "cache de sesiones", project="local/otro")
    _save(any_store, "cache propio", "cache de sesiones del proyecto")
    hits = any_store.search("cache", project=P, limit=5)
    assert [h.title for h in hits] == ["cache propio"]
    assert any_store.search("cache", project=P, type="decision") == []


def test_preview_truncado_y_get_completo(store: MemoryStore) -> None:
    content = "palabra " * 200
    obs_id = _save(store, "Largo", content)
    hit = store.search("palabra")[0]
    assert len(hit.preview) <= 300
    assert hit.preview.endswith("…")
    assert store.get(obs_id).content == content


def test_consulta_vacia_o_solo_simbolos(any_store: MemoryStore) -> None:
    _save(any_store, "Algo", "contenido")
    assert any_store.search("") == []
    assert any_store.search('"*()') == []


def test_limit(any_store: MemoryStore) -> None:
    for i in range(12):
        _save(any_store, f"nota {i}", "texto repetido")
    assert len(any_store.search("repetido", limit=5)) == 5
    with pytest.raises(MemoryStoreError, match="limit"):
        any_store.search("repetido", limit=0)


# -- contexto ---------------------------------------------------------------------------


def test_contexto_reciente_con_tope(store: MemoryStore) -> None:
    for i in range(30):
        _save(store, f"Decisión {i}", "detalle " * 50, type="decision")
    _save(store, "De otro proyecto", "no va", project="local/otro")
    text = store.context(P, limit=10, max_chars=2000)
    assert len(text) <= 2000
    assert "Decisión 29" in text
    assert "De otro proyecto" not in text
    assert "session summary" in text


def test_contexto_sin_memorias(store: MemoryStore) -> None:
    text = store.context(P)
    assert "no memories" in text


def test_lo_guardado_sin_fts5_se_reindexa_al_abrir_con_fts5(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    with MemoryStore(path) as store:
        _save(store, "Antes", "indexado")
    with MemoryStore(path, fts=False) as store:
        _save(store, "Sin índice", "guardado sin fts")
        store.delete(store.search("indexado")[0].id)
    with MemoryStore(path) as store:
        assert [h.title for h in store.search("fts")] == ["Sin índice"]
        assert store.search("indexado") == []
        assert store.rebuild_fts() == 1
