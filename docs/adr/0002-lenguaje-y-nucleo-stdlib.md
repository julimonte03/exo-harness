# ADR-0002 — Lenguaje del runtime y núcleo solo stdlib

- **Estado:** Aceptada
- **Fecha:** 2026-10-29
- **Decisiones:** D-02, D-15 (`docs/plan/04-DECISIONES.md`)

## Contexto

El runtime del sistema original era Python solo stdlib, con 11 invariantes pensadas para eso (§4.6 del reporte). El motor nuevo tiene que instalarse en máquinas de equipos con Windows, macOS y Linux, convivir con varios agentes y sumar memoria vectorial, que sí necesita dependencias. La máquina de desarrollo de este repo es Windows 11 y tiene Python 3.14 y `uv`.

## Decisión

1. **Python ≥ 3.10.** El paquete `src/exo` usa solo biblioteca estándar, salvo `memory/backends/` y `memory/embeddings/`, que importan sus dependencias de forma diferida y fallan con un mensaje claro (invariante 4 de `docs/plan/02-ARQUITECTURA.md` §2.13; 1 en `AGENTS.md`). Las dependencias opcionales van como extras (`[vector]`, más adelante `[qdrant]`) y las de desarrollo en `[dev]`.
2. **Sistemas (D-15): mixto, con Windows como prioridad local.** La CI corre en Ubuntu, macOS y Windows con Python 3.10 y 3.13 (F8 amplía a 3.10–3.13). Las pruebas manuales se hacen primero en Windows, y en F2 `install.ps1` es prioridad 1.

## Alternativas

- **Go con binario único (D-02 b).** Instala sin ningún prerrequisito, pero corta la continuidad con el reporte y complica los embeddings locales. Conviene solo si la instalación sin Python fuera crítica para usuarios no técnicos, y no es el caso del equipo.
- **Python con dependencias en el núcleo** (PyYAML, click, etc.). Rompe esa invariante y complica la instalación en entornos corporativos con proxy.

## Consecuencias

- El instalador necesita Python ≥ 3.10. F2 lo resuelve usando `uv` si está, o un venv propio.
- Nada de APIs de 3.11+ sin alternativa para 3.10. Por ejemplo, no hay `tomllib`: el TOML de Codex se gestiona con bloques marcados, como ya prevé el plan.
- El frontmatter YAML se parsea con un subconjunto propio (F1, `core/frontmatter.py`).
- En Windows se cuidan rutas, CRLF y rutas largas desde F1. El repo fuerza LF con `.gitattributes`, salvo los scripts de Windows.
- Verificado en F0: la suite pasa con Python 3.14.5 (venv local) y 3.10.20 (venv con `uv`).
