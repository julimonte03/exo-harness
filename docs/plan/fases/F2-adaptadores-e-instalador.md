# F2 — Adaptadores multi-agente e instalador de un comando

## Objetivo

Que con **un comando** se instale el motor en la máquina y con **otro** se adopte en un proyecto: detecta qué agentes se usan (o pregunta), genera exactamente los archivos que cada uno necesita, no pisa nada del humano, es idempotente y se puede desinstalar dejando el proyecto como estaba.

## Depende de

F1 cerrada. Decisiones D-04, D-05, D-06 y D-16. Matriz verificada en `docs/agent-matrix.md`.

## Alcance

Entra: interfaz de adaptadores, adaptadores de Tier 1 y Tier 2, adaptador genérico, detección, motor de operaciones con lock y snapshots, wizard de `arnes init`, `sync`, `add-agent`, `remove-agent`, `uninstall`, `status`, port de `curate` (detección de stack para sugerir packs), `install.sh` e `install.ps1`, chequeos de doctor por agente.

No entra: skills reales (F4), hooks de memoria (F3), git hooks y guardas (F5).

## Diseño

**Interfaz.** La de `02-ARQUITECTURA.md` §2.8. Los adaptadores no escriben; devuelven una lista de `FileOp`.

**Bundle canónico.** `CanonicalBundle` reúne, para los packs resueltos: reglas (`AGENTS.base.md` + secciones por pack), skills (carpetas completas), subagentes, contratos de `shared/` y datos de capacidades. Lo construye el motor; los adaptadores solo lo leen.

**Operaciones por adaptador.**

| Adaptador | Operaciones |
|---|---|
| `generic` (siempre) | Bloque `core` en `AGENTS.md`; copia de skills en `.agents/skills/`; contratos en `.arnes/shared/`; `.arnes/config.json`, `.arnes/lock.json`, `.arnes/skill-registry.md` |
| `claude-code` | Bloque en `CLAUDE.md` con `@AGENTS.md` y nota de capacidades (lo crea si no existe; si existe, inserta el bloque al principio); espejo `.claude/skills/`; subagentes en `.claude/agents/`; clave `mcpServers.arnes` en `.mcp.json` |
| `copilot` | Subagentes en `.github/agents/*.agent.md`; clave `servers.arnes` en `.vscode/mcp.json`; bloque puntero en `.github/copilot-instructions.md` solo si F0 determinó que hace falta |
| `cursor` | Clave `mcpServers.arnes` en `.cursor/mcp.json`; subagentes solo si `.claude/agents/` no se genera (Cursor ya lo lee) |
| `codex` | Tabla `[mcp_servers.arnes]` entre marcadores `# BEGIN/END:arnes:mcp` en `.codex/config.toml` |
| `gemini` | Clave `mcpServers.arnes` en `.gemini/settings.json`; lectura de `AGENTS.md` por config o bloque puntero en `GEMINI.md` |
| `windsurf-devin` | Lo que F0 haya verificado; como mínimo depende del genérico e imprime el snippet MCP |

**Motor de operaciones.** Calcula operaciones de todos los adaptadores elegidos → las compara contra el lock → si no hay cambios termina con "sin cambios" → si hay, snapshot de rutas afectadas, aplicación atómica, actualización del lock. Archivos modificados a mano se reportan como conflicto y no se tocan sin `--force`. Toda operación tiene `--dry-run` que imprime la lista de archivos.

**Wizard de `arnes init`.** Pasos: (1) agentes detectados preseleccionados, (2) stack detectado y packs sugeridos (port de `StackSignals` de `curate.py`: package.json, dependencias Python, Docker, JVM, Spring Boot/Security, JPA, backend Python/JS), (3) tracker y prefijo, (4) idiomas, (5) backend de memoria (`auto`), (6) resumen con la lista de archivos y confirmación. Con `--yes` y flags se corre sin preguntas.

**Comando MCP en los configs.** `"command": "arnes", "args": ["mcp"]`. `doctor` verifica que resuelva. Opción `--mcp-absolute` que escribe la ruta absoluta en la config de usuario del agente (no versionada) para editores gráficos que no heredan el `PATH`.

**Instaladores de un comando.**

