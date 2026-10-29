# F6 — Ingeniería inversa y adopción de proyectos existentes

## Objetivo

Que el motor pueda llegar a un proyecto que ya existe y, sin tocar su código, lo entienda: inventario determinista, mapa de módulos, extracción asistida de lo que el sistema hace hoy con evidencia verificable, specs "as-is" por capacidad, wiki del proyecto, decisiones de arquitectura recuperadas y un backlog de adopción. Cada ajuste que haga falta para que el proyecto quede alineado al ciclo gobernado se ejecuta después **como un cambio SDD normal**, con su tier y sus gates.

## Por qué así

Las specs reconstruidas desde código son artefactos derivados y suelen tener errores si se generan de una sola pasada. El diseño ataca eso con cuatro reglas:

1. **Determinista primero.** El runtime arma el inventario, el grafo y el plan de trabajo; el modelo trabaja sobre unidades acotadas, nunca sobre el repo entero de golpe.
2. **Evidencia o no existe.** Cada requisito recuperado cita `path:line` o queda marcado `[Inferido]` con un nivel de confianza. Se reusa la convención del reporte: `[Código]`, `[Doc]`, `[Inferencia]`, `[No verificado]`.
3. **Auditoría independiente.** Un verificador con contexto fresco revisa una muestra de afirmaciones contra el código y calcula la precisión por capacidad.
4. **Hipótesis hasta validar.** Una spec recuperada está en estado `as-is` hasta que un humano la valida (`as-is-validated`).

## Depende de

F4 cerrada (formato de specs vivas, `change-root`, ciclo). F3 recomendable (la memoria híbrida ayuda a responder "dónde se maneja X" sobre los resúmenes extraídos). Decisiones D-14 y D-19.

## Alcance

Entra: módulos `discovery/` del runtime, tools MCP de discovery, pack `discovery` con sus skills, skill `architecture-decision-record` (se adelanta desde el pack `design` porque produce los ADRs recuperados), skill `context-config-audit` (audita la configuración de agentes que ya tuviera el repo), subagentes `re-extractor` y `re-auditor`, fixtures con verdad conocida.

No entra: modificar el proyecto adoptado (eso son cambios SDD del backlog); parsers con tree-sitter (D-14, futuro).

## Pipeline

| Etapa | Quién | Salida | Gate |
|---|---|---|---|
| R0 Inventario | Runtime: `arnes discover inventory` | `.arnes/discovery/inventory.json` | — |
| R1 Estructura | Runtime: `arnes discover structure` | `structure.json`, `module-graph.mmd`, `hotspots.json`, `ownership.json` | — |
| R2 Plan | Runtime: `arnes discover plan` | `plan.json` (unidades de trabajo, prioridad, estimación), `state.json` | El humano elige profundidad (`quick`, `standard`, `deep`) viendo la estimación |
| R3 Extracción | Skill `re-extract` en subagente `re-extractor`, una unidad por vez (en paralelo si el agente lo permite) | `.arnes/discovery/units/<unidad>.md` + memoria `discovery/<unidad>` | — |
| R4 Síntesis | Skill `re-synthesize` | `specs/capabilities/*/spec.md` (`as-is`), `.arnes/context.md`, ADRs recuperados, `open-questions.md`, registro de deuda | — |
| R5 Auditoría | Skill `re-audit` en subagente `re-auditor` + `arnes discover sample` | Precisión por capacidad, `coverage.md`, banderas | Capacidades con precisión baja vuelven a R3 |
| R6 Validación y adopción | Skill `arnes-adopt` + humano | Specs `as-is-validated`, `.arnes/adoption-backlog.md`, changes creados con `sdd-new` | Aprobación humana por capacidad |

### R0 — Inventario (determinista)

Lenguajes y líneas por lenguaje; manifiestos y dependencias; puntos de entrada; frameworks (extensión de `StackSignals`: además de lo del reporte, Go, .NET y otros a nivel básico); frameworks y archivos de test; configuración de CI; Docker e infraestructura como código; migraciones de base de datos; contratos de API (OpenAPI, proto, GraphQL); archivos de configuración (solo nombres, nunca contenido si pueden tener secretos). Respeta `.gitignore`, `discovery.ignore` y excluye vendorizado y generado.

### R1 — Estructura (determinista)

Detección de módulos por lenguaje (paquetes Python, workspaces o carpetas JS/TS, paquetes y módulos Maven/Gradle Java, carpetas de primer nivel como fallback). Grafo de imports: `ast` para Python, expresiones regulares para `import`/`require` en JS/TS e `import` en Java. Hotspots: churn de `git log --numstat` en los últimos N meses por tamaño. Ownership: `git shortlog` por módulo. Acoplamiento: fan-in y fan-out.

### R2 — Plan (determinista)

Unidades de trabajo de tamaño acotado (por módulo, partiendo los grandes), prioridad por criticidad (palabras clave de autenticación, pagos, seguridad y datos personales; hotspots; fan-in), estimación de esfuerzo, y `state.json` con el hash de los archivos de cada unidad. La profundidad elegida decide cuántas unidades se extraen en detalle y cuáles solo se resumen.

### R3 — Extracción (skill, por unidad)

El subagente lee la unidad y escribe: responsabilidades, entidades y modelos de datos, operaciones o endpoints, reglas de negocio, invariantes, integraciones externas, manejo de errores y notas de cobertura de tests. Cada afirmación con evidencia o marcada como inferida. Antes de mandar contenido al modelo aplica `data-classification` y `prompt-hygiene`; nunca lee `.env`, dumps ni secretos.

