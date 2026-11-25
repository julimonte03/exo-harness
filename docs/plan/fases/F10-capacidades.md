# F10 — Catálogo de capacidades y perfil por máquina

> Fase del paquete de capacidades y tiers (`docs/plan/paquete-capacidades.md`, sección 5). Decisiones: D-53 → ADR-0020. Rama: `feat/F10-capacidades`.
>
> Cada fase va en su propia rama, arranca en plan mode, tiene los tests primero y se cierra con cada criterio corrido con su comando exacto y anotado en `PROGRESO.md`. La cobertura de `src/exo` sigue en ≥ 85 % y la CI tiene que estar verde en los tres sistemas operativos. La rama llega a `main` por un PR que abre y mergea el dueño (D-51).
>
> Los números de sección que cita este archivo ("3.1", "3.5", "sección 0", "sección 6") son los del paquete.

## Objetivo

Que exo sepa qué trae el agente de cada persona, pregunte una sola vez qué usar y lo informe a las skills con un comando.

## Depende de

F9.

## Tareas, en orden

1. **Verificación del catálogo (spike, como la tarea 0.4 de F0).** Para Claude Code, Copilot CLI y Copilot en VS Code, y para cada capacidad del catálogo, relevá:
   - si es nativa;
   - desde qué versión;
   - cómo se activa;
   - cómo se comprueba que está activa;
   - qué restricciones tiene (proveedor, plan, flags);
   - la fuente oficial, con URL y fecha.

   El resultado va en `docs/capabilities-matrix.md`. La sección 6 trae el punto de partida; nada de ahí se da por cierto sin verificar.
2. **El catálogo como datos dentro del paquete** (no se instala en los proyectos):
   - `catalog.json` con cada capacidad: id, política, propósito, fallback de exo y fallback humano;
   - un archivo por agente, con el soporte de cada capacidad y `verified_at`.

   Proponé la ubicación en plan mode.
3. **Perfil por máquina** en el directorio de datos del usuario (por ejemplo, `~/.exo/profiles/<agente>.json`, y su equivalente en Windows). Contiene:
   - agente y versión;
   - elección por capacidad (`native` o `exo`) con `chosen_by` (`user` o `default`);
   - la versión de los datos usados;
   - el mapa de modelos (lo completa F11).

   **Nunca va al repo ni al lock.**
4. **`exo capabilities [--json] [--agent <id>] [--reconfigure]`.**
   - Detecta el agente por el entorno (o lo toma de `--agent`) y devuelve, por capacidad: resolución (`native`, `exo` o `human`), motivo y cómo usarla.
   - Si el agente es desconocido, devuelve `exo` o `human` para todo.
5. **Pregunta única en `exo init`** (3.2):
   - con terminal: tres opciones (todas, elegir una por una, ninguna);
   - sin terminal: el default de 3.5;
   - `--reconfigure` vuelve a preguntar todo;
   - `exo doctor` detecta un agente o una versión nuevos, o una capacidad nativa nueva en los datos, y marca pendiente solo lo nuevo.
6. **`exo doctor`:**
   - avisa si los datos tienen más de 60 días;
   - avisa si falta el perfil del agente detectado;
   - avisa si una capacidad elegida como nativa dejó de estar disponible.
7. **`exo validate`:** cada capacidad del catálogo tiene datos para `claude-code` y `copilot`, y ninguna capacidad con política `exo` aparece como ofrecible.
8. **Contrato `agent-capabilities.md`** reescrito: al empezar cada fase, la skill corre `exo capabilities --json` y sigue la resolución, en vez de suponer.
9. **AI Usage Record:** campo `provided_by` (`native`, `exo` o `human`) en cada entrada de `capabilities_used`, con subida de esquema y migración tolerante.

## Catálogo inicial

| id | Para qué | Política | Fallback de exo | Fallback humano |
|---|---|---|---|---|
| `subagents` | Delegar con contexto propio | native | Inline, declarando "sin aislamiento" | — |
| `subagent_model` | Correr un subagente con el modelo del tier | native | Modelo de la sesión, con aviso | — |
| `fresh_context` | Revisar sin arrastrar la conversación | native | Sesión nueva con archivo de traspaso | — |
| `parallel_agents` | Varias unidades a la vez | native | Modo secuencial de `parallel-dispatch` | — |
| `read_only_mode` | Explorar sin poder escribir | native | Subagente `sdd-explorer` | — |
| `headless` | Evals y lotes sin interfaz | native | — | Correrlo a mano |
| `second_opinion` | Consultar en los 3 puntos | native (solo Tier 2; ver D-55) | Subagente `exo-advisor` | Preguntar a la persona |
| `builtin_reviewer` | Hallazgos extra de un revisor incorporado | complement | — | — |
| `rules`, `skills`, `mcp`, `commands` | Lo que ya instalan los adaptadores | native | Adaptador genérico o snippet impreso | — |
| `memory` | Memoria entre sesiones, igual en cualquier agente | exo | `exo mem` | — |
| `enforcement` | Hooks y bloqueos | exo | Git hooks + `exo check` en CI (D-31) | — |
| `governance` | Gates, jueces, `judgment-day`, fitness, `check`, AI Usage Record, specs | exo | — | — |

Si la verificación encuentra una capacidad relevante que no está en la lista, proponela como D-xx. No la agregues sin preguntar.

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Matriz verificada | `docs/capabilities-matrix.md` tiene todas las capacidades × Claude Code y Copilot, cada celda con URL y fecha o `[No verificado]` |
| 2 | Resolución correcta | Golden tests de `exo capabilities --json` con entornos simulados (`CLAUDECODE=1`, `COPILOT_CLI=1`, desconocido) y perfiles de fixture |
| 3 | Pregunta única | En un `HOME` temporal, el primer `exo init` pregunta y el segundo no. Si los datos agregan una capacidad nativa, solo se pregunta por esa |
| 4 | Nada personal en el repo | Después de `exo init`, `git status` y `.exo/lock.json` no muestran el perfil ni modelos concretos |
| 5 | Gobierno intocable | Test: ninguna capacidad `exo` aparece en la pregunta ni puede elegirse como nativa |
| 6 | Doctor | Avisa con datos de más de 60 días, sin perfil y con una capacidad nativa que desapareció |
| 7 | Validador | `exo validate` falla si una capacidad no tiene datos para `claude-code` o `copilot` |

## Puntos abiertos (ADR-0020)

- A qué agentes pregunta `exo init` cuando el proyecto tiene más de uno. Propuesta para el plan mode: los del proyecto que estén presentes en la máquina (ejecutable o variable de entorno); el resto, con `exo capabilities --reconfigure --agent <id>`.
- Rubber Duck: el spike releva cómo se activa y qué familia de modelos usa, para resolver antes de F12 el punto abierto de ADR-0020.

## Referencias

Paquete (`docs/plan/paquete-capacidades.md`): §3.2 (D-53), §4 (lo que se reutiliza) y §6 (hechos externos para verificar).
