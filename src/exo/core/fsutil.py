"""Escritura atómica, hashes y saneo de rutas.

Invariantes 2 y 3 de `docs/plan/02-ARQUITECTURA.md` §2.13: idempotencia por
SHA256 y escrituras atómicas (temporal en el mismo directorio + `os.replace`).
Todo se escribe en binario, para copiar skills byte a byte y conservar los
fines de línea del humano.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import stat
import sys
import tempfile
import time
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath

_RETRIES = 5
_RETRY_DELAY = 0.05
_CHUNK = 1024 * 1024
_DEFAULT_MODE = 0o644
_WINDOWS_MAX_PATH = 240


class UnsafePathError(ValueError):
    """Una ruta relativa intenta salir de su raíz o no es portable."""


_LONG_PREFIX = "\\\\?\\"


def _os_path(path: Path) -> str:
    """Ruta para el sistema operativo, con prefijo `\\\\?\\` en rutas largas de Windows."""
    text = str(path)
    if sys.platform == "win32" and len(text) >= _WINDOWS_MAX_PATH:
        if text.startswith(_LONG_PREFIX):
            return text
        absolute = os.path.abspath(text)
        if absolute.startswith("\\\\"):
            return _LONG_PREFIX + "UNC\\" + absolute[2:]
        return _LONG_PREFIX + absolute
    return text


def read_bytes(path: Path) -> bytes:
    with open(_os_path(Path(path)), "rb") as fh:
        return fh.read()


def _replace_with_retry(src: str, dst: str) -> None:
    # En Windows, antivirus e indexadores bloquean archivos un instante.
    for attempt in range(_RETRIES):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == _RETRIES - 1:
                raise
            time.sleep(_RETRY_DELAY * (attempt + 1))


def write_atomic(path: Path, data: bytes, *, mode: int | None = None) -> None:
    """Escribe `data` en `path` de forma atómica.

    Conserva el modo del archivo existente; los nuevos quedan en 0644 salvo que
    se indique `mode`.
    """
    target = Path(path)
    os_target = _os_path(target)
    os_parent = _os_path(target.parent)
    os.makedirs(os_parent, exist_ok=True)
    if mode is None:
        try:
            mode = stat.S_IMODE(os.stat(os_target).st_mode)
        except FileNotFoundError:
            mode = _DEFAULT_MODE
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=os_parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        _replace_with_retry(tmp, os_target)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def write_if_changed(path: Path, data: bytes, *, mode: int | None = None) -> bool:
    """Escribe solo si el contenido cambia. Devuelve si escribió."""
    try:
        if read_bytes(path) == data:
            return False
    except FileNotFoundError:
        pass
    write_atomic(path, data, mode=mode)
    return True


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(_os_path(Path(path)), "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relpath(raw: str | PurePath) -> PurePosixPath:
    """Normaliza una ruta relativa portable o la rechaza.

    Rechaza vacías, absolutas (POSIX, Windows, UNC), con letra de unidad, con
    componentes `..` o con bytes nulos. Acepta `\\` como separador.
    """
    text = str(raw)
    if not text or "\x00" in text:
        raise UnsafePathError(f"ruta vacía o con bytes nulos: {text!r}")
    windows = PureWindowsPath(text)
    if windows.drive or windows.root or text.startswith(("/", "\\")):
        raise UnsafePathError(f"la ruta tiene que ser relativa, sin unidad ni raíz: {text!r}")
    parts = [part for part in text.replace("\\", "/").split("/") if part not in ("", ".")]
    if not parts:
        raise UnsafePathError(f"la ruta no apunta a nada: {text!r}")
    if ".." in parts:
        raise UnsafePathError(f"la ruta no puede contener '..': {text!r}")
    return PurePosixPath(*parts)


def resolve_within(root: Path, raw: str | PurePath) -> Path:
    """Resuelve `raw` dentro de `root`, siguiendo symlinks, y verifica que no escape."""
    base = Path(root).resolve()
    candidate = base.joinpath(*safe_relpath(raw).parts).resolve()
    if not candidate.is_relative_to(base):
        raise UnsafePathError(f"la ruta sale de {base}: {raw!r}")
    return candidate
