"""IDs de ticket agnósticos de tracker (ADR-0012) y nombres de cambio (D-26).

Cada proyecto define en su config una expresión regular para sus IDs de ticket
(`tickets.pattern`) y un ejemplo para los mensajes (`tickets.example`). Sin
patrón, los cambios no llevan ticket. El motor no se conecta a ningún tracker:
solo valida el ID y lo usa.

En los nombres de cambio y de épica el ID va normalizado: todo lo que no sea
letra o dígito pasa a guion (`AB#123` → `AB-123`, `#123` → `123`), porque un `#`
al principio de una palabra es un comentario en el shell. El ID exacto queda en
el AI Usage Record.
"""

from __future__ import annotations

import re

MAX_PATTERN = 200
MAX_CHANGE_NAME = 100
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# Nombre de carpeta seguro para un cambio o una épica.
SEGMENT = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
RESERVED = ("archive", "capabilities")
# Sugerencias para el wizard (ADR-0012): ejemplos, no tipos con comportamiento propio.
SUGGESTIONS = (
    (r"[A-Z][A-Z0-9]*-\d+", "PROJ-123"),
    (r"#\d+", "#123"),
    (r"AB#\d+", "AB#123"),
)
_NOT_ALNUM = re.compile(r"[^A-Za-z0-9]+")


class TicketError(ValueError):
    """Patrón, ID de ticket o nombre de cambio inválido."""


def compile_pattern(pattern: object) -> re.Pattern[str]:
    if not isinstance(pattern, str) or not pattern.strip():
        raise TicketError("the ticket pattern must be a non-empty regular expression")
    if len(pattern) > MAX_PATTERN:
        raise TicketError(f"the ticket pattern is too long (more than {MAX_PATTERN} characters)")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise TicketError(
            f"the ticket pattern {pattern!r} is not a valid regular expression ({exc})"
        ) from exc
    if compiled.fullmatch(""):
        raise TicketError(
            f"the ticket pattern {pattern!r} accepts an empty ID; make it require at least "
            "one character (for example \\d+ instead of \\d*)"
        )
    return compiled


def check_example(pattern: str, example: object) -> None:
    if not isinstance(example, str) or not compile_pattern(pattern).fullmatch(example):
        raise TicketError(f"the example {example!r} does not match the ticket pattern {pattern}")


def validate_ticket(ticket: object, pattern: str | None, example: str | None = None) -> str:
    """Devuelve el ID tal cual si cumple el patrón del proyecto."""
    if pattern is None:
        raise TicketError(
            "this project has no ticket pattern (tickets.pattern in the config), so changes "
            "have no ticket: leave it out, or set one with `exo init --ticket-pattern`"
        )
    if not isinstance(ticket, str) or not compile_pattern(pattern).fullmatch(ticket):
        hint = f" (for example {example})" if example else ""
        raise TicketError(
            f"{ticket!r} does not match this project's ticket pattern {pattern}{hint}"
        )
    return ticket


def normalize(ticket: str) -> str:
    value = _NOT_ALNUM.sub("-", ticket).strip("-")
    if not value:
        raise TicketError(f"the ticket ID {ticket!r} has no letters or digits")
    return value


def _check_length(name: str) -> str:
    if len(name) > MAX_CHANGE_NAME:
        raise TicketError(
            f"the change name {name!r} is longer than {MAX_CHANGE_NAME} characters; "
            "use a shorter slug"
        )
    return name


def change_name(
    slug: object,
    ticket: str | None = None,
    *,
    pattern: str | None = None,
    example: str | None = None,
) -> str:
    """`[<ticket normalizado>-]<slug>` (D-26)."""
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise TicketError(
            f"invalid change slug {slug!r}: use lowercase kebab-case (a-z, 0-9, single "
            "hyphens), for example add-login"
        )
    if slug in RESERVED:
        raise TicketError(f"{slug!r} is reserved for the specs folder; choose another slug")
    name = slug
    if ticket is not None:
        validate_ticket(ticket, pattern, example)
        name = f"{normalize(ticket)}-{slug}"
    return _check_length(name)


def epic_folder(epic: str, *, pattern: str | None, example: str | None = None) -> str:
    """Carpeta de la épica (§6.5 F): un solo segmento, con el ID normalizado."""
    validate_ticket(epic, pattern, example)
    folder = normalize(epic)
    if folder.lower() in RESERVED:
        raise TicketError(f"the epic {epic!r} would use the reserved folder {folder!r}")
    return _check_length(folder)


def is_segment(name: object) -> bool:
    return (
        isinstance(name, str)
        and len(name) <= MAX_CHANGE_NAME
        and SEGMENT.fullmatch(name) is not None
    )
