"""Detección del stack del proyecto para sugerir packs.

Lee solo manifiestos conocidos y nunca contenido que pueda tener secretos. Los
packs sugeridos que todavía no existen en el contenido se informan como
pendientes. `pyproject.toml` se revisa como texto porque `tomllib` no existe en
Python 3.10.

Los manifiestos se buscan también en subcarpetas, hasta `MAX_DEPTH` carpetas por
debajo de la raíz (F7): en un monorepo, react vive en `packages/web/package.json`.
La lista sale de `discovery.files.project_names`, sin la carpeta del motor ni lo de
terceros o de build, y nunca se sigue un link. Lo que está dentro de una carpeta de
muestra (`SAMPLE_DIRS`: ejemplos, fixtures, tests, docs) no cuenta: un ejemplo en
React no hace un proyecto de frontend.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from exo.core import fsutil
from exo.discovery import files

ALWAYS = ("core", "sdd")
MAX_DEPTH = 3
# Carpetas de muestra: sus manifiestos no son el stack del proyecto (sin distinguir mayúsculas).
SAMPLE_DIRS = frozenset({"examples", "example", "samples", "fixtures", "test", "tests", "docs"})
_DOCKER = ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml")
_PY_MANIFESTS = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile")
_JVM_MANIFESTS = ("pom.xml", "build.gradle", "build.gradle.kts")
_PY_BACKEND = re.compile(r"\b(fastapi|flask|django|starlette|aiohttp)\b", re.IGNORECASE)
_JS_BACKEND = ("express", "@nestjs/core", "koa", "fastify", "hapi")
_JS_FRONTEND = ("react", "vue", "@angular/core", "svelte", "next", "nuxt")


@dataclass
class StackReport:
    signals: dict[str, list[str]] = field(default_factory=dict)  # señal -> evidencia
    suggested: list[str] = field(default_factory=list)
    # Packs que se muestran pero no se preseleccionan (D-33): con --yes no se instalan.
    offered: list[str] = field(default_factory=list)

    def has(self, name: str) -> bool:
        return name in self.signals


def _read(path: Path) -> str:
    if fsutil.is_link(path):
        return ""
    try:
        # `utf-8-sig`: un manifiesto guardado con BOM (editores de Windows) también es JSON.
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _package_deps(path: Path) -> set[str]:
    try:
        data = json.loads(_read(path))
    except ValueError:
        return set()
    if not isinstance(data, dict):
        return set()
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = data.get(key)
        if isinstance(value, dict):
            deps |= set(value)
    return deps


def _by_name(project: Path) -> dict[str, list[str]]:
    """Nombre de archivo -> rutas (relativas, con /) hasta `MAX_DEPTH` carpetas de hondo,
    fuera de las carpetas de muestra."""
    found: dict[str, list[str]] = {}
    for rel in files.project_names(project):
        folders = PurePosixPath(rel).parts[:-1]
        if len(folders) <= MAX_DEPTH and not any(f.lower() in SAMPLE_DIRS for f in folders):
            found.setdefault(PurePosixPath(rel).name, []).append(rel)
    return found


def detect_stack(project: Path) -> StackReport:
    project = Path(project)
    report = StackReport()
    names = _by_name(project)
    every = [rel for paths in names.values() for rel in paths]

    def mark(name: str, evidence: str) -> None:
        if evidence not in report.signals.get(name, []):
            report.signals.setdefault(name, []).append(evidence)

    for rel in sorted(names.get("package.json", [])):
        mark("node", rel)
        deps = _package_deps(project / rel)
        for dep in _JS_BACKEND:
            if dep in deps:
                mark("backend-js", f"{rel}: {dep}")
        for dep in _JS_FRONTEND:
            if dep in deps:
                mark("frontend", f"{rel}: {dep}")
    py_text = ""
    for name in _PY_MANIFESTS:
        for rel in sorted(names.get(name, [])):
            mark("python", rel)
            py_text += _read(project / rel)
    for match in sorted({m.lower() for m in _PY_BACKEND.findall(py_text)}):
        mark("backend-python", f"dependency {match}")
    jvm_text = ""
    for name in _JVM_MANIFESTS:
        for rel in sorted(names.get(name, [])):
            mark("jvm", rel)
            jvm_text += _read(project / rel)
    if "spring-boot" in jvm_text:
        mark("spring-boot", "spring-boot in the build")
    if "spring-boot-starter-security" in jvm_text or "spring-security" in jvm_text:
        mark("spring-security", "spring-security in the build")
    if "data-jpa" in jvm_text or "jakarta.persistence" in jvm_text or "hibernate" in jvm_text:
        mark("jpa", "JPA in the build")
    for name in _DOCKER:
        for rel in sorted(names.get(name, [])):
            mark("docker", rel)
    if any(rel.endswith(".tf") or "terraform" in rel.split("/")[:-1] for rel in every):
        mark("infra", "terraform")
    if "Chart.yaml" in names or any("k8s" in rel.split("/")[:-1] for rel in every):
        mark("infra", "kubernetes")
    report.suggested = _suggest(report)
    if files.has_code(project):
        report.offered = ["discovery"]
    return report


def _suggest(report: StackReport) -> list[str]:
    suggested = list(ALWAYS)

    def add(pack: str) -> None:
        if pack not in suggested:
            suggested.append(pack)

    code = any(report.has(s) for s in ("node", "python", "jvm"))
    if code:
        add("quality")
        add("security")
    if report.has("frontend"):
        add("frontend")
    if report.has("jvm"):
        add("java")
    if report.has("python"):
        add("python")
    if report.has("docker") or report.has("infra"):
        add("ops")
    return suggested
