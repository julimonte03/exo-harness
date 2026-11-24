"""Comandos configurados que esta máquina aprobó (threat model, TM-21 y M-1).

`exo gate publish` ejecuta `review.publish_command` en una shell, una vez por gate. El
comando sale de la config del proyecto, que puede venir de una rama ajena o escribirla un
agente: corre solo si la persona lo aprobó en esta máquina. Se guarda el SHA256 del texto
exacto en `approved-commands.json`, en la carpeta de datos del usuario (nunca en el repo):
un comando distinto, aunque sea por un espacio, vuelve a pedir aprobación.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exo import _meta, paths
from exo.core import fsutil

FILE_NAME = "approved-commands.json"
SCHEMA = 1


class ApprovalError(ValueError):
    """`approved-commands.json` no se puede leer."""


def file_path() -> Path:
    return paths.user_data_dir() / FILE_NAME


def digest(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def _load() -> dict[str, Any]:
    target = file_path()
    try:
        data = json.loads(fsutil.read_bytes(target).decode("utf-8"))
    except FileNotFoundError:
        return {"schema": SCHEMA, "commands": {}}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApprovalError(
            f"{target}: not valid JSON ({exc}); delete it to approve the commands again"
        ) from exc
    if (
        not isinstance(data, dict)
        or data.get("schema") != SCHEMA
        or not isinstance(data.get("commands"), dict)
    ):
        raise ApprovalError(
            f"{target}: unexpected content; delete it to approve the commands again"
        )
    return data


def is_approved(command: str) -> bool:
    return digest(command) in _load()["commands"]


def approve(command: str) -> bool:
    """Aprueba el comando en esta máquina. Devuelve si escribió."""
    data = _load()
    key = digest(command)
    if key in data["commands"]:
        return False
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data["commands"][key] = {"command": command, "approved_at": stamp}
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    target = file_path()
    paths.private_dir(target.parent)
    return fsutil.write_if_changed(target, text.encode("utf-8"), mode=paths.PRIVATE_FILE)


def explain(command: str) -> str:
    """Qué hacer con un comando sin aprobar (para los mensajes del CLI)."""
    return (
        f"review.publish_command is not approved on this machine:\n  {command}\n"
        "It runs in a shell once per gate. If you trust it, approve exactly that text with "
        f"`{_meta.NAME} gate publish --approve-command '<the command>'` (or answer yes in a "
        "terminal); a different command asks again"
    )
