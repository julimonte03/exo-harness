"""installer/stack: señales de stack y packs sugeridos (fixtures sintéticos)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exo import _meta
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


def test_monorepo_con_workspaces_detecta_el_frontend_del_paquete(tmp_path: Path) -> None:
    """F7: `node-shop` tenía react en `packages/web/package.json` y no se detectaba."""
    _write(tmp_path, "package.json", json.dumps({"private": True, "workspaces": ["packages/*"]}))
    _write(tmp_path, "packages/web/package.json", json.dumps({"dependencies": {"react": "^19"}}))
    _write(tmp_path, "packages/api/package.json", json.dumps({"dependencies": {"express": "^5"}}))
    report = detect_stack(tmp_path)
    assert report.signals["frontend"] == ["packages/web/package.json: react"]
    assert report.signals["backend-js"] == ["packages/api/package.json: express"]
    assert "frontend" in report.suggested


@pytest.mark.parametrize(
    ("rel", "text", "signal"),
    [
        ("services/billing/pom.xml", "<artifactId>spring-boot</artifactId>", "spring-boot"),
        ("backend/pyproject.toml", '[project]\ndependencies = ["django"]\n', "backend-python"),
        ("deploy/api/Dockerfile", "FROM scratch\n", "docker"),
        ("infra/k8s/deploy.yaml", "kind: Deployment\n", "infra"),
    ],
)
def test_manifiestos_en_subcarpetas(tmp_path: Path, rel: str, text: str, signal: str) -> None:
    _write(tmp_path, rel, text)
    assert detect_stack(tmp_path).has(signal)


def test_no_mira_terceros_ni_mas_alla_de_la_profundidad(tmp_path: Path) -> None:
    react = json.dumps({"dependencies": {"react": "^19"}})
    _write(tmp_path, "node_modules/some-lib/package.json", react)
    _write(tmp_path, "a/b/c/d/package.json", react)
    _write(tmp_path, f"{_meta.PROJECT_DIR}/x/package.json", react)
    assert not detect_stack(tmp_path).has("frontend")


@pytest.mark.parametrize("with_git", [True, False])
@pytest.mark.parametrize(
    ("fixture", "expected", "absent"),
    [
        ("py-invoices", {"python", "ops"}, {"java", "frontend"}),
        ("toy-python", {"python"}, {"java", "frontend"}),
        ("java-library", {"java"}, {"python", "frontend"}),
        ("node-shop", {"frontend"}, {"java", "python"}),
    ],
)
def test_criterio_4_cada_fixture_sugiere_su_pack(
    tmp_path: Path, fixture: str, expected: set[str], absent: set[str], with_git: bool
) -> None:
    """Criterio 4 de F7: la detección sobre los fixtures de cada stack (port de curate)."""
    import shutil

    from _git import FIXTURES, init_repo

    if with_git and shutil.which("git") is None:
        pytest.skip("requiere git")
    root = tmp_path / fixture
    if with_git:
        init_repo(root, fixture=fixture)
    else:
        shutil.copytree(FIXTURES / fixture, root)
    suggested = set(detect_stack(root).suggested)
    assert expected <= suggested, suggested
    assert not absent & suggested, suggested
    assert {"core", "sdd", "quality", "security"} <= suggested


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
