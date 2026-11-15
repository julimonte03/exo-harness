"""Llamadas a git para los hooks y los chequeos, con timeout y salida en UTF-8."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_TIMEOUT = 30
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class Run:
    ok: bool
    out: str
    err: str


def run(project: Path, *args: str, stdin: bytes | None = None) -> Run:
    command = ["git", "-c", "core.quotepath=false", "-C", str(project), *args]
    try:
        done = subprocess.run(
            command, input=stdin, capture_output=True, timeout=_TIMEOUT, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Run(False, "", str(exc))
    decode = lambda raw: (raw or b"").decode("utf-8", errors="replace")  # noqa: E731
    return Run(done.returncode == 0, decode(done.stdout), decode(done.stderr))


def toplevel(project: Path) -> Path | None:
    result = run(project, "rev-parse", "--show-toplevel")
    return Path(result.out.strip()) if result.ok and result.out.strip() else None


def config_get(project: Path, key: str) -> str | None:
    result = run(project, "config", "--local", "--get", key)
    return result.out.strip() or None if result.ok else None


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


def staged_files(project: Path) -> list[str]:
    result = run(
        project, "diff", "--cached", "--name-only", "-z", "--relative", "--diff-filter=ACMR"
    )
    return [item for item in result.out.split("\0") if item] if result.ok else []


def added_lines(project: Path, *diff_args: str) -> dict[str, list[tuple[int, str]]]:
    """Líneas agregadas por archivo (`ruta -> [(número, texto)]`) de un `git diff`."""
    result = run(project, "diff", "-U0", "--no-color", "--no-ext-diff", "--relative", *diff_args)
    found: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    number = 0
    for line in result.out.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = target[2:] if target.startswith("b/") else None
            continue
        if line.startswith("--- "):
            continue
        hunk = _HUNK.match(line)
        if hunk:
            number = int(hunk.group(1))
            continue
        if current is not None and line.startswith("+"):
            found.setdefault(current, []).append((number, line[1:]))
            number += 1
    return found
