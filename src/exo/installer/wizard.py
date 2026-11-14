"""Wizard interactivo de `exo init` (`docs/plan/02-ARQUITECTURA.md` §2.9).

Pasos: agentes detectados (preseleccionados para confirmar), packs sugeridos
por el stack, tracker y prefijo, y resumen con la lista de archivos para
confirmar. `ask` y `out` se inyectan para poder probarlo sin terminal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from exo.adapters import KNOWN_AGENTS
from exo.adapters.detect import Detection, preselect
from exo.core import config
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
    tracker: dict[str, Any] = field(default_factory=dict)


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

    tracker_type = _valid(
        ask,
        out,
        f"Ticket tracker ({'/'.join(config.TRACKERS)}) [none]: ",
        _tracker_type,
        f"one of {', '.join(config.TRACKERS)}",
    )
    tracker: dict[str, Any] = {"type": tracker_type}
    if tracker_type != "none":
        tracker["prefix"] = _valid(
            ask,
            out,
            "Ticket prefix (for example PROJ), empty if none: ",
            _prefix,
            "letters and digits, starting with a letter (for example PROJ)",
        )
    return Choices(agents, packs, tracker)


def _tracker_type(answer: str) -> str:
    value = answer.lower() or "none"
    if value not in config.TRACKERS:
        raise ValueError(value)
    return value


def _prefix(answer: str) -> str | None:
    value = answer.upper()
    if value and not config.PREFIX.match(value):
        raise ValueError(value)
    return value or None


def _valid(ask: Ask, out: Out, prompt: str, parse: Callable[[str], Any], hint: str) -> Any:
    """Pregunta hasta que `parse` acepte la respuesta (si no, lanza ValueError)."""
    while True:
        answer = ask(prompt).strip()
        try:
            return parse(answer)
        except ValueError:
            out(f"invalid value: {answer!r}; {hint}")


def confirm(summary: list[str], *, ask: Ask | None = None, out: Out | None = None) -> bool:
    ask = ask or _input
    out = out or print
    out("About to apply:")
    for line in summary:
        out(f"  {line}")
    return ask("Continue? [y/N]: ").strip().lower() in ("y", "yes", "s", "si", "sí")
