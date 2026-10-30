"""Ubicación del contenido canónico (`content/`: packs, reglas, contratos, plantillas).

Orden de búsqueda:
1. la variable `<ENV_PREFIX>CONTENT_ROOT` (desarrollo o contenido propio);
2. el contenido empaquetado en la wheel (`exo/_content`);
3. `content/` del repo, cuando el paquete se instaló en modo editable.
"""

from __future__ import annotations

import os
from pathlib import Path

from exo import _meta

ENV_VAR = f"{_meta.ENV_PREFIX}CONTENT_ROOT"
_PACKAGE_DIR = Path(__file__).resolve().parent
_CANDIDATES: tuple[Path, ...] = (_PACKAGE_DIR / "_content", _PACKAGE_DIR.parents[1] / "content")


class ContentError(RuntimeError):
    """No hay contenido canónico disponible."""


def _valid(root: Path) -> bool:
    return (root / "packs").is_dir()


def content_root() -> Path:
    override = os.environ.get(ENV_VAR)
    if override:
        root = Path(override).expanduser().resolve()
        if not _valid(root):
            raise ContentError(f"{ENV_VAR}={override} no apunta a un contenido con packs/")
        return root
    for candidate in _CANDIDATES:
        if _valid(candidate):
            return candidate
    raise ContentError(
        "no se encontró el contenido del motor (packs/); reinstalá el paquete o definí "
        f"{ENV_VAR}"
    )
