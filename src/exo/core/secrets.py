"""Fachada del escáner para el contenido del motor: solo secretos, sin datos personales.

El escáner completo, con los detectores de datos personales, está en
`core/scan.py` (ADR-0014). `exo validate` usa esta fachada sobre `content/`.
"""

from __future__ import annotations

from exo.core.scan import Finding as SecretFinding
from exo.core.scan import scan_text as _scan_text

__all__ = ["SecretFinding", "scan_text"]


def scan_text(text: str, *, skip_code_blocks: bool = True) -> list[SecretFinding]:
    return _scan_text(text, skip_code_blocks=skip_code_blocks, pii=())
