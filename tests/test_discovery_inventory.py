"""R0, inventario (F6, ADR-0015): qué detecta y que sea determinista."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import exo
from _git import init_repo
from exo.discovery import inventory, store

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")

TREE = {
    "pyproject.toml": """[project]
name = "invoices"
dependencies = [
    "fastapi>=0.110",
    "pydantic[email]>=2",
    "SQLAlchemy==2.0.30",
]

[project.optional-dependencies]
dev = ["pytest>=8", "alembic"]

[project.scripts]
invoices = "invoices.cli:main"
""",
    "src/invoices/__init__.py": "",
    "src/invoices/__main__.py": "from .cli import main\n\nmain()\n",
    "src/invoices/cli.py": "def main():\n    return 0\n",
    "src/invoices/tools/report.py": "def run():\n    pass\n\n\nif __name__ == '__main__':\n    run()\n",
    "tests/test_cli.py": "def test_main():\n    assert True\n",
    "alembic/versions/0001_init.py": "def upgrade():\n    pass\n",
    "web/package.json": json.dumps(
        {
            "name": "@shop/web",
            "main": "./src/index.js",
            "bin": {"shop": "bin/shop.js"},
            "scripts": {"start": "node src/server.js", "test": "vitest"},
            "dependencies": {"react": "^18", "express": "^4"},
            "devDependencies": {"vitest": "^1", "typescript": "^5"},
        }
    ),
    "web/src/index.js": "module.exports = {};\n",
    "web/src/server.js": "require('./index');\n",
    "web/bin/shop.js": "#!/usr/bin/env node\n",
    "web/index.html": '<html><script type="module" src="/src/main.tsx"></script></html>\n',
    "web/src/main.tsx": "export {};\n",
    "web/tsconfig.json": "{}\n",
    "lib/pom.xml": "<project><dependencies><dependency><artifactId>spring-boot-starter-web</artifactId></dependency>"
    "<dependency><artifactId>flyway-core</artifactId></dependency></dependencies></project>\n",
    "lib/src/main/java/com/example/App.java": "@SpringBootApplication\npublic class App {\n  public static void main(String[] a) {}\n}\n",
    "lib/src/test/java/com/example/AppTest.java": "class AppTest {}\n",
    ".github/workflows/ci.yml": "on: push\n",
    "azure-pipelines.yml": "steps: []\n",
    "Dockerfile": "FROM python:3.12\n",
    "deploy/k8s/app.yaml": "kind: Deployment\n",
    "api/openapi.yaml": "openapi: 3.0.0\n",
    "proto/orders.proto": 'syntax = "proto3";\n',
    "config/application.yml": "server: {}\n",
    ".env": "TOKEN=never-read\n",
    "doc/adr/0001-use-fastapi.md": "# 1. Use FastAPI\n",
}


def _tree(root: Path) -> Path:
    for rel, text in TREE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return root


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = _tree(tmp_path / "repo")
    if shutil.which("git"):
        init_repo(root)
    return root


def test_inventario_de_un_proyecto_mixto(repo: Path) -> None:
    data = inventory.build(repo)
    assert {"python", "javascript", "typescript", "java"} <= set(data["languages"])
    assert data["languages"]["python"]["files"] == 6
    expected = {"fastapi", "pydantic", "sqlalchemy", "pytest", "alembic", "react", "express"}
    expected |= {"vitest", "typescript", "spring-boot", "spring-web", "flyway", "maven"}
    assert expected <= set(data["frameworks"])
    entry = {e["path"]: e["kinds"] for e in data["entrypoints"]}
    assert entry == {
        "lib/src/main/java/com/example/App.java": ["spring-boot"],
        "src/invoices/__main__.py": ["python-main"],
        "src/invoices/cli.py": ["console-script"],
        "src/invoices/tools/report.py": ["main-guard"],
        "web/bin/shop.js": ["node-bin"],
        "web/src/index.js": ["node-main"],
        "web/src/main.tsx": ["html-module"],
        "web/src/server.js": ["node-script"],
    }
    assert data["tests"]["files"] == [
        "lib/src/test/java/com/example/AppTest.java",
        "tests/test_cli.py",
    ]
    assert data["tests"]["frameworks"] == ["pytest", "vitest"]
    assert data["ci"] == [".github/workflows/ci.yml", "azure-pipelines.yml"]
    assert data["migrations"] == ["alembic/versions/0001_init.py"]
    assert data["api_contracts"] == ["api/openapi.yaml", "proto/orders.proto"]
    assert data["infrastructure"] == ["Dockerfile", "deploy/k8s/app.yaml"]
    assert "config/application.yml" in data["config_files"]
    assert data["sensitive_files"] == [".env"]
    assert (data["adr_dir"], data["adr_dir_exists"]) == ("doc/adr", True)
    [py] = [m for m in data["manifests"] if m["path"] == "pyproject.toml"]
    assert py["name"] == "invoices"
    assert py["dependencies"] == ["alembic", "fastapi", "pydantic", "pytest", "sqlalchemy"]


def test_no_lee_el_archivo_de_credenciales(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from exo.core import fsutil

    real = fsutil.read_bytes
    real_text = fsutil.read_text_auto

    def guard(path: Path) -> bytes:
        assert Path(path).name != ".env", "the credentials file was read"
        return real(path)

    def guard_text(path: Path) -> str:
        assert Path(path).name != ".env", "the credentials file was read"
        return real_text(path)

    monkeypatch.setattr(fsutil, "read_bytes", guard)
    monkeypatch.setattr(fsutil, "read_text_auto", guard_text)
    assert inventory.build(repo)["sensitive_files"] == [".env"]


def test_sin_carpeta_de_adrs_el_default(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    data = inventory.build(root)
    assert (data["adr_dir"], data["adr_dir_exists"]) == ("docs/adr", False)


@needs_git
def test_criterio_1_el_inventario_es_determinista(repo: Path) -> None:
    """Dos corridas en subprocesos con PYTHONHASHSEED distinto dan bytes idénticos."""
    src = str(Path(exo.__file__).resolve().parents[1])
    outputs = []
    for seed in ("1", "4242"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": src}
        code = "import sys; from exo.discovery import inventory; inventory.write(sys.argv[1])"
        subprocess.run([sys.executable, "-c", code, str(repo)], check=True, env=env)
        outputs.append((store.root(repo) / inventory.FILENAME).read_bytes())
    assert outputs[0] == outputs[1]
    data = json.loads(outputs[0])
    assert data["schema"] == store.SCHEMA
    _, written = inventory.write(repo)
    assert written is False
