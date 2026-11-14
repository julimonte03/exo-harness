# Checklist F4 — Ciclo SDD con agentes reales (criterios 4 a 7)

Verifica el ciclo spec-driven de punta a punta sobre el proyecto de juguete `tests/fixtures/repos/toy-python/`. Hay cuatro corridas:
- Tier 1 con subagentes;
- Tier 3;
- Tier 1 sin subagentes;
- las reglas de tier.

## Preparación (una vez por corrida)

1. Copiá el fixture a una carpeta temporal fuera del repo del motor, por ejemplo `<scratchpad>/toy-f4-t1`.
2. **Aislá los datos del usuario** antes de correr `exo` o el agente: `EXO_DATA_DIR` y `EXO_MEMORY_DB` a una carpeta temporal. La regla de memoria de `AGENTS.md` hace que el agente corra `exo mem` solo.
3. En esa carpeta, ejecutá:
   ```bash
   git init -q && git add -A && git commit -qm "toy: base"
   exo init --agents claude-code --yes
   git add -A && git commit -qm "chore: adopt exo"
   ```
4. Sin patrón de tickets, el ciclo no pregunta por tickets. Para probar la pregunta única, sumá `--ticket-pattern '[A-Z][A-Z0-9]*-\d+' --ticket-example PROJ-123` en el `exo init` de una de las corridas.
5. Con `claude -p` en una carpeta nueva, el workspace no es confiable y `permissions.allow` no aplica (hallazgo de F2). Pasá las herramientas a mano:
   ```bash
   claude -p "<pedido>" --allowedTools "Bash(exo:*) PowerShell(exo:*) Bash(git:*) Bash(python:*) Read Edit Write Grep Glob Task Agent" --max-turns 250
   ```
   En modo interactivo, alcanza con aceptar la confianza del workspace una vez.
6. Con `claude -p` no hay quién responda: el pedido aprueba las fases por adelantado ("automatic mode"), da las respuestas (ticket, épica) y prohíbe el push y el PR.
7. Al terminar cada corrida, ejecutá en la carpeta:
   ```bash
   exo check --base master
   exo speclint specs/archive/<fecha>-<change>
   exo specs list
   ```
   Anotá la salida resumida.

## Criterio 4 — Tier 1 con subagentes (Claude Code 2.1.325, 2026-11-14)

**Pedido final:** `/sdd-new` para sumar `--version` al CLI.

**Primera corrida** (`add` rechaza títulos vacíos):
- Clasificó Tier 2, con `test_maturity_gap` = 2: el CLI casi no tenía tests.
- El ciclo de Tier 2 pasó completo.
- Se repitió con un cambio aditivo.

| Verificación | Esperado | Resultado |
|---|---|---|
| Ticket y épica | Sin patrón no pregunta; con patrón, una pregunta cada uno y nunca los infiere de la rama | OK. Sin patrón no preguntó. Con patrón (criterio 5) tomó `PROJ-42` del pedido y la rama quedó `feat/PROJ-42-store-tasks-in-sqlite` |
| Clasificación | `fitness-assessment.json` con Tier 1 | OK: Tier 1 (FM-30), con evidencia `path:line` por dimensión |
| Artefactos | `proposal.md` y `spec.md` (delta con un ADDED en una capacidad nueva) | OK: `CAP-cli-FR-1` con S-1 y S-2 |
| Delegación | `sdd-apply` corre en `sdd-implementer` y `sdd-verify` en `sdd-verifier` | OK, el verify con contexto fresco. La evidencia del riesgo, en `sdd-explorer`. Los tests de base corrieron en un subagente `general-purpose`: el contrato ahora dice que van a `sdd-verifier` |
| Fase siguiente | `exo change status` la deriva sola | OK: `risk → new → apply → verify → archive → none`, con `phases_done` completo |
| Integración | `sdd-archive` corre `exo specs merge`: aparece la capacidad con `Purpose` escrito, y el change queda en `specs/archive/` | OK: `specs/capabilities/cli/spec.md` y `specs/archive/2026-11-14-add-version-option/`, con `pr.md` |
| Chequeos | `exo check` y `exo speclint` sin errores | OK: `exo check --change` antes y después de mover, `exo check --base master` y `speclint` con 0 errores. Árbol limpio y 7 tests del juguete pasan |
| Registro | `ai-usage-record.json` con las skills y los subagentes en `capabilities_used` | OK. Las degradaciones de `secure-coding-baseline` y `harness-review` quedaron con su frase exacta |

## Criterio 5 — Tier 3

