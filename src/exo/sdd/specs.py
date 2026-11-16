"""Specs vivas por capacidad y deltas por cambio (D-11, ADR-0013).

- **Spec de capacidad** (`<specs_dir>/capabilities/<cap>/spec.md`): la fuente de
  verdad del comportamiento vigente. `## Requirements` tiene un bloque por
  requisito (`### CAP-<cap>-FR-n: <título>`, texto y `#### Scenario: …`), y
  `## Removed Requirements` guarda las lápidas de los que se borraron, para que
  sus IDs no se reusen y una integración repetida se reconozca.
- **Delta** (el `spec.md` de un change): `## ADDED Requirements`,
  `## MODIFIED Requirements` (texto nuevo completo) y `## REMOVED Requirements`
  (con `Reason:`). Los escenarios llevan `S-n` para que el design y el test-spec
  los citen.
- **`merge`**: integra el delta por ID, de forma determinista. Valida todo antes
  de escribir; si nada cambia, no escribe ni crea snapshot; si cambia algo, hace
  snapshot de las specs que existían y escribe de forma atómica, preservando los
  fines de línea y todo lo que está fuera de los bloques tocados.

Los comentarios HTML y los bloques de código no cuentan como estructura.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from exo.core import config, fsutil, snapshots

CAPABILITIES = "capabilities"
SPEC_FILE = "spec.md"
REQUIREMENTS = "Requirements"
REMOVED_REQUIREMENTS = "Removed Requirements"
DELTA_SECTIONS = {
    "added requirements": "added",
    "modified requirements": "modified",
    "removed requirements": "removed",
}
CAPABILITY_NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
REQUIREMENT_ID = re.compile(rf"CAP-({CAPABILITY_NAME})-(N?FR)-([1-9]\d*)")
SCENARIO_ID = re.compile(r"S-[1-9]\d*")
NEW_CAPABILITY = """# Capability: {name}

## Purpose

<!-- What this capability is for, in one or two sentences. -->

