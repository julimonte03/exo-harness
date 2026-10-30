"""Fixtures compartidas."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def make_dir_link() -> Callable[[Path, Path], None]:
    """Crea un link de directorio: junction en Windows (sin privilegios), symlink en POSIX."""

    def create(link: Path, target: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
        else:
            os.symlink(target, link, target_is_directory=True)

    return create
