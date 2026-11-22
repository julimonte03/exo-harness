"""Las citas OWASP del contenido usan el Top 10:2025 (F8).

Recorre `content/` y las plantillas de `src/exo/sdd/templates/`. La tabla
compartida `owasp-2025.md` es la fuente de las categorías: de ella salen los
nombres y el mapeo CWE → categoría, y su columna de equivalencias es el único
lugar donde queda una cita de 2021 (para traducir reportes viejos).

Una cita es `A<nn>:<año>` con `nn` entre 01 y 10; un `CVE-2021-44228` o un año
suelto no lo son.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CONTENT = REPO / "content"
TEMPLATES = REPO / "src" / "exo" / "sdd" / "templates"
TABLE = CONTENT / "packs" / "core" / "shared" / "owasp-2025.md"
SECURITY = CONTENT / "packs" / "security" / "skills"
CHECKLISTS = (
    SECURITY / "security-code-review" / "references" / "review-checklist.md",
    SECURITY / "secure-coding-baseline" / "references" / "checklist.md",
)

YEAR = "2025"
ID = r"A(?:0[1-9]|10)"
CITE = re.compile(rf"\b({ID}):(\d{{4}})\b")
CWE = re.compile(r"\bCWE-(\d+)\b")
# Los nombres de 2021: solo para reconocer una cita sin año que usa el nombre viejo.
NAMES_2021 = (
    "Broken Access Control",
    "Cryptographic Failures",
    "Injection",
    "Insecure Design",
    "Security Misconfiguration",
    "Vulnerable and Outdated Components",
    "Identification and Authentication Failures",
    "Software and Data Integrity Failures",
    "Security Logging and Monitoring Failures",
    "Server-Side Request Forgery",
)
# Lo que separa el ID del nombre: un espacio, o un guion o dos puntos con espacios.
SEP = r"(?:[ \t]*[-–—][ \t]*|:[ \t]+|[ \t]+)"
# Los CWE de A10:2025 Mishandling of Exceptional Conditions que la checklist de revisión cubre.
A10_CWES = ("209", "215", "252", "636", "755", "617")


def _rows(text: str) -> list[list[str]]:
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.lstrip().startswith("|")
    ]


def _categories() -> dict[str, str]:
    """ID → nombre, de la tabla de categorías (`| A01:2025 | Broken Access Control | …`)."""
    found = {}
    for cells in _rows(TABLE.read_text(encoding="utf-8")):
        match = re.fullmatch(rf"({ID}):{YEAR}", cells[0])
        if match and len(cells) >= 2:
            found[match.group(1)] = cells[1]
    return found


def _cwe_map() -> dict[str, str]:
    """CWE → ID de categoría, de la tabla `CWE to category`."""
    found = {}
    for cells in _rows(TABLE.read_text(encoding="utf-8")):
        cwe = re.fullmatch(r"CWE-(\d+)", cells[0])
        if cwe and len(cells) >= 3:
            category = re.match(rf"({ID}):{YEAR}\b", cells[2])
            if category:
                found[cwe.group(1)] = category.group(1)
    return found


CATEGORIES = _categories()
CWE_MAP = _cwe_map()
_NAMES_2025 = "|".join(re.escape(name) for name in CATEGORIES.values())
_NAMES_ANY = "|".join(
    re.escape(name)
    for name in sorted(set(CATEGORIES.values()) | set(NAMES_2021), key=len, reverse=True)
)
BARE = re.compile(rf"\bOWASP[ \t]+{ID}\b(?!:\d)|\b{ID}\b(?!:\d){SEP}(?:{_NAMES_ANY})\b")
NAMED = re.compile(rf"\b({ID}):{YEAR}\b{SEP}(?=[A-Z])")
# Un par contiguo va separado solo por una coma o un paréntesis; un `;` separa grupos.
PAIR_AFTER = re.compile(rf"\b({ID}):{YEAR}\b(?:[ \t]+(?:{_NAMES_2025}))?,?[ \t]*\(?CWE-(\d+)\b")
PAIR_BEFORE = re.compile(rf"\bCWE-(\d+),?[ \t]*({ID}):{YEAR}\b")


def _wrong_years(text: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group(0)) for m in CITE.finditer(text) if m.group(2) != YEAR]


def _bare(text: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group(0)) for m in BARE.finditer(text)]


def _misnamed(text: str) -> list[tuple[int, str]]:
    """Una cita de 2025 seguida de un nombre que no es el de su categoría."""
    wrong = []
    for m in NAMED.finditer(text):
        expected = CATEGORIES[m.group(1)]
        if not text.startswith(expected, m.end()):
            found = text[m.end() : m.end() + len(expected) + 10].splitlines()[0]
            wrong.append((m.start(), f"{m.group(0)}{found!r}, expected {expected!r}"))
    return wrong


def _mismapped(text: str) -> list[tuple[int, str]]:
    """`CWE-89, A05:2025` o `A01:2025 Broken Access Control (CWE-22)` con otro mapeo que la tabla."""
    pairs = [(m.start(), m.group(2), m.group(1)) for m in PAIR_AFTER.finditer(text)]
    pairs += [(m.start(), m.group(1), m.group(2)) for m in PAIR_BEFORE.finditer(text)]
    return [
        (start, f"CWE-{cwe} is {CWE_MAP[cwe]}:{YEAR}, not {category}:{YEAR}")
        for start, cwe, category in pairs
        if cwe in CWE_MAP and CWE_MAP[cwe] != category
    ]


def _without_equivalence_column(text: str) -> str:
    """La tabla compartida sin la última celda de su tabla de categorías (la de 2021)."""
    lines = []
    for line in text.splitlines():
        if re.match(rf"\|\s*{ID}:{YEAR}\s*\|", line.lstrip()):
            line = line.rstrip().rstrip("|").rsplit("|", 1)[0] + "|"
        lines.append(line)
    return "\n".join(lines)


def _sources() -> list[tuple[Path, str]]:
    paths = [p for root in (CONTENT, TEMPLATES) for p in sorted(root.rglob("*")) if p.is_file()]
    found = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found.append((path, _without_equivalence_column(text) if path == TABLE else text))
    return found


SOURCES = _sources()


def _report(check) -> list[str]:
    return [
        f"{path.relative_to(REPO).as_posix()}:{text.count(chr(10), 0, start) + 1}: {what}"
        for path, text in SOURCES
        for start, what in check(text)
    ]


# -- los detectores -------------------------------------------------------------------------------


def test_la_tabla_tiene_las_diez_categorias_de_2025() -> None:
    assert sorted(CATEGORIES) == [f"A{n:02d}" for n in range(1, 11)]
    assert CATEGORIES["A05"] == "Injection"
    assert CATEGORIES["A10"] == "Mishandling of Exceptional Conditions"
    assert TABLE in {path for path, _ in SOURCES} and len(SOURCES) > 100


def test_un_cve_o_un_anio_no_son_citas() -> None:
    text = (
        "CVE-2021-44228 (Log4Shell), created in 2021, SHA-1, OWASP Top 10:2021, A03:2021 Injection"
    )
    assert _wrong_years(text) == [(text.index("A03"), "A03:2021")]


def test_la_columna_de_equivalencias_es_la_unica_excepcion() -> None:
    row = "| A05:2025 | Injection | SQL and XSS | A03:2021 |"
    assert _wrong_years(_without_equivalence_column(row)) == []
    assert _wrong_years(_without_equivalence_column("Keep A03:2021 out.")) != []


@pytest.mark.parametrize(
    "text",
    ["see A03 Injection", "OWASP A01 applies", "A09 - Security Logging and Monitoring Failures"],
)
def test_detecta_una_cita_sin_anio(text: str) -> None:
    assert _bare(text)


@pytest.mark.parametrize(
    "text", ["never a bare `A05`. The same number", "A05:2025 Injection", "A01:2025, CWE-639"]
)
def test_no_toma_por_cita_sin_anio_un_ejemplo_ni_una_cita_con_anio(text: str) -> None:
    assert _bare(text) == []


def test_detecta_un_nombre_de_categoria_equivocado() -> None:
    assert _misnamed("A09:2025 Security Logging and Monitoring Failures")
    assert _misnamed("A07:2025 Identification and Authentication Failures")
    assert (
        _misnamed("A05:2025 Injection, A03:2025, CWE-1395, | A01:2025 | Broken Access Control |")
        == []
    )


def test_detecta_un_par_cwe_categoria_que_contradice_la_tabla() -> None:
    assert _mismapped("CWE-89, A01:2025")
    assert _mismapped("A10:2025 (CWE-639)")
    assert (
        _mismapped("SCR-AUTHZ-2, A01:2025, CWE-639; A01:2025 Broken Access Control (CWE-22)") == []
    )
    assert _mismapped("A01:2025 (CWE-862, CWE-639); A07:2025 (CWE-306)") == []


# -- el contenido ---------------------------------------------------------------------------------


def test_toda_cita_owasp_es_de_2025() -> None:
    wrong = _report(_wrong_years)
    assert not wrong, "cite OWASP Top 10:2025 (from .exo/shared/owasp-2025.md):\n" + "\n".join(
        wrong
    )


def test_no_hay_citas_owasp_sin_anio() -> None:
    wrong = _report(_bare)
    assert not wrong, (
        "an OWASP category always carries its year (A05:2025 Injection):\n" + "\n".join(wrong)
    )


def test_toda_cita_de_2025_usa_el_nombre_de_su_categoria() -> None:
    wrong = _report(_misnamed)
    assert not wrong, "use the category name of .exo/shared/owasp-2025.md:\n" + "\n".join(wrong)


def test_los_pares_cwe_y_categoria_contiguos_coinciden_con_la_tabla() -> None:
    wrong = _report(_mismapped)
    assert not wrong, "take the category from the CWE in .exo/shared/owasp-2025.md:\n" + "\n".join(
        wrong
    )


@pytest.mark.parametrize("checklist", CHECKLISTS, ids=lambda p: p.parent.parent.name)
def test_los_cwe_de_las_checklists_de_security_estan_en_la_tabla(checklist: Path) -> None:
    """La categoría de un hallazgo sale de su CWE por la tabla: la tabla los tiene a todos."""
    cwes = sorted(set(CWE.findall(checklist.read_text(encoding="utf-8"))), key=int)
    missing = [f"CWE-{cwe}" for cwe in cwes if cwe not in CWE_MAP]
    assert not missing, (
        f"add to {TABLE.name}, verified against top10.owasp.org: {', '.join(missing)}"
    )


def test_la_checklist_de_revision_cubre_a10_2025() -> None:
    text = CHECKLISTS[0].read_text(encoding="utf-8")
    missing = [f"CWE-{cwe}" for cwe in A10_CWES if not re.search(rf"\bCWE-{cwe}\b", text)]
    assert not missing, f"A10:2025 Mishandling of Exceptional Conditions needs {', '.join(missing)}"
    assert all(CWE_MAP[cwe] == "A10" for cwe in A10_CWES)
