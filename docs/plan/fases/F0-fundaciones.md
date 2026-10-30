# F0 — Fundaciones y verificación

## Objetivo

Dejar el repo listo para construir: empaquetado, reglas de desarrollo, CI en tres sistemas operativos, decisiones iniciales registradas como ADR y, sobre todo, la **matriz de agentes verificada contra documentación oficial** antes de escribir un solo adaptador.

## Depende de

Decisiones D-01, D-02, D-03 y D-15 confirmadas o aceptadas con su default.

## Alcance

Entra: esqueleto del paquete, CLI mínimo (`--version`), configuración de tests y lint, CI, documentación de referencia copiada, ADRs 0001–0004, verificación de convenciones de agentes, plantilla de PR y definición de "terminado".

No entra: ninguna lógica de dominio (eso es F1).

## Entregables

| Ruta | Contenido |
|---|---|
| `pyproject.toml` | Paquete `arnes`, Python ≥ 3.10, **sin** dependencias de runtime, extras `[dev]` (pytest, pytest-cov, ruff) y `[vector]` (vacío por ahora), entry point `arnes = arnes.cli:main` |
| `src/arnes/_meta.py` | `NAME`, `DISPLAY_NAME`, `PROJECT_DIR = ".arnes"`, `ENV_PREFIX = "ARNES_"`, `BLOCK_PREFIX = "arnes"`, `VERSION` |
| `src/arnes/__main__.py`, `src/arnes/cli.py` | `arnes --version` y `python -m arnes --version` |
| `AGENTS.md`, `CLAUDE.md` | Copiados de `docs/plan/repo-raiz/` |
| `tests/test_meta.py` | Test que falla si aparece el literal `".arnes"` o `"ARNES_"` fuera de `_meta.py` |
| `.github/workflows/ci.yml` | Matriz ubuntu/macos/windows × Python 3.10 y 3.13: ruff + pytest con cobertura |
| `docs/referencia/` | Los 16 `.md` de la transcripción, sin modificar |
| `docs/plan/` | Este plan + `PROGRESO.md` |
| `docs/adr/0001-nombre-y-layout.md` | D-01 |
| `docs/adr/0002-lenguaje-y-nucleo-stdlib.md` | D-02 |
| `docs/adr/0003-fuente-canonica-y-adaptadores.md` | Principio 1 de `01-VISION-Y-ALCANCE.md` |
| `docs/adr/0004-relacion-con-upstream.md` | D-03, con resultado de la verificación de licencias |
| `docs/agent-matrix.md` | Matriz verificada (ver tarea 0.4) |
| `.github/pull_request_template.md` | Resumen, fase, tareas cubiertas, criterios de aceptación corridos, riesgos |

> **Actualizado por ADR-0008 (D-16), 2026-10-30:** los repos van a estar en Azure DevOps. La CI es `azure-pipelines.yml` y la plantilla de PR está en `.azuredevops/pull_request_template.md`.

## Tareas (en orden)

**0.1 Esqueleto y empaquetado.** Crear la estructura `src/arnes/`, `pyproject.toml`, `_meta.py`, CLI con `argparse` y `--version`. Test de que `python -m arnes --version` imprime `VERSION`.

**0.2 Reglas de desarrollo.** Copiar `AGENTS.md` y `CLAUDE.md` del plan. Verificar que Claude Code las carga (en una sesión nueva, preguntarle qué reglas tiene activas).

**0.3 Calidad y CI.** Configurar pytest (umbral de cobertura inicial 80 %, que sube a 85 % en F1), ruff, y el workflow de CI con la matriz de sistemas operativos. Agregar `tests/test_meta.py`.

**0.4 Spike de verificación de agentes.** Para cada agente de Tier 1 y Tier 2 (`03-MATRIZ-AGENTES.md`), buscar en la documentación oficial y completar `docs/agent-matrix.md` con estas columnas, cada celda con URL y fecha o `[No verificado]`:

1. Archivo de reglas y precedencia (qué pasa si conviven `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `copilot-instructions.md`).
2. Directorios de skills de proyecto y de usuario; si lee `.agents/skills/`.
3. Comportamiento cuando la misma skill aparece en dos directorios que el agente lee (¿duplica, ignora, error?).
4. Formato y directorio de subagentes; si lee `.claude/agents/`.
5. Ruta y esquema del config MCP de proyecto (clave raíz, formato JSON/JSONC/TOML, si necesita "proyecto confiable").
6. Hooks: archivo, eventos disponibles, formato.
7. Comandos o prompts invocables.
8. Variables de entorno que el agente define al ejecutar comandos de shell (para la detección).

Si hay agentes instalados en esta computadora, sumar una **prueba empírica**: un repo temporal con una skill `hello-probe` en `.agents/skills/` y otra en `.claude/skills/`, más un server MCP de eco, y anotar qué ve cada agente. Registrar los pasos en `docs/spikes/agent-probe.md` para poder repetirlos.

**0.5 Licencias upstream.** Revisar la licencia de gentle-ai y de Engram, y anotarlas en el ADR-0004. Regla para todo el proyecto: no se copia texto ni código de terceros sin licencia compatible y atribución.

**0.6 ADRs y definición de terminado.** Escribir ADR-0001 a 0004 (formato: contexto, decisión, alternativas, consecuencias). Escribir en `docs/plan/PROGRESO.md` la definición de "fase terminada": criterios en verde con comando exacto, CI verde en los tres sistemas, PR mergeado.

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | El paquete se instala y responde | `pip install -e ".[dev]"` y luego `arnes --version` y `python -m arnes --version` muestran la misma versión |
| 2 | Tests y lint verdes | `pytest` y `ruff check .` sin errores |
| 3 | CI verde en los 3 sistemas operativos | Run de GitHub Actions del PR |
| 4 | El nombre está centralizado | `tests/test_meta.py` pasa |
| 5 | Matriz de agentes completa | `docs/agent-matrix.md` tiene las 8 columnas para Claude Code, Copilot, Cursor, Codex, Gemini CLI y Windsurf/Devin, cada celda con URL o `[No verificado]` |
| 6 | Decisiones registradas | ADR-0001 a 0004 en `docs/adr/` y D-01, D-02, D-03, D-15 marcadas como Decididas |
| 7 | Diferencias con el plan anotadas | Si la verificación contradice `03-MATRIZ-AGENTES.md`, se actualiza ese archivo en el mismo PR |

## Riesgos

La documentación de los agentes puede contradecirse entre superficies (por ejemplo Copilot en VS Code y en GitHub.com). En ese caso se anotan ambas y el adaptador genera lo necesario para las dos.
