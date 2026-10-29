# F8 — Endurecimiento, evals y distribución (v1.0)

## Objetivo

Llevar el motor a una v1.0 que se pueda actualizar sin romper proyectos, que esté probado en los tres sistemas operativos y con agentes reales, cuya propia superficie de seguridad esté analizada, y que se pueda instalar desde un repositorio remoto con un comando.

## Depende de

F6 y F7 cerradas. Decisión D-22.

## Alcance

**Actualización.** `arnes update` en modo vista previa por defecto y `--apply` para aplicar (comportamiento del reporte, §4.2): muestra qué archivos generados cambian con la nueva versión del motor, respeta los conflictos del lock y nunca borra skills huérfanas sin confirmación. Migraciones versionadas de `config.json`, `lock.json` y del esquema de memoria. `CHANGELOG.md` con semver.

**Multiplataforma.** Windows (rutas, CRLF, PowerShell, permisos de ejecución de los git hooks, rutas largas), macOS (editores gráficos y `PATH`, Python sin carga de extensiones de SQLite) y Linux. Matriz de CI completa con Python 3.10 a 3.13.

**Evals con agentes reales.** Escenarios guionados que corren agentes en modo no interactivo sobre los fixtures (por ejemplo Claude Code con `claude -p`, y los equivalentes de Copilot CLI, Codex y Gemini CLI según lo verificado en F0) y verifican los artefactos con `arnes speclint` y `arnes check`. Escenarios mínimos: cambio Tier 1, cambio Tier 3, adopción con `/arnes-adopt` en modo `quick`. Se marcan como `agent_e2e`, no corren en la CI normal, y se ejecutan de forma manual o programada con presupuesto acotado.

**Rendimiento.** Metas: `arnes init` en menos de 10 s, `arnes sync` sin cambios en menos de 1 s, `arnes discover inventory` sobre 50 mil líneas en menos de 30 s, búsqueda de memoria según F3.

**Seguridad del propio motor.** Actualizar el threat model lite (§7.6 del reporte cubría MCP de observabilidad, RAG y multicanal) con las superficies nuevas: instaladores por `curl`/`irm`, git hooks que se ejecutan en máquinas del equipo, servidor MCP, export de memoria, proveedores de embeddings, lectura de código durante la ingeniería inversa. Cada amenaza con mitigación o riesgo aceptado registrado.

**Documentación.** `README.md`, `QUICK-START.md`, una guía por agente, guía de adopción de proyectos existentes, troubleshooting y `CONTRIBUTING.md` (cómo agregar un adaptador, un pack o una skill). Se mantiene al día la deuda documental: el reporte original tenía conteos y nombres desactualizados en varios documentos (§12.1); acá `arnes validate` verifica que los conteos citados en la documentación coincidan con el contenido real.

**Distribución.** Repo remoto (D-16, D-22), releases con tags, instaladores remotos (`curl -fsSL <url>/install.sh | sh`, `irm <url>/install.ps1 | iex`), ejecución sin instalar con `uvx --from git+<url> arnes init`. Opcionales: PyPI y empaquetado como plugin para los agentes que tengan marketplace.

**Pendientes opcionales.** Overlays de persona (D-17), `arnes status` con vista de terminal enriquecida.

## Criterios de aceptación (v1.0 = definición de éxito de `01-VISION-Y-ALCANCE.md`)

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Instalación y adopción en menos de 2 minutos con Claude Code y Copilot | Checklist cronometrado |
| 2 | Segundo agente sin romper el primero | Golden tests + checklist |
| 3 | Ciclos Tier 1 y Tier 3 válidos | Evals `agent_e2e` en verde |
| 4 | Ingeniería inversa: cobertura ≥ 80 % y precisión ≥ 90 % | Reporte de F6 sobre el repo de escala, repetido con la versión final |
| 5 | Memoria con decisión documentada | ADR de F3 vigente |
| 6 | CI verde en los tres sistemas y Python 3.10–3.13, cobertura ≥ 85 % | CI |
| 7 | Actualización segura | `arnes update` de la versión 0.x a 1.0 sobre un proyecto instalado preserva los archivos del humano y reporta conflictos |
| 8 | Threat model actualizado | Documento con todas las superficies nuevas y sus mitigaciones |

**Hito M4 (v1.0)** al cerrar esta fase.
