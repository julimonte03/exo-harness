"""Lint de artefactos SDD contra sus plantillas (`exo/sdd/templates/`).

Tipos (§4.1 del reporte, más los de ADR-0013 y ADR-0016): `functional` (proposal.md),
`delta` (el spec.md de un change), `capability` (la spec viva de una capacidad,
`capabilities/<cap>/spec.md`), `technical` (design.md), `canvas` (el Canvas REASONS
del overlay SPDD), `test-spec`, `verify-record` y `pr`. Las secciones `##` de cada
plantilla son obligatorias y no pueden quedar vacías (los comentarios HTML no cuentan
como contenido), salvo en el delta, donde cada sección es opcional. Además:

- delta y capacidad: el formato de `sdd/specs.py` (IDs `CAP-<cap>-FR-n`,
  escenarios con Given, When y Then, `S-n` solo en el delta).
- verify-record.md: Verdict `ready|needs-rework|blocked` y marcador de gate.
- gates (`<change-root>/gates/<gate>.md`, F5): el marcador con el nombre del
  archivo, Verdict `APPROVED|ESCALATED`, y en Approval la línea
  `Requires tech_lead approval: yes|no` y `Source:`.
- Carpeta de change: cada `S-n` del delta aparece en el Test Plan de design.md;
  cada requisito ADDED o MODIFIED y cada escenario del delta aparecen en
  test-spec.md; y toda referencia a un ID existe en el delta o en las specs vivas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from exo import _meta
from exo.sdd import specs

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
# Nombre de archivo del artefacto -> plantilla.
ARTIFACTS = {
    "proposal.md": "proposal",
    "spec.md": "spec",
    "design.md": "design",
    "canvas.md": "canvas",
    "test-spec.md": "test-spec",
    "verify-record.md": "verify-record",
    "pr.md": "pr",
}
KIND_OF = {
    "proposal": "functional",
    "spec": "delta",
    "capability-spec": "capability",
    "design": "technical",
    "canvas": "canvas",
    "test-spec": "test-spec",
    "verify-record": "verify-record",
    "pr": "pr",
    "gate": "gate",
}
KINDS = (
    "functional",
    "delta",
    "capability",
    "technical",
    "canvas",
    "test-spec",
    "verify-record",
    "pr",
    "gate",
)
GATES_DIR = "gates"
GATE_VERDICTS = ("APPROVED", "ESCALATED")
CONTRACT_GATE = "contract_check"
# El Canvas REASONS del overlay SPDD (ADR-0016) y el gate humano que lo aprueba.
CANVAS = "canvas.md"
CANVAS_GATE = "prompt_spec_review"
VERDICTS = ("ready", "needs-rework", "blocked")
GATE_MARKER = re.compile(rf"<!--\s*{re.escape(_meta.BLOCK_PREFIX)}-gate:[a-z][a-z0-9_]*\s*-->")

_H2 = re.compile(r"^##(?!#)\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_VERDICT_WORD = re.compile(r"^[\s*_`]*([A-Za-z-]+)")
_GATE_NAME = re.compile(rf"<!--\s*{re.escape(_meta.BLOCK_PREFIX)}-gate:([a-z][a-z0-9_]*)\s*-->")
_APPROVAL = re.compile(r"Requires tech_lead approval:\s*(yes|no)\b", re.IGNORECASE)
_SOURCE = re.compile(r"^\s*Source:\s*\S", re.MULTILINE)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# Un ID de requisito entero o un escenario; `CAP-x-FR-12` no se lee como `FR-12`.
_REFERENCE = re.compile(rf"\b(CAP-{specs.CAPABILITY_NAME}-N?FR-[1-9]\d*|S-[1-9]\d*)\b")


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
    warnings: list[Issue] = field(default_factory=list)


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


_EMPTY_REQUIREMENTS = "section 'Requirements' is empty"


def verdict(text: str) -> str | None:
    """La primera palabra de la sección Verdict, si es un veredicto válido."""
    section = _find(_sections(text), "Verdict")
    if section is None or not section.text().strip():
        return None
    first = next(line for line in section.text().splitlines() if line.strip())
    match = _VERDICT_WORD.match(first)
    word = match.group(1).lower() if match else None
    return word if word in VERDICTS else None


@dataclass(frozen=True)
class GateInfo:
    name: str
    verdict: str | None  # APPROVED | ESCALATED | None si no se puede leer
    needs_approval: bool
    path: Path


def _first_word(section: _Section | None) -> str | None:
    if section is None or not section.text().strip():
        return None
    first = next(line for line in section.text().splitlines() if line.strip())
    match = _VERDICT_WORD.match(first)
    return match.group(1) if match else None


def section_text(path: Path, title: str) -> str | None:
    """El texto de una sección `##`, con sus comentarios, o None si no está."""
    section = _find(_sections(Path(path).read_text(encoding="utf-8-sig")), title)
    return section.text(comments=True) if section is not None else None


def gate_info(path: Path) -> GateInfo:
    """Nombre, veredicto y si pide aprobación de `tech_lead`, de un archivo de gate."""
    text = Path(path).read_text(encoding="utf-8-sig")
    sections = _sections(text)
    found = _GATE_NAME.search(text)
    word = (_first_word(_find(sections, "Verdict")) or "").upper()
    approval = _find(sections, "Approval")
    answer = _APPROVAL.search(approval.text()) if approval else None
    verdict = word if word in GATE_VERDICTS else None
    needs = verdict != "APPROVED" or bool(answer and answer.group(1).lower() == "yes")
    return GateInfo(found.group(1) if found else Path(path).stem, verdict, needs, Path(path))


def contract_gate(verify_record: Path) -> GateInfo:
    """El gate `contract_check` sale del Gate summary de verify-record.md."""
    text = Path(verify_record).read_text(encoding="utf-8-sig")
    sections = _sections(text)
    summary = _find(sections, "Gate summary")
    # Sin comentarios: la plantilla trae comentada la línea "yes | no".
    answer = _APPROVAL.search(summary.text()) if summary else None
    result = verdict(text)
    gate_verdict = "APPROVED" if result == "ready" else ("ESCALATED" if result else None)
    needs = gate_verdict != "APPROVED" or bool(answer and answer.group(1).lower() == "yes")
    return GateInfo(CONTRACT_GATE, gate_verdict, needs, Path(verify_record))


def _check_gate(path: Path, text: str, sections: list[_Section], errors: list[Issue]) -> None:
    found = _GATE_NAME.search(text)
    expected = path.stem if path.parent.name == GATES_DIR else None
    if found is None:
        errors.append(Issue(1, f"missing gate marker (<!-- {_meta.BLOCK_PREFIX}-gate:<gate> -->)"))
    elif expected is not None and found.group(1) != expected:
        errors.append(
            Issue(1, f"the gate marker says {found.group(1)} but the file is {expected}.md")
        )
    verdict_section = _find(sections, "Verdict")
    word = _first_word(verdict_section)
    if verdict_section is not None and word is not None and word.upper() not in GATE_VERDICTS:
        errors.append(Issue(verdict_section.line, "Verdict must start with APPROVED or ESCALATED"))
    approval = _find(sections, "Approval")
    if approval is not None and approval.text().strip():
        if not _APPROVAL.search(approval.text()):
            message = "Approval needs the line 'Requires tech_lead approval: yes|no'"
            errors.append(Issue(approval.line, message))
        if not _SOURCE.search(approval.text()):
            errors.append(Issue(approval.line, "Approval needs the line 'Source: skill <name>'"))


def _check_delta(text: str, errors: list[Issue]) -> dict[str, int]:
    delta = specs.parse_delta(text)
    errors.extend(Issue(p.line, p.message) for p in delta.problems)
    return {**delta.ids(), **delta.scenarios}


def _check_capability(
    text: str, name: str, errors: list[Issue], warnings: list[Issue]
) -> dict[str, int]:
    cap = specs.parse_capability(text, name)
    for problem in cap.problems:
        target = warnings if problem.severity == "warning" else errors
        target.append(Issue(problem.line, problem.message))
    return {block.id: block.line for block in cap.requirements.values()}


def _check_verify(sections: list[_Section], errors: list[Issue]) -> None:
    section = _find(sections, "Verdict")
    if section is not None and section.text().strip():
        text = "\n".join(f"## {s.title}\n{s.text(comments=True)}" for s in sections)
        if verdict(text) is None:
            message = (
                "Verdict must be ready, needs-rework or blocked (the first word of the section; "
                "the reason can follow)"
            )
            errors.append(Issue(section.line, message))
    gate = _find(sections, "Gate summary")
    if gate is not None and not GATE_MARKER.search(gate.text(comments=True)):
        marker = f"<!-- {_meta.BLOCK_PREFIX}-gate:<gate> -->"
        errors.append(Issue(gate.line, f"missing gate marker ({marker}) in 'Gate summary'"))


def _is_capability(path: Path) -> bool:
    return path.name == specs.SPEC_FILE and path.parent.parent.name == specs.CAPABILITIES


def _template_for(path: Path, kind: str | None) -> str:
    if kind is None:
        if _is_capability(path):
            return "capability-spec"
        if path.parent.name == GATES_DIR and path.suffix == ".md":
            return "gate"
        template = ARTIFACTS.get(path.name)
        if template is None:
            raise SpeclintError(
                f"unknown artifact type for {path.name}; pass --type ({', '.join(KINDS)})"
            )
        return template
    if kind not in KINDS:
        raise SpeclintError(f"unknown type: {kind!r} (one of {', '.join(KINDS)})")
    return next(t for t, k in KIND_OF.items() if k == kind)


def _lint_file(path: Path, template: str) -> tuple[FileReport, list[_Section], dict[str, int]]:
    text = path.read_text(encoding="utf-8-sig")
    sections = _sections(text)
    report = FileReport(path, KIND_OF[template], template)
    defined: dict[str, int] = {}
    if template == "spec":
        defined = _check_delta(text, report.errors)
    else:
        _check_structure(sections, template, report.errors)
    if template == "capability-spec":
        defined = _check_capability(text, path.parent.name, report.errors, report.warnings)
        if specs.parse_capability(text, path.parent.name).removed:
            # Todos los requisitos se borraron: quedan las lápidas, y vale.
            report.errors = [e for e in report.errors if e.message != _EMPTY_REQUIREMENTS]
    elif template == "verify-record":
        _check_verify(sections, report.errors)
    elif template == "gate":
        _check_gate(path, text, sections, report.errors)
    return report, sections, defined


# -- carpeta ------------------------------------------------------------------


def _references(path: Path) -> list[tuple[int, str]]:
    refs: list[tuple[int, str]] = []
    in_code = False
    raw = path.read_text(encoding="utf-8-sig")
    text = _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), raw)
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if not in_code:
            refs.extend((number, token) for token in _REFERENCE.findall(line))
    return refs


def _living_ids(change: Path) -> set[str]:
    """IDs vigentes en `capabilities/`, buscando hacia arriba desde el change (épica, archive)."""
    for ancestor in list(change.resolve().parents)[:3]:
        root = ancestor / specs.CAPABILITIES
        if root.is_dir():
            found: set[str] = set()
            for path in sorted(root.glob(f"*/{specs.SPEC_FILE}")):
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                cap = specs.parse_capability(text, path.parent.name)
                found.update(cap.requirements)
                found.update(cap.removed)
            return found
    return set()


def _cross_check(
    folder: Path, reports: dict[str, tuple[FileReport, list[_Section], dict[str, int]]]
) -> None:
    if "spec.md" not in reports:
        return
    defined = reports["spec.md"][2]
    living: set[str] | None = None
    for name in ("design.md", CANVAS, "test-spec.md", "verify-record.md"):
        if name not in reports:
            continue
        report = reports[name][0]
        seen: set[str] = set()
        for number, token in _references(report.path):
            if token in defined or token in seen:
                continue
            seen.add(token)
            if token.startswith("CAP-"):
                if living is None:
                    living = _living_ids(folder)
                if token not in living:
                    message = f"{token} is not defined in spec.md nor in the living specs"
                    report.errors.append(Issue(number, message))
            else:
                report.errors.append(Issue(number, f"{token} is not defined in spec.md"))
    if "test-spec.md" in reports:
        report = reports["test-spec.md"][0]
        mentioned = {token for _, token in _references(report.path)}
        delta = specs.parse_delta((folder / "spec.md").read_text(encoding="utf-8-sig"))
        covered = [b.id for b in (*delta.added, *delta.modified)] + list(delta.scenarios)
        for token in covered:
            if token not in mentioned:
                message = f"{token} from spec.md is not covered in test-spec.md"
                report.errors.append(Issue(1, message))
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
        name: _lint_file(path / name, _template_for(path / name, None))
        for name in ARTIFACTS
        if (path / name).is_file()
    }
    gates = sorted((path / GATES_DIR).glob("*.md")) if (path / GATES_DIR).is_dir() else []
    if not reports and not gates:
        empty = FileReport(path, "change", "")
        empty.errors.append(Issue(0, f"no SDD artifacts in {path} ({', '.join(ARTIFACTS)})"))
        return LintReport([empty])
    _cross_check(path, reports)
    gate_reports = [_lint_file(gate, "gate")[0] for gate in gates]
    return LintReport([entry[0] for entry in reports.values()] + gate_reports)