## Requirements
"""

_HEADING = re.compile(r"^(#{2,4})(?!#)\s+(.*?)\s*#*\s*$")
# Marcas de evidencia de la ingeniería inversa (ADR-0015). `FACTS`: solo las que citan
# código o docs, sin las inferencias.
_FACT_MARKS = r"\[Code\]\s+[^\s\[\]]+:\d+(?:-\d+)?|\[Doc\]\s+[^\s\[\]]+"
FACTS = re.compile(_FACT_MARKS)
EVIDENCE = re.compile(rf"{_FACT_MARKS}|\[Inferred:\s*(?:high|medium|low)\]")
STATUSES = ("as-is", "as-is-validated")
# `Status: as-is`, `**Status:** as-is`, `**Status**: as-is` o `status: as-is`.
_PREAMBLE = re.compile(
    r"^\s*(?:\*\*|__)?(status|source)(?:\*\*|__)?\s*:\s*(?:\*\*|__)?\s*(.*?)\s*$",
    re.IGNORECASE,
)
_LATE_STATUS = "Status goes before ## Purpose"
_REQ_HEADING = re.compile(r"^([^\s:]+)\s*:?\s*(.*)$")
_SCENARIO = re.compile(r"^Scenario\b\s*(S-[0-9]+)?\s*:?\s*(.*)$", re.IGNORECASE)
_FENCE = re.compile(r"^\s*(```|~~~)")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_REASON = re.compile(r"^\s*Reason:\s*\S", re.IGNORECASE)
_DELTA_HINT = "use ## ADDED Requirements, ## MODIFIED Requirements or ## REMOVED Requirements"
_ID_HINT = "expected CAP-<capability>-FR-n or CAP-<capability>-NFR-n (ADR-0013)"


class SpecsError(ValueError):
    """Capacidad o change inexistente, o ruta insegura."""


class MergeError(SpecsError):
    """El delta no se puede integrar; no se escribió nada."""

    def __init__(self, change: str, problems: list[str]) -> None:
        self.change = change
        self.problems = problems
        detail = "\n".join(f"- {p}" for p in problems)
        super().__init__(f"the delta of {change} was not merged (nothing was written):\n{detail}")


@dataclass(frozen=True)
class Problem:
    line: int
    message: str
    severity: str = "error"  # error | warning (ADR-0015)


@dataclass(frozen=True)
class Block:
    id: str
    capability: str
    title: str
    line: int
    lines: tuple[
        str, ...
    ]  # bloque normalizado, desde el encabezado ### y sin líneas vacías al final
    scenarios: tuple[str, ...] = ()


@dataclass(frozen=True)
class Delta:
    added: tuple[Block, ...]
    modified: tuple[Block, ...]
    removed: tuple[Block, ...]
    scenarios: dict[str, int]
    problems: tuple[Problem, ...]

    def blocks(self) -> list[tuple[str, Block]]:
        return [
            *(("add", b) for b in self.added),
            *(("modify", b) for b in self.modified),
            *(("remove", b) for b in self.removed),
        ]

    def ids(self) -> dict[str, int]:
        return {block.id: block.line for _, block in self.blocks()}


@dataclass(frozen=True)
class Capability:
    name: str
    requirements: dict[str, Block]
    removed: dict[str, Block]
    problems: tuple[Problem, ...]
    status: str | None = None  # None: una spec viva normal; as-is | as-is-validated (ADR-0015)
    source: str | None = None

    @property
    def errors(self) -> tuple[Problem, ...]:
        return tuple(p for p in self.problems if p.severity == "error")


@dataclass(frozen=True)
class CapabilityInfo:
    name: str
    path: str
    functional: int
    non_functional: int
    removed: int
    problems: int  # solo errores; los warnings no cuentan
    status: str | None = None


@dataclass(frozen=True)
class MergeOp:
    id: str
    action: str  # add | modify | remove
    status: str  # applied | already


@dataclass
class CapabilityMerge:
    name: str
    path: str
    action: str  # create | update | unchanged
    ops: list[MergeOp] = field(default_factory=list)


@dataclass
class MergeResult:
    change: str
    capabilities: list[CapabilityMerge]
    written: bool
    snapshot: str | None = None
    notes: list[str] = field(default_factory=list)


# -- texto ---------------------------------------------------------------------


def _split(text: str) -> tuple[list[str], str, bool]:
    """Líneas sin fin de línea, el fin de línea del archivo y si termina con uno."""
    eol = "\r\n" if "\r\n" in text else "\n"
    body = text.replace("\r\n", "\n")
    final = body.endswith("\n")
    lines = body.split("\n")
    if final:
        lines.pop()
    return lines, eol, final


def _mask(lines: list[str]) -> list[str]:
    """Las mismas líneas con los comentarios HTML en blanco (conserva la numeración)."""
    text = "\n".join(lines)
    masked = _COMMENT.sub(lambda m: "".join(c if c == "\n" else " " for c in m.group(0)), text)
    return masked.split("\n")


def _headings(masked: list[str]) -> list[tuple[int, int, str]]:
    """`(índice, nivel, texto)` de los encabezados ##, ### y #### fuera de bloques de código."""
    found: list[tuple[int, int, str]] = []
    in_code = False
    for index, line in enumerate(masked):
        if _FENCE.match(line):
            in_code = not in_code
            continue
        match = None if in_code else _HEADING.match(line)
        if match:
            found.append((index, len(match.group(1)), match.group(2)))
    return found


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def _clean(lines: list[str]) -> list[str]:
    """Sin espacios al final, sin líneas vacías repetidas ni en los extremos."""
    out: list[str] = []
    for line in (raw.rstrip() for raw in lines):
        if line or (out and out[-1]):
            out.append(line)
    while out and not out[-1]:
        out.pop()
    return out


@dataclass
class _Section:
    title: str
    start: int  # índice del encabezado ##
    end: int  # índice exclusivo
    blocks: list[tuple[int, int, str, str]]  # (inicio, fin, token, título) de cada ###


def _sections(masked: list[str]) -> list[_Section]:
    heads = _headings(masked)
    sections: list[_Section] = []
    h2 = [(i, text) for i, level, text in heads if level == 2]
    for number, (start, title) in enumerate(h2):
        end = h2[number + 1][0] if number + 1 < len(h2) else len(masked)
        h3 = [(i, text) for i, level, text in heads if level == 3 and start < i < end]
        blocks: list[tuple[int, int, str, str]] = []
        for k, (i, text) in enumerate(h3):
            block_end = h3[k + 1][0] if k + 1 < len(h3) else end
            match = _REQ_HEADING.match(text)
            token, label = (match.group(1), match.group(2)) if match else (text, "")
            blocks.append((i, block_end, token, label))
        sections.append(_Section(title, start, end, blocks))
    return sections


