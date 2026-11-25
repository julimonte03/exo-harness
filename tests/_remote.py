"""Remoto simulado con la forma de GitHub para los tests de los instaladores (F8).

Sirve por http en 127.0.0.1, sin salir de la máquina:

- `/<owner>/<repo>`: un repo de git servido como archivos estáticos (el protocolo
  "dumb" de git), con una foto del árbol de trabajo en `main` y el tag `v<VERSION>`;
- `/<owner>/<repo>/releases/latest`: redirige a `releases/tag/<tag>` o, si no hay
  releases (`Remote.latest = None`), a `releases`, como GitHub;
- `/<owner>/<repo>/releases/download/<tag>/`: el wheel y su `SHA256SUMS`. El release
  `BAD_TAG` trae un `SHA256SUMS` que no coincide con su wheel, y `NO_SUMS_TAG`, que
  también es un tag de git, trae el wheel sin `SHA256SUMS`. En `REDIRECT_TAG` el
  `SHA256SUMS` está y el wheel redirige (302) a otro protocolo: a `https://` en un
  puerto de 127.0.0.1 que rechaza las conexiones (`Remote.redirect_to`);
- `/<owner>/<REDIRECT_REPO>/...`: todo redirige a `Remote.redirect_to`, también lo que
  pide git (`info/refs`): un clon que siguiera el salto cambiaría de protocolo;
- `/raw/<script>`: los instaladores del árbol de trabajo, como
  raw.githubusercontent.com (texto en UTF-8).

El mismo repo se usa también por `file://` (`Remote.file_url`). La foto incluye los
cambios sin commitear, así los tests prueban lo que hay en disco. `Remote.commit` le
agrega un commit a una rama, para probar que volver a instalarla trae el commit nuevo.
"""

from __future__ import annotations

import functools
import hashlib
import http.server
import os
import shutil
import socket
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
NO_SUMS_TAG = "v0.0.0-nosums"
REDIRECT_TAG = "v0.0.0-redirect"
REDIRECT_REPO = f"{NAME}-redirige"
SCRIPTS =("install.sh", "install.ps1", "uninstall.sh", "uninstall.ps1")


@dataclass
class Remote:
    """El remoto armado. `latest` y `requests` los ajusta y los lee cada test."""

    root: Path
    tag: str
    wheel: str
    port: int = 0
    latest: str | None = None
    requests: list[str] = field(default_factory=list)
    # Adónde redirige el wheel de REDIRECT_TAG: si un cliente siguiera el salto, la
    # conexión se rechaza enseguida, sin colgarse ni llegar a nada real.
    redirect_to: str = ""
    # El repo de trabajo del que sale el remoto: `commit` agrega ahí y publica.
    work: Path | None = None

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

    @property
    def redirect_repo_url(self) -> str:
        """Un repo en el que todo redirige a otro protocolo (`redirect_to`)."""
        return f"http://127.0.0.1:{self.port}/{OWNER}/{REDIRECT_REPO}"

    def redirect_repo_fetched(self) -> bool:
        """Si git pidió el repo que redirige (`info/refs`)."""
        prefix = f"/{OWNER}/{REDIRECT_REPO}/info/refs"
        return any(path.startswith(prefix) for path in self.requests)

    def raw(self, script: str) -> str:
        return f"http://127.0.0.1:{self.port}/raw/{script}"

    def git_fetched(self) -> bool:
        """Si alguien clonó el repo por http (git pide primero `info/refs`)."""
        return any(path.startswith(f"{self.path}/info/refs") for path in self.requests)

    def commit(self, branch: str, files: dict[str, str]) -> None:
        """Agrega un commit con `files` (ruta relativa -> texto) a `branch`, que sale de
        `main` si no existe, y lo publica en el remoto. `main` y los tags no cambian."""
        assert self.work is not None, "Remote.commit needs the work repo of build()"
        env = _git_env(self.work.parent)
        exists = subprocess.run(
            ["git", "rev-parse", "--verify", "-q", f"refs/heads/{branch}"],
            cwd=self.work,
            env=env,
            capture_output=True,
            check=False,
        )
        if exists.returncode == 0:
            _git(self.work, env, "checkout", "-q", branch)
        else:
            _git(self.work, env, "checkout", "-q", "-b", branch, "main")
        for rel, text in files.items():
            target = self.work / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        _git(self.work, env, "add", "--", *files)
        _git(self.work, env, "commit", "-q", "--no-verify", "-m", f"cambio en {branch}")
        _git(self.work, env, "checkout", "-q", "main")
        bare = self.root / OWNER / NAME
        _git(self.work, env, "push", "-q", str(bare), branch)
        _git(bare, env, "update-server-info")


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
            self._redirect(target)
            return
        redirected = f"{remote.path}/releases/download/{REDIRECT_TAG}/"
        if self.path.startswith(redirected) and not self.path.endswith("/SHA256SUMS"):
            self._redirect(remote.redirect_to + self.path)
            return
        if self.path.startswith(f"/{OWNER}/{REDIRECT_REPO}/"):
            self._redirect(remote.redirect_to + self.path)
            return
        super().do_GET()

    def _redirect(self, target: str) -> None:
        self.send_response(302)
        self.send_header("Location", target)
        self.send_header("Content-Length", "0")
        self.end_headers()

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
    _git(snap, env, "tag", NO_SUMS_TAG)
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
    # Un release sin SHA256SUMS: si el instalador pasara a git, el tag está y se instalaría.
    _release(bare, NO_SUMS_TAG, wheel, digest)
    (bare / "releases" / "download" / NO_SUMS_TAG / "SHA256SUMS").unlink()
    # Su wheel no se sirve: el handler lo redirige a otro protocolo.
    _release(bare, REDIRECT_TAG, wheel, digest)

    raw = root / "raw"
    raw.mkdir()
    for script in SCRIPTS:
        shutil.copy2(repo / script, raw / script)
    return Remote(root=root, tag=tag, wheel=wheel.name, latest=tag, work=snap)


@contextmanager
def serve(remote: Remote) -> Iterator[Remote]:
    """Sirve el remoto en un puerto libre de 127.0.0.1 mientras dura el bloque."""
    handler = functools.partial(_Handler, directory=str(remote.root))
    server = _Server(("127.0.0.1", 0), handler)
    server.remote = remote
    remote.port = server.server_address[1]
    # Un puerto tomado sin listen(): nadie más lo usa y rechaza cada conexión.
    refused = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    refused.bind(("127.0.0.1", 0))
    remote.redirect_to = f"https://127.0.0.1:{refused.getsockname()[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield remote
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        refused.close()
