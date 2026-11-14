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
    assert cfg["schema"] == config.CURRENT_SCHEMA == 2
    assert cfg["specs_dir"] == "specs"
    assert cfg["tickets"] == {"pattern": None, "example": None}
    assert "tracker" not in cfg
    assert cfg["sdd"] == {"persistence": "filesystem", "mode": "interactive"}
    assert cfg["project"]["chat_language"] is None
    assert cfg["mcp"] == {"enabled": False}
    assert cfg["memory"]["embeddings"]["allow_remote"] is False
    assert cfg["governance"]["protected_branches"] == ["main", "master", "prod", "production"]


def test_defaults_son_copias_independientes() -> None:
    a = config.defaults()
    a["agents"].append("x")
    assert config.defaults()["agents"] == []


def test_config_valida_completa(tmp_path: Path) -> None:
    payload = {
        "schema": 2,
        "project": {"name": "mi-servicio", "chat_language": "es", "artifact_language": "en"},
        "agents": ["claude-code", "copilot"],
        "packs": ["core", "sdd", "quality", "security"],
        "tickets": {"pattern": r"(?:PROJ|OPS)-\d+", "example": "PROJ-123"},
        "specs_dir": "docs/specs",
        "sdd": {"persistence": "hybrid", "mode": "auto"},
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
    assert "is not valid JSON" in result.warnings[0]


def test_raiz_que_no_es_objeto(tmp_path: Path) -> None:
    _write(tmp_path, [1, 2])
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert "JSON object" in result.warnings[0]


def test_campo_invalido_vuelve_a_su_default_y_el_resto_se_conserva(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "schema": 2,
            "tickets": {"pattern": "(", "example": "X-1"},
            "specs_dir": "mis-specs",
            "mcp": {"enabled": "si"},
        },
    )
    result = config.load(tmp_path)
    assert result.config["tickets"] == {"pattern": None, "example": None}
    assert result.config["specs_dir"] == "mis-specs"
    assert result.config["mcp"] == {"enabled": False}
    joined = "\n".join(result.warnings)
    assert "tickets.pattern" in joined
    assert "tickets.example" in joined
    assert "mcp.enabled" in joined


@pytest.mark.parametrize(
    "bad",
    ["../fuera", "/abs/specs", "C:\\specs", "D:/specs", "\\\\srv\\share", "", 7],
)
def test_specs_dir_inseguro(tmp_path: Path, bad: object) -> None:
    _write(tmp_path, {"schema": 2, "specs_dir": bad})
    result = config.load(tmp_path)
    assert result.config["specs_dir"] == "specs"
    assert any("specs_dir" in w for w in result.warnings)


def test_specs_dir_se_normaliza(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 2, "specs_dir": "./docs\\specs/"})
    assert config.load(tmp_path).config["specs_dir"] == "docs/specs"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"agents": ["Claude Code"]}, "agents[0]"),
        ({"packs": "core"}, "packs"),
        ({"project": {"chat_language": "español"}}, "project.chat_language"),
        ({"tickets": {"pattern": r"\d*"}}, "tickets.pattern"),
        ({"tickets": {"pattern": r"#\d+", "example": "PROJ-1"}}, "tickets.example"),
        ({"tickets": {"example": "PROJ-1"}}, "tickets.example"),
        ({"tickets": "PROJ"}, "tickets"),
        ({"sdd": {"persistence": "nube"}}, "sdd.persistence"),
        ({"sdd": {"mode": "a veces"}}, "sdd.mode"),
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
    _write(tmp_path, {"schema": 2, **payload})
    result = config.load(tmp_path)
    assert any(w.startswith(field) for w in result.warnings), result.warnings


def test_agentes_y_packs_sin_duplicados(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 2, "agents": ["cursor", "cursor", "codex"]})
    assert config.load(tmp_path).config["agents"] == ["cursor", "codex"]


def test_claves_desconocidas_se_conservan_con_advertencia(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 2, "extra": {"a": 1}, "tickets": {"pattern": None, "nota": "x"}})
    result = config.load(tmp_path)
    assert result.config["extra"] == {"a": 1}
    assert result.config["tickets"]["nota"] == "x"
    assert any("extra" in w for w in result.warnings)
    assert any("tickets.nota" in w for w in result.warnings)


def test_sin_campo_schema(tmp_path: Path) -> None:
    _write(tmp_path, {"specs_dir": "s"})
    result = config.load(tmp_path)
    assert result.config["specs_dir"] == "s"
    assert any("schema" in w for w in result.warnings)


def test_esquema_futuro_desconocido_da_defaults(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 99, "specs_dir": "otra"})
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert any("schema 99" in w for w in result.warnings)


def test_migraciones_encadenadas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def v2_to_v3(raw: dict) -> dict:
        raw = copy.deepcopy(raw)
        raw["specs_dir"] = raw.pop("specs_folder", "specs")
        raw["schema"] = 3
        return raw

    monkeypatch.setattr(config, "CURRENT_SCHEMA", 3)
    monkeypatch.setattr(config, "MIGRATIONS", {**config.MIGRATIONS, 2: v2_to_v3})
    _write(tmp_path, {"schema": 1, "specs_folder": "legacy", "tracker": {"type": "github"}})
    result = config.load(tmp_path)
    assert result.config["schema"] == 3
    assert result.config["specs_dir"] == "legacy"
    assert result.config["tickets"]["pattern"] == r"#\d+"
    assert any("migrated from schema 1 to 3" in w for w in result.warnings)


