"""Wizard interactivo de `exo init` (`docs/plan/02-ARQUITECTURA.md` §2.9).

Pasos: agentes detectados (preseleccionados para confirmar), packs sugeridos
por el stack, patrón de los IDs de ticket con su ejemplo (ADR-0012), y resumen
con la lista de archivos para confirmar. `ask` y `out` se inyectan para poder probarlo sin terminal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from exo.adapters import KNOWN_AGENTS
from exo.adapters.detect import Detection, preselect
from exo.core import tickets
from exo.installer.stack import StackReport

Ask = Callable[[str], str]
Out = Callable[[str], None]


def _input(prompt: str) -> str:
    # Se busca en tiempo de llamada para poder reemplazarlo en los tests.
    return input(prompt)


@dataclass
class Choices:
    agents: list[str]
    packs: list[str]
    tickets: dict[str, Any] | None = field(default=None)


def _list(answer: str, default: list[str]) -> list[str]:
    answer = answer.strip()
    if not answer:
        return default
    return [item.strip() for item in answer.split(",") if item.strip()]


def choose(
    detections: list[Detection],
    stack: StackReport,
    available_packs: list[str],
    *,
    ask: Ask | None = None,
    out: Out | None = None,
) -> Choices:
    ask = ask or _input
    out = out or print
    out("Detected agents:")
    for item in detections:
        mark = "x" if item.strong else " "
        out(f"  [{mark}] {item.agent}: {', '.join(item.evidence)}")
    if not detections:
        out("  (none: installing the generic base, for any agent that reads AGENTS.md)")
    default_agents = preselect(detections) or ["generic"]
    out(f"Known: {', '.join(KNOWN_AGENTS)}")
    agents = _list(ask(f"Agents [{', '.join(default_agents)}]: "), default_agents)

    pending = [p for p in stack.suggested if p not in available_packs]
    default_packs = [p for p in stack.suggested if p in available_packs]
    if stack.signals:
        out("Stack: " + ", ".join(sorted(stack.signals)))
    if pending:
        out(f"Suggested packs that do not exist yet (coming later): {', '.join(pending)}")
    packs = _list(ask(f"Packs [{', '.join(default_packs)}]: "), default_packs)

    out("Ticket IDs: a regular expression for this project's ticket IDs; empty for no tickets.")
    out("  Suggestions: " + ", ".join(f"{p} ({e})" for p, e in tickets.SUGGESTIONS))
    pattern = _valid(
        ask, out, "Ticket pattern [none]: ", _pattern, "a regular expression, or empty"
    )
    return Choices(agents, packs, ticket_config(pattern, None, ask=ask, out=out))


def default_example(pattern: str) -> str | None:
    return next((example for p, example in tickets.SUGGESTIONS if p == pattern), None)


def ticket_config(
    pattern: str | None, example: str | None, *, ask: Ask | None = None, out: Out | None = None
) -> dict[str, Any]:
    """`{pattern, example}`; sin ejemplo, usa el de la sugerencia o lo pregunta si hay `ask`."""
    if pattern is None:
        return {"pattern": None, "example": None}
    if example is None:
        example = default_example(pattern)
        if ask is not None:
            prompt = f"Example ticket ID [{example}]: " if example else "Example ticket ID: "
            example = _valid(
                ask,
                out or print,
                prompt,
                lambda answer: _example(answer or example, pattern),
                f"an ID that matches {pattern}",
            )
    return {"pattern": pattern, "example": example}


def _pattern(answer: str) -> str | None:
    if not answer:
        return None
    try:
        tickets.compile_pattern(answer)
    except tickets.TicketError as exc:
        raise ValueError(str(exc)) from exc
    return answer


def _example(answer: str | None, pattern: str) -> str:
    try:
        tickets.check_example(pattern, answer)
    except tickets.TicketError as exc:
        raise ValueError(str(exc)) from exc
    assert answer is not None
    return answer


def _valid(ask: Ask, out: Out, prompt: str, parse: Callable[[str], Any], hint: str) -> Any:
    """Pregunta hasta que `parse` acepte la respuesta (si no, lanza ValueError)."""
    while True:
        answer = ask(prompt).strip()
        try:
            return parse(answer)
        except ValueError as exc:
            detail = f" ({exc})" if str(exc) and str(exc) != answer else ""
            out(f"invalid value: {answer!r}{detail}; {hint}")


def confirm(summary: list[str], *, ask: Ask | None = None, out: Out | None = None) -> bool:
    ask = ask or _input
    out = out or print
    out("About to apply:")
    for line in summary:
        out(f"  {line}")
    return ask("Continue? [y/N]: ").strip().lower() in ("y", "yes", "s", "si", "sí")
