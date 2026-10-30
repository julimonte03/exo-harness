"""core/config: `.exo/config.json` con defaults silenciosos, saneo y migraciones."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from exo import _meta
from exo.core import config
from exo.core.config import ConfigError


def _write(project: Path, payload: object) -> Path:
    path = project / _meta.PROJECT_DIR / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    path.write_text(text, encoding="utf-8")
    return path


def test_sin_archivo_usa_defaults_sin_advertencias(tmp_path: Path) -> None:
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert result.warnings == []
    assert result.source is None


def test_defaults_esperados() -> None:
    cfg = config.defaults()
    assert cfg["schema"] == config.CURRENT_SCHEMA == 1
    assert cfg["specs_dir"] == "specs"
    assert cfg["tracker"] == {"type": "none", "prefix": None, "prefixes": []}
    assert cfg["mcp"] == {"enabled": False}
    assert cfg["memory"]["embeddings"]["allow_remote"] is False
    assert cfg["governance"]["protected_branches"] == ["main", "master", "prod", "production"]


def test_defaults_son_copias_independientes() -> None:
    a = config.defaults()
    a["agents"].append("x")
    assert config.defaults()["agents"] == []


def test_config_valida_completa(tmp_path: Path) -> None:
    payload = {
        "schema": 1,
        "project": {"name": "mi-servicio", "chat_language": "es", "artifact_language": "en"},
        "agents": ["claude-code", "copilot"],
        "packs": ["core", "sdd", "quality", "security"],
        "tracker": {"type": "jira", "prefix": "PROJ", "prefixes": ["OPS"]},
        "specs_dir": "docs/specs",
        "memory": {
            "backend": "auto",
            "embeddings": {"provider": "local", "model": None, "allow_remote": False},
        },
        "governance": {
            "protected_branches": ["main"],
            "roles": {"tech_lead": ["ana"], "developer": []},
            "dpa_profile": "legacy-profile",
            "githooks": True,
        },
        "discovery": {"ignore": ["vendor/"], "depth": "deep"},
        "mcp": {"enabled": True},
    }
    path = _write(tmp_path, payload)
    result = config.load(tmp_path)
    assert result.warnings == []
    assert result.config == payload
    assert result.source == path


def test_json_invalido_da_defaults_y_advertencia(tmp_path: Path) -> None:
    _write(tmp_path, "{ esto no es json")
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert len(result.warnings) == 1
    assert "no es JSON válido" in result.warnings[0]


def test_raiz_que_no_es_objeto(tmp_path: Path) -> None:
    _write(tmp_path, [1, 2])
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert "objeto JSON" in result.warnings[0]


def test_campo_invalido_vuelve_a_su_default_y_el_resto_se_conserva(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "schema": 1,
            "tracker": {"type": "jira", "prefix": "proj", "prefixes": ["OK1", "mal", 3]},
            "specs_dir": "mis-specs",
            "mcp": {"enabled": "si"},
        },
    )
    result = config.load(tmp_path)
    assert result.config["tracker"] == {"type": "jira", "prefix": None, "prefixes": ["OK1"]}
    assert result.config["specs_dir"] == "mis-specs"
    assert result.config["mcp"] == {"enabled": False}
    joined = "\n".join(result.warnings)
    assert "tracker.prefix" in joined
    assert "tracker.prefixes[1]" in joined
    assert "tracker.prefixes[2]" in joined
    assert "mcp.enabled" in joined


@pytest.mark.parametrize(
    "bad",
    ["../fuera", "/abs/specs", "C:\\specs", "D:/specs", "\\\\srv\\share", "", 7],
)
def test_specs_dir_inseguro(tmp_path: Path, bad: object) -> None:
    _write(tmp_path, {"schema": 1, "specs_dir": bad})
    result = config.load(tmp_path)
    assert result.config["specs_dir"] == "specs"
    assert any("specs_dir" in w for w in result.warnings)


def test_specs_dir_se_normaliza(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1, "specs_dir": "./docs\\specs/"})
    assert config.load(tmp_path).config["specs_dir"] == "docs/specs"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"agents": ["Claude Code"]}, "agents[0]"),
        ({"packs": "core"}, "packs"),
        ({"project": {"chat_language": "español"}}, "project.chat_language"),
        ({"tracker": {"type": "trello"}}, "tracker.type"),
        ({"memory": {"backend": "redis"}}, "memory.backend"),
        ({"memory": {"embeddings": {"allow_remote": "no"}}}, "memory.embeddings.allow_remote"),
        ({"memory": {"embeddings": {"provider": "magia"}}}, "memory.embeddings.provider"),
        ({"governance": {"protected_branches": [""]}}, "governance.protected_branches[0]"),
        ({"governance": {"roles": {"tech_lead": "ana"}}}, "governance.roles.tech_lead"),
        ({"governance": {"githooks": 1}}, "governance.githooks"),
        ({"discovery": {"depth": "infinita"}}, "discovery.depth"),
        ({"project": "x"}, "project"),
    ],
)
def test_validaciones_por_campo(tmp_path: Path, payload: dict, field: str) -> None:
    _write(tmp_path, {"schema": 1, **payload})
    result = config.load(tmp_path)
    assert any(w.startswith(field) for w in result.warnings), result.warnings


def test_agentes_y_packs_sin_duplicados(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1, "agents": ["cursor", "cursor", "codex"]})
    assert config.load(tmp_path).config["agents"] == ["cursor", "codex"]


def test_claves_desconocidas_se_conservan_con_advertencia(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1, "extra": {"a": 1}, "tracker": {"type": "none", "nota": "x"}})
    result = config.load(tmp_path)
    assert result.config["extra"] == {"a": 1}
    assert result.config["tracker"]["nota"] == "x"
    assert any("extra" in w for w in result.warnings)
    assert any("tracker.nota" in w for w in result.warnings)


def test_sin_campo_schema(tmp_path: Path) -> None:
    _write(tmp_path, {"specs_dir": "s"})
    result = config.load(tmp_path)
    assert result.config["specs_dir"] == "s"
    assert any("schema" in w for w in result.warnings)


def test_esquema_futuro_desconocido_da_defaults(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 99, "specs_dir": "otra"})
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert any("esquema 99" in w for w in result.warnings)


def test_migraciones_encadenadas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def v1_to_v2(raw: dict) -> dict:
        raw = copy.deepcopy(raw)
        raw["specs_dir"] = raw.pop("specs_folder", "specs")
        raw["schema"] = 2
        return raw

    monkeypatch.setattr(config, "CURRENT_SCHEMA", 2)
    monkeypatch.setattr(config, "MIGRATIONS", {1: v1_to_v2})
    _write(tmp_path, {"schema": 1, "specs_folder": "legacy"})
    result = config.load(tmp_path)
    assert result.config["schema"] == 2
    assert result.config["specs_dir"] == "legacy"
    assert any("migrada del esquema 1 al 2" in w for w in result.warnings)


def test_migracion_faltante(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CURRENT_SCHEMA", 3)
    monkeypatch.setattr(config, "MIGRATIONS", {})
    _write(tmp_path, {"schema": 1, "specs_dir": "x"})
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert any("no hay migración" in w for w in result.warnings)


def test_save_y_load_ida_y_vuelta(tmp_path: Path) -> None:
    cfg = config.defaults()
    cfg["agents"] = ["claude-code"]
    cfg["tracker"] = {"type": "github", "prefix": None, "prefixes": []}
    assert config.save(tmp_path, cfg) is True
    assert config.load(tmp_path).config == cfg
    raw = (tmp_path / _meta.PROJECT_DIR / "config.json").read_bytes()
    assert raw.endswith(b"}\n")
    assert b"\r\n" not in raw


def test_save_es_idempotente(tmp_path: Path) -> None:
    cfg = config.defaults()
    assert config.save(tmp_path, cfg) is True
    assert config.save(tmp_path, cfg) is False


def test_save_rechaza_config_invalida(tmp_path: Path) -> None:
    cfg = config.defaults()
    cfg["specs_dir"] = "../fuera"
    with pytest.raises(ConfigError, match="specs_dir"):
        config.save(tmp_path, cfg)
    assert not (tmp_path / _meta.PROJECT_DIR / "config.json").exists()


def test_save_no_pisa_una_config_de_esquema_mas_nuevo(tmp_path: Path) -> None:
    path = _write(tmp_path, {"schema": 99, "algo": "del futuro"})
    loaded = config.load(tmp_path)
    with pytest.raises(ConfigError, match="esquema 99"):
        config.save(tmp_path, loaded.config)
    assert json.loads(path.read_text(encoding="utf-8")) == {"schema": 99, "algo": "del futuro"}
