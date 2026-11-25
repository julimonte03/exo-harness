"""Repo sintético grande para las metas de rendimiento (F8), con historia determinista.

`build` arma un monorepo de tres paquetes con código que se importa entre carpetas:
- **Python** (`pyproject.toml`, `src/shop/<área>/`, `tests/`), alrededor del 40 %;
- **TypeScript** (`web/package.json`, `web/tsconfig.json`, `web/src/<área>/`), el 35 %;
- **Java** (`api/pom.xml`, `api/src/main/java/...`, `api/src/test/java/...`), el 25 %.

Cada archivo importa dos de otras áreas, así el grafo de R1 tiene aristas de verdad, y
hay entrypoints (un `__main__`, un `@SpringBootApplication`, el `main` del
`package.json`) y CI, como en un proyecto real. El contenido es sintético: nombres de
un comercio ficticio, sin datos reales. Todo sale de los índices: dos corridas con los
mismos parámetros dan los mismos bytes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from _git import Commit, init_repo

AREAS = (
    "billing",
    "catalog",
    "checkout",
    "customers",
    "delivery",
    "inventory",
    "loyalty",
    "notifications",
    "orders",
    "payments",
    "pricing",
    "reports",
    "returns",
    "search",
    "shipping",
    "stores",
    "suppliers",
    "taxes",
    "users",
    "warehouse",
)
FILE_LINES = 100  # líneas por archivo de código, aproximadas
SHARES = (("python", 0.40), ("typescript", 0.35), ("java", 0.25))
_STEMS = ("service", "model", "rules", "store", "handler", "mapper", "client", "policy")


@dataclass(frozen=True)
class SyntheticRepo:
    root: Path
    lines: int  # líneas de código y de tests escritas, como las cuenta `count_lines`
    files: int


def _name(index: int) -> str:
    return f"{_STEMS[index % len(_STEMS)]}_{index // len(_STEMS)}"


def _camel(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def _peers(area: int, index: int) -> list[tuple[str, str]]:
    """Las dos (área, archivo) de otras carpetas que importa un archivo."""
    count = len(AREAS)
    return [
        (AREAS[(area + 1) % count], _name(index)),
        (AREAS[(area + 7) % count], _name(index + 1)),
    ]


def _pad(lines: list[str], block: Callable[[int], list[str]], target: int) -> list[str]:
    """Agrega bloques (`block(i)` da una lista de líneas) hasta llegar a `target` líneas."""
    i = 0
    while len(lines) < target:
        lines += block(i)
        i += 1
    return lines


def _python(area: int, index: int, target: int) -> str:
    here = AREAS[area]
    lines = [
        f'"""{here}: {_name(index)} (synthetic)."""',
        "",
        "from __future__ import annotations",
        "",
    ]
    lines += ["import json", "from dataclasses import dataclass", ""]
    for other, name in _peers(area, index):
        lines.append(f"from shop.{other}.{name} import compute_0 as {other}_{name}")
    lines += ["", ""]

    def block(i: int) -> list[str]:
        return [
            f"def compute_{i}(value: int, factor: int = {i + 1}) -> int:",
            f'    """Step {i} of the {here} flow."""',
            "    total = value * factor",
            "    if total > 1000:",
            "        return total - factor",
            "    return json.loads(json.dumps(total + 1))",
            "",
            "",
        ]

    lines = _pad(lines, block, target - 6)
    lines += [
        "@dataclass",
        f"class {_camel(_name(index))}:",
        "    code: str",
        "    amount: int = 0",
        "",
    ]
    return "\n".join(lines) + "\n"


def _typescript(area: int, index: int, target: int) -> str:
    here = AREAS[area]
    lines = [f"// {here}: {_name(index)} (synthetic)."]
    for other, name in _peers(area, index):
        lines.append(f'import {{ compute0 as {other}_{name} }} from "../{other}/{name}";')
    lines += [
        "",
        f"export interface {_camel(_name(index))} {{",
        "  code: string;",
        "  amount: number;",
        "}",
        "",
    ]

    def block(i: int) -> list[str]:
        return [
            f"export function compute{i}(value: number, factor = {i + 1}): number {{",
            f"  // Step {i} of the {here} flow.",
            "  const total = value * factor;",
            "  if (total > 1000) {",
            "    return total - factor;",
            "  }",
            "  return total + 1;",
            "}",
            "",
        ]

    return "\n".join(_pad(lines, block, target)) + "\n"


def _java(area: int, index: int, target: int, *, test: bool = False) -> str:
    here = AREAS[area]
    cls = _camel(_name(index)) + ("Test" if test else "")
    lines = [f"package com.example.shop.{here};", ""]
    for other, name in _peers(area, index):
        lines.append(f"import com.example.shop.{other}.{_camel(name)};")
    lines += ["import java.util.List;", ""]
    if area == 0 and index == 0 and not test:
        lines.append("@SpringBootApplication")
    lines += [f"public class {cls} {{", ""]
    if area == 0 and index == 0 and not test:
        lines += ["    public static void main(String[] args) {", "    }", ""]

    def block(i: int) -> list[str]:
        return [
            f"    public int compute{i}(int value) {{",
            f"        // Step {i} of the {here} flow.",
            f"        int total = value * {i + 1};",
            "        if (total > 1000) {",
            f"            return total - {i + 1};",
            "        }",
            "        return List.of(total + 1).get(0);",
            "    }",
            "",
        ]

    return "\n".join(_pad(lines, block, target - 1) + ["}"]) + "\n"


def _python_test(area: int) -> str:
    here = AREAS[area]
    lines = [f"from shop.{here}.{_name(0)} import compute_0", "", ""]

    def block(i: int) -> list[str]:
        return [f"def test_compute_{i}() -> None:", f"    assert compute_0({i}) >= {i}", "", ""]

    return "\n".join(_pad(lines, block, FILE_LINES // 2)) + "\n"


def _typescript_test(area: int) -> str:
    here = AREAS[area]
    lines = [f'import {{ compute0 }} from "../{here}/{_name(0)}";', ""]

    def block(i: int) -> list[str]:
        return [
            f'test("compute {i}", () => {{',
            f"  expect(compute0({i})).toBeGreaterThan(0);",
            "});",
            "",
        ]

    return "\n".join(_pad(lines, block, FILE_LINES // 2)) + "\n"


_FIXED = {
    "README.md": "# Shop\n\nSynthetic monorepo for performance tests.\n",
    "pyproject.toml": (
        "[project]\n"
        'name = "shop"\n'
        'version = "0.1.0"\n'
        'dependencies = ["fastapi>=0.110", "pydantic>=2", "sqlalchemy>=2"]\n'
        "\n"
        "[project.optional-dependencies]\n"
        'dev = ["pytest>=8"]\n'
        "\n"
        "[project.scripts]\n"
        'shop = "shop.cli:main"\n'
    ),
    "src/shop/__init__.py": "",
    "src/shop/__main__.py": "from shop.cli import main\n\nmain()\n",
    "src/shop/cli.py": (
        "import sys\n\n\ndef main() -> int:\n    return 0\n\n\n"
        'if __name__ == "__main__":\n    sys.exit(main())\n'
    ),
    "tests/conftest.py": "import pytest\n",
    "web/package.json": (
        "{\n"
        '  "name": "shop-web",\n'
        '  "main": "src/index.ts",\n'
        '  "scripts": {"start": "node dist/index.js", "test": "vitest"},\n'
        '  "dependencies": {"react": "^18.3.1", "express": "^4.19.2"},\n'
        '  "devDependencies": {"typescript": "^5.4.5", "vitest": "^1.6.0", "vite": "^5.2.0"}\n'
        "}\n"
    ),
    "web/tsconfig.json": '{\n  "compilerOptions": {"strict": true, "baseUrl": "."}\n}\n',
    "web/src/index.ts": 'export { compute0 } from "./orders/service_0";\n',
    "api/pom.xml": (
        "<project>\n"
        "  <artifactId>shop-api</artifactId>\n"
        "  <dependencies>\n"
        "    <dependency><artifactId>spring-boot-starter-web</artifactId></dependency>\n"
        "    <dependency><artifactId>spring-boot-starter-test</artifactId></dependency>\n"
        "  </dependencies>\n"
        "</project>\n"
    ),
    ".github/workflows/ci.yml": "name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
    "Dockerfile": "FROM python:3.12-slim\nCOPY . /app\n",
    ".gitignore": "node_modules/\n__pycache__/\n",
}


def files(lines: int = 50_000) -> dict[str, str]:
    """Las rutas y el texto del repo, sin escribir nada: unas `lines` líneas en total."""
    tree = dict(_FIXED)
    for language, share in SHARES:
        count = max(1, round(lines * share / FILE_LINES))
        for n in range(count):
            area, index = n % len(AREAS), n // len(AREAS)
            here = AREAS[area]
            if language == "python":
                tree[f"src/shop/{here}/__init__.py"] = ""
                tree[f"src/shop/{here}/{_name(index)}.py"] = _python(area, index, FILE_LINES)
            elif language == "typescript":
                tree[f"web/src/{here}/{_name(index)}.ts"] = _typescript(area, index, FILE_LINES)
            else:
                folder = f"api/src/main/java/com/example/shop/{here}"
                tree[f"{folder}/{_camel(_name(index))}.java"] = _java(area, index, FILE_LINES)
        tests = max(1, count // 10)
        for n in range(tests):
            area = n % len(AREAS)
            here = AREAS[area]
            if language == "python":
                tree[f"tests/test_{here}_{n}.py"] = _python_test(area)
            elif language == "typescript":
                tree[f"web/src/__tests__/{here}_{n}.test.ts"] = _typescript_test(area)
            else:
                folder = f"api/src/test/java/com/example/shop/{here}"
                tree[f"{folder}/{_camel(_name(n))}Test.java"] = _java(
                    area, n, FILE_LINES // 2, test=True
                )
    return tree


def _history(tree: dict[str, str], commits: int) -> list[Commit]:
    """Commits chicos sobre archivos de código, para que churn y ownership tengan datos."""
    code = sorted(p for p in tree if p.endswith((".py", ".ts", ".java")) and tree[p])
    authors = ("Ana Base", "Bruno Dev", "Carla Ops")
    history = []
    for i in range(commits):
        path = code[(i * 37) % len(code)]
        history.append(
            Commit(
                f"2026-02-{1 + i % 27:02d}T10:00:00+00:00",
                authors[i % len(authors)],
                f"feat: change {i}",
                {
                    path: tree[path]
                    + ("# touched\n" if path.endswith(".py") else "// touched\n") * (i + 1)
                },
            )
        )
    return history


def build(target: Path, *, lines: int = 50_000, commits: int = 6) -> SyntheticRepo:
    """Escribe el repo en `target` (con LF) y le da una historia de git determinista."""
    tree = files(lines)
    for rel, text in tree.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    history = _history(tree, commits)
    init_repo(target, history=history)
    final = dict(tree)
    for commit in history:
        final.update(commit.files)
    counted = [t for p, t in final.items() if p.endswith((".py", ".ts", ".java"))]
    total = sum(t.count("\n") for t in counted)
    return SyntheticRepo(target, total, len(final))
