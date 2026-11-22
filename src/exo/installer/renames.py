"""Renombres conocidos del contenido (F8), para mostrar un renombre como tal.

Sin esta tabla, una skill que cambió de nombre aparece como una huérfana más y una
skill nueva. Con ella, `exo update` y `exo sync` dicen que `review` pasó a
`pre-commit-review`. La copia vieja sigue siendo una huérfana: se borra con `--prune`.

Vive en el motor y no en `content/`: describe cómo cambió lo que el motor instaló
entre versiones, y el motor y el contenido viajan juntos en el mismo paquete.
`tests/test_update.py` verifica que cada nombre nuevo exista en el contenido y que
el viejo ya no.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping

# Nombre viejo -> nombre nuevo, de skills y subagentes.
RENAMED: dict[str, str] = {
    # 1.0.0 (F7, D-40): `review` chocaba con el comando /review de Claude Code.
    "review": "pre-commit-review",
}


def rename_path(path: str, table: Mapping[str, str] | None = None) -> str | None:
    """La ruta con el nombre nuevo en el primer segmento que es un nombre viejo.

    El segmento es la carpeta de una skill (`<viejo>`) o el archivo de un subagente
    (`<viejo>.md`). None si ningún segmento coincide.
    """
    table = RENAMED if table is None else table
    parts = path.split("/")
    for index, part in enumerate(parts):
        stem, dot, rest = part.partition(".")
        if stem and stem in table:
            parts[index] = table[stem] + dot + rest
            return "/".join(parts)
    return None


def find(
    gone: Iterable[str], planned: Collection[str], table: Mapping[str, str] | None = None
) -> dict[str, str]:
    """`{ruta vieja: ruta nueva}` de lo que se fue y tiene su versión renombrada en el plan."""
    found: dict[str, str] = {}
    for path in gone:
        new = rename_path(path, table)
        if new is not None and new in planned:
            found[path] = new
    return found
