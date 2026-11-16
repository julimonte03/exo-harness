"""R0, inventario determinista de un proyecto existente (F6, ADR-0015).

Lee solo nombres de archivo y manifiestos (nunca el contenido de un archivo de
credenciales) y produce `discovery/inventory.json`:
- lenguajes y líneas;
- manifiestos y dependencias;
- frameworks;
- entrypoints;
- tests, CI, migraciones, contratos de API e infraestructura;
- archivos de config y de credenciales, solo por nombre;
- la carpeta de ADRs.

Los frameworks salen de las dependencias declaradas, con un vocabulario fijo. Los
manifiestos se leen con parsers mínimos con stdlib: `tomllib` no existe en 3.10 y el
resultado no puede depender de la versión de Python.
"""

from __future__ import annotations

import fnmatch
import json
import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import Any

from exo.discovery import files as files_mod
from exo.discovery import store

FILENAME = "inventory.json"

# Vocabulario de frameworks: dependencia declarada -> nombre (ADR-0015).
PYTHON_FRAMEWORKS = {
    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",
    "pydantic": "pydantic",
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic",
    "pytest": "pytest",
}
NODE_FRAMEWORKS = {
    "express": "express",
    "react": "react",
    "vite": "vite",
    "jest": "jest",
    "vitest": "vitest",
    "knex": "knex",
    "typescript": "typescript",
}
TEST_FRAMEWORKS = ("jest", "junit", "pytest", "vitest")
CI_PATTERNS = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    ".circleci/config.yml",
    "bitbucket-pipelines.yml",
)
API_PATTERNS = (
    "openapi*.yaml",
    "openapi*.yml",
    "openapi*.json",
    "swagger*.yaml",
    "swagger*.yml",
    "swagger*.json",
    "*.proto",
    "*.graphql",
    "*.gql",
)
CONFIG_PATTERNS = (
    "application*.yml",
    "application*.yaml",
    "application*.properties",
    "*.ini",
    "*.cfg",
    "*.conf",
    "*.properties",
    ".env.example",
    ".env.sample",
    ".env.template",
    "tsconfig*.json",
    "vite.config.*",
    "jest.config.*",
    "vitest.config.*",
    ".eslintrc*",
    ".prettierrc*",
    "logback*.xml",
)
ADR_DIRS = files_mod.ADR_DIRS
DEFAULT_ADR_DIR = "docs/adr"

_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_TOML_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_TOML_STRING = re.compile(r"\"([^\"]*)\"|'([^']*)'")
_MAIN_GUARD = re.compile(r"^if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", re.MULTILINE)
_SPRING_APP = re.compile(r"@SpringBootApplication\b")
_JAVA_MAIN = re.compile(r"public\s+static\s+void\s+main\s*\(")
_NODE_SCRIPT = re.compile(r"(?:^|[\s;&|])node\s+(?:--\S+\s+)*([^\s;&|]+\.(?:m?js|cjs|ts))")
_HTML_MODULE = re.compile(
    r"<script\b[^>]*\btype=[\"']module[\"'][^>]*\bsrc=[\"']([^\"']+)[\"']"
    r"|<script\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*\btype=[\"']module[\"']",
    re.IGNORECASE,
)
_ARTIFACT = re.compile(r"<artifactId>\s*([^<\s]+)\s*</artifactId>")


def _match(path: str, patterns: tuple[str, ...]) -> bool:
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatchcase(path if "/" in p else name, p) for p in patterns)


def _dep_name(spec: str) -> str | None:
    match = _REQ_NAME.match(spec)
    return match.group(1).lower().replace("_", "-") if match else None


# -- manifiestos --------------------------------------------------------------------------


def _toml_sections(text: str) -> dict[str, list[str]]:
    """Las líneas de cada sección de un TOML, sin comentarios de línea entera."""
    sections: dict[str, list[str]] = {"": []}
    current = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        header = _TOML_SECTION.match(line)
        if header:
            current = header.group(1).strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _toml_strings(lines: list[str]) -> list[str]:
    return [a or b for a, b in _TOML_STRING.findall("\n".join(lines))]


