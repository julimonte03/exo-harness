"""Detección del proyecto de la memoria desde `git remote origin`, normalizado.

La referencia dice solo «auto-detectado desde `git remote origin`
(normalizado)»; las reglas son definiciones propias:

- sin esquema, credenciales, puerto, barras de más ni `.git` final;
- la forma SCP (`git@host:ruta`) equivale a la URL;
- Azure DevOps (HTTPS, SSH y la forma vieja `<org>.visualstudio.com`) queda
  como `dev.azure.com/<org>/<proyecto>/<repo>`;
- todo en minúsculas: los hosts habituales no distinguen mayúsculas, y así
  las variantes de un mismo remoto caen en el mismo proyecto.

Sin remoto, el proyecto es `local/<carpeta>` (la raíz del repo o la carpeta).
"""

from __future__ import annotations

import configparser
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

LOCAL_PREFIX = "local/"
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_SCP = re.compile(r"^(?:[^@/\s]+@)?(?P<host>[^:/\s]+):(?P<path>[^\s]+)$")
_BARE = re.compile(r"^(?P<host>[^/\s]+\.[^/\s]+)/(?P<path>[^\s]+)$")


@dataclass(frozen=True)
class DetectedProject:
    name: str
    source: str  # git-remote | folder
    remote: str | None
    path: Path


def _split(remote: str) -> tuple[str, str] | None:
    if _SCHEME.match(remote):
        parts = urlsplit(remote)
        if not parts.hostname:
            return None
        return parts.hostname, parts.path
    for pattern in (_SCP, _BARE):
        match = pattern.match(remote)
        # Una letra sola es una unidad de Windows (C:\repo), no un host.
        if match and len(match["host"]) > 1:
            return match["host"], match["path"]
    return None


def _azure(host: str, segments: list[str]) -> list[str] | None:
    """Formas de Azure DevOps a `[org, proyecto, repo]`, o None si no es Azure."""
    if host == "dev.azure.com" and len(segments) == 4 and segments[2] == "_git":
        return [segments[0], segments[1], segments[3]]
    if host == "ssh.dev.azure.com" and len(segments) == 4 and segments[0] == "v3":
        return segments[1:]
    if host == "vs-ssh.visualstudio.com" and len(segments) == 4 and segments[0] == "v3":
        return segments[1:]
    if host.endswith(".visualstudio.com") and "_git" in segments:
        org = host.removesuffix(".visualstudio.com")
        rest = [s for s in segments if s != "defaultcollection"]
        if len(rest) == 3 and rest[1] == "_git":
            return [org, rest[0], rest[2]]
    return None


def normalize_remote(remote: str) -> str | None:
    """Nombre del proyecto para un remoto de git, o None si no parece un remoto."""
    split = _split(remote.strip())
    if split is None:
        return None
    host, path = split[0].lower(), unquote(split[1]).lower()
    segments = [s for s in path.strip("/").split("/") if s]
    if segments and segments[-1].endswith(".git"):
        segments[-1] = segments[-1].removesuffix(".git")
    segments = [s for s in segments if s]
    if not segments:
        return None
    azure = _azure(host, segments)
    if azure is not None:
        return "/".join(["dev.azure.com", *azure])
    return "/".join([host, *segments])


def canonical(name: str) -> str:
    """Nombre canónico de un proyecto guardado: el remoto normalizado, o el nombre en minúsculas."""
    return normalize_remote(name) or name.strip().lower()


def _git_root(start: Path) -> Path | None:
    for folder in (start, *start.parents):
        if (folder / ".git").exists():
            return folder
    return None


def _git_remote(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    url = result.stdout.strip()
    return url if result.returncode == 0 and url else None


def _config_remote(root: Path) -> str | None:
    """Lee `remote.origin.url` de `.git/config` sin ejecutar git."""
    config_file = root / ".git" / "config"
    if not config_file.is_file():
        return None
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        parser.read(config_file, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError):
        return None
    return parser.get('remote "origin"', "url", fallback=None)


def detect(cwd: Path) -> DetectedProject:
    cwd = Path(cwd).resolve()
    root = _git_root(cwd)
    if root is not None:
        remote = _git_remote(root) or _config_remote(root)
        name = normalize_remote(remote) if remote else None
        if name:
            return DetectedProject(name, "git-remote", remote, root)
    folder = root or cwd
    return DetectedProject(f"{LOCAL_PREFIX}{folder.name.lower()}", "folder", None, folder)
