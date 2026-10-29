# F4 — Ciclo SDD con specs vivas

## Objetivo

Que un cambio recorra el ciclo spec-driven proporcional a su riesgo, de punta a punta, tanto en un agente con subagentes (Claude Code) como en uno sin ellos (modo inline declarado), y que el comportamiento aprobado se acumule en specs vivas por capacidad.

## Depende de

F2 cerrada (para instalar y probar en agentes reales). F3 es opcional: si no está, el ciclo usa el modo de persistencia `filesystem` (default del reporte). Decisiones D-09, D-10, D-11 y D-13.

## Alcance

Entra: contratos compartidos, skills del pack `core` que el ciclo necesita, todas las skills de fase del pack `sdd`, subagentes canónicos completos, plantilla de `proposal.md`, deltas de specs y su integración, esquema del AI Usage Record, comandos `arnes change` y `arnes specs`, y la primera versión de `arnes check`.

No entra: gates de calidad y seguridad, jueces y git hooks (F5); SPDD/REASONS Canvas (F7).

## Contratos compartidos (`content/shared/` → `.arnes/shared/`)

Se escriben de nuevo a partir de lo que el reporte describe (los textos originales no están disponibles):

| Archivo | Contenido mínimo | Fuente en el reporte |
|---|---|---|
| `phase-skill-map.md` | Tabla fase → skills Required, Conditional (trigger → skill) y jueces por tier; máximo 5 skills por delegación | §6.4 |
| `sdd-phase-common.md` | Secciones A (cargar skills leyendo el `SKILL.md` completo), B (modos de recuperación `filesystem`/`memory`/`hybrid`/`none`), C (persistencia en `<change-root>`, nombres exactos por fase, no tocar artefactos de otras fases), D (envelope YAML), E (`change-name` y pregunta única por ticket), F (épica) | §6.5 |
| `skill-resolver.md` | Resolución por nombre, degradación declarada cuando falta un pack, registro de `skill_resolution` | §2.5, §6.6 |
| `sdd-status-contract.md` | Cómo se deriva el estado de un change desde artefactos y memoria, sin adivinar | `sdd-status` (§3) |
| `project-wiki-guard.md` | Chequeo de frescura de la rama y de `.arnes/context.md` al inicio y antes del PR | §6.2 (diagrama) |
| `memory-convention.md` | Tags `sdd/<change-name>/<artefacto>`, recuperación en 2 pasos, artefacto de estado para sobrevivir a la compactación | §5.6 |
| `capability-attribution.md` | Registro de capacidades usadas (`capabilities_used`: nombre, tipo, activación) | §6.6, §7.7 |
| `agent-capabilities.md` (nuevo) | Qué hacer con y sin subagentes, con y sin hooks, y cómo emular "contexto fresco" (sesión nueva con archivo de traspaso) | Nuevo |
| `schemas/ai-usage-record.schema.json` | Campos del §7.7, con `capabilities_used` obligatorio y no vacío | §7.7 |

## Skills a escribir

Cada skill sigue el formato canónico (`02-ARQUITECTURA.md` §2.6), tiene hasta 500 líneas, empieza por el resultado esperado, y declara en su `description` cuándo usarla con disparadores en español e inglés.

**Pack `core`:** `context-retrieval` (ex `knowledge-retrieval`: recuperar contexto antes de afirmar, cita corta junto a cada afirmación y línea final `Fuentes:` con Código/Docs/Memoria/MCP), `ai-usage-record`, `test-strategy`, `code-generation`, `branch-pr`, `work-unit-commits`, `project-onboarding` (refina el perfil del proyecto después de `arnes init` y lo guarda en `.arnes/context.md` y en memoria).

