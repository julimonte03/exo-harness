"""Única fuente de los nombres visibles del motor (D-01, ADR-0001).

Ningún otro módulo de `src/exo` puede escribir estos valores como literal;
`tests/test_meta.py` lo verifica.
"""

NAME = "exo"
DISPLAY_NAME = "Exo"
# Nombre de distribución y de la carpeta de datos de usuario. No se usa `~/.exo`
# porque lo usa (y lo borra al desinstalarse) exo-explore/exo (ADR-0001).
DIST_NAME = "exo-harness"
USER_DIR_NAME = DIST_NAME
PROJECT_DIR = ".exo"
ENV_PREFIX = "EXO_"
BLOCK_PREFIX = "exo"
VERSION = "1.0.0"
