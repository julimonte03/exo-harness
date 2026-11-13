"""Lint de artefactos SDD contra sus plantillas (`exo/sdd/templates/`).

Tipos (§4.1 del reporte): `functional` (proposal.md y spec.md), `technical`
(design.md), `test-spec`, `verify-record` y `pr`. Las secciones `##` de cada
plantilla son obligatorias y no pueden quedar vacías (los comentarios HTML no
cuentan como contenido). Además:

- spec.md: IDs `FR-n`, `NFR-n` en Requirements y `S-n` en Scenarios, bien
  formados y sin repetir; cada escenario con Given, When y Then.
- verify-record.md: Verdict `ready|needs-rework|blocked` y marcador de gate.
- Carpeta de change: cada `S-n` de spec.md aparece en el Test Plan de
  design.md, y toda referencia a un ID existe en spec.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from exo import _meta

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
# Nombre de archivo del artefacto -> plantilla.
ARTIFACTS = {
    "proposal.md": "proposal",
    "spec.md": "spec",
    "design.md": "design",
    "test-spec.md": "test-spec",
    "verify-record.md": "verify-record",
    "pr.md": "pr",
}
KIND_OF = {
    "proposal": "functional",
    "spec": "functional",
    "design": "technical",
    "test-spec": "test-spec",
    "verify-record": "verify-record",
    "pr": "pr",
}
KINDS = ("functional", "technical", "test-spec", "verify-record", "pr")
VERDICTS = ("ready", "needs-rework", "blocked")
GATE_MARKER = re.compile(rf"<!--\s*{re.escape(_meta.BLOCK_PREFIX)}-gate:[a-z_]+\s*-->")

_H2 = re.compile(r"^##(?!#)\s+(.+?)\s*#*\s*$")
_SUBHEADING = re.compile(r"^(#{3,6})\s+(.*)$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_ITEM_TOKEN = re.compile(r"^\s*[-*+]\s+\**\s*([A-Za-z]{1,3}-?[0-9A-Za-z]+)")
_HEADING_TOKEN = re.compile(r"^#{3,6}\s+\**\s*([A-Za-z]{1,3}-?[0-9A-Za-z]+)")
_LOOSE_REQ = re.compile(r"^n?fr-?\d+$", re.IGNORECASE)
_LOOSE_SCENARIO = re.compile(r"^s-?\d+$", re.IGNORECASE)
_STRICT = {"req": re.compile(r"^N?FR-[1-9]\d*$"), "scenario": re.compile(r"^S-[1-9]\d*$")}
# Dónde se definen los IDs de cada clase: (token al inicio de línea, forma laxa).
_DEFINITION = {"req": (_ITEM_TOKEN, _LOOSE_REQ), "scenario": (_HEADING_TOKEN, _LOOSE_SCENARIO)}
_ID_HINT = "expected for example FR-1, NFR-1, S-1"
_REFERENCE = re.compile(r"\b((?:N?FR|S)-[1-9]\d*)\b")


class SpeclintError(ValueError):
    """No se puede lintear: ruta inexistente o tipo desconocido."""


@dataclass
class Issue:
    line: int
    message: str


@dataclass
class FileReport:
    path: Path
    kind: str
    template: str
    errors: list[Issue] = field(default_factory=list)


@dataclass
class LintReport:
    files: list[FileReport]

    @property
    def ok(self) -> bool:
        return all(not f.errors for f in self.files)


@dataclass
class _Section:
    title: str
    line: int
    body: list[tuple[int, str]]

    def text(self, *, comments: bool = False) -> str:
        raw = "\n".join(line for _, line in self.body)
        return raw if comments else _COMMENT.sub("", raw)


def template_text(name: str) -> str:
    return (TEMPLATES_DIR / f"{name}.md").read_text(encoding="utf-8")


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def _sections(text: str) -> list[_Section]:
    sections: list[_Section] = []
    current: _Section | None = None
    in_code = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_code = not in_code
        match = None if in_code else _H2.match(line)
        if match:
            current = _Section(match.group(1), number, [])
            sections.append(current)
        elif current is not None:
            current.body.append((number, line))
    return sections


def _required(template: str) -> list[str]:
    return [s.title for s in _sections(template_text(template))]


def _find(sections: list[_Section], title: str) -> _Section | None:
    return next((s for s in sections if _norm(s.title) == _norm(title)), None)


# -- reglas por archivo -------------------------------------------------------


def _check_structure(sections: list[_Section], template: str, errors: list[Issue]) -> None:
    for title in _required(template):
        section = _find(sections, title)
        if section is None:
            errors.append(Issue(1, f"missing section '## {title}'"))
        elif not section.text().strip():
            errors.append(Issue(section.line, f"section '{section.title}' is empty"))


def _definitions(section: _Section, kind: str, errors: list[Issue]) -> dict[str, int]:
    pattern, loose = _DEFINITION[kind]
    strict = _STRICT[kind]
    found: dict[str, int] = {}
    in_code = False
    for number, line in section.body:
        if _FENCE.match(line):
            in_code = not in_code
            continue
        match = None if in_code else pattern.match(line)
        if not match or not loose.match(match.group(1)):
            continue
        token = match.group(1)
        if not strict.match(token):
            errors.append(Issue(number, f"malformed ID: {token} ({_ID_HINT})"))
        elif token in found:
            message = f"{token} defined twice (first on line {found[token]})"
            errors.append(Issue(number, message))
        else:
            found[token] = number
    return found


def _scenario_blocks(section: _Section) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for _, line in section.body:
        heading = _SUBHEADING.match(line)
        if heading:
            token = _HEADING_TOKEN.match(line)
            valid = token is not None and _STRICT["scenario"].match(token.group(1))
            current = token.group(1) if valid else None
            if current is not None:
                blocks.setdefault(current, [])
            continue
        if current is not None:
            blocks[current].append(line)
    return {k: _COMMENT.sub("", "\n".join(v)) for k, v in blocks.items()}


def _check_spec(sections: list[_Section], errors: list[Issue]) -> dict[str, int]:
    defined: dict[str, int] = {}
    requirements = _find(sections, "Requirements")
    if requirements is not None:
        reqs = _definitions(requirements, "req", errors)
        if not any(token.startswith("FR-") for token in reqs):
            errors.append(Issue(requirements.line, "no FR-n requirements in 'Requirements'"))
        defined.update(reqs)
    scenarios = _find(sections, "Scenarios")
    if scenarios is not None:
        found = _definitions(scenarios, "scenario", errors)
        if not found:
            errors.append(Issue(scenarios.line, "no S-n scenarios in 'Scenarios'"))
        for token, body in _scenario_blocks(scenarios).items():
            for word in ("Given", "When", "Then"):
                if not re.search(rf"\b{word}\b", body, re.IGNORECASE):
                    line = found.get(token, scenarios.line)
                    errors.append(Issue(line, f"{token} has no {word}"))
        defined.update(found)
    return defined


def _check_verify(sections: list[_Section], errors: list[Issue]) -> None:
    verdict = _find(sections, "Verdict")
    if verdict is not None and verdict.text().strip():
        words = set(re.findall(r"[a-z-]+", verdict.text().lower()))
        if len(words & set(VERDICTS)) != 1:
            message = "Verdict must be ready, needs-rework or blocked"
            errors.append(Issue(verdict.line, message))
    gate = _find(sections, "Gate summary")
    if gate is not None and not GATE_MARKER.search(gate.text(comments=True)):
        marker = f"<!-- {_meta.BLOCK_PREFIX}-gate:<gate> -->"
        errors.append(Issue(gate.line, f"missing gate marker ({marker}) in 'Gate summary'"))


def _template_for(path: Path, kind: str | None) -> str:
    if kind is None:
        template = ARTIFACTS.get(path.name)
        if template is None:
            raise SpeclintError(
                f"unknown artifact type for {path.name}; pass --type ({', '.join(KINDS)})"
            )
        return template
    if kind not in KINDS:
        raise SpeclintError(f"unknown type: {kind!r} (one of {', '.join(KINDS)})")
    if kind == "functional":
        return "proposal" if "proposal" in path.name else "spec"
    return next(t for t, k in KIND_OF.items() if k == kind)


def _lint_file(path: Path, template: str) -> tuple[FileReport, list[_Section], dict[str, int]]:
    text = path.read_text(encoding="utf-8")
    sections = _sections(text)
    report = FileReport(path, KIND_OF[template], template)
    _check_structure(sections, template, report.errors)
    defined: dict[str, int] = {}
    if template == "spec":
        defined = _check_spec(sections, report.errors)
    elif template == "verify-record":
        _check_verify(sections, report.errors)
    return report, sections, defined


# -- carpeta ------------------------------------------------------------------


def _references(path: Path) -> list[tuple[int, str]]:
    refs: list[tuple[int, str]] = []
    in_code = False
    text = _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), path.read_text(encoding="utf-8"))
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if not in_code:
            refs.extend((number, token) for token in _REFERENCE.findall(line))
    return refs


def _cross_check(reports: dict[str, tuple[FileReport, list[_Section], dict[str, int]]]) -> None:
    if "spec.md" not in reports:
        return
    defined = reports["spec.md"][2]
    for name in ("design.md", "test-spec.md", "verify-record.md"):
        if name not in reports:
            continue
        report = reports[name][0]
        seen: set[str] = set()
        for number, token in _references(report.path):
            if token not in defined and token not in seen:
                seen.add(token)
                report.errors.append(Issue(number, f"{token} is not defined in spec.md"))
    if "design.md" in reports:
        report, sections, _ = reports["design.md"]
        plan = _find(sections, "Test Plan")
        if plan is not None:
            mentioned = set(_REFERENCE.findall(plan.text()))
            for token in defined:
                if token.startswith("S-") and token not in mentioned:
                    message = f"{token} from spec.md does not appear in the Test Plan of design.md"
                    report.errors.append(Issue(plan.line, message))


def lint_path(path: Path, kind: str | None = None) -> LintReport:
    path = Path(path)
    if not path.exists():
        raise SpeclintError(f"{path} does not exist")
    if path.is_file():
        report, _, _ = _lint_file(path, _template_for(path, kind))
        return LintReport([report])
    reports = {
        name: _lint_file(path / name, template)
        for name, template in ARTIFACTS.items()
        if (path / name).is_file()
    }
    if not reports:
        empty = FileReport(path, "change", "")
        empty.errors.append(
            Issue(0, f"no SDD artifacts in {path} ({', '.join(ARTIFACTS)})")
        )
        return LintReport([empty])
    _cross_check(reports)
    return LintReport([entry[0] for entry in reports.values()])
