"""core/tickets: IDs de ticket agnósticos (ADR-0012) normalizados en los nombres (D-26)."""

from __future__ import annotations

import pytest

from exo.core import tickets
from exo.core.tickets import TicketError

JIRA = r"[A-Z][A-Z0-9]*-\d+"
GITHUB = r"#\d+"
AZURE = r"AB#\d+"


@pytest.mark.parametrize(("pattern", "example"), tickets.SUGGESTIONS)
def test_las_sugerencias_son_validas(pattern: str, example: str) -> None:
    tickets.check_example(pattern, example)


@pytest.mark.parametrize(
    ("pattern", "message"),
    [
        ("", "non-empty"),
        ("   ", "non-empty"),
        (7, "non-empty"),
        ("(", "not a valid regular expression"),
        (r"\d*", "empty ID"),
        ("x" * (tickets.MAX_PATTERN + 1), "too long"),
    ],
)
def test_patron_invalido(pattern: object, message: str) -> None:
    with pytest.raises(TicketError, match=message):
        tickets.compile_pattern(pattern)


def test_el_patron_se_aplica_entero() -> None:
    compiled = tickets.compile_pattern(GITHUB)
    assert compiled.fullmatch("#12")
    assert not compiled.fullmatch("x#12")
    assert not compiled.fullmatch("#12x")


def test_el_ejemplo_tiene_que_cumplir_el_patron() -> None:
    with pytest.raises(TicketError, match="does not match"):
        tickets.check_example(JIRA, "#123")


@pytest.mark.parametrize(
    ("ticket", "folder"),
    [
        ("PROJ-123", "PROJ-123"),
        ("AB#123", "AB-123"),
        ("#123", "123"),
        ("a b//c", "a-b-c"),
        ("--X--1--", "X-1"),
    ],
)
def test_normaliza(ticket: str, folder: str) -> None:
    assert tickets.normalize(ticket) == folder
    assert tickets.SEGMENT.fullmatch(folder)


def test_normalizar_algo_sin_letras_ni_digitos() -> None:
    with pytest.raises(TicketError, match="no letters or digits"):
        tickets.normalize("##")


@pytest.mark.parametrize(
    ("pattern", "ticket", "name"),
    [
        (JIRA, "PROJ-123", "PROJ-123-add-login"),
        (GITHUB, "#123", "123-add-login"),
        (AZURE, "AB#123", "AB-123-add-login"),
    ],
)
def test_nombre_con_ticket(pattern: str, ticket: str, name: str) -> None:
    assert tickets.change_name("add-login", ticket, pattern=pattern) == name


def test_nombre_sin_ticket() -> None:
    assert tickets.change_name("add-login") == "add-login"
    assert tickets.change_name("add-login", pattern=JIRA) == "add-login"


def test_ticket_que_no_cumple_el_patron_muestra_el_ejemplo() -> None:
    with pytest.raises(TicketError, match="for example PROJ-123"):
        tickets.change_name("add-login", "proj-1", pattern=JIRA, example="PROJ-123")


def test_ticket_sin_patron() -> None:
    with pytest.raises(TicketError, match="no ticket pattern"):
        tickets.change_name("add-login", "PROJ-1")


@pytest.mark.parametrize("slug", ["Add-Login", "add login", "add--login", "-add", "", "añadir"])
def test_slug_invalido(slug: str) -> None:
    with pytest.raises(TicketError, match="kebab-case"):
        tickets.change_name(slug)


@pytest.mark.parametrize("slug", ["archive", "capabilities"])
def test_nombres_reservados(slug: str) -> None:
    with pytest.raises(TicketError, match="reserved"):
        tickets.change_name(slug)


def test_nombre_demasiado_largo() -> None:
    with pytest.raises(TicketError, match="characters"):
        tickets.change_name("a" * (tickets.MAX_CHANGE_NAME + 1))


def test_epica() -> None:
    assert tickets.epic_folder("AB#100", pattern=AZURE) == "AB-100"
    with pytest.raises(TicketError, match="does not match"):
        tickets.epic_folder("PROJ-1", pattern=AZURE, example="AB#1")


@pytest.mark.parametrize(
    ("name", "ok"),
    [
        ("add-login", True),
        ("PROJ-123-add-login", True),
        ("123-add-login", True),
        ("../x", False),
        ("a/b", False),
        ("a b", False),
        ("", False),
        ("x" * (tickets.MAX_CHANGE_NAME + 1), False),
        (None, False),
    ],
)
def test_segmento_seguro(name: object, ok: bool) -> None:
    assert tickets.is_segment(name) is ok
