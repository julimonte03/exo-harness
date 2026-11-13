"""doctor: diagnóstico del entorno, del contenido y de la config del proyecto."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from exo import _meta, content, doctor
from exo.cli import main


def _by_name(checks: list[doctor.Check]) -> dict[str, doctor.Check]:
    return {c.name: c for c in checks}


def test_todo_ok_en_el_entorno_de_desarrollo(tmp_path: Path) -> None:
    checks = _by_name(doctor.run_checks(tmp_path))
    for name in ("python", "version", "content", "filemerge", "snapshots", "disk", "config"):
        assert checks[name].status in ("ok", "info"), (name, checks[name])
    assert checks["version"].detail == f"{_meta.NAME} {_meta.VERSION}"
    assert "packs" in checks["content"].detail
    assert checks["config"].status == "info"


def test_config_con_advertencias(tmp_path: Path) -> None:
    path = tmp_path / _meta.PROJECT_DIR / "config.json"
    path.parent.mkdir()
    path.write_text('{"schema": 1, "specs_dir": "../fuera"}', encoding="utf-8")
    check = _by_name(doctor.run_checks(tmp_path))["config"]
    assert check.status == "warn"
    assert "specs_dir" in check.detail


def test_python_viejo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor.sys, "version_info", (3, 9, 18))
    assert _by_name(doctor.run_checks(tmp_path))["python"].status == "error"


def test_ejecutable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    assert _by_name(doctor.run_checks(tmp_path))["path"].status == "warn"
    other = tmp_path / "otro" / _meta.NAME
    monkeypatch.setattr(doctor.shutil, "which", lambda name: str(other))
    check = _by_name(doctor.run_checks(tmp_path))["path"]
    assert check.status == "warn"
    assert "no es este motor" in check.detail


def test_contenido_ausente(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(content.ENV_VAR, str(tmp_path / "nada"))
    assert _by_name(doctor.run_checks(tmp_path))["content"].status == "error"


def test_disco_lleno(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(doctor.shutil, "disk_usage", lambda path: usage._replace(free=10))
    assert _by_name(doctor.run_checks(tmp_path))["disk"].status == "warn"


def test_autotest_que_falla_se_reporta(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def broken(*args: object, **kwargs: object) -> bytes:
        raise OSError("sin permisos")

    monkeypatch.setattr(doctor.snapshots, "build_archive", broken)
    check = _by_name(doctor.run_checks(tmp_path))["snapshots"]
    assert check.status == "error"
    assert "sin permisos" in check.detail


def test_encoding_no_utf8(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Stream:
        encoding = "cp1252"

    monkeypatch.setattr(doctor.sys, "stdout", Stream())
    check = _by_name(doctor.run_checks(tmp_path))["encoding"]
    assert check.status == "warn"


def test_cli_doctor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "python" in out
    assert "content" in out
    assert main(["doctor", "--project", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert {c["name"] for c in payload["checks"]} >= {"python", "content", "snapshots"}


def test_cli_doctor_con_errores(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(content.ENV_VAR, str(tmp_path / "nada"))
    assert main(["doctor", "--project", str(tmp_path)]) == 1
    assert "error" in capsys.readouterr().out


# -- chequeos de instalación y por agente (F2) ----------------------------------


def _installed(tmp_path: Path, agents: list[str]) -> Path:
    from exo.installer import project

    root = tmp_path / "p"
    root.mkdir()
    project.sync(root, agents=agents)
    return root


def test_install_sin_motor_y_con_drift(tmp_path: Path) -> None:
    assert _by_name(doctor.run_checks(tmp_path))["install"].status == "info"
    root = _installed(tmp_path, ["claude-code"])
    assert _by_name(doctor.run_checks(root))["install"].status == "ok"
    (root / ".claude" / "agents" / "sdd-judge.md").write_bytes(b"tocado")
    check = _by_name(doctor.run_checks(root))["install"]
    assert check.status == "warn"
    assert ".claude/agents/sdd-judge.md (modified)" in check.detail


@pytest.mark.parametrize(
    ("version", "status"),
    [((2, 1, 312), "ok"), ((2, 1, 281), "ok"), ((2, 1, 200), "warn"), (None, "info")],
)
def test_version_de_claude_code_sin_claude_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: tuple[int, ...] | None, status: str
) -> None:
    root = _installed(tmp_path, ["claude-code"])
    monkeypatch.setattr(doctor, "_claude_version", lambda: version)
    check = _by_name(doctor.run_checks(root))["claude-code"]
    assert check.status == status
    if status == "warn":
        assert "--claude-md" in check.detail


def test_claude_code_con_claude_md_o_sin_ser_destino(tmp_path: Path) -> None:
    root = _installed(tmp_path, ["copilot"])
    assert _by_name(doctor.run_checks(root))["claude-code"].status == "info"
    (root / "CLAUDE.md").write_text("# mio\n", encoding="utf-8")
    from exo.installer import project

    project.sync(root, agents=["claude-code"])
    assert _by_name(doctor.run_checks(root))["claude-code"].status == "ok"


def test_lee_la_version_de_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    monkeypatch.setattr(doctor.shutil, "which", lambda name: "/bin/claude")
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="2.1.312 (Claude Code)\n"),
    )
    assert doctor._claude_version() == (2, 1, 312)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    assert doctor._claude_version() is None


def test_confianza_del_workspace_de_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _installed(tmp_path, ["claude-code"])
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(doctor.Path, "home", classmethod(lambda cls: home))
    assert _by_name(doctor.run_checks(root))["claude-trust"].status == "info"
    key = root.resolve().as_posix()
    (home / ".claude.json").write_text(
        json.dumps({"projects": {key: {"hasTrustDialogAccepted": True}}}), encoding="utf-8"
    )
    assert _by_name(doctor.run_checks(root))["claude-trust"].status == "ok"
    (home / ".claude.json").write_text("{ roto", encoding="utf-8")
    assert _by_name(doctor.run_checks(root))["claude-trust"].status == "info"
    (tmp_path / "otro").mkdir()
    other = _installed(tmp_path / "otro", ["copilot"])
    assert (
        _by_name(doctor.run_checks(other))["claude-trust"].detail
        == "no es agente destino del proyecto"
    )


# -- memoria (F3) ----------------------------------------------------------------------


def test_memoria_sin_base_todavia() -> None:
    checks = _by_name(doctor.run_checks(Path(".")))
    assert checks["memory"].status == "info" and "todavía no hay memoria" in checks["memory"].detail
    assert checks["memory-fts5"].status == "ok"
    assert checks["memory-semantic"].status == "info"


def test_memoria_lexica_y_aviso_de_hibrida() -> None:
    from exo.memory.store import MemoryStore

    with MemoryStore() as store:
        store.save(project="local/x", title="t", content="c")
    checks = _by_name(doctor.run_checks(Path(".")))
    assert checks["memory"].status == "ok" and "1 observaciones" in checks["memory"].detail
    assert checks["memory-semantic"].status == "info"
    assert "reindex --provider local" in checks["memory-semantic"].detail


def test_memoria_semantica(monkeypatch: pytest.MonkeyPatch) -> None:
    from _memory_fakes import FakeProvider
    from exo.memory import embeddings
    from exo.memory.backends import sqlite_vec
    from exo.memory.store import MemoryStore

    provider = FakeProvider()
    monkeypatch.setitem(embeddings.FACTORIES, "fake", lambda model, allow_remote: provider)
    with MemoryStore() as store:
        store.save(project="local/x", title="t", content="c")
        store.reindex(provider="fake")
    check = _by_name(doctor.run_checks(Path(".")))["memory-semantic"]
    assert check.status in ("ok", "warn") and "fake:v1" in check.detail
    with monkeypatch.context() as patch:
        # Contexto propio: undo() del monkeypatch general desharía también el aislamiento de
        # la carpeta de datos (conftest) y escribiría en la memoria real.
        patch.setattr(sqlite_vec, "available", lambda: False)
        check = _by_name(doctor.run_checks(Path(".")))["memory-semantic"]
        assert check.status == "warn" and "Python" in check.detail
    provider.fail = True
    with MemoryStore() as store:
        store.save(project="local/x", title="otra", content="sin vector")
    provider.fail = False
    check = _by_name(doctor.run_checks(Path(".")))["memory-semantic"]
    assert check.status == "warn" and "sin vector" in check.detail


def test_memoria_con_proveedor_que_no_se_puede_usar(monkeypatch: pytest.MonkeyPatch) -> None:
    import sqlite3

    from exo import paths
    from exo.memory.store import MemoryStore

    MemoryStore().close()
    conn = sqlite3.connect(paths.memory_db_path())
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [("embedding_provider", "static"), ("embedding_model", "x/y")],
    )
    conn.commit()
    conn.close()
    from exo.memory import embeddings

    monkeypatch.setattr(embeddings, "installed", lambda provider: True)
    check = _by_name(doctor.run_checks(Path(".")))["memory-semantic"]
    assert check.status == "warn" and "model pull static" in check.detail


def test_memoria_de_un_esquema_mas_nuevo_es_error() -> None:
    import sqlite3

    from exo import paths
    from exo.memory.store import MemoryStore

    MemoryStore().close()
    conn = sqlite3.connect(paths.memory_db_path())
    conn.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    conn.commit()
    conn.close()
    assert _by_name(doctor.run_checks(Path(".")))["memory"].status == "error"


def test_memoria_sin_fts5(monkeypatch: pytest.MonkeyPatch) -> None:
    from exo.memory import db

    monkeypatch.setattr(db, "fts5_available", lambda conn: False)
    check = _by_name(doctor.run_checks(Path(".")))["memory-fts5"]
    assert check.status == "warn" and "FTS5" in check.detail


def test_seccion_memory_de_la_config_sin_efecto(tmp_path: Path) -> None:
    path = tmp_path / _meta.PROJECT_DIR / "config.json"
    path.parent.mkdir()
    path.write_text('{"schema": 1, "memory": {"backend": "lexical"}}', encoding="utf-8")
    check = _by_name(doctor.run_checks(tmp_path))["memory-config"]
    assert check.status == "info" and "ADR-0009" in check.detail
    assert _by_name(doctor.run_checks(tmp_path / "otro"))["memory-config"].status == "ok"
