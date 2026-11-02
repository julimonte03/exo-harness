"""Fixtures de proyecto para los golden tests de adopción (sintéticos, sin datos reales).

Se arman en código y no como carpetas versionadas, para que el repo no tenga
`AGENTS.md`, `CLAUDE.md` ni `.claude/` anidados que los agentes confundan con
los del motor.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from pathlib import Path

from exo import _meta

HUMAN_AGENTS = "# Reglas del equipo\n\n- Usar tipos en todo el código.\n- Nada de prints de depuración.\n"
HUMAN_CLAUDE = "# Notas para Claude\n\nPreferir cambios chicos.\n"


def _write(root: Path, rel: str, data: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def vacio(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)


def agents_humano(root: Path) -> None:
    _write(root, "AGENTS.md", HUMAN_AGENTS.encode())


def claude_existente(root: Path) -> None:
    _write(root, "AGENTS.md", HUMAN_AGENTS.encode())
    _write(root, "CLAUDE.md", HUMAN_CLAUDE.encode())


def crlf(root: Path) -> None:
    _write(root, "AGENTS.md", HUMAN_AGENTS.replace("\n", "\r\n").encode())
    _write(root, "CLAUDE.md", HUMAN_CLAUDE.replace("\n", "\r\n").encode())
    _write(root, ".gitignore", b"node_modules/\r\n*.log\r\n")


def mcp_jsonc(root: Path) -> None:
    _write(root, ".mcp.json", b'{\n  // servidores del equipo\n  "mcpServers": {}\n}\n')


FIXTURES: dict[str, Callable[[Path], None]] = {
    "vacio": vacio,
    "agents-humano": agents_humano,
    "claude-existente": claude_existente,
    "crlf": crlf,
    "mcp-jsonc": mcp_jsonc,
}


def tree(root: Path) -> dict[str, bytes]:
    """Archivos del proyecto, sin los backups (llevan fecha)."""
    backups = root / _meta.PROJECT_DIR / "backups"
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not p.is_relative_to(backups)
    }


def encode_tree(files: dict[str, bytes]) -> str:
    out = {}
    for rel, data in sorted(files.items()):
        try:
            out[rel] = data.decode("utf-8")
        except UnicodeDecodeError:
            out[rel] = {"base64": base64.b64encode(data).decode("ascii")}
    return json.dumps({"files": out}, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def decode_tree(text: str) -> dict[str, bytes]:
    files = json.loads(text)["files"]
    return {
        rel: base64.b64decode(value["base64"]) if isinstance(value, dict) else value.encode("utf-8")
        for rel, value in files.items()
    }
