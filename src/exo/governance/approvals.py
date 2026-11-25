"""Comandos configurados que esta máquina aprobó (threat model, TM-20, TM-21 y M-1).

`exo gate publish` ejecuta `review.publish_command` en una shell, una vez por gate. El
comando sale de la config del proyecto, que puede venir de una rama ajena o escribirla un
agente: corre solo si la persona lo aprobó en esta máquina. La aprobación queda atada a:

1. la raíz resuelta del proyecto: el mismo texto en otro repo vuelve a preguntar;
2. el texto exacto del comando: un espacio de más vuelve a preguntar;
3. el SHA256 de cada archivo del proyecto que nombra el comando (los tokens que resuelven
   a un archivo dentro de la raíz, como `scripts/publish-gate.sh`, y en Windows también
   `<palabra>.cmd` y las demás de PATHEXT, que `cmd` busca primero en la raíz): una rama que
   cambia o planta el script que corre vuelve a preguntar, y el mensaje dice cuál.

No cubre lo que esos archivos leen a su vez (un script que hace `source` de otro): por eso el
contrato `ci-and-review` recomienda un comando que no ejecute archivos de la rama.

Se guarda en `approved-commands.json`, en la carpeta de datos del usuario (nunca en el repo).
El esquema 1 guardaba solo el SHA256 del texto, válido en cualquier repo y sin los archivos:
no alcanza para el esquema 2, así que se toma como no aprobado (el mensaje lo dice) y la
próxima aprobación reescribe el archivo en el esquema actual.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exo import _meta, paths
from exo.core import fsutil

FILE_NAME = "approved-commands.json"
SCHEMA = 2
_LEGACY_SCHEMA = 1


class ApprovalError(ValueError):
    """`approved-commands.json` no se puede leer, o lo escribió un motor más nuevo."""


@dataclass(frozen=True)
class Decision:
    """Si el comando está aprobado en esta máquina para este proyecto, y por qué no."""

    project: Path
    command: str
    files: dict[str, str]  # archivos que cubre la aprobación (relativos, POSIX) -> SHA256
    approved: bool
    changed: tuple[str, ...] = ()  # cubiertos que cambiaron, aparecieron o faltan
    earlier: bool = False  # lo aprobó un motor anterior, que no ataba proyecto ni archivos


def file_path() -> Path:
    return paths.user_data_dir() / FILE_NAME


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -- lo que cubre la aprobación ---------------------------------------------------------------


def _root(project: Path) -> Path:
    return Path(project).resolve()


def _tokens(command: str) -> list[str]:
    """Las palabras del comando, como las partiría una shell, sin expandir nada.

    Se parte dos veces y se juntan: con la barra invertida como escape (`sh`) y sin escape
    (`cmd`, donde es el separador de carpetas). Un `--opción=valor` suma el valor. Si las
    comillas no cierran, se parte por espacios. Cubrir de más solo hace preguntar de más.
    """
    found: list[str] = []
    for escape in ("\\", ""):
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.escape = escape
        try:
            words = list(lexer)
        except ValueError:
            words = command.split()
        for word in words:
            found.append(word)
            if "=" in word:
                found.append(word.split("=", 1)[1])
    return list(dict.fromkeys(w for w in found if w))


def _inside(candidate: Path, root: Path) -> str | None:
    """La ruta relativa a `root` (POSIX) si `candidate` queda dentro; si no, None.

    Primero sin seguir links (un link del repo que apunta afuera también lo controla la
    rama), después resuelta (nombres cortos de Windows, mayúsculas)."""
    for path in (Path(os.path.normpath(candidate)), Path(os.path.realpath(candidate))):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if rel.parts:
            return rel.as_posix()
    return None


def _with_extensions(token: str) -> list[str]:
    """En Windows, `cmd` busca `gh` primero en la carpeta actual (la raíz del proyecto) como
    `gh.com`, `gh.exe`, `gh.bat`, `gh.cmd`... (PATHEXT): un programa que plantó la rama corre
    antes que el del PATH. Esos nombres también se cubren; en POSIX, `sh` no mira ahí."""
    if os.name != "nt" or Path(token).suffix:
        return [token]
    pathext = os.environ.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD"
    extensions = [ext.lower() for ext in pathext.split(";") if ext.startswith(".")]
    return [token, *(token + ext for ext in extensions)]


def covered_files(project: Path, command: str) -> dict[str, Path]:
    """Los archivos del proyecto que nombra el comando: ruta relativa (POSIX) -> ruta."""
    root = _root(project)
    found: dict[str, Path] = {}
    for word in _tokens(command):
        for token in _with_extensions(word):
            try:
                candidate = Path(token)
                if not candidate.is_absolute():
                    candidate = root / candidate
                rel = _inside(candidate, root)
                if rel is not None and rel not in found and candidate.is_file():
                    found[rel] = candidate
            except (OSError, ValueError):
                continue
    return dict(sorted(found.items()))


def _hashes(project: Path, command: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, path in covered_files(project, command).items():
        try:
            out[rel] = fsutil.sha256_file(path)
        except OSError:
            out[rel] = "<unreadable>"
    return out


def _key(root: Path, command: str) -> str:
    return digest(f"{os.path.normcase(str(root))}\n{command}")


# -- el archivo de aprobaciones ---------------------------------------------------------------


def _damaged(target: Path, why: str) -> ApprovalError:
    return ApprovalError(f"{target}: {why}; delete it to approve the commands again")


def _load() -> tuple[dict[str, Any], set[str]]:
    """`(aprobaciones del esquema actual, SHA256 de textos aprobados por el esquema 1)`."""
    target = file_path()
    try:
        data = json.loads(fsutil.read_bytes(target).decode("utf-8"))
    except FileNotFoundError:
        return {}, set()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _damaged(target, f"not valid JSON ({exc})") from exc
    schema = data.get("schema") if isinstance(data, dict) else None
    if isinstance(schema, int) and not isinstance(schema, bool) and schema > SCHEMA:
        raise ApprovalError(
            f"{target} was written by a newer {_meta.NAME} (schema {schema}; this engine "
            f"understands up to {SCHEMA}); upgrade {_meta.NAME} to use its approvals"
        )
    if schema == _LEGACY_SCHEMA and isinstance(data.get("commands"), dict):
        return {}, set(data["commands"])
    entries = data.get("approvals") if schema == SCHEMA else None
    if not isinstance(entries, dict) or not all(_valid(e) for e in entries.values()):
        raise _damaged(target, "unexpected content")
    return entries, set()


def _valid(entry: Any) -> bool:
    files = entry.get("files") if isinstance(entry, dict) else None
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("project"), str)
        and isinstance(entry.get("command"), str)
        and isinstance(files, dict)
        and all(isinstance(k, str) and isinstance(v, str) for k, v in files.items())
    )


def check(project: Path, command: str) -> Decision:
    """¿Está aprobado este comando para este proyecto, con estos archivos?"""
    root = _root(project)
    entries, legacy = _load()
    current = _hashes(root, command)
    entry = entries.get(_key(root, command))
    if entry is None or entry["command"] != command:
        return Decision(root, command, current, False, earlier=digest(command) in legacy)
    approved = entry["files"]
    changed = tuple(
        sorted(r for r in {*approved, *current} if approved.get(r) != current.get(r))
    )
    return Decision(root, command, current, not changed, changed)


def approve(project: Path, command: str) -> bool:
    """Aprueba el comando en esta máquina, para este proyecto y con el contenido actual de los
    archivos que nombra. Devuelve si escribió."""
    root = _root(project)
    entries, _legacy = _load()  # las del esquema 1 no sirven: se reemplazan
    key = _key(root, command)
    files = _hashes(root, command)
    previous = entries.get(key)
    if previous is not None and previous["command"] == command and previous["files"] == files:
        return False
    entries[key] = {
        "project": str(root),
        "command": command,
        "files": files,
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data = {"schema": SCHEMA, "approvals": dict(sorted(entries.items()))}
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    target = file_path()
    paths.private_dir(target.parent)
    return fsutil.write_if_changed(target, text.encode("utf-8"), mode=paths.PRIVATE_FILE)


def coverage(decision: Decision) -> str:
    """Qué cubre la aprobación, en una línea (para preguntar y para el error sin TTY)."""
    if not decision.files:
        return (
            "The approval covers this text in this project; the command names no file of "
            "the project."
        )
    return (
        "The approval covers this text in this project and the current content of the "
        f"project files it names: {', '.join(decision.files)}."
    )


def explain(decision: Decision) -> str:
    """Qué hacer con un comando sin aprobar (para los mensajes del CLI)."""
    if decision.changed:
        head = (
            f"review.publish_command was approved on this machine for {decision.project}, "
            f"but files it names changed since: {', '.join(decision.changed)}"
        )
    else:
        head = f"review.publish_command is not approved on this machine for {decision.project}"
    lines = [f"{head}:", f"  {decision.command}"]
    if decision.earlier:
        lines.append(
            f"An earlier {_meta.NAME} approved this text for every project and without the "
            "files it runs; approve it again."
        )
    lines += [
        coverage(decision),
        "It runs in a shell once per gate. Read the command and those files; if you trust "
        f"them, approve exactly that text with `{_meta.NAME} gate publish --approve-command "
        "'<the command>'` (or answer yes in a terminal). A different command, another project "
        "or a change to those files asks again.",
    ]
    return "\n".join(lines)