def _toml_array(lines: list[str], key: str) -> list[str]:
    """Los strings del arreglo `key = [ ... ]`, aunque ocupe varias líneas."""
    text = "\n".join(lines)
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\[", text)
    if match is None:
        return []
    found: list[str] = []
    index = match.end()
    while index < len(text):
        char = text[index]
        if char == "]":
            break
        if char == "#":  # comentario hasta el fin de línea
            index = text.find("\n", index)
            index = len(text) if index < 0 else index
            continue
        if char in "\"'":
            close = text.find(char, index + 1)
            if close < 0:
                break
            found.append(text[index + 1 : close])
            index = close + 1
            continue
        index += 1
    return found


def _toml_pairs(lines: list[str]) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*([A-Za-z0-9_.\"'-]+)\s*=\s*[\"']([^\"']*)[\"']", line)
        if match:
            pairs[match.group(1).strip("\"'")] = match.group(2)
    return pairs


def _pyproject(text: str) -> tuple[str | None, list[str], dict[str, str]]:
    sections = _toml_sections(text)
    project = sections.get("project", [])
    name = _toml_pairs(project).get("name")
    deps = list(_toml_array(project, "dependencies"))
    deps += _toml_strings(sections.get("project.optional-dependencies", []))
    poetry = sections.get("tool.poetry.dependencies", []) + sections.get(
        "tool.poetry.group.dev.dependencies", []
    )
    deps += [k for k in _toml_pairs(poetry) if k != "python"]
    deps += [line.split("=")[0].strip() for line in poetry if "=" in line and "{" in line]
    scripts = _toml_pairs(sections.get("project.scripts", []))
    names = sorted({n for n in (_dep_name(d) for d in deps) if n})
    if "tool.pytest.ini_options" in sections and "pytest" not in names:
        names.append("pytest")
    return name, sorted(names), scripts


def _requirements(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith(("-", "git+", "http")):
            name = _dep_name(line)
            if name:
                names.append(name)
    return sorted(set(names))


def _package_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _node_deps(data: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = data.get(key)
        if isinstance(block, dict):
            names |= {str(k) for k in block}
    return sorted(names)


def _maven_deps(text: str) -> list[str]:
    return sorted(set(_ARTIFACT.findall(text)))


def _java_frameworks(artifacts: list[str], build: str) -> set[str]:
    found = {build}
    for artifact in artifacts:
        if artifact.startswith("spring-boot"):
            found.add("spring-boot")
        if artifact == "spring-boot-starter-web" or artifact == "spring-webmvc":
            found.add("spring-web")
        if artifact == "spring-boot-starter-data-jpa" or artifact == "spring-data-jpa":
            found.add("spring-data-jpa")
        if artifact.startswith("junit") or artifact == "spring-boot-starter-test":
            found.add("junit")
        if artifact.startswith("flyway"):
            found.add("flyway")
    return found


def _manifests(
    reader: files_mod.TextReader, paths: list[str]
) -> tuple[list[dict[str, Any]], set[str]]:
    manifests: list[dict[str, Any]] = []
    frameworks: set[str] = set()
    _read = reader.text
    for rel in paths:
        name = PurePosixPath(rel).name
        if name == "pyproject.toml":
            pkg, deps, scripts = _pyproject(_read(rel))
            manifests.append(
                {"path": rel, "ecosystem": "python", "name": pkg, "dependencies": deps}
            )
            frameworks |= {PYTHON_FRAMEWORKS[d] for d in deps if d in PYTHON_FRAMEWORKS}
        elif fnmatch.fnmatchcase(name, "requirements*.txt"):
            deps = _requirements(_read(rel))
            manifests.append(
                {"path": rel, "ecosystem": "python", "name": None, "dependencies": deps}
            )
            frameworks |= {PYTHON_FRAMEWORKS[d] for d in deps if d in PYTHON_FRAMEWORKS}
        elif name == "package.json":
            data = _package_json(_read(rel))
            deps = _node_deps(data)
            pkg = data.get("name") if isinstance(data.get("name"), str) else None
            manifests.append({"path": rel, "ecosystem": "node", "name": pkg, "dependencies": deps})
            frameworks |= {NODE_FRAMEWORKS[d] for d in deps if d in NODE_FRAMEWORKS}
        elif name == "pom.xml":
            deps = _maven_deps(_read(rel))
            manifests.append(
                {"path": rel, "ecosystem": "maven", "name": None, "dependencies": deps}
            )
            frameworks |= _java_frameworks(deps, "maven")
        elif name in ("build.gradle", "build.gradle.kts"):
            text = _read(rel)
            deps = sorted(set(re.findall(r"['\"][\w.-]+:([\w.-]+)(?::[\w.+-]+)?['\"]", text)))
            manifests.append(
                {"path": rel, "ecosystem": "gradle", "name": None, "dependencies": deps}
            )
            frameworks |= _java_frameworks(deps, "gradle")
        elif name == "go.mod":
            text = _read(rel)
            module = re.search(r"(?m)^module\s+(\S+)", text)
            deps = sorted(set(re.findall(r"(?m)^\s*([\w.-]+\.[\w./-]+)\s+v[\w.+-]+", text)))
            manifests.append(
                {
                    "path": rel,
                    "ecosystem": "go",
                    "name": module.group(1) if module else None,
                    "dependencies": deps,
                }
            )
            frameworks.add("go")
        elif name.endswith(".csproj"):
            deps = sorted(set(re.findall(r'PackageReference\s+Include="([^"]+)"', _read(rel))))
            manifests.append(
                {"path": rel, "ecosystem": "dotnet", "name": None, "dependencies": deps}
            )
            frameworks.add("dotnet")
        elif name == "Cargo.toml":
            sections = _toml_sections(_read(rel))
            deps = sorted(
                {
                    line.split("=")[0].strip()
                    for line in sections.get("dependencies", [])
                    if "=" in line
                }
            )
            manifests.append({"path": rel, "ecosystem": "rust", "name": None, "dependencies": deps})
    return sorted(manifests, key=lambda m: m["path"]), frameworks


# -- entrypoints ----------------------------------------------------------------------------


def _script_target(base: PurePosixPath, target: str, existing: set[str]) -> str | None:
    """`pkg.cli:main` -> `src/pkg/cli.py` o `pkg/cli.py`, relativos al pyproject."""
    module = target.split(":", 1)[0].strip()
    if not module:
        return None
    parts = module.split(".")
    for root in ("src", ""):
        for candidate in ("/".join(parts) + ".py", "/".join(parts) + "/__init__.py"):
            path = (base / root / candidate) if root else (base / candidate)
            rel = posixpath.normpath(path.as_posix())
            if rel in existing:
                return rel
    return None


def _node_path(base: PurePosixPath, target: str, existing: set[str]) -> str | None:
    """Un archivo de un `package.json` o de un `index.html`, relativo a su carpeta."""
    rel = posixpath.normpath((base / target).as_posix())
    if rel.startswith("../"):
        return None
    if rel in existing:
        return rel
    for ext in (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"):
        if rel + ext in existing:
            return rel + ext
    return None


def _entrypoints(
    reader: files_mod.TextReader, fileset: files_mod.FileSet, manifests: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    existing = {f.path for f in fileset.files}
    found: dict[str, set[str]] = {}
    _read = reader.text

    def add(path: str | None, kind: str) -> None:
        if path:
            found.setdefault(path, set()).add(kind)

    for item in fileset.files:
        if item.category != "code":
            continue
        name = PurePosixPath(item.path).name
        if item.language == "python":
            if name == "__main__.py":
                add(item.path, "python-main")
            if _MAIN_GUARD.search(_read(item.path)):
                add(item.path, "main-guard")
        elif item.language == "java":
            text = _read(item.path)
            if _SPRING_APP.search(text):
                add(item.path, "spring-boot")
            elif _JAVA_MAIN.search(text):
                add(item.path, "java-main")
    for manifest in manifests:
        base = PurePosixPath(manifest["path"]).parent
        if manifest["ecosystem"] == "python" and manifest["path"].endswith("pyproject.toml"):
            _, _, scripts = _pyproject(_read(manifest["path"]))
            for target in scripts.values():
                add(_script_target(base, target, existing), "console-script")
        if manifest["ecosystem"] == "node":
            data = _package_json(_read(manifest["path"]))
            main = data.get("main")
            if isinstance(main, str):
                add(_node_path(base, main, existing), "node-main")
            bins = data.get("bin")
            for target in (bins.values() if isinstance(bins, dict) else [bins]) if bins else []:
                if isinstance(target, str):
                    add(_node_path(base, target, existing), "node-bin")
            scripts = data.get("scripts")
            for command in scripts.values() if isinstance(scripts, dict) else []:
                if isinstance(command, str):
                    for target in _NODE_SCRIPT.findall(command):
                        add(_node_path(base, target, existing), "node-script")
    for item in fileset.files:
        if PurePosixPath(item.path).name == "index.html":
            base = PurePosixPath(item.path).parent
            for a, b in _HTML_MODULE.findall(_read(item.path)):
                src = a or b
                if "://" not in src:
                    target = src.lstrip("/")
                    add(_node_path(base, target, existing), "html-module")
    return [{"path": p, "kinds": sorted(k)} for p, k in sorted(found.items())]


# -- inventario -----------------------------------------------------------------------------


def _adr_dir(paths: list[str]) -> tuple[str, bool]:
    """La carpeta de ADRs del proyecto. Los recuperados no están en `paths` (se excluyen),
    así que escribirlos no la "crea"."""
    for folder in ADR_DIRS:
        if any(p.startswith(folder + "/") and p.endswith(".md") for p in paths):
            return folder, True
    return DEFAULT_ADR_DIR, False


def build(project: Path, fileset: files_mod.FileSet | None = None) -> dict[str, Any]:
    project = Path(project)
    fileset = fileset or files_mod.list_files(project)
    paths = [f.path for f in fileset.files]
    languages: dict[str, dict[str, int]] = {}
    categories: dict[str, int] = {}
    for item in fileset.files:
        categories[item.category] = categories.get(item.category, 0) + 1
        if item.language and not item.sensitive:
            entry = languages.setdefault(item.language, {"files": 0, "lines": 0})
            entry["files"] += 1
            entry["lines"] += item.lines
    readable = [f.path for f in fileset.files if not f.sensitive]
    reader = files_mod.TextReader(project)
    manifests, frameworks = _manifests(reader, readable)
    if any(PurePosixPath(p).name.startswith("tsconfig") for p in readable):
        frameworks.add("typescript")
    if any(PurePosixPath(p).name == "conftest.py" for p in readable):
        frameworks.add("pytest")
    if any(PurePosixPath(p).name == "alembic.ini" for p in readable):
        frameworks.add("alembic")
    tests = [f.path for f in fileset.files if f.category == "test"]
    adr_dir, adr_exists = _adr_dir(paths)
    entrypoints = _entrypoints(reader, fileset, manifests)
    return {
        "files": {
            "analyzed": len(fileset.files),
            "excluded": dict(sorted(fileset.excluded.items())),
            "git": fileset.git,
        },
        "languages": dict(sorted(languages.items())),
        "categories": dict(sorted(categories.items())),
        "manifests": manifests,
        "frameworks": sorted(frameworks),
        "entrypoints": entrypoints,
        "tests": {
            "frameworks": sorted(f for f in frameworks if f in TEST_FRAMEWORKS),
            "files": tests,
        },
        "ci": [p for p in readable if _match(p, CI_PATTERNS)],
        "migrations": [f.path for f in fileset.files if f.category == "migration"],
        "api_contracts": [p for p in readable if _match(p, API_PATTERNS)],
        "infrastructure": [p for p in readable if _infrastructure(p)],
        "config_files": [p for p in readable if _match(p, CONFIG_PATTERNS)],
        "sensitive_files": [f.path for f in fileset.files if f.sensitive],
        "adr_dir": adr_dir,
        "adr_dir_exists": adr_exists,
        "warnings": [*fileset.warnings, *reader.warnings],
    }


def _infrastructure(path: str) -> bool:
    pure = PurePosixPath(path)
    name = pure.name
    return (
        name == "Dockerfile"
        or name.startswith("Dockerfile.")
        or fnmatch.fnmatchcase(name, "docker-compose*.yml")
        or fnmatch.fnmatchcase(name, "docker-compose*.yaml")
        or name.endswith(".tf")
        or name == "Chart.yaml"
        or "k8s" in pure.parts[:-1]
    )


def write(project: Path) -> tuple[dict[str, Any], bool]:
    """Arma el inventario y lo escribe en `discovery/inventory.json`. Devuelve (datos, escribió)."""
    data = build(project)
    return data, store.write_json(project, FILENAME, data)
