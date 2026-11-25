# ADR-0001 — Nombre del motor y layout

- **Estado:** Aceptada
- **Fecha:** 2026-10-29
- **Decisión:** D-01

## Contexto

El plan usa `arnes` como nombre de trabajo y exige que todo nombre visible salga de una sola constante (invariante 12 de `AGENTS.md`), para que renombrar sea barato. El dueño eligió **`exo`**, el nombre de la carpeta de trabajo `exo-harness`. La verificación de F0 (fuentes consultadas el 2026-10-29) encontró dos colisiones:

- **exo-explore/exo** (Apache-2.0, activo) usa el mismo CLI `exo` (`exo = "exo.main:main"`) y el mismo paquete importable `src/exo`. También usa `~/.exo` como carpeta de usuario en macOS y Windows: ahí guarda logs, modelos y un pid, y su desinstalador borra `~/.exo`. Define variables `EXO_HOME`, `EXO_RUNTIME_DIR`, `EXO_OFFLINE`, `EXO_DEFAULT_MODELS_DIR`, `EXO_MODELS_DIRS`, `EXO_MODELS_READ_ONLY_DIRS`, `EXO_ENABLE_IMAGE_MODELS`, `EXO_ZENOH_NAMESPACE`, `EXO_FAST_SYNCH`, `EXO_TRACING_ENABLED` y `EXO_TESTS`. Fuentes: https://github.com/exo-explore/exo/blob/871caad407a70647426dffaa455bd4d0ab1d48e6/src/exo/shared/constants.py#L7-L27 y https://github.com/exo-explore/exo/blob/main/README.md
- **PyPI:** `exo` está tomado por otro proyecto (CEGRcode, sin releases desde 2020): https://pypi.org/project/exo/. `exo-harness` está libre (404 en https://pypi.org/pypi/exo-harness/json).

## Decisión

Se mantiene `exo`, con mitigaciones:

| Elemento | Valor | Constante en `src/exo/_meta.py` |
|---|---|---|
| CLI y paquete importable | `exo` | `NAME` |
| Nombre para mostrar | `Exo` | `DISPLAY_NAME` |
| Distribución (PyPI, `uv tool`) | `exo-harness` | `DIST_NAME` |
| Carpeta dentro de cada proyecto | `.exo/` | `PROJECT_DIR` |
| Carpeta de datos de usuario (memoria, caches) | `exo-harness` bajo el directorio de datos del sistema, **nunca `~/.exo`** | `USER_DIR_NAME` |
| Prefijo de variables | `EXO_` | `ENV_PREFIX` |
| Marcadores de bloque | `BEGIN/END:exo:<id>` | `BLOCK_PREFIX` |
| Metadata propia en skills | `exo-` | (contenido, F1) |

Reglas:

- **Nunca** se definen variables que use exo-explore. Las de la lista de arriba quedan reservadas y el motor no las lee ni las escribe.
- En F2, `exo doctor` avisa si el primer `exo` del `PATH` no es este motor.
- El plan conserva su texto; donde dice `arnes`, se lee `exo`.

## Alternativas

- **Volver a `arnes`.** No tiene colisiones conocidas, pero el dueño prefirió `exo`.
- **Renombrar solo el CLI** (por ejemplo `exoh`). Evita el choque en el `PATH`, pero confunde: el proyecto, el CLI y la carpeta tendrían nombres distintos.
- **Evitar `.harness/`**, como recomendaba D-01, porque lo usa la plataforma Harness. Ninguna opción lo usa.

## Consecuencias

- Una persona que tenga instalado exo-explore tendría dos ejecutables `exo`. Se mitiga instalando el motor en un entorno aislado (`uv tool` o venv propio, F2), con el aviso de `doctor` y con la documentación. El público objetivo (equipos de desarrollo corporativos) rara vez usa exo-explore.
- La ruta de la memoria de F3 cambia respecto del plan: no es `~/.exo/memory.db` sino `<datos de usuario>/exo-harness/memory.db`. El override pasa a ser `EXO_MEMORY_DB`. La ruta exacta por sistema operativo (por ejemplo `%LOCALAPPDATA%` en Windows, `~/Library/Application Support` en macOS, `$XDG_DATA_HOME` en Linux) se fija en F3, junto con D-07.
- `tests/test_meta.py` impide que `.exo`, `EXO_` o `exo-harness` aparezcan como literal fuera de `_meta.py`.
- Si en el futuro se renombra, se cambia `_meta.py`, `pyproject.toml` (nombre de distribución y script) y la carpeta `src/exo`.
