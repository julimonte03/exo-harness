"""Vista de terminal de `exo status` (F8): el proyecto y sus changes activos.

Junta lo que ya calculan otros módulos (la instalación, los hooks, la persona y la
observabilidad de los changes) y lo arma en líneas. Los colores son ANSI, solo en una
TTY y sin `NO_COLOR` (no-color.org); en Windows, además, solo si la consola acepta el
modo VT. `exo status --json` no pasa por acá: su salida no cambia.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exo import _meta, persona
from exo.core import lock
from exo.governance import githooks
from exo.installer import project as installed
from exo.sdd import observability, speclint

_CODES = {"ok": "32", "warn": "33", "bad": "31", "dim": "2", "bold": "1"}
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TIER_SOURCE = {"missing": "unclassified", "unreadable": "unreadable assessment"}
_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004


def _enable_vt(
    stream: Any, kernel32: Any = None, get_handle: Callable[[int], int] | None = None
) -> bool:
    """Activa el modo VT de la consola de Windows para `stream`; False si no se puede.

    Sin `ENABLE_VIRTUAL_TERMINAL_PROCESSING`, conhost muestra los códigos ANSI como texto.
    `kernel32` y `get_handle` se inyectan en los tests."""
    try:
        import ctypes

        if kernel32 is None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        if get_handle is None:
            import msvcrt

            get_handle = msvcrt.get_osfhandle  # type: ignore[attr-defined]
        handle = get_handle(stream.fileno())
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False  # no es una consola
        if mode.value & _ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            return True
        wanted = mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return bool(kernel32.SetConsoleMode(handle, wanted))
    except (AttributeError, ImportError, OSError, ValueError):
        return False


def use_color(stream: Any, env: Mapping[str, str], *, windows: bool | None = None) -> bool:
    """Colores solo en una TTY, sin `NO_COLOR` (si no está vacía) y sin `TERM=dumb`. En
    Windows, solo si se pudo activar el modo VT de la consola (F8R1-6)."""
    if env.get("NO_COLOR") or env.get("TERM") == "dumb":
        return False
    isatty = getattr(stream, "isatty", None)
    if not (isatty and isatty()):
        return False
    if sys.platform == "win32" if windows is None else windows:
        return _enable_vt(stream)
    return True


@dataclass(frozen=True)
class Style:
    color: bool = False

    def paint(self, kind: str, text: str) -> str:
        return f"\x1b[{_CODES[kind]}m{text}\x1b[0m" if self.color else text

    @staticmethod
    def strip(text: str) -> str:
        return _ANSI.sub("", text)


@dataclass
class ChangeRow:
    name: str
    tier: int
    tier_source: str
    phase: str | None
    next_phase: str | None
    next_reason: str
    gates: list[speclint.GateInfo]
    followups_open: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class View:
    info: installed.Status
    hooks: githooks.Status
    persona: str | None
    persona_error: str | None
    changes: list[ChangeRow]
    changes_error: str | None = None


def _gates(folder: Path) -> list[speclint.GateInfo]:
    found = []
    for path in sorted((folder / "gates").glob("*.md")) if (folder / "gates").is_dir() else []:
        try:
            found.append(speclint.gate_info(path))
        except (OSError, ValueError):
            found.append(speclint.GateInfo(path.stem, None, True, path))
    return found


def _changes(project: Path) -> list[ChangeRow]:
    rows = []
    for change in observability.find_changes(project, include_archived=False):
        state = observability.state_of(project, change)
        rows.append(
            ChangeRow(
                name=state["name"],
                tier=state["tier"],
                tier_source=state["tier_source"],
                phase=state["phase"],
                next_phase=state["next_phase"],
                next_reason=state["next_reason"],
                gates=_gates(Path(project) / change.path),
                followups_open=state["followups"]["open"],
                warnings=list(state["warnings"]),
            )
        )
    return rows


def gather(project: Path, info: installed.Status | None = None) -> View:
    """Lee el estado del proyecto. Un problema en una parte se muestra, no corta la vista."""
    project = Path(project)
    info = info or installed.status(project)
    try:
        role, role_error = persona.read(), None
    except persona.PersonaError as exc:
        role, role_error = None, str(exc)
    except OSError as exc:
        role, role_error = None, f"could not read {persona.file_path()}: {exc}"
    view = View(info, githooks.status(project), role, role_error, [])
    try:
        view.changes = _changes(project)
    except (OSError, ValueError) as exc:
        view.changes_error = str(exc)
    return view


def _engine(info: installed.Status, style: Style) -> str:
    line = f"engine: {_meta.VERSION} (lock written by {info.lock_version}"
    if info.lock_version == _meta.VERSION:
        return line + ")"
    # Un lock más nuevo: `exo update` lo rechaza, así que se actualiza el motor (como doctor).
    if info.lock_version and lock.newer_than_engine(info.lock_version):
        return line + "; " + style.paint("warn", f"upgrade {_meta.NAME}") + ")"
    return line + "; " + style.paint("warn", f"run `{_meta.NAME} update`") + ")"


def _hooks(hooks: githooks.Status, style: Style) -> str:
    if hooks.status == "ok":
        return "hooks: " + style.paint("ok", "ok") + f" ({hooks.detail})"
    if hooks.status == "warn":
        return "hooks: " + style.paint("warn", f"warning: {hooks.detail}")
    return f"hooks: {hooks.detail}"


def _persona(view: View, style: Style) -> str:
    if view.persona_error:
        return "persona: " + style.paint("warn", f"warning: {view.persona_error}")
    if view.persona:
        return f"persona: {view.persona}"
    return f"persona: none (`{_meta.NAME} persona set <role>`)"


def _gate(info: speclint.GateInfo, style: Style) -> str:
    if info.verdict is None:
        return f"{info.name} " + style.paint("bad", "unreadable")
    if not info.needs_approval:
        return f"{info.name} " + style.paint("ok", info.verdict)
    return f"{info.name} " + style.paint("warn", f"{info.verdict} (needs tech_lead)")


def _change(row: ChangeRow, style: Style) -> list[str]:
    tier = f"Tier {row.tier}"
    if row.tier_source in _TIER_SOURCE:
        tier += f" ({_TIER_SOURCE[row.tier_source]})"
    head = (
        f"  {style.paint('bold', row.name)}  {tier}  phase: {row.phase or '-'}  "
        f"next: {row.next_phase or '-'} " + style.paint("dim", f"({row.next_reason})")
    )
    gates = ", ".join(_gate(g, style) for g in row.gates) if row.gates else "none yet"
    lines = [head, f"    gates: {gates}"]
    if row.followups_open:
        lines.append("    followups: " + style.paint("warn", f"{row.followups_open} open"))
    lines += ["    " + style.paint("warn", f"warning: {w}") for w in row.warnings]
    return lines


def render(view: View, style: Style) -> list[str]:
    info = view.info
    lines = [
        f"agents: {', '.join(info.agents)}",
        f"packs: {', '.join(info.packs)}",
        _engine(info, style),
        f"managed files: {info.files}",
        _hooks(view.hooks, style),
        _persona(view, style),
    ]
    for drift in info.drift:
        entry = drift.entry
        text = f"manual change: {entry.path} ({entry.kind}): {drift.status}"
        lines.append(style.paint("warn", text))
    if not info.drift:
        lines.append("no manual changes to generated files")
    lines += [style.paint("warn", f"warning: {w}") for w in info.warnings]
    lines.append("")
    if view.changes_error:
        lines.append("changes: " + style.paint("bad", f"could not read them: {view.changes_error}"))
    elif not view.changes:
        lines.append("changes: none active")
    else:
        lines.append(style.paint("bold", f"changes: {len(view.changes)} active"))
        for row in view.changes:
            lines += _change(row, style)
    return lines