**El bucle lo maneja el motor, no la memoria del agente.** El agente pide la siguiente unidad con `discovery_next_unit`, registra afirmaciones con `discovery_record_claim` y cierra con `discovery_mark_done`. Así el proceso sobrevive a la compactación de contexto, a cortes y a cambios de sesión o de agente.

### R4 — Síntesis (skill)

Agrupa unidades en capacidades (contextos delimitados) y escribe:

- `specs/capabilities/<capacidad>/spec.md` con `status: as-is`, procedencia, requisitos con evidencia y confianza, y escenarios derivados de los tests cuando existen.
- `.arnes/context.md`: visión general, arquitectura (diagrama Mermaid de contexto y contenedores), módulos, flujos principales, integraciones, convenciones, cómo correr y testear.
- ADRs recuperados en `doc/adr/NNNN-recovered-<slug>.md` con estado `Recovered` y confianza.
- `.arnes/discovery/open-questions.md` con lo que solo puede responder una persona.
- Registro de deuda técnica observada.

### R5 — Auditoría

`arnes discover sample --n 30` elige afirmaciones al azar (con semilla registrada) ponderando por criticidad. El auditor, con contexto fresco, verifica cada una contra el código y marca correcta, incorrecta o no verificable. El runtime calcula precisión por capacidad y escribe `coverage.md` (porcentaje de módulos cubiertos y de requisitos con evidencia).

### R6 — Validación humana y adopción

`arnes-adopt` presenta el reporte, recorre las capacidades con el humano y las pasa a `as-is-validated` (o registra correcciones). Después analiza brechas de adopción: runner de tests, linters, CI, git hooks, CODEOWNERS, documentación mínima, convenciones de commits, ignorado de secretos, ADRs. Cada brecha se vuelve un item de `.arnes/adoption-backlog.md` y, con confirmación, un change creado con `sdd-new` que pasa por fitness. Para capacidades críticas (componentes de Tier 3 o 4) propone **tests de caracterización** que fijen el comportamiento actual antes de cualquier modificación, también como changes.

### Actualización incremental

`arnes discover update` recalcula hashes, marca como `stale` las unidades y capacidades afectadas, y la skill re-extrae solo eso. La guarda de frescura de la wiki (`project-wiki-guard`) usa esta información.

## Skills y subagentes nuevos (pack `discovery`)

| Nombre | Rol |
|---|---|
| `arnes-adopt` | Punto de entrada (`/arnes-adopt`): corre R0–R2 por CLI, conduce R3–R6, maneja reanudación |
| `re-extract` | Extracción de una unidad con evidencia |
| `re-synthesize` | Agrupación en capacidades y escritura de specs, wiki y ADRs recuperados |
| `re-audit` | Verificación de la muestra contra el código |
| `re-adoption-plan` | Análisis de brechas y backlog de adopción |
| `re-extractor`, `re-auditor` | Subagentes de solo lectura |

## Fixtures con verdad conocida

Tres repos sintéticos en `tests/fixtures/repos/` (Python tipo API, Node con Express y React, Java con Spring), de 2 a 3 mil líneas cada uno, con un archivo `GROUND_TRUTH.md` que lista capacidades, reglas de negocio y dependencias esperadas. Para la evaluación manual de escala se usa además un repo open source de tamaño medio elegido en la fase.

## Tareas (en orden)

1. `discovery/inventory.py` y `stack.py` + golden JSON sobre los tres fixtures.
2. `graph.py`, `git_metrics.py` + golden de aristas.
3. `planner.py`, `state.py`, `sampler.py`, `coverage.py` + tests de determinismo y reanudación.
4. Tools MCP de discovery + CLI `arnes discover {inventory,structure,plan,status,sample,update}`.
5. Formato de unidades, afirmaciones y specs `as-is` + extensiones de `speclint`.
6. Skills `re-extract`, `re-synthesize`, `re-audit`, `re-adoption-plan`, `arnes-adopt`, más `architecture-decision-record` y `context-config-audit`.
7. Subagentes y su render en los adaptadores.
8. Checklist manual en `docs/checklists/F6-adopcion.md` sobre un fixture y sobre el repo de escala.

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Determinismo | `arnes discover inventory/structure/plan` dos veces sobre el mismo repo produce JSON idéntico |
| 2 | Inventario correcto | En los tres fixtures se detectan stack, puntos de entrada y tests según `GROUND_TRUTH.md`; el grafo coincide con el golden |
| 3 | Adopción completa | Con Claude Code, `/arnes-adopt` sobre un fixture termina y genera al menos una spec por capacidad del ground truth |
| 4 | Precisión | La auditoría da precisión ≥ 90 % en la muestra de cada fixture |
| 5 | Solo lectura | `git status` después de R0–R5 muestra cambios solo en las rutas permitidas por la invariante 15 |
| 6 | Reanudable | Cortar el proceso a mitad de R3 y volver a correrlo continúa desde `state.json` sin rehacer unidades terminadas |
| 7 | Incremental | Modificar un archivo y correr `arnes discover update` marca como `stale` solo su unidad y su capacidad |
| 8 | Escala | En el repo de 20–50 mil líneas, cobertura de módulos ≥ 80 % (`coverage.md`) |

**Hito M3** al cerrar esta fase.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Repos enormes que no entran en contexto | Unidades acotadas, profundidad elegible, estimación previa |
| Reglas de negocio inventadas | Evidencia obligatoria, auditoría con contexto fresco, gate humano |
| Costo y tiempo de tokens | Plan con estimación, prioridad por criticidad, modo `quick` |
| Parsers heurísticos con límites | Fallback a nivel de archivo; tree-sitter como extra posterior (D-14) |
| Datos sensibles en el código | `data-classification` antes de cada lectura enviada al modelo, exclusiones duras |