def _check_block(
    masked: list[str],
    start: int,
    end: int,
    block_id: str,
    *,
    removed: bool,
    delta: bool,
    problems: list[Problem],
    scenarios: dict[str, int],
    status: str | None = None,
) -> tuple[str, ...]:
    """Valida un bloque de requisito y devuelve los IDs de sus escenarios.

    En una capacidad con preámbulo (`status`), un requisito que trae evidencia
    (`[Code] path:line`, `[Doc] path` o `[Inferred: …]`) puede no tener escenario: es un
    warning. En una `as-is`, un requisito sin evidencia es un error. Sin preámbulo todo
    es como antes de la ingeniería inversa (ADR-0015).
    """
    heads = [(i, text) for i, level, text in _headings(masked[start:end]) if level == 4]
    heads = [(start + i, text) for i, text in heads]
    body_end = heads[0][0] if heads else end
    if removed:
        if delta and not any(_REASON.match(line) for line in masked[start + 1 : end]):
            problems.append(Problem(start + 1, f"{block_id} in REMOVED needs a 'Reason: …' line"))
        return ()
    if not any(line.strip() for line in masked[start + 1 : body_end]):
        problems.append(Problem(start + 1, f"{block_id} has no requirement text"))
    found: list[str] = []
    for k, (index, text) in enumerate(heads):
        stop = heads[k + 1][0] if k + 1 < len(heads) else end
        match = _SCENARIO.match(text)
        if match is None:
            problems.append(
                Problem(
                    index + 1,
                    f"unexpected heading inside {block_id}; scenarios use '#### Scenario …'",
                )
            )
            continue
        token = match.group(1)
        label = token or f"a scenario of {block_id}"
        if delta:
            if token is None or not SCENARIO_ID.fullmatch(token):
                problems.append(
                    Problem(
                        index + 1,
                        f"scenario without an S-n ID in {block_id} "
                        "(expected '#### Scenario S-1: <title>')",
                    )
                )
            elif token in scenarios:
                problems.append(
                    Problem(index + 1, f"{token} appears twice (first on line {scenarios[token]})")
                )
            else:
                scenarios[token] = index + 1
                found.append(token)
        elif token is not None:
            problems.append(
                Problem(
                    index + 1,
                    "scenario IDs (S-n) belong to change deltas; use '#### Scenario: <title>' "
                    "in capability specs",
                )
            )
        body = "\n".join(masked[index + 1 : stop])
        for word in ("Given", "When", "Then"):
            if not re.search(rf"\b{word}\b", body, re.IGNORECASE):
                problems.append(Problem(index + 1, f"{label} has no {word}"))
    has_evidence = status is not None and any(
        EVIDENCE.search(line) for line in masked[start + 1 : end]
    )
    if status == "as-is" and not has_evidence:
        problems.append(
            Problem(
                start + 1,
                f"{block_id} needs evidence in an as-is spec: [Code] path:line, [Doc] path or "
                "[Inferred: high|medium|low]",
            )
        )
    if not heads and "-FR-" in block_id and "-NFR-" not in block_id:
        if has_evidence:
            message = f"{block_id} has no scenarios yet: add one when a change touches it"
            problems.append(Problem(start + 1, message, "warning"))
        else:
            problems.append(Problem(start + 1, f"{block_id} has no scenarios"))
    return tuple(found)


def _block(
    masked: list[str], start: int, end: int, block_id: str, title: str, scenarios: tuple[str, ...]
) -> Block:
    match = REQUIREMENT_ID.fullmatch(block_id)
    capability = match.group(1) if match else ""
    return Block(
        block_id, capability, title, start + 1, tuple(_clean(masked[start:end])), scenarios
    )


# -- delta ---------------------------------------------------------------------


