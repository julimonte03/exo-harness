"""core/waivers: excepciones aprobadas y vigentes para datos personales (D-12, ADR-0014)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from exo import _meta
from exo.core import scan, waivers

TODAY = date(2026, 11, 15)
OK = {
    "detector": "ar-dni",
    "path": "tests/fixtures/**",
    "reason": "synthetic DNIs for the parser tests",
    "approved_by": "ana",
    "expires": "2027-01-31",
}


def _write(project: Path, data: object) -> Path:
    path = project / _meta.PROJECT_DIR / waivers.FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


def _finding(kind: str = "ar-dni", level: str = scan.RESTRICTED) -> scan.Finding:
    return scan.Finding(3, kind, level, "3012…")


def test_sin_archivo_no_hay_waivers(tmp_path: Path) -> None:
    loaded = waivers.load(tmp_path, today=TODAY)
    assert (loaded.active, loaded.expired, loaded.problems) == ([], [], [])


def test_un_waiver_vigente_cubre_su_detector_y_su_ruta(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1, "waivers": [OK]})
    loaded = waivers.load(tmp_path, today=TODAY)
    assert len(loaded.active) == 1
    assert waivers.covers(loaded, _finding(), "tests/fixtures/people/dni.csv") is not None
    assert waivers.covers(loaded, _finding(), "src/app.py") is None
    assert waivers.covers(loaded, _finding("card"), "tests/fixtures/x.csv") is None


def test_un_secreto_nunca_tiene_waiver(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1, "waivers": [{**OK, "detector": "card"}]})
    loaded = waivers.load(tmp_path, today=TODAY)
    assert waivers.covers(loaded, _finding("card", scan.CRITICAL), "tests/fixtures/x") is None


def test_vencido_no_cubre_y_se_informa(tmp_path: Path) -> None:
    _write(tmp_path, {"schema": 1, "waivers": [{**OK, "expires": "2026-11-14"}]})
    loaded = waivers.load(tmp_path, today=TODAY)
    assert loaded.active == [] and len(loaded.expired) == 1
    assert waivers.covers(loaded, _finding(), "tests/fixtures/a") is None


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        ("{ roto", "not valid JSON"),
        ({"waivers": [{**OK, "detector": "passport"}]}, "detector"),
        ({"waivers": [{k: v for k, v in OK.items() if k != "reason"}]}, "reason"),
        ({"waivers": [{**OK, "expires": "31/01/2027"}]}, "expires"),
    ],
)
def test_waivers_invalidos_se_informan_y_no_cubren(
    tmp_path: Path, data: object, fragment: str
) -> None:
    _write(tmp_path, data)
    loaded = waivers.load(tmp_path, today=TODAY)
    assert loaded.active == []
    assert any(fragment in p for p in loaded.problems), loaded.problems


def test_el_esquema_conoce_los_mismos_detectores_que_el_escaner() -> None:
    schema = json.loads(waivers.SCHEMA_FILE.read_text(encoding="utf-8"))
    detector = schema["properties"]["waivers"]["items"]["properties"]["detector"]
    assert tuple(detector["enum"]) == scan.KNOWN_PII


def test_una_entrada_invalida_no_anula_las_demas(tmp_path: Path) -> None:
    _write(tmp_path, {"waivers": [OK, {**OK, "detector": "passport"}]})
    loaded = waivers.load(tmp_path, today=TODAY)
    assert len(loaded.active) == 1
    assert any("waivers[1]" in p and "detector" in p for p in loaded.problems), loaded.problems


def test_un_archivo_ilegible_se_informa_sin_traceback(tmp_path: Path) -> None:
    (tmp_path / _meta.PROJECT_DIR / waivers.FILENAME).mkdir(parents=True)
    loaded = waivers.load(tmp_path, today=TODAY)
    assert loaded.active == [] and loaded.problems


def test_el_vencido_que_cubriria_se_nombra(tmp_path: Path) -> None:
    _write(tmp_path, {"waivers": [{**OK, "expires": "2026-11-14"}]})
    loaded = waivers.load(tmp_path, today=TODAY)
    old = waivers.expired_for(loaded, _finding(), "tests/fixtures/a")
    assert old is not None and old.expires == date(2026, 11, 14)
    assert waivers.expired_for(loaded, _finding(), "src/a.py") is None
