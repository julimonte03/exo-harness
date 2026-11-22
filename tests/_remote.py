"""Remoto simulado con la forma de GitHub para los tests de los instaladores (F8).

Sirve por http en 127.0.0.1, sin salir de la máquina:

- `/<owner>/<repo>`: un repo de git servido como archivos estáticos (el protocolo
  "dumb" de git), con una foto del árbol de trabajo en `main` y el tag `v<VERSION>`;
- `/<owner>/<repo>/releases/latest`: redirige a `releases/tag/<tag>` o, si no hay
  releases (`Remote.latest = None`), a `releases`, como GitHub;
- `/<owner>/<repo>/releases/download/<tag>/`: el wheel y su `SHA256SUMS`. El release
  `BAD_TAG` trae un `SHA256SUMS` que no coincide con su wheel;
- `/raw/<script>`: los instaladores del árbol de trabajo, como
  raw.githubusercontent.com (texto en UTF-8).

El mismo repo se usa también por `file://` (`Remote.file_url`). La foto incluye los
cambios sin commitear, así los tests prueban lo que hay en disco.
"""

from __future__ import annotations

import functools
import hashlib
import http.server
import os
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

OWNER = "owner"
NAME = "exo-harness"
BAD_TAG = "v0.0.0-bad"
SCRIPTS = ("install.sh", "install.ps1", "uninstall.sh", "uninstall.ps1")


@dataclass
class Remote:
    """El remoto armado. `latest` y `requests` los ajusta y los lee cada test."""

    root: Path
    tag: str
    wheel: str
    port: int = 0
    latest: str | None = None
    requests: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/{OWNER}/{NAME}"

    @property
    def path(self) -> str:
        """Prefijo de las rutas del repo en `requests`."""
        return f"/{OWNER}/{NAME}"

    @property
    def file_url(self) -> str:
        return (self.root / OWNER / NAME).as_uri()

    def raw(self, script: str) -> str:
        return f"http://127.0.0.1:{self.port}/raw/{script}"

    def git_fetched(self) -> bool:
        """Si alguien clonó el repo por http (git pide primero `info/refs`)."""
        return any(path.startswith(f"{self.path}/info/refs") for path in self.requests)


class _Server(http.server.ThreadingHTTPServer):
    remote: Remote


class _Handler(http.server.SimpleHTTPRequestHandler):
    server: _Server

    def do_GET(self) -> None:
        remote = self.server.remote
        remote.requests.append(self.path)
        if self.path == f"{remote.path}/releases/latest":
            target = f"{remote.url}/releases"
            if remote.latest:
                target += f"/tag/{remote.latest}"
            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        super().do_GET()

    def guess_type(self, path: str | os.PathLike[str]) -> str:
        if str(path).endswith((".sh", ".ps1")):
            return "text/plain; charset=utf-8"
        return super().guess_type(path)

    def log_message(self, format: str, *args: object) -> None:
        pass


def _git_env(base: Path) -> dict[str, str]:
    """Git sin la config del dev (hooks, firmas) y con una identidad fija."""
    empty = base / "gitconfig"
    empty.write_text("", encoding="utf-8")
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": str(empty),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "exo tests",
        "GIT_AUTHOR_EMAIL": "tests@example.com",
        "GIT_COMMITTER_NAME": "exo tests",
        "GIT_COMMITTER_EMAIL": "tests@example.com",
    }


def _git(cwd: Path, env: dict[str, str], *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


def _snapshot(repo: Path, target: Path) -> None:
    """Copia lo versionado y lo nuevo que git no ignora, tal como está en disco."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    for rel in filter(None, listed.split("\0")):
        source = repo / rel
        if not source.is_file():  # borrado y sin commitear
            continue
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)


def _release(bare: Path, tag: str, wheel: Path, digest: str) -> None:
    folder = bare / "releases" / "download" / tag
    folder.mkdir(parents=True)
    shutil.copy2(wheel, folder / wheel.name)
    sdist = wheel.name.split("-py3-")[0] + ".tar.gz"
    # Como el SHA256SUMS del release: el wheel y el sdist (que el instalador ignora).
    (folder / "SHA256SUMS").write_text(
        f"{'1' * 64}  {sdist}\n{digest}  {wheel.name}\n", encoding="utf-8", newline="\n"
    )


def build(base: Path, repo: Path, version: str) -> Remote:
    """Arma el remoto en `base` a partir del árbol de trabajo de `repo`."""
    env = _git_env(base)
    snap = base / "foto"
    _snapshot(repo, snap)
    _git(snap, env, "init", "-q", "-b", "main")
    _git(snap, env, "add", "-A")
    _git(snap, env, "commit", "-q", "--no-verify", "-m", "foto del árbol de trabajo")
    tag = f"v{version}"
    _git(snap, env, "tag", tag)
    root = base / "remoto"
    bare = root / OWNER / NAME
    # --no-local: un solo pack, que el protocolo dumb baja de una vez.
    _git(base, env, "clone", "-q", "--bare", "--no-local", str(snap), str(bare))
    _git(bare, env, "update-server-info")

    wheels = base / "wheels"
    # Con uv si está (un venv de uv no trae pip); si no, con el pip de este Python.
    uv = shutil.which("uv")
    if uv:
        build_cmd = [uv, "build", "--wheel", "--quiet", "--out-dir", str(wheels), str(snap)]
    else:
        build_cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "--quiet",
                     "--disable-pip-version-check", "-w", str(wheels), str(snap)]
    subprocess.run(build_cmd, check=True, capture_output=True)
    wheel = next(wheels.glob("*.whl"))
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    _release(bare, tag, wheel, digest)
    _release(bare, BAD_TAG, wheel, "0" * 64)

    raw = root / "raw"
    raw.mkdir()
    for script in SCRIPTS:
        shutil.copy2(repo / script, raw / script)
    return Remote(root=root, tag=tag, wheel=wheel.name, latest=tag)


@contextmanager
def serve(remote: Remote) -> Iterator[Remote]:
    """Sirve el remoto en un puerto libre de 127.0.0.1 mientras dura el bloque."""
    handler = functools.partial(_Handler, directory=str(remote.root))
    server = _Server(("127.0.0.1", 0), handler)
    server.remote = remote
    remote.port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield remote
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