def parse_delta(text: str) -> Delta:
    lines, _, _ = _split(text)
    masked = _mask(lines)
    problems: list[Problem] = []
    groups: dict[str, list[Block]] = {"added": [], "modified": [], "removed": []}
    seen: dict[str, int] = {}
    scenarios: dict[str, int] = {}
    for section in _sections(masked):
        kind = DELTA_SECTIONS.get(_norm(section.title))
        if kind is None:
            problems.append(
                Problem(
                    section.start + 1,
                    f"unknown section '## {section.title}' in a change spec; {_DELTA_HINT} "
                    "(ADR-0013)",
                )
            )
            continue
        for start, end, token, title in section.blocks:
            if not REQUIREMENT_ID.fullmatch(token):
                problems.append(
                    Problem(start + 1, f"malformed requirement ID: {token} ({_ID_HINT})")
                )
                continue
            if token in seen:
                problems.append(
                    Problem(start + 1, f"{token} appears twice (first on line {seen[token]})")
                )
                continue
            seen[token] = start + 1
            found = _check_block(
                masked,
                start,
                end,
                token,
                removed=kind == "removed",
                delta=True,
                problems=problems,
                scenarios=scenarios,
            )
            groups[kind].append(_block(masked, start, end, token, title, found))
    if not seen and not any("malformed" in p.message for p in problems):
        problems.append(
            Problem(
                1,
                "the spec has no requirements; a change spec lists ADDED, MODIFIED or REMOVED "
                "requirements (ADR-0013)",
            )
        )
    return Delta(
        tuple(groups["added"]),
        tuple(groups["modified"]),
        tuple(groups["removed"]),
        scenarios,
        tuple(sorted(problems, key=lambda p: p.line)),
    )


# -- capacidad -------------------------------------------------------------------


def _status_value(value: str) -> str:
    return value.strip("`*_ ").lower()


def _preamble(masked: list[str], problems: list[Problem]) -> tuple[str | None, str | None]:
    """`Status:` y `Source:` antes del primer `##`, fuera de los bloques (ADR-0015).

    Un `Status:` desconocido es un warning: una spec viva que ya tenía, por ejemplo,
    `Status: draft` sigue siendo una spec viva y no bloquea nada. Un `Status: as-is`
    después del primer `##` no cuenta, y es un warning.
    """
    status = source = None
    first = next((i for i, line in enumerate(masked) if _HEADING.match(line)), len(masked))
    for index, line in enumerate(masked[:first]):
        match = _PREAMBLE.match(line)
        if match is None:
            continue
        key, value = match.groups()
        if key.lower() == "source":
            source = value or None
        elif _status_value(value) in STATUSES:
            status = _status_value(value)
        else:
            problems.append(
                Problem(
                    index + 1,
                    f"Status must be {' or '.join(STATUSES)}, not {value!r}; without one of "
                    "them this is a normal living spec",
                    "warning",
                )
            )
    in_code = False
    for index in range(first, len(masked)):
        line = masked[index]
        if _FENCE.match(line):
            in_code = not in_code
            continue
        match = None if in_code else _PREAMBLE.match(line)
        if match is None or match.group(1).lower() != "status":
            continue
        if _status_value(match.group(2)) in STATUSES:
            message = f"{_LATE_STATUS}: move it above the first section, or it does not count"
            problems.append(Problem(index + 1, message, "warning"))
    return status, source


def parse_capability(text: str, name: str) -> Capability:
    lines, _, _ = _split(text)
    masked = _mask(lines)
    problems: list[Problem] = []
    status, source = _preamble(masked, problems)
    requirements: dict[str, Block] = {}
    removed: dict[str, Block] = {}
    seen: dict[str, int] = {}
    sections_seen: dict[str, int] = {}
    for section in _sections(masked):
        title = _norm(section.title)
        if title == _norm(REQUIREMENTS):
            target, is_removed = requirements, False
        elif title == _norm(REMOVED_REQUIREMENTS):
            target, is_removed = removed, True
        else:
            continue
        if title in sections_seen:
            problems.append(
                Problem(
                    section.start + 1,
                    f"section '## {section.title}' appears twice (first on line "
                    f"{sections_seen[title]}); keep one",
                )
            )
        sections_seen.setdefault(title, section.start + 1)
        for start, end, token, label in section.blocks:
            match = REQUIREMENT_ID.fullmatch(token)
            if match is None:
                problems.append(
                    Problem(start + 1, f"malformed requirement ID: {token} ({_ID_HINT})")
                )
                continue
            if match.group(1) != name:
                problems.append(
                    Problem(
                        start + 1,
                        f"{token} belongs to capability {match.group(1)}, not {name}; "
                        f"its spec is capabilities/{match.group(1)}/spec.md",
                    )
                )
            if token in seen:
                problems.append(
                    Problem(start + 1, f"{token} appears twice (first on line {seen[token]})")
                )
                continue
            seen[token] = start + 1
            _check_block(
                masked,
                start,
                end,
                token,
                removed=is_removed,
                delta=False,
                problems=problems,
                scenarios={},
                status=status,
            )
            target[token] = _block(masked, start, end, token, label, ())
    ordered = tuple(sorted(problems, key=lambda p: p.line))
    return Capability(name, requirements, removed, ordered, status, source)