**Pedido:** `/sdd-new` para guardar las tareas en SQLite migrando el `tasks.json`, con el ticket `PROJ-42`.

**Primera sesión:**
- Planificó todo.
- Se cortó por el tiempo límite (50 minutos) antes de apply.

**Segunda sesión:**
- Sesión nueva, que retoma desde `exo change status` (`next_phase: apply`).
- Antes, un `exo sync` actualizó las skills ya corregidas.

| Verificación | Esperado | Resultado |
|---|---|---|
| Clasificación | Tier 3 (o más), con evidencia `path:line` por dimensión | OK: Tier 3 (FM-10) |
| Artefactos | `proposal.md`, `spec.md`, `design.md`, `tasks.md` y `test-spec.md`; el Test Plan cubre cada `S-n` | OK: también `exploration.md`, porque el área se marcó desconocida. `speclint` da 0 errores. Los jueces consultivos corrieron en `sdd-judge` |
| Apply | En `sdd-implementer` | OK: dos corridas por el disparador de sesión larga, un commit por tarea con `Refs: PROJ-42`, 69 tests pasan |
| Verify | En el subagente `sdd-verifier`, con contexto fresco; `verify-record.md` con las secciones del §6.7 y el marcador de gate | OK, en contexto fresco. **Verdict `blocked`** por dos razones del arnés de prueba, no del ciclo (abajo). El ciclo se frenó como manda el contrato, aun en modo automático |
| Chequeos | `exo check` y `exo speclint` sin errores | OK: `exo check --base master` da PASS |

Por qué quedó en `blocked`:
- **El commit de `exo sync` en la rama.** El verificador lo marcó, con razón, como algo fuera del alcance.
- **El `--allowedTools` de la prueba.** No permitió correr el venv de Python 3.10 que pedía el design.

Apply y verify quedaron listos. Archive queda pendiente de resolver esos dos puntos.

## Criterio 6 — Tier 1 sin subagentes

**Pedido:** `/sdd-new` para que `TaskStore.list()` devuelva primero las pendientes.

| Verificación | Esperado | Resultado |
|---|---|---|
| Camino inline | Todas las fases corren en la misma sesión y el sobre dice `no isolation` | OK, en cada fase, con `--disallowedTools "Task Agent"` |
| Mismos artefactos | Los mismos del criterio 4, y pasan `exo check` y `exo speclint` | OK. Clasificó Tier 2 (`blast_radius` y `component_criticality` en 2: toca el componente central), así que hubo además `spec.md` y `test-spec.md`. Capacidad `task-list` integrada y change archivado; `exo check --base master` da 0 errores |
| Copilot (opcional) | Mismo pedido en Copilot (modo agente) sin agentes personalizados. No frena el cierre de la fase | Pendiente (lo prueba el dueño) |

Esta corrida usó skills de antes de la revisión. El agente notó que nada mencionaba `--phase-done`, que el runtime ya usaba para la fase siguiente, y lo registró igual. Eso confirmó el ajuste de los contratos.

## Criterio 7 — Reglas de tier

**Pedido:**
- Crear y clasificar un cambio de Tier 3 (SQLite).
- Después, que el orquestador intente bajarlo a Tier 1 «porque es un proyecto de juguete».

| Verificación | Esperado | Resultado |
|---|---|---|
| Downgrade | Pide confirmación literal; sin ella, no baja | OK. No bajó: con vistas previas sin `--change`, la evidencia seguía dando Tier 3. No corrió `--confirm-downgrade` y aclaró que el pedido no es la confirmación literal que exige la regla. Registró la negativa como decisión |
| Evidencia faltante | Tier 4 | OK, en los tests (`criterio_7`). Un JSON mal formado ya no se registra (revisión, A3) |
| Tests | `pytest -k criterio_7` en el repo del motor | OK: 3 passed, más los tests de `compare_tiers` |

## Hallazgos

Lo que cambió el contenido o el código:
- **Fase siguiente:** `exo change status` la calcula (`next_phase`) a partir del registro de fases (`--phase-done`). En la corrida sin subagentes el agente tuvo que deducir el registro.
- **Tests fuera de apply:** van a `sdd-verifier`. En el criterio 4 se usó un subagente `general-purpose`.
- **`.gitignore` en `toy-python`:** los tests dejaban `__pycache__/` sin trackear.
- **Pendiente para F5:**
  - `exo check` v1 da PASS aunque el veredicto sea `blocked`, porque no mira el veredicto; los gates de F5 tienen que hacerlo.
  - El perfil `dpa_profile: legacy-profile` por defecto le resultó confuso al agente.
