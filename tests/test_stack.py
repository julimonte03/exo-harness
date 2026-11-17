"""installer/stack: señales de stack y packs sugeridos (fixtures sintéticos)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo.installer import stack
from exo.installer.stack import detect_stack


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_proyecto_vacio_sugiere_solo_la_base(tmp_path: Path) -> None:
    report = detect_stack(tmp_path)
    assert report.signals == {}
    assert report.suggested == ["core", "sdd"]


def test_node_con_react_y_express(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "package.json",
        json.dumps(
            {"dependencies": {"react": "^19", "express": "^5"}, "devDependencies": {"vite": "x"}}
        ),
    )
    report = detect_stack(tmp_path)
    assert {"node", "frontend", "backend-js"} <= set(report.signals)
    assert report.suggested == ["core", "sdd", "quality", "security", "frontend"]


def test_python_con_fastapi(tmp_path: Path) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\ndependencies = ["FastAPI>=0.110", "pydantic"]\n')
    report = detect_stack(tmp_path)
    assert report.signals["backend-python"] == ["dependency fastapi"]
    assert report.suggested == ["core", "sdd", "quality", "security", "python"]


def test_spring_boot_con_security_y_jpa(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pom.xml",
        "<dependency><artifactId>spring-boot-starter-security</artifactId></dependency>"
        "<dependency><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>",
    )
    report = detect_stack(tmp_path)
    assert {"jvm", "spring-boot", "spring-security", "jpa"} <= set(report.signals)
    assert "java" in report.suggested


@pytest.mark.parametrize(
    "rel", ["Dockerfile", "compose.yaml", "main.tf", "k8s/deploy.yaml", "Chart.yaml"]
)
def test_infra_sugiere_ops(tmp_path: Path, rel: str) -> None:
    _write(tmp_path, rel, "x")
    assert "ops" in detect_stack(tmp_path).suggested


def test_package_json_roto_no_rompe(tmp_path: Path) -> None:
    _write(tmp_path, "package.json", "{ roto")
    report = detect_stack(tmp_path)
    assert report.signals == {"node": ["package.json"]}
    _write(tmp_path, "package.json", "[1]")
    assert detect_stack(tmp_path).signals == {"node": ["package.json"]}


def test_discovery_se_ofrece_solo_si_el_repo_ya_tiene_codigo(tmp_path: Path) -> None:
    """D-33: se ofrece, no se sugiere (lo sugerido se instala con --yes)."""
    assert stack.detect_stack(tmp_path).offered == []
    _write(tmp_path, "node_modules/x/index.js", "module.exports = 1;\n")
    assert stack.detect_stack(tmp_path).offered == []
    _write(tmp_path, "src/app/main.py", "print('hi')\n")
    report = stack.detect_stack(tmp_path)
    assert report.offered == ["discovery"]
    assert "discovery" not in report.suggested


def test_el_wizard_ofrece_discovery_sin_preseleccionarlo() -> None:
    from exo.installer import wizard

    report = stack.StackReport(suggested=["core", "sdd"], offered=["discovery"])
    lines: list[str] = []
    answers = iter(["", "", ""])
    choices = wizard.choose(
        [], report, ["core", "sdd", "discovery"], ask=lambda _q: next(answers), out=lines.append
    )
    assert choices.packs == ["core", "sdd"]
    assert any("discovery" in line and "--packs" in line for line in lines)