def capabilities_root(project: Path) -> Path:
    return Path(project) / config.load(project).config["specs_dir"] / CAPABILITIES


def _relative(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def capability_texts(
    project: Path, warnings: list[str] | None = None
) -> list[tuple[str, Path, str]]:
    """(nombre, ruta, texto) de cada spec de capacidad, por nombre.

    Una spec que no es UTF-8 se saltea y, si se pasa `warnings`, deja un aviso que la
    nombra: una spec ilegible no frena a las demás.
    """
    project = Path(project)
    root = capabilities_root(project)
    if not root.is_dir():
        return []
    found: list[tuple[str, Path, str]] = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and p.name[0] not in "._"):
        path = folder / SPEC_FILE
        if not path.is_file():
            continue
        try:
            text = path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            if warnings is not None:
                warnings.append(
                    f"{_relative(project, path)} is not UTF-8 text ({exc.reason}), so it was "
                    "skipped; save it as UTF-8 to include it"
                )
            continue
        found.append((folder.name, path, text))
    return found


def list_capabilities(project: Path, warnings: list[str] | None = None) -> list[CapabilityInfo]:
    """Las capacidades, salteando con un aviso (en `warnings`) las que no son UTF-8."""
    project = Path(project)
    found: list[CapabilityInfo] = []
    for name, path, text in capability_texts(project, warnings):
        cap = parse_capability(text, name)
        functional = sum(1 for key in cap.requirements if "-NFR-" not in key)
        found.append(
            CapabilityInfo(
                name,
                _relative(project, path),
                functional,
                len(cap.requirements) - functional,
                len(cap.removed),
                len(cap.errors),
                cap.status,
            )
        )
    return found


# -- integración -------------------------------------------------------------------


def _to_capability(block: Block) -> list[str]:
    """El bloque del delta como va en la capacidad: los escenarios pierden su `S-n`."""
    out: list[str] = []
    for line in block.lines:
        match = _HEADING.match(line)
        if match and len(match.group(1)) == 4:
            scenario = _SCENARIO.match(match.group(2))
            if scenario is not None:
                title = scenario.group(2).strip()
                line = "#### Scenario: " + title if title else "#### Scenario"
        out.append(line)
    return out


def _tombstone(change: str, removed: Block, existing: Block) -> list[str]:
    heading = existing.lines[0] if existing.lines else f"### {removed.id}"
    reason = [line for line in removed.lines[1:] if line.strip()]
    return [heading, f"Removed by change `{change}`.", *reason]


_PIECE = re.compile(r"[^\n]*\n|[^\n]+")


