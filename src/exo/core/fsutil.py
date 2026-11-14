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
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


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


def is_link(path: Path) -> bool:
    """Symlink, o junction de Windows (directorio con reparse point). No sigue el link."""
    try:
        info = os.lstat(_os_path(Path(path)))
    except (FileNotFoundError, NotADirectoryError):
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISDIR(info.st_mode) and bool(attributes & _REPARSE_POINT)


def walk_files(root: Path) -> list[Path]:
    """Archivos regulares bajo `root`, ordenados, sin entrar en symlinks ni junctions."""
    found: list[Path] = []
    pending = [Path(root)]
    while pending:
        folder = pending.pop()
        try:
            entries = sorted(os.scandir(folder), key=lambda e: e.name)
        except (FileNotFoundError, NotADirectoryError):
            continue
        for entry in entries:
            path = Path(entry.path)
            if is_link(path):
                continue
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                found.append(path)
    return sorted(found)


def _os_parent(target: Path, os_target: str) -> str:
    """Directorio del temporal: con prefijo de ruta larga si el destino lo necesita.

    El temporal tiene un nombre más largo que el destino; si el destino ya pasa
    el límite, el directorio prefijado evita que el temporal falle cuando
    Windows no tiene habilitadas las rutas largas.
    """
    if os_target.startswith(_LONG_PREFIX):
        return os.path.dirname(os_target)
    return _os_path(target.parent)


def write_atomic(
    path: Path, data: bytes, *, mode: int | None = None, follow_symlinks: bool = True
) -> None:
    """Escribe `data` en `path` de forma atómica.

    Conserva el modo del archivo existente; los nuevos quedan en 0644 salvo que
    se indique `mode`. Si `path` es un symlink, por defecto escribe en su destino
    (por ejemplo `CLAUDE.md -> AGENTS.md`) en lugar de reemplazar el link; que el
    destino quede dentro del proyecto lo verifica quien llama (`resolve_within`).
    """
    target = Path(path)
    if follow_symlinks and os.path.islink(_os_path(target)):
        target = Path(os.path.realpath(_os_path(target)))
    os_target = _os_path(target)
    os_parent = _os_parent(target, os_target)
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
        # En Windows no se puede borrar un archivo de solo lectura: el temporal ya
        # tiene el modo del destino.
        with contextlib.suppress(OSError):
            os.chmod(tmp, stat.S_IREAD | stat.S_IWRITE)
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def write_if_changed(
    path: Path, data: bytes, *, mode: int | None = None, follow_symlinks: bool = True
) -> bool:
    """Escribe solo si el contenido cambia. Devuelve si escribió."""
    try:
        if read_bytes(path) == data and (follow_symlinks or not os.path.islink(path)):
            return False
    except (FileNotFoundError, IsADirectoryError):
        pass
    write_atomic(path, data, mode=mode, follow_symlinks=follow_symlinks)
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
        raise UnsafePathError(f"empty path or path with null bytes: {text!r}")
    windows = PureWindowsPath(text)
    if windows.drive or windows.root or text.startswith(("/", "\\")):
        raise UnsafePathError(f"the path must be relative, with no drive or root: {text!r}")
    parts = [part for part in text.replace("\\", "/").split("/") if part not in ("", ".")]
    if not parts:
        raise UnsafePathError(f"the path points to nothing: {text!r}")
    if ".." in parts:
        raise UnsafePathError(f"the path cannot contain '..': {text!r}")
    return PurePosixPath(*parts)


def join_within(root: Path, raw: str | PurePath) -> Path:
    """Ruta dentro de `root` armada sin resolver, rechazando cualquier componente que sea link.

    Es la forma segura de obtener una ruta para escribir o borrar: el motor no
    gestiona rutas que pasan por symlinks o junctions.
    """
    current = Path(root)
    for part in safe_relpath(raw).parts:
        current = current / part
        if is_link(current):
            raise UnsafePathError(
                f"{raw}: {current} is a symlink or junction; the engine does not manage paths "
                "through links"
            )
    return current


def resolve_within(root: Path, raw: str | PurePath) -> Path:
    """Resuelve `raw` dentro de `root`, siguiendo symlinks, y verifica que no escape."""
    base = Path(root).resolve()
    candidate = base.joinpath(*safe_relpath(raw).parts).resolve()
    if not candidate.is_relative_to(base):
        raise UnsafePathError(f"the path escapes {base}: {raw!r}")
    return candidate


def read_text_auto(path: Path) -> str:
    """Texto de un archivo que puede venir de otra herramienta: UTF-8 (con o sin BOM) o UTF-16
    con BOM, que es lo que escribe Windows PowerShell 5.1 con `>` u `Out-File`.

    Cualquier otra codificación es un `ValueError` con qué hacer.
    """
    data = read_bytes(Path(path))
    try:
        if data.startswith((b"\xff\xfe", b"\xfe\xff")):
            return data.decode("utf-16")
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"{path} is not UTF-8 or UTF-16 text ({exc.reason}); save it as UTF-8, for example "
            "with your editor or `Set-Content -Encoding utf8` in PowerShell"
        ) from exc