```bash
# Linux / macOS, desde el clon del motor
./install.sh                 # instala el CLI
./install.sh --init ~/mi-proyecto   # instala y adopta un proyecto
./install.sh --with-vector   # además el extra de memoria vectorial
```

```powershell
# Windows
.\install.ps1
.\install.ps1 -Init C:\code\mi-proyecto
```

Comportamiento: verificar Python ≥ 3.10; si hay `uv`, usar `uv tool install` desde el clon; si no, crear un venv en el directorio de datos del usuario e instalar ahí; dejar un ejecutable `arnes` en un directorio del `PATH` de usuario (y agregarlo al `PATH` si falta, avisando); correr `arnes doctor`. Re-ejecutar actualiza. `uninstall.sh` / `uninstall.ps1` revierten. Cuando exista repo remoto (F8) se suman `curl -fsSL …/install.sh | sh`, `irm …/install.ps1 | iex` y `uvx --from git+<url> arnes init`.

## Tareas (en orden)

1. Tipos (`FileOp`, `Capabilities`, `Detection`, `CanonicalBundle`) y motor de operaciones con lock, snapshots y `--dry-run`.
2. Adaptador `generic` + golden tests.
3. Adaptador `claude-code` + golden tests.
4. Adaptador `copilot` + golden tests.
5. Detección (`adapters/detect.py`) + tests tabulares de señales.
6. Wizard y comandos `init`, `sync`, `status`, `add-agent`, `remove-agent`, `uninstall`.
7. Port de `curate` (sugerencia de packs por stack) + tests sobre fixtures.
8. Adaptadores de Tier 2 + golden tests.
9. Chequeos de doctor por agente (archivos esperados presentes, comando MCP resoluble, drift del lock).
10. `install.sh`, `install.ps1` y sus desinstaladores + job de CI que los corre en un `HOME` temporal en los tres sistemas.
11. Contenido para ejercitar la instalación: los 4 subagentes canónicos del ciclo como esqueletos, `AGENTS.base.md` real en versión mínima, y 3 skills esqueleto (`hello-arnes`, `memory-protocol`, `sdd-status`).
12. Checklist manual de verificación con agentes reales en `docs/checklists/F2-agentes.md`.

## Golden tests

Para cada adaptador y cada fixture de proyecto, el árbol resultante se compara contra `tests/golden/<adaptador>/<fixture>/`. Fixtures mínimos: proyecto vacío; proyecto con `AGENTS.md` del humano; proyecto con `CLAUDE.md` existente; proyecto con `.vscode/mcp.json` que tiene comentarios (JSONC); proyecto con archivos en CRLF. Regenerar con `pytest --update-golden` solo de forma explícita y revisando el diff.

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Instalación de un comando | En un clon limpio, `./install.sh` (o `.\install.ps1`) termina sin errores y `arnes doctor` da todo OK, en los tres sistemas (job de CI) |
| 2 | Adopción reproducible | `arnes init --agents claude-code,copilot --yes` sobre el fixture vacío produce exactamente el golden |
| 3 | Idempotencia | Correr `arnes init` o `arnes sync` por segunda vez informa "sin cambios" y no crea snapshot |
| 4 | Respeto de archivos del humano | En los fixtures con `AGENTS.md`/`CLAUDE.md` propios, el contenido del humano queda byte a byte igual fuera de los bloques |
| 5 | Conflictos detectados | Editar a mano un archivo generado y correr `arnes sync` lo reporta como conflicto y no lo pisa |
| 6 | Reversible | `arnes init` seguido de `arnes uninstall` deja el fixture idéntico al original |
| 7 | Multi-agente incremental | `arnes add-agent cursor` sobre un proyecto ya instalado solo agrega lo de Cursor |
| 8 | Funciona en agentes reales | Checklist manual: en Claude Code se ven las skills, las reglas cargan vía `CLAUDE.md` y `/mcp` muestra `arnes` conectado; en Copilot (VS Code, modo agente) se ven las skills y el server MCP está activo. Resultado anotado en `PROGRESO.md` |

**Hito M1** al cerrar esta fase.

## Riesgos

Editores gráficos que no heredan el `PATH` del shell (mitigación: `--mcp-absolute` + doctor). Formatos de config que cambian (mitigación: golden tests + `docs/agent-matrix.md` con fecha). Copilot listando skills duplicadas por el espejo (mitigación decidida en F0).
