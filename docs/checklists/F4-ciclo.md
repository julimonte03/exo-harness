# Checklist F4 — Ciclo SDD con agentes reales (criterios 4 a 7)

Verifica el ciclo spec-driven de punta a punta sobre el proyecto de juguete `tests/fixtures/repos/toy-python/`. Hay cuatro corridas:
- Tier 1 con subagentes;
- Tier 3;
- Tier 1 sin subagentes;
- las reglas de tier.

## Preparación (una vez por corrida)

1. Copiá el fixture a una carpeta temporal fuera del repo del motor, por ejemplo `<scratchpad>/toy-f4-t1`.
2. En esa carpeta, ejecutá:
   ```bash
   git init -q && git add -A && git commit -qm "toy: base"
   exo init --agents claude-code --yes
   git add -A && git commit -qm "chore: adopt exo"
   ```
3. Sin patrón de tickets, el ciclo no pregunta por tickets. Para probar la pregunta única, sumá `--ticket-pattern '[A-Z][A-Z0-9]*-\d+' --ticket-example PROJ-123` en el `exo init` de una de las corridas.
4. Con `claude -p` en una carpeta nueva, el workspace no es confiable y `permissions.allow` no aplica (hallazgo de F2). Pasá las herramientas a mano:
   ```bash
   claude -p "<pedido>" --allowedTools "Bash(exo:*) PowerShell(exo:*) Bash(git:*) Bash(python:*) Read Edit Write Grep Glob Task" --max-turns 60
   ```
   En modo interactivo, alcanza con aceptar la confianza del workspace una vez.
5. Al terminar cada corrida, ejecutá en la carpeta:
   ```bash
   exo check
   exo speclint specs/archive/<fecha>-<change>
   exo specs list
   ```
   Anotá la salida resumida.

## Criterio 4 — Tier 1 con subagentes (Claude Code)

Pedido: `/sdd-new` para que `add` rechace títulos vacíos o que sean solo espacios, con un mensaje de error.

| Verificación | Esperado | Resultado |
|---|---|---|
| Ticket y épica | Sin patrón no pregunta; con patrón, una pregunta cada uno y nunca los infiere de la rama | Pendiente |
| Clasificación | `fitness-assessment.json` con Tier 1 | Pendiente |
| Artefactos | `proposal.md` y `spec.md` (delta con un ADDED en una capacidad nueva, por ejemplo `CAP-tasks-FR-1`) | Pendiente |
| Delegación | `sdd-apply` corre en `sdd-implementer` y `sdd-verify` en `sdd-verifier` | Pendiente |
| Integración | `sdd-archive` corre `exo specs merge`: aparece `specs/capabilities/<cap>/spec.md` con `Purpose` escrito, y el change queda en `specs/archive/` | Pendiente |
| Chequeos | `exo check` y `exo speclint` sin errores | Pendiente |
| Registro | `ai-usage-record.json` con las skills y subagentes en `capabilities_used` | Pendiente |

## Criterio 5 — Tier 3

Pedido: `/sdd-new` para guardar las tareas en SQLite en lugar del JSON, migrando el `tasks.json` existente sin perder datos.

| Verificación | Esperado | Resultado |
|---|---|---|
| Clasificación | Tier 3 (o más), con evidencia `path:line` por dimensión | Pendiente |
| Artefactos | `proposal.md`, `spec.md`, `design.md`, `tasks.md` y `test-spec.md`; el Test Plan cubre cada `S-n` | Pendiente |
| Verify | En el subagente `sdd-verifier`, con contexto fresco; `verify-record.md` con las secciones del §6.7 y el marcador de gate | Pendiente |
| Chequeos | `exo check` y `exo speclint` sin errores | Pendiente |

## Criterio 6 — Tier 1 sin subagentes

Pedido: `/sdd-new` para que `list` muestre primero las pendientes. Correlo sin la herramienta de subagentes: `claude -p` sin `Task` en `--allowedTools`, o con `--disallowedTools Task`.

| Verificación | Esperado | Resultado |
|---|---|---|
| Camino inline | Todas las fases corren en la misma sesión y el sobre dice `no isolation` | Pendiente |
| Mismos artefactos | Los mismos del criterio 4, y pasan `exo check` y `exo speclint` | Pendiente |
| Copilot (opcional) | Mismo pedido en Copilot (modo agente) sin agentes personalizados. No frena el cierre de la fase | Pendiente |

## Criterio 7 — Reglas de tier

Usá la conversación del criterio 5:
1. Pedí bajar el cambio a Tier 1.
   - Esperado: el orquestador pide la confirmación literal y recién después corre `exo fitness classify --change <c> --confirm-downgrade "<tus palabras>"`.
   - Las palabras quedan en el `history` de `fitness-assessment.json`.
2. Borrá `fitness-assessment.json` y pedí `/sdd-status`.
   - Esperado: informa Tier 4 por evaluación faltante.

| Verificación | Esperado | Resultado |
|---|---|---|
| Downgrade | Pide confirmación literal; sin ella, no baja | Pendiente |
| Evidencia faltante | Tier 4 | Pendiente |
| Tests | `pytest -k criterio_7` en el repo del motor | Pendiente |

## Hallazgos

Anotá acá lo que cambió el código o el contenido.