@dataclass
class _Doc:
    """Texto de una spec de capacidad que se edita por bloques, sin tocar el resto.

    Cada línea guarda su propio fin de línea, así las que no se tocan quedan byte a
    byte aunque el archivo los mezcle. Las líneas nuevas llevan el más frecuente.
    """

    lines: list[str]  # sin fin de línea
    ends: list[str]  # "\r\n", "\n" o "" (la última, si el archivo no termina con uno)
    eol: str
    bom: bool

    @classmethod
    def from_text(cls, text: str, bom: bool = False) -> _Doc:
        lines: list[str] = []
        ends: list[str] = []
        for piece in _PIECE.findall(text):
            end = "\r\n" if piece.endswith("\r\n") else ("\n" if piece.endswith("\n") else "")
            lines.append(piece[: len(piece) - len(end)])
            ends.append(end)
        eol = "\r\n" if ends.count("\r\n") > ends.count("\n") else "\n"
        return cls(lines, ends, eol, bom)

    @classmethod
    def parse(cls, raw: bytes) -> _Doc:
        text = raw.decode("utf-8")
        bom = text.startswith("﻿")
        return cls.from_text(text[1:] if bom else text, bom)

    @classmethod
    def new(cls, name: str) -> _Doc:
        return cls.from_text(NEW_CAPABILITY.format(name=name))

    def render(self) -> bytes:
        text = "".join(line + end for line, end in zip(self.lines, self.ends, strict=True))
        return (("﻿" if self.bom else "") + text).encode("utf-8")

    def _insert(self, index: int, new: list[str]) -> None:
        at_end = index == len(self.lines)
        unterminated = bool(self.ends) and self.ends[-1] == ""
        if index > 0 and self.ends[index - 1] == "":
            self.ends[index - 1] = self.eol
        ends = [self.eol] * len(new)
        if at_end and unterminated and ends:
            ends[-1] = ""
        self.lines[index:index] = new
        self.ends[index:index] = ends

    def _replace(self, start: int, stop: int, new: list[str]) -> None:
        last_end = self.ends[stop - 1] if stop > start else self.eol
        ends = [self.eol] * len(new)
        if ends and stop == len(self.lines) and last_end == "":
            ends[-1] = ""
        self.lines[start:stop] = new
        self.ends[start:stop] = ends

    def _delete(self, start: int, stop: int) -> None:
        del self.lines[start:stop]
        del self.ends[start:stop]

    def _section(self, title: str) -> _Section | None:
        wanted = _norm(title)
        return next((s for s in _sections(_mask(self.lines)) if _norm(s.title) == wanted), None)

    def _find(self, section: _Section, block_id: str) -> tuple[int, int] | None:
        return next(((s, e) for s, e, token, _ in section.blocks if token == block_id), None)

    def _content_end(self, start: int, end: int) -> int:
        while end > start and not self.lines[end - 1].strip():
            end -= 1
        return end

    def _append(self, section: _Section, block: list[str]) -> None:
        """Agrega el bloque al final de la sección, separado por una línea vacía."""
        last = self._content_end(section.start, section.end)
        self._insert(last, ["", *block])
        after = last + 1 + len(block)
        # Si lo que sigue quedó pegado (el próximo encabezado), se separa con una línea vacía.
        if after < len(self.lines) and self.lines[after].strip():
            self._insert(after, [""])

    def _trim_end(self) -> None:
        while self.lines and not self.lines[-1].strip():
            self._delete(len(self.lines) - 1, len(self.lines))

    def add(self, block: list[str]) -> None:
        section = self._section(REQUIREMENTS)
        if section is None:
            self._trim_end()
            self._insert(len(self.lines), ["", f"## {REQUIREMENTS}"])
            section = self._section(REQUIREMENTS)
            assert section is not None
        self._append(section, block)

    def replace(self, block_id: str, block: list[str]) -> None:
        section = self._section(REQUIREMENTS)
        assert section is not None
        found = self._find(section, block_id)
        assert found is not None
        start, end = found
        self._replace(start, self._content_end(start, end), block)

    def remove(self, block_id: str, tombstone: list[str]) -> None:
        section = self._section(REQUIREMENTS)
        assert section is not None
        found = self._find(section, block_id)
        assert found is not None
        self._delete(*found)
        removed = self._section(REMOVED_REQUIREMENTS)
        if removed is None:
            self._trim_end()
            self._insert(len(self.lines), ["", f"## {REMOVED_REQUIREMENTS}"])
            removed = self._section(REMOVED_REQUIREMENTS)
            assert removed is not None
        self._append(removed, tombstone)


def _same(existing: Block, block: list[str]) -> bool:
    return list(existing.lines) == block


def _plan(
    change: str, delta: Delta, docs: dict[str, tuple[_Doc, Capability] | None]
) -> tuple[dict[str, list[tuple[str, Block, str]]], list[str]]:
    """Decide cada operación sin tocar nada: `(ops por capacidad, problemas)`."""
    problems: list[str] = []
    plan: dict[str, list[tuple[str, Block, str]]] = {}
    for action, block in delta.blocks():
        state = docs.get(block.capability)
        cap = state[1] if state else None
        target = _to_capability(block)
        where = f"capabilities/{block.capability}/spec.md"
        status = "applied"
        if action == "add":
            if cap and block.id in cap.requirements:
                if not _same(cap.requirements[block.id], target):
                    problems.append(
                        f"{block.id} already exists in {where}; use MODIFIED to change it, "
                        "or a new number for a new requirement"
                    )
                status = "already"
            elif cap and block.id in cap.removed:
                problems.append(
                    f"{block.id} was removed by an earlier change; requirement IDs are not "
                    "reused, use a new number"
                )
        elif cap is None:
            problems.append(
                f"{block.id}: capability {block.capability} does not exist ({where}); "
                "only ADDED can create a capability"
            )
        elif action == "modify":
            if block.id in cap.requirements:
                if _same(cap.requirements[block.id], target):
                    status = "already"
            elif block.id in cap.removed:
                problems.append(
                    f"{block.id} was removed by an earlier change; it cannot be modified"
                )
            else:
                problems.append(f"{block.id} does not exist in {where}")
        elif block.id in cap.removed:
            status = "already"
        elif block.id not in cap.requirements:
            problems.append(f"{block.id} does not exist in {where}")
        plan.setdefault(block.capability, []).append((action, block, status))
    return plan, problems


