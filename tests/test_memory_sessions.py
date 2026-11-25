"""memory: sesiones, proyectos (lista, merge, consolidate), stats y export/import."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from exo.memory import exchange
from exo.memory.store import MemoryStore, MemoryStoreError, NotFoundError

P = "github.com/acme/api"


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    with MemoryStore(tmp_path / "memory.db") as opened:
        yield opened


# -- sesiones ---------------------------------------------------------------------------


def test_sesion_completa(store: MemoryStore) -> None:
    session = store.session_start(P, agent="claude-code")
    assert session.ended_at is None
    store.save(project=P, title="Decisión", content="Usar colas.", session_id=session.id)
    store.session_summary(P, "Se eligió usar colas; falta el retry.", session_id=session.id)
    ended = store.session_end(session.id)
    assert ended.ended_at is not None
    shown = store.session_show(session.id)
    assert shown.session.summary == "Se eligió usar colas; falta el retry."
    assert [o.title for o in shown.observations] == ["Decisión"]
    summary_hit = store.search("retry", project=P)[0]
    assert summary_hit.type == "session-summary"
    assert summary_hit.topic_key == f"session/{session.id}"


def test_resumen_sin_sesion_abierta_crea_una(store: MemoryStore) -> None:
    result = store.session_summary(P, "Resumen suelto.")
    shown = store.session_show()
    assert shown.session.id == result.session_id
    assert shown.session.summary == "Resumen suelto."


def test_resumen_usa_la_sesion_abierta_mas_reciente(store: MemoryStore) -> None:
    store.session_start(P)
    newer = store.session_start(P)
    store.session_start("local/otro")
    assert store.session_summary(P, "va a la nueva").session_id == newer.id


def test_session_show_y_end_inexistentes(store: MemoryStore) -> None:
    with pytest.raises(NotFoundError):
        store.session_show(99)
    with pytest.raises(NotFoundError):
        store.session_end(99)
    with pytest.raises(NotFoundError, match="no sessions"):
        store.session_show()


def test_el_contexto_incluye_el_ultimo_resumen(store: MemoryStore) -> None:
    store.session_summary(P, "Quedó pendiente el retry de pagos.")
    assert "Quedó pendiente el retry de pagos." in store.context(P)


# -- proyectos y stats --------------------------------------------------------------------


def test_projects_list_con_conteos(store: MemoryStore) -> None:
    store.register_project(P, remote="https://github.com/acme/api.git", path=Path("C:/code/api"))
    store.save(project=P, title="a", content="1")
    store.save(project=P, title="b", content="2")
    store.save(project="local/otro", title="c", content="3")
    listed = {p.name: p for p in store.projects_list()}
    assert listed[P].observations == 2
    assert listed[P].remote == "https://github.com/acme/api.git"
    assert listed["local/otro"].observations == 1


def test_merge_mueve_todo_y_resuelve_topic_keys_repetidos(store: MemoryStore) -> None:
    store.save(
        project="old/api", title="Perfil viejo", content="v-old", topic_key="project/profile"
    )
    store.save(project=P, title="Perfil nuevo", content="v-new", topic_key="project/profile")
    store.save(project="old/api", title="Bug", content="NPE")
    store.session_start("old/api")
    result = store.projects_merge("old/api", P)
    assert (result.moved, result.conflicts) == (1, 1)
    titles = sorted(o.title for o in store.list(P))
    assert titles == ["Bug", "Perfil nuevo"]
    assert store.list("old/api", scope="project") == []
    assert "old/api" not in {p.name for p in store.projects_list()}
    assert store.session_show().session.project == P


def test_merge_conserva_el_mas_reciente(store: MemoryStore) -> None:
    store.save(project=P, title="Perfil", content="viejo", topic_key="project/profile")
    store.save(project="old/api", title="Perfil", content="nuevo", topic_key="project/profile")
    store.projects_merge("old/api", P)
    assert [o.content for o in store.list(P)] == ["nuevo"]
    assert store.search("nuevo", project=P)[0].project == P


def test_merge_con_la_misma_hora_conserva_el_ultimo_escrito(
    store: MemoryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """En Windows antes de 3.13 el reloj tiene unos 15 ms de resolución: dos escrituras
    seguidas tendrían la misma hora. La hora del store crece siempre dentro del proceso."""
    from exo.memory import store as module

    frozen = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(module, "_clock", lambda: frozen)
    stamps = [module.now() for _ in range(3)]
    assert stamps == sorted(set(stamps))  # estrictamente creciente con el reloj quieto
    store.save(project=P, title="Perfil", content="viejo", topic_key="project/profile")
    store.save(project="old/api", title="Perfil", content="nuevo", topic_key="project/profile")
    store.projects_merge("old/api", P)
    assert [o.content for o in store.list(P)] == ["nuevo"]
    # Y al revés: el último escrito está en el destino.
    store.save(project="otro/api", title="Perfil", content="más viejo", topic_key="project/profile")
    store.save(project=P, title="Perfil", content="el último", topic_key="project/profile")
    store.projects_merge("otro/api", P)
    assert [o.content for o in store.list(P)] == ["el último"]


def test_merge_invalido(store: MemoryStore) -> None:
    with pytest.raises(MemoryStoreError, match="itself"):
        store.projects_merge(P, P)
    with pytest.raises(NotFoundError):
        store.projects_merge("no/existe", P)


def test_consolidate_une_variantes_del_mismo_remoto(store: MemoryStore) -> None:
    store.save(project="https://github.com/Acme/Api.git", title="a", content="1")
    store.save(project="GitHub.com/acme/api", title="b", content="2")
    store.save(project=P, title="c", content="3")
    store.save(project="local/otro", title="d", content="4")
    preview = store.projects_consolidate(dry_run=True)
    assert preview == {P: ["GitHub.com/acme/api", "https://github.com/Acme/Api.git"]}
    assert len(store.projects_list()) == 4
    assert store.projects_consolidate() == preview
    assert sorted(p.name for p in store.projects_list()) == ["github.com/acme/api", "local/otro"]
    assert len(store.list(P)) == 3


def test_stats(store: MemoryStore) -> None:
    store.save(project=P, title="a", content="1", type="decision")
    store.save(project=P, title="b", content="2", type="bugfix")
    store.save(project="", title="c", content="3", scope="personal")
    store.session_start(P)
    stats = store.stats()
    assert stats.observations == 3
    assert stats.by_type == {"bugfix": 1, "decision": 1, "note": 1}
    assert stats.by_project[P] == 2
    assert stats.sessions == 1
    assert stats.fts is True
    assert stats.size_bytes > 0


# -- export / import ------------------------------------------------------------------------


def test_export_import_ida_y_vuelta(store: MemoryStore, tmp_path: Path) -> None:
    session = store.session_start(P)
    store.save(
        project=P,
        title="Decisión",
        content="Usar colas.",
        type="decision",
        topic_key="arq/colas",
        session_id=session.id,
    )
    store.save(project="", title="Preferencia", content="Respuestas cortas.", scope="personal")
    store.save(project="local/otro", title="Otro", content="de otro proyecto")
    data = exchange.export(store)
    assert data["format"] == exchange.FORMAT
    assert sorted(o["title"] for o in data["observations"]) == ["Decisión", "Otro", "Preferencia"]
    text = json.dumps(data)
    with MemoryStore(tmp_path / "otra.db") as other:
        result = exchange.import_(other, json.loads(text))
        assert (result.created, result.updated, result.unchanged, result.skipped) == (3, 0, 0, 0)
        imported = other.get(other.search("colas")[0].id)
        original = store.get(store.search("colas")[0].id)
        assert (imported.topic_key, imported.created_at, imported.updated_at) == (
            "arq/colas",
            original.created_at,
            original.updated_at,
        )
        assert other.list("", scope="personal")[0].title == "Preferencia"
        again = exchange.import_(other, json.loads(text))
        assert (again.created, again.unchanged) == (0, 3)


def test_export_de_un_proyecto_no_lleva_lo_personal(store: MemoryStore) -> None:
    store.save(project=P, title="Decisión", content="Usar colas.")
    store.save(project="", title="Preferencia", content="Respuestas cortas.", scope="personal")
    assert [o["title"] for o in exchange.export(store, project=P)["observations"]] == ["Decisión"]
    assert [o["title"] for o in exchange.export(store, scope="personal")["observations"]] == [
        "Preferencia"
    ]


def test_import_no_pisa_algo_mas_nuevo(store: MemoryStore) -> None:
    store.save(project=P, title="Perfil", content="viejo", topic_key="project/profile")
    data = exchange.export(store, project=P)
    store.save(project=P, title="Perfil", content="nuevo", topic_key="project/profile")
    result = exchange.import_(store, data)
    assert result.skipped == 1
    assert store.list(P)[0].content == "nuevo"


def test_import_a_otro_proyecto(store: MemoryStore) -> None:
    store.save(project=P, title="Bug", content="NPE")
    data = exchange.export(store, project=P)
    exchange.import_(store, data, project="local/copia")
    assert [o.title for o in store.list("local/copia", scope="project")] == ["Bug"]


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        ({"format": "otro"}, "format"),
        ({"format": exchange.FORMAT, "schema": 99, "observations": []}, "schema"),
        (
            {"format": exchange.FORMAT, "schema": 1, "observations": [{"title": "x"}]},
            re.escape("observations[0]"),
        ),
        (
            {
                "format": exchange.FORMAT,
                "schema": 1,
                "observations": [{"project": "p", "title": "t", "content": "c", "scope": "equipo"}],
            },
            "scope",
        ),
    ],
)
def test_import_invalido_no_escribe_nada(store: MemoryStore, data: dict, fragment: str) -> None:
    with pytest.raises(MemoryStoreError, match=fragment):
        exchange.import_(store, data)
    assert store.stats().observations == 0


def test_import_con_la_misma_fecha_y_otro_contenido_conserva_lo_local(store: MemoryStore) -> None:
    store.save(project=P, title="Perfil", content="local", topic_key="project/profile")
    local = store.list(P)[0]
    data = exchange.export(store, project=P)
    data["observations"][0]["content"] = "importado"
    data["observations"][0]["updated_at"] = local.updated_at
    assert exchange.import_(store, data).skipped == 1
    assert store.list(P)[0].content == "local"