@pytest.mark.parametrize(
    ("tracker", "tickets"),
    [
        ({"type": "none", "prefix": None, "prefixes": []}, {"pattern": None, "example": None}),
        ({"type": "none", "prefix": "PROJ"}, {"pattern": None, "example": None}),
        ({"type": "jira", "prefix": "PROJ", "prefixes": []}, {"pattern": r"PROJ-\d+", "example": "PROJ-123"}),
        (
            {"type": "jira", "prefix": "PROJ", "prefixes": ["OPS", "PROJ", "mal"]},
            {"pattern": r"(?:PROJ|OPS)-\d+", "example": "PROJ-123"},
        ),
        ({"type": "linear", "prefixes": ["ENG"]}, {"pattern": r"ENG-\d+", "example": "ENG-123"}),
        ({"type": "jira"}, {"pattern": r"[A-Z][A-Z0-9]*-\d+", "example": "PROJ-123"}),
        ({"type": "linear", "prefix": None}, {"pattern": r"[A-Z][A-Z0-9]*-\d+", "example": "PROJ-123"}),
        ({"type": "github"}, {"pattern": r"#\d+", "example": "#123"}),
        ({"type": "gitlab", "prefix": None, "prefixes": []}, {"pattern": r"#\d+", "example": "#123"}),
        ({"type": "trello"}, {"pattern": None, "example": None}),
        ("jira", {"pattern": None, "example": None}),
    ],
)
def test_migracion_del_tracker_al_patron(tmp_path: Path, tracker: object, tickets: dict) -> None:
    """ADR-0012: el tracker de lista cerrada del esquema 1 pasa a un patrón."""
    _write(tmp_path, {"schema": 1, "agents": ["claude-code"], "tracker": tracker})
    result = config.load(tmp_path)
    assert result.config["tickets"] == tickets
    assert "tracker" not in result.config
    assert result.config["agents"] == ["claude-code"]
    assert result.invalid == []
    assert any("migrated from schema 1 to 2" in w for w in result.warnings)


def test_migracion_sin_tracker_y_con_tickets_ya_puestos(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1})
    assert config.load(tmp_path).config["tickets"] == {"pattern": None, "example": None}
    _write(tmp_path, {"schema": 1, "tracker": {"type": "jira"}, "tickets": {"pattern": r"#\d+"}})
    assert config.load(tmp_path).config["tickets"] == {"pattern": r"#\d+", "example": None}


def test_save_de_una_config_migrada_escribe_el_esquema_2(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1, "tracker": {"type": "jira", "prefix": "PROJ"}})
    loaded = config.load(tmp_path)
    assert config.save(tmp_path, loaded.config) is True
    raw = json.loads((tmp_path / _meta.PROJECT_DIR / "config.json").read_text(encoding="utf-8"))
    assert raw["schema"] == 2
    assert raw["tickets"] == {"pattern": r"PROJ-\d+", "example": "PROJ-123"}
    assert "tracker" not in raw


def test_migracion_faltante(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CURRENT_SCHEMA", 3)
    monkeypatch.setattr(config, "MIGRATIONS", {})
    _write(tmp_path, {"schema": 2, "specs_dir": "x"})
    result = config.load(tmp_path)
    assert result.config == config.defaults()
    assert any("no migration" in w for w in result.warnings)


def test_save_y_load_ida_y_vuelta(tmp_path: Path) -> None:
    cfg = config.defaults()
    cfg["agents"] = ["claude-code"]
    cfg["tickets"] = {"pattern": r"#\d+", "example": "#123"}
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
    with pytest.raises(ConfigError, match="schema 99"):
        config.save(tmp_path, loaded.config)
    assert json.loads(path.read_text(encoding="utf-8")) == {"schema": 99, "algo": "del futuro"}


@pytest.mark.parametrize(
    "raw",
    ["{ esto no es json", "[1, 2]", '{"schema": 99}', '{"schema": "uno"}'],
    ids=["json-roto", "no-objeto", "esquema-futuro", "esquema-invalido"],
)
def test_load_marca_cuando_no_pudo_usar_el_archivo(tmp_path: Path, raw: str) -> None:
    config.config_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    config.config_path(tmp_path).write_text(raw, encoding="utf-8")
    result = config.load(tmp_path)
    assert result.fallback is True
    assert result.invalid == []


def test_load_lista_los_campos_invalidos(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 2, "agents": "claude-code", "specs_dir": "s"})
    result = config.load(tmp_path)
    assert result.fallback is False
    assert [problem.split(":")[0] for problem in result.invalid] == ["agents"]
    assert result.config["specs_dir"] == "s"


def test_load_valido_no_marca_nada(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 2, "extra": True})
    result = config.load(tmp_path)
    assert (result.fallback, result.invalid) == (False, [])
    assert config.load(tmp_path / "otro").fallback is False