**Pack `sdd`:** `sdd-orchestrator`, `sdd-init`, `sdd-new`, `sdd-explore`, `sdd-propose`, `sdd-spec`, `sdd-design`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-archive`, `sdd-status`, `risk-tiering` (ex `spdd-fitness-matrix`: junta evidencia de las 7 dimensiones y llama a `arnes fitness classify`).

Reglas que el contenido tiene que respetar (del reporte):

- El orquestador coordina y no ejecuta; deriva `change-name` y épica con una pregunta cada uno; corre el fitness gate; es el único que re-clasifica el tier (upgrade automático, downgrade con confirmación literal del humano); tier desconocido es Tier 4 (§6.1, §6.3).
- Delegación: leer 1–3 archivos inline, 4 o más delegar; tests y build delegados; permisos por defecto denegados; nadie re-delega; los revisores son solo lectura; disparadores obligatorios de delegación (regla de 4 archivos, escritura multi-archivo, revisión fresca antes del PR, incidente, sesión larga, revisión fresca) (§6.6).
- Ceremonias por tier y artefactos obligatorios: Tier ≥ 2 exige `test-spec.md` (§6.3, §6.4).
- `sdd-verify` devuelve exactamente las secciones del §6.7, incluido el `Gate summary` con su marcador.
- `sdd-init` y `sdd-archive` corren **inline** (resuelve la inconsistencia 4 del reporte: interactúan con el humano y tocan la wiki y el archivo).
- Modo interactivo por defecto ("¿Ajustamos algo o seguimos?") y modo automático opcional.

**Subagentes canónicos completos:** `sdd-explorer`, `sdd-implementer`, `sdd-verifier`, `sdd-judge` (este último se usa recién en F5), con las herramientas permitidas de cada rol.

## Specs vivas (D-11)

- `specs/capabilities/<capacidad>/spec.md` es la fuente de verdad del comportamiento vigente, con requisitos identificados (`CAP-<capacidad>-FR-n`) y escenarios.
- El `spec.md` de un change es un **delta** con secciones `ADDED Requirements`, `MODIFIED Requirements` y `REMOVED Requirements`, que referencian IDs existentes o nuevos.
- `arnes specs merge <change>` aplica el delta de forma determinista (por ID) y falla si un `MODIFIED` o `REMOVED` apunta a un ID inexistente. `sdd-archive` lo invoca y resuelve con juicio lo que no es mecánico.
- `speclint` valida el formato del delta y las referencias.

## Runtime de esta fase

- `arnes change new <nombre>`: valida el nombre (§6.5 E, adaptado al tracker), crea el `change-root` y el AI Usage Record inicial.
- `arnes change status [<nombre>]`: lo mismo que `get_change_state`, por CLI.
- `arnes specs merge <change>` y `arnes specs list`.
- `arnes check` (v1): speclint sobre los changes tocados en el diff, presencia y esquema de `ai-usage-record.json`, artefactos obligatorios por tier. F5 lo extiende.
- Plantilla `proposal.md` (intención, alcance, enfoque, fuera de alcance).

## Tareas (en orden)

1. Contratos compartidos + esquema del AI Usage Record + validador de esquema mínimo en stdlib.
2. Deltas de specs: formato, `speclint` extendido, `arnes specs merge` + tests.
3. `arnes change new/status` + `arnes check` v1 + tests.
4. Skills `core` del ciclo.
5. Skills `sdd` de fase, empezando por `sdd-new`, `sdd-status` y `risk-tiering`; después el resto en orden de fase.
6. `sdd-orchestrator` con sus meta-comandos (`/sdd-new`, `/sdd-continue`, `/sdd-ff`, `/sdd-status`) y el camino sin subagentes.
7. Subagentes canónicos completos y su render en los adaptadores.
8. Test de consistencia del mapa fase → skills (port del smoke `test_phase_skill_map_consistency`): toda skill mencionada existe o pertenece a un pack opcional y tiene degradación declarada.
9. Fixture `tests/fixtures/repos/toy-python/` y checklist manual del ciclo en `docs/checklists/F4-ciclo.md`.
10. A partir del cierre de esta fase, las funcionalidades nuevas del propio motor se desarrollan con este ciclo (dogfooding).

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Contenido válido | `arnes validate` verde con las ~21 skills de esta fase y los contratos |
| 2 | Mapa consistente | Test de consistencia del mapa fase → skills verde |
| 3 | Deltas deterministas | `arnes specs merge` sobre fixtures produce el resultado esperado y falla en referencias inexistentes |
| 4 | Ciclo Tier 1 con subagentes | En Claude Code sobre `toy-python`: `/sdd-new` → … → `sdd-archive` produce artefactos que pasan `arnes speclint` y `arnes check`, y el delta queda integrado en `specs/capabilities/` |
| 5 | Ciclo Tier 3 | Mismo fixture, un cambio que el fitness clasifica Tier 3: aparecen `design.md`, `tasks.md` y `test-spec.md`; `sdd-verify` corre en un subagente con contexto fresco |
| 6 | Ciclo sin subagentes | Con un agente sin delegación (o Copilot en un modo sin subagentes), el Tier 1 corre inline, declara "sin aislamiento" y los artefactos pasan los mismos chequeos |
| 7 | Reglas de tier | Evidencia faltante da Tier 4; un downgrade pide confirmación literal (verificado en la conversación del checklist y en tests de `compare_tiers`) |

## Referencias al reporte

Capítulo 06 completo, §5.6, §7.7, §10.4 (escenarios del smoke).
