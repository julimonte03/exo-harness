"""Detección del stack del proyecto para sugerir packs (port de `StackSignals` de curate).

Lee solo manifiestos conocidos y nunca contenido que pueda tener secretos. Los
packs sugeridos que todavía no existen en el contenido se informan como
pendientes (llegan en F7). `pyproject.toml` se revisa como texto porque
`tomllib` no existe en Python 3.10.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from exo.discovery import files

ALWAYS = ("core", "sdd")
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
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _package_deps(project: Path) -> set[str]:
    try:
        data = json.loads((project / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = data.get(key)
        if isinstance(value, dict):
            deps |= set(value)
    return deps


def detect_stack(project: Path) -> StackReport:
    project = Path(project)
    report = StackReport()

    def mark(name: str, evidence: str) -> None:
        report.signals.setdefault(name, []).append(evidence)

    if (project / "package.json").is_file():
        mark("node", "package.json")
        deps = _package_deps(project)
        for dep in _JS_BACKEND:
            if dep in deps:
                mark("backend-js", f"package.json: {dep}")
        for dep in _JS_FRONTEND:
            if dep in deps:
                mark("frontend", f"package.json: {dep}")
    py_text = ""
    for name in _PY_MANIFESTS:
        if (project / name).is_file():
            mark("python", name)
            py_text += _read(project / name)
    for match in sorted({m.lower() for m in _PY_BACKEND.findall(py_text)}):
        mark("backend-python", f"dependency {match}")
    jvm_text = ""
    for name in _JVM_MANIFESTS:
        if (project / name).is_file():
            mark("jvm", name)
            jvm_text += _read(project / name)
    if "spring-boot" in jvm_text:
        mark("spring-boot", "spring-boot in the build")
    if "spring-boot-starter-security" in jvm_text or "spring-security" in jvm_text:
        mark("spring-security", "spring-security in the build")
    if "data-jpa" in jvm_text or "jakarta.persistence" in jvm_text or "hibernate" in jvm_text:
        mark("jpa", "JPA in the build")
    for name in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"):
        if (project / name).is_file():
            mark("docker", name)
    if any(project.glob("*.tf")) or (project / "terraform").is_dir():
        mark("infra", "terraform")
    if (project / "Chart.yaml").is_file() or (project / "k8s").is_dir():
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
