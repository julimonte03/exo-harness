"""Llamadas a git para los hooks y los chequeos, con timeout y salida en UTF-8.

El diff que se escanea no depende de la config del dev ni de los atributos del
repo: `--text` (un `-diff` o `binary` en `.gitattributes` no esconde contenido),
sin textconv ni diff externo, y prefijos `a/` y `b/` explícitos (aunque haya
`diff.noprefix` o `diff.mnemonicPrefix`). El parser sigue los contadores de cada
hunk, así que una línea de contenido que empieza con `++ ` o `-- ` no se confunde
con un encabezado, y decodifica los nombres que git entrecomilla.

Si git falla, se levanta `GitError`: no escanear nunca pasa como "no hay nada".
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_TIMEOUT = 30
_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_FLAGS = (
    "-U0",
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "--text",
    "--src-prefix=a/",
    "--dst-prefix=b/",
    "--relative",
)
# El árbol vacío: la base de una rama nueva sin historia en común con nada.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}
_OCTAL = re.compile(r"[0-7]{3}")


class GitError(RuntimeError):
    """Git no corrió o falló: lo que dependía de él no se pudo verificar."""


@dataclass(frozen=True)
class Run:
    ok: bool
    out: str
    err: str


def run(project: Path, *args: str, stdin: bytes | None = None, timeout: float | None = None) -> Run:
    command = ["git", "-c", "core.quotepath=false", "-C", str(project), *args]
    try:
        done = subprocess.run(
            command, input=stdin, capture_output=True, timeout=timeout or _TIMEOUT, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Run(False, "", str(exc))
    decode = lambda raw: (raw or b"").decode("utf-8", errors="replace")  # noqa: E731
    return Run(done.returncode == 0, decode(done.stdout), decode(done.stderr))


def _required(project: Path, *args: str) -> str:
    result = run(project, *args)
    if not result.ok:
        detail = result.err.strip() or "no output"
        raise GitError(f"git {' '.join(args[:2])} failed: {detail}")
    return result.out


def toplevel(project: Path) -> Path | None:
    result = run(project, "rev-parse", "--show-toplevel")
    return Path(result.out.strip()) if result.ok and result.out.strip() else None


def config_get(project: Path, key: str) -> str | None:
    result = run(project, "config", "--local", "--get", key)
    return result.out.strip() or None if result.ok else None


def config_get_any(project: Path, key: str) -> tuple[str, str] | None:
    """`(scope, valor)` del valor efectivo, mirando todos los scopes (local, global, system)."""
    result = run(project, "config", "--show-scope", "--get", key)
    if not result.ok or not result.out.strip():
        return None
    scope, _, value = result.out.strip().partition("\t")
    return (scope, value) if value else ("unknown", scope)


def config_set(project: Path, key: str, value: str) -> bool:
    return run(project, "config", "--local", key, value).ok


def config_unset(project: Path, key: str) -> bool:
    return run(project, "config", "--local", "--unset", key).ok


def is_zero(sha: str) -> bool:
    return bool(sha) and set(sha) == {"0"}


def is_ancestor(project: Path, older: str, newer: str) -> bool | None:
    """¿`older` es ancestro de `newer`? None si git no puede saberlo (falta el objeto)."""
    result = run(project, "merge-base", "--is-ancestor", older, newer)
    if result.ok:
        return True
    probe = run(project, "cat-file", "-e", f"{older}^{{commit}}")
    return False if probe.ok else None


def resolve(project: Path, ref: str) -> str | None:
    """El commit al que apunta `ref`, o None si no existe."""
    result = run(project, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return result.out.strip() or None if result.ok else None


def merge_base(project: Path, one: str, other: str) -> str | None:
    result = run(project, "merge-base", one, other)
    return result.out.strip() or None if result.ok else None


def staged_files(project: Path) -> list[str]:
    out = _required(
        project, "diff", "--cached", "--name-only", "-z", "--relative", "--diff-filter=ACMR"
    )
    return [item for item in out.split("\0") if item]


def added_lines(project: Path, *diff_args: str) -> dict[str, list[tuple[int, str]]]:
    """Líneas agregadas por archivo (`ruta -> [(número, texto)]`) de un `git diff`."""
    return parse_added(_required(project, "diff", *_DIFF_FLAGS, *diff_args))


def _unquote(raw: str) -> str:
    """Un nombre entrecomillado al estilo C, como lo escribe git (`"b/a\\"b.txt"`)."""
    body = raw[1:-1] if len(raw) > 1 and raw.endswith('"') else raw[1:]
    out = bytearray()
    index = 0
    while index < len(body):
        char = body[index]
        if char == "\\" and index + 1 < len(body):
            octal = body[index + 1 : index + 4]
            if _OCTAL.fullmatch(octal):
                out.append(int(octal, 8))
                index += 4
                continue
            code = _ESCAPES.get(body[index + 1])
            if code is not None:
                out.append(code)
                index += 2
                continue
        out.extend(char.encode("utf-8"))
        index += 1
    return out.decode("utf-8", errors="replace")


def _target(raw: str) -> str | None:
    # Git agrega un tab al final del encabezado cuando el nombre tiene espacios.
    raw = raw[:-1] if raw.endswith("\t") else raw
    if raw.startswith('"'):
        raw = _unquote(raw)
    return raw[2:] if raw.startswith("b/") else None


def parse_added(text: str) -> dict[str, list[tuple[int, str]]]:
    """Parser con estado de `git diff -U0`: los encabezados solo valen fuera de un hunk."""
    found: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    in_header = False
    old_left = new_left = 0
    number = 0
    for raw in text.split("\n"):
        line = raw[:-1] if raw.endswith("\r") else raw
        if old_left > 0 or new_left > 0:
            if line.startswith("+"):
                if current is not None:
                    found.setdefault(current, []).append((number, line[1:]))
                number += 1
                new_left -= 1
            elif line.startswith("-"):
                old_left -= 1
            elif line.startswith(" "):
                old_left -= 1
                new_left -= 1
                number += 1
            elif not line.startswith("\\"):
                old_left = new_left = 0  # salida inesperada: se descarta el hunk
            continue
        if line.startswith("diff --git "):
            current = None
            in_header = True
            continue
        hunk = _HUNK.match(line)
        if hunk:
            in_header = False
            old_left = int(hunk.group(1)) if hunk.group(1) is not None else 1
            number = int(hunk.group(2))
            new_left = int(hunk.group(3)) if hunk.group(3) is not None else 1
            continue
        if in_header and line.startswith("+++ "):
            current = _target(line[4:])
    return found