def merge(project: Path, change: str, *, dry_run: bool = False) -> MergeResult:
    from exo.sdd import observability

    project = Path(project)
    try:
        found = observability.get_change(project, change)
    except observability.ObservabilityError as exc:
        raise MergeError(change, [str(exc)]) from exc
    delta_path = project / found.path / SPEC_FILE
    if not delta_path.is_file():
        note = f"{found.path} has no spec.md: nothing to merge (the change must not alter behavior)"
        return MergeResult(change, [], False, notes=[note])
    try:
        delta = parse_delta(delta_path.read_bytes().decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        rel = f"{found.path}/{SPEC_FILE}"
        problem = f"{rel}: not UTF-8 text ({exc.reason}); save it as UTF-8"
        raise MergeError(change, [problem]) from exc
    if delta.problems:
        rel = f"{found.path}/{SPEC_FILE}"
        raise MergeError(change, [f"{rel}:{p.line}: {p.message}" for p in delta.problems])
    root = capabilities_root(project)
    try:
        base = _relative(project, root)
        paths = {
            name: fsutil.join_within(project, f"{base}/{name}/{SPEC_FILE}")
            for name in sorted({b.capability for _, b in delta.blocks()})
        }
    except fsutil.UnsafePathError as exc:
        raise MergeError(change, [str(exc)]) from exc
    docs: dict[str, tuple[_Doc, Capability] | None] = {}
    problems: list[str] = []
    for name, path in paths.items():
        if not path.is_file():
            docs[name] = None
            continue
        raw = path.read_bytes()
        try:
            doc = _Doc.parse(raw)
            cap = parse_capability(raw.decode("utf-8-sig"), name)
        except UnicodeDecodeError as exc:
            rel = _relative(project, path)
            problems.append(f"{rel}: not UTF-8 text ({exc.reason}); save it as UTF-8")
            continue
        rel = _relative(project, path)
        if cap.errors:
            problems += [f"{rel}:{p.line}: {p.message}" for p in cap.errors]
        if cap.status == "as-is":
            problems.append(
                f"{rel}: the capability is an as-is spec recovered from code; a person validates "
                "it first (Status: as-is-validated), then changes modify it by delta"
            )
        docs[name] = (doc, cap)
    plan, plan_problems = _plan(change, delta, docs)
    problems += plan_problems
    if problems:
        raise MergeError(change, problems)

    result = MergeResult(change, [], False)
    writes: dict[Path, bytes] = {}
    for name, ops in sorted(plan.items()):
        path = paths[name]
        state = docs[name]
        doc = state[0] if state else _Doc.new(name)
        cap = state[1] if state else None
        before = doc.render() if state else None
        for action, block, status in ops:
            if status == "applied":
                target = _to_capability(block)
                if action == "add":
                    doc.add(target)
                elif action == "modify":
                    doc.replace(block.id, target)
                else:
                    assert cap is not None
                    doc.remove(block.id, _tombstone(change, block, cap.requirements[block.id]))
        after = doc.render()
        if state is None:
            action_name = "create"
            result.notes.append(
                f"new capability {name}: write its Purpose in {_relative(project, path)}"
            )
        else:
            action_name = "unchanged" if after == before else "update"
        entry = CapabilityMerge(name, _relative(project, path), action_name)
        entry.ops = [MergeOp(block.id, action, status) for action, block, status in ops]
        result.capabilities.append(entry)
        if action_name != "unchanged":
            writes[path] = after
    if dry_run or not writes:
        return result
    existing = [_relative(project, p) for p in writes if p.is_file()]
    if existing:
        result.snapshot = snapshots.snapshot(project, existing).name
    for path, data in writes.items():
        fsutil.write_atomic(path, data)
    result.written = True
    return result
