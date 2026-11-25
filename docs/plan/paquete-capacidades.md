# Paquete de trabajo: capacidades del agente, modelo por tier, segunda opinión y 3 tiers

> Escrito el 2026-11-22 a partir de una sesión de diseño con el dueño. Es un paquete posterior a F8: agrega las fases F9 a F13 al plan. Va en `docs/plan/paquete-capacidades.md`.
>
> **Registro en el plan (paso 0, 2026-11-25):**
> - **Numeración.** El original traía las decisiones D-49 a D-52. Esos números ya estaban usados (D-49 licencia, D-50 y D-51 cierre de F8), así que pasaron a **D-52 (tres tiers), D-53 (catálogo), D-54 (modelos) y D-55 (segunda opinión)**, y este archivo ya usa los números nuevos. Los ADRs son el 0019 (tres tiers) y el 0020 (capacidades, modelos y segunda opinión).
> - **Versión.** `git tag --list "v1*"` devuelve `v1.0.0`, así que el paquete termina en **2.0.0** (sección 0, punto 2).
> - **Decisiones del dueño del 2026-11-25**, que se suman a D-52 y a F9: los gates del Tier 3 son la unión de los del Tier 3 y el Tier 4; los cambios activos en Tier 3 adoptan las reglas nuevas; y los archivados con assessment del esquema viejo se validan solo por estructura.
> - **Cierre de cada fase:** por PR, que el dueño abre y mergea (D-51).

---

## 0. Para el dueño: cómo usar este archivo

1. Copiá este archivo a `docs/plan/paquete-capacidades.md` en el repo de exo.
2. Corrélo cuando F8 esté cerrada.
   - Si la v1.0 todavía no tiene tag, el paquete entra antes del tag y no hace falta cambiar de versión mayor.
   - Si la v1.0 ya tiene tag, el paquete termina en **2.0.0**, porque pasar de 4 tiers a 3 es incompatible con lo publicado. La migración va incluida.
3. Abrí Claude Code en la raíz del repo y pegá:

```text
Leé docs/plan/paquete-capacidades.md completo y seguí la sección 1.
Arrancá por el paso 0 en plan mode y esperá mi aprobación.
```

4. Cada fase se aprueba en plan mode, como en F0 a F8.

---

## 1. Instrucciones para Claude Code

Vas a construir un paquete nuevo sobre exo, que ya está terminado hasta F8. El plan sigue mandando sobre todo lo demás. Este archivo agrega decisiones del dueño y cinco fases nuevas.

### Antes de empezar

1. Leé `CLAUDE.md`, `AGENTS.md`, `docs/plan/00-LEEME-PRIMERO.md`, `docs/plan/02-ARQUITECTURA.md`, `docs/plan/03-MATRIZ-AGENTES.md`, `docs/plan/04-DECISIONES.md`, `docs/plan/PROGRESO.md` y este archivo completo.
2. Confirmá en `PROGRESO.md` que F8 está **Terminada**. Si no lo está, frená y avisá.
3. Corré `git tag --list "v1*"` y anotá el resultado en `PROGRESO.md`. Define la versión de salida (ver sección 0, punto 2).

### Paso 0 — Registrar el paquete en el plan (rama `feat/paquete-registro`, un solo PR)

1. Agregá a `04-DECISIONES.md` las decisiones D-52 a D-55 de la sección 3, con estado "Decidida por el dueño, 2026-11-22". (El original decía D-49 a D-52; ver la nota del principio.)
2. Escribí un ADR por decisión (o uno solo que las agrupe, si es más claro), con el siguiente número libre. En el ADR, listá los defaults de la sección 3.5 como **revisables**.
3. Creá `docs/plan/fases/F9-tres-tiers.md` a `F13-medicion.md` copiando la sección 5. No cambies criterios sin preguntar.
4. Sumá F9 a F13 a la tabla de `PROGRESO.md` y al mapa de fases de `00-LEEME-PRIMERO.md`.
5. En `02-ARQUITECTURA.md` agregá una sección nueva, "Capacidades, modelos y segunda opinión", que resuma la sección 3 y apunte a los ADRs.

### Reglas propias de este paquete

- **Los nombres de archivos y módulos de este prompt son orientativos.** Ubicá los reales antes de tocar nada. Por ejemplo, las tools viven en `src/exo/tools/registry.py` (ADR-0005).
- **Todo dato sobre lo que trae un agente se verifica en la fuente oficial**, con URL y fecha. Lo que no se pueda confirmar queda `[No verificado]` y su comportamiento degrada. No se inventa.
- **exo no llama a modelos ni a APIs de IA.** Quien consulta un modelo es siempre el agente. La segunda opinión propia es un subagente del agente, no una llamada del runtime. Esto no cambia la invariante 11.
- **Sin hooks de agente** (D-31). Lo que haya que hacer en un momento dado va en el texto de las skills, y lo verificable va a `exo check`.
- **CLI primero** (ADR-0005). Todo lo nuevo es un subcomando `exo … --json`; MCP solo lo expone si está habilitado.
- **Idiomas** (ADR-0011, D-48). Lo que se instala en los proyectos va en inglés: skills, subagentes, contratos, artefactos, mensajes del CLI y docs de usuario. El plan y los ADRs van en español.
- **Adaptadores propios solo para Claude Code y Copilot** (D-04). El resto de los agentes resuelve todo como `exo` o `human`.
- **Lo que depende de cada persona vive en su máquina**, nunca en el repo: elecciones nativo/exo y modelos concretos.
- **Si aparece una duda que cambia el diseño**, agregala como D-xx y preguntá antes de seguir.

---

## 2. Objetivo

Al terminar el paquete:

1. El ciclo SDD tiene **3 tiers** en lugar de 4.
2. exo sabe qué trae de fábrica el agente de cada persona. Para cada funcionalidad usa la nativa o la propia, según lo que esa persona eligió **una sola vez**.
3. Cada fase corre con un **modelo acorde a su tier y a su rol**.
4. En los Tiers 2 y 3, el agente pide **segunda opinión en tres puntos fijos**, con tope. En el Tier 3, lo que se aconsejó queda escrito.
5. Hay **datos** para saber si esto bajó el retrabajo y cuánto cuesta.

---

## 3. Decisiones del dueño (2026-11-22)

### 3.1 D-52 — Tres tiers

| Tier | Nombre | Para qué | Artefactos obligatorios | Chequeo |
|---|---|---|---|---|
| 1 | Small | Cambio pequeño, sin riesgo | `proposal.md`; `spec.md` solo si cambia comportamiento (regla actual de D-27) | `verify` |
| 2 | Spec | Riesgo leve | `proposal.md`, `spec.md`, `test-spec.md` (lo escribe `sdd-spec` con `test-strategy`) | `verify` + segunda opinión en los 3 puntos |
| 3 | Full | Riesgo alto o crítico | `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `test-spec.md` (lo escribe `sdd-tasks`) | `verify` + segunda opinión en los 3 puntos + jueces + `judgment-day` **siempre** |

Todos los tiers siguen exigiendo `ai-usage-record.json` válido.

**Reglas del fitness:**

| Regla | Condición | Antes | Ahora |
|---|---|---|---|
| FM-01, FM-02, FM-03 | Seguridad/datos, reversibilidad o impacto regulatorio == 3 | Tier 4 | **Tier 3** |
| FM-10 a FM-13 | Criticidad, blast radius o footprint == 3, o ≥ 3 dimensiones ≥ 2 | Tier 3 | Tier 3 |
| FM-20 | ≥ 1 dimensión ≥ 2 | Tier 2 | Tier 2 |
| FM-30 | Todas ≤ 1 | Tier 1 | Tier 1 |
| Evidencia faltante o ilegible | — | Tier 4 | **Tier 3** |

- **Ceremonias:** `minimal`, `light` y `full`, una por tier. Antes había cuatro tiers para tres ceremonias.
- **No hay marca de "piso duro".** Como `judgment-day` corre siempre en el Tier 3, no hace falta distinguirlo. La regla que disparó el tier (FM-01, FM-10…) queda anotada en `fitness-assessment.json`, como hoy.
- **Bajar de tier** sigue pidiendo la confirmación literal de la persona.
- **Migración:**
  - Los cambios activos con tier 4 pasan a tier 3 y registran `migrated_from: 4`.
  - Los cambios archivados no se reescriben. Al leerlos, un 4 se interpreta como 3 (lectura tolerante).
- Esta decisión **reemplaza D-27** en todo lo que toca a los Tiers 3 y 4.

### 3.2 D-53 — Catálogo de capacidades: nativo primero, con pregunta única

- **Catálogo completo desde la primera versión** (lista en F10). Cada capacidad tiene una política:
  - `native`: si el agente la trae y la persona la aceptó, se usa la nativa; si no, la de exo; si tampoco hay, la persona.
  - `exo`: siempre la de exo. Es el caso de todo lo que gobierna o deja prueba: gates, jueces, `judgment-day`, fitness, `exo check`, AI Usage Record, specs, memoria y enforcement. **Nunca se ofrece como nativa.**
  - `complement`: la nativa puede sumar información, pero nunca reemplaza a la de exo. Por ejemplo, un revisor incorporado puede aportar hallazgos al gate.
- **Pregunta única por máquina.**
  - En `exo init`, si no hay perfil para el agente detectado, exo muestra qué capacidades `native` trae ese agente y ofrece tres opciones: usar todas, elegir una por una, o ninguna.
  - La respuesta se guarda en el perfil de la máquina.
  - Solo se vuelve a preguntar si cambia el agente o si una versión nueva trae una capacidad nativa que antes no estaba, y en ese caso solo por esa capacidad.

### 3.3 D-54 — Modelo por tier y por rol

- **Tres niveles abstractos:** `fast`, `balanced` y `deep`.
  - **La política vive en el repo** (`.exo/config.json`) y usa solo niveles.
  - **El mapa de nivel a modelo concreto vive en el perfil de cada máquina**, porque depende del agente y de la cuenta de cada persona.
- **Defaults:**

| Rol | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| explore (solo lectura) | fast | fast | fast |
| propose / spec / tasks | balanced | balanced | balanced |
| design | — | — | deep |
| apply | balanced | balanced | balanced |
| verify | balanced | balanced | deep |
| jueces y `judgment-day` | — | — | deep |
| segunda opinión | — | deep | deep |

- **Cómo se aplica.** Al delegar, el orquestador pasa el modelo que corresponde a ese rol y ese tier.
  - Si el agente no permite elegir el modelo de un subagente, se usa el de la sesión, se avisa y se registra.
  - Nunca se escribe un modelo concreto en archivos versionados.

### 3.4 D-55 — Segunda opinión

- **Tier 1:** solo si la persona lo pide.
- **Tiers 2 y 3: en tres puntos.**

| Punto | Cuándo | Obligatorio |
|---|---|---|
| `approach` | Una vez por cambio, antes de comprometer el enfoque. Tier 2: al empezar `apply`, antes de escribir. Tier 3: al cerrar `design` | Sí |
| `stuck` | Cuando el mismo error aparece por segunda vez, o tras dos intentos fallidos de arreglar algo | Solo si pasa |
| `done` | Al terminar `apply`, antes de `verify` | Sí |

- **Orden de resolución:**
  - **Tier 2:** nativa (si la persona la aceptó y está disponible) → `exo-advisor` → persona.
  - **Tier 3:** `exo-advisor` → persona. Va siempre por el camino propio para que lo aconsejado **quede escrito**, porque el advisor nativo puede no dejar leer lo que dijo.
- **Tope por tier, configurable** (`second_opinion.max_per_change`).
  - El tope cuenta todas las consultas a modelos, pero siempre reserva lugar para los puntos obligatorios que falten. Las consultas `stuck` solo usan lo que sobra.
  - Al llegar al tope, el agente no consulta más modelos, lo registra y, si sigue trabado, le pregunta a la persona.
  - Las respuestas de la persona no cuentan para el tope.
- **Registro:**
  - Cada consulta queda en el AI Usage Record: punto, quién la resolvió (`native`, `exo` o `human`), modelo pedido y modelo informado.
  - En el Tier 3, además, cada consulta deja un archivo de consejo en el change.

### 3.5 Defaults que el dueño no confirmó todavía

Se aplican, y en el ADR quedan como **revisables**:

- **Topes:** Tier 2 = 3 consultas por cambio; Tier 3 = 6.
- **Exploración** y búsquedas de solo lectura en `fast`.
- **Misma familia:** la segunda opinión usa un modelo más fuerte del mismo agente. Usar otra familia de modelos (como Rubber Duck en Copilot) queda fuera del paquete.
- **`exo init` sin terminal:** se aplica la política (nativas donde corresponde) y se registra `chosen_by: default`.
- **Datos viejos:** `exo doctor` avisa cuando los datos de capacidades tienen más de 60 días desde `verified_at`.
- **Cambios archivados:** no se reescriben.

---

## 4. Lo que ya existe y se reutiliza

- **Detección del agente** por variables de entorno (`CLAUDECODE=1`, `COPILOT_CLI=1`, `AI_AGENT`, `CURSOR_AGENT`, `GEMINI_CLI`), verificada en F0 y documentada en `03-MATRIZ-AGENTES.md`.
- **`capabilities()` de cada adaptador** (§2.8): reglas, skills, subagentes, MCP, hooks y comandos. El catálogo nuevo lo amplía, no lo reemplaza.
- **El contrato `agent-capabilities.md`**: qué hacer con y sin subagentes, y cómo emular contexto fresco.
- **`capabilities_used` del AI Usage Record** (`{name, type, activation}`). Ojo: `activation` ya significa "a pedido o automático". Para "quién la resolvió" se agrega un campo **nuevo**, `provided_by`; no se reutiliza `activation`.
- **El protocolo de degradación declarada** (§2.5).
- **El campo `model` opcional** en el formato canónico de subagente (§2.7).
- **`docs/agent-matrix.md`**: URL y fecha por celda.

**Lo que no existe:** la selección de modelo por niveles se diseñó antes de la versión actual del plan y nunca entró. Se implementa acá (D-54).

---

## 5. Fases

Cada fase va en su propia rama (`feat/F<n>-<slug>`), arranca en plan mode, tiene los tests primero y se cierra con cada criterio corrido con su comando exacto y anotado en `PROGRESO.md`. La cobertura de `src/exo` sigue en ≥ 85 % y la CI tiene que estar verde en los tres sistemas operativos.

### F9 — Tres tiers

**Objetivo.** Pasar de 4 tiers a 3 sin perder ningún control, con una migración para los proyectos que ya tienen cambios en Tier 4.

**Depende de.** El paso 0 cerrado.

**Tareas, en orden:**

1. **Fitness** (`sdd/fitness.py` o donde viva):
   - remapear las reglas según 3.1;
   - la evidencia faltante o ilegible da Tier 3;
   - el mapeo de ceremonias queda `minimal`, `light`, `full`;
   - `compare_tiers` conserva su semántica.
2. **`classification-rules.md`** de `risk-tiering`, actualizado, con el test de paridad en verde.
3. **Esquema de `fitness-assessment.json`:**
   - el tier pasa a 1–3;
   - se suma el campo opcional `migrated_from`;
   - se sube la versión del esquema.
4. **`exo check`:**
   - artefactos por tier según 3.1;
   - en el Tier 3, `judgment-day` registrado siempre.
5. **Contenido.** Buscá "Tier 4", "Tier ≥ 3", "tier 4" y "piso duro" en `content/` y actualizá lo que encuentres. Como mínimo:
   - `risk-tiering`, `sdd-orchestrator` y `phase-skill-map.md` (jueces y `judgment-day` en Tier 3);
   - `sdd-verify` (el "Judgment Day Handoff" pasa a Tier 3);
   - `judgment-day`;
   - los contratos `sdd-phase-common.md` y `agent-capabilities.md`;
   - en la adopción, los tests de caracterización para Tier 3.
6. **Migración:**
   - un paso de migración, dentro del mecanismo que ya use `exo update`, que pase de 4 a 3 los cambios activos y registre `migrated_from: 4`;
   - lectura tolerante en la observabilidad y en `exo check`, para que un archivado con tier 4 se lea como 3 sin reescribirlo.
7. **Docs de usuario en inglés** (README, QUICK-START y guías), CHANGELOG con entrada **BREAKING** y la versión según la sección 0.
8. **Tests:** tabla de reglas, fixtures de migración y el escenario `agent_e2e` de Tier 3 actualizado.

**Criterios de aceptación:**

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Las reglas críticas dan Tier 3 | `exo fitness classify --evidence-json '{"security_data_sensitivity":3, …}'` devuelve Tier 3 con la regla FM-01 |
| 2 | Tabla completa y paridad | `pytest tests/test_fitness.py` cubre FM-01 a FM-30 y la evidencia ilegible (Tier 3); la paridad con el Markdown, en verde |
| 3 | Check estricto en Tier 3 | `exo check` falla en un Tier 3 sin `design.md`, sin `tasks.md`, sin `test-spec.md` o sin el registro de `judgment-day`, y pasa cuando está completo |
| 4 | Migración | Sobre un fixture con un cambio activo en Tier 4 y otro archivado en Tier 4: después de migrar, el activo queda en Tier 3 con `migrated_from: 4`, el archivado queda idéntico byte a byte, y `exo check` y `exo change status` funcionan con los dos |
| 5 | Sin restos | `grep -rn "Tier 4" content/ src/` solo devuelve el código de migración y de lectura tolerante |
| 6 | Agente real | Con Claude Code, un cambio con `security_data_sensitivity: 3` queda en Tier 3 y corre `judgment-day` |

### F10 — Catálogo de capacidades y perfil por máquina

**Objetivo.** Que exo sepa qué trae el agente de cada persona, pregunte una sola vez qué usar y lo informe a las skills con un comando.

**Depende de.** F9.

**Tareas, en orden:**

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

**Catálogo inicial:**

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

**Criterios de aceptación:**

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Matriz verificada | `docs/capabilities-matrix.md` tiene todas las capacidades × Claude Code y Copilot, cada celda con URL y fecha o `[No verificado]` |
| 2 | Resolución correcta | Golden tests de `exo capabilities --json` con entornos simulados (`CLAUDECODE=1`, `COPILOT_CLI=1`, desconocido) y perfiles de fixture |
| 3 | Pregunta única | En un `HOME` temporal, el primer `exo init` pregunta y el segundo no. Si los datos agregan una capacidad nativa, solo se pregunta por esa |
| 4 | Nada personal en el repo | Después de `exo init`, `git status` y `.exo/lock.json` no muestran el perfil ni modelos concretos |
| 5 | Gobierno intocable | Test: ninguna capacidad `exo` aparece en la pregunta ni puede elegirse como nativa |
| 6 | Doctor | Avisa con datos de más de 60 días, sin perfil y con una capacidad nativa que desapareció |
| 7 | Validador | `exo validate` falla si una capacidad no tiene datos para `claude-code` o `copilot` |

### F11 — Modelo por tier y por rol

**Objetivo.** Que cada fase corra con el modelo que pide su tier, con la política en el repo y los modelos concretos en la máquina de cada persona.

**Depende de.** F10 (perfil y verificación de `subagent_model`).

**Tareas, en orden:**

1. **Política en `.exo/config.json`:**
   - `models.policy` por tier y por rol, con los defaults de D-54;
   - solo admite `fast`, `balanced` y `deep`;
   - subida de esquema, con una migración que agrega los defaults si falta la sección.
2. **Mapa en el perfil de la máquina:**
   - nivel → modelo concreto del agente;
   - la pregunta única de F10 suma este paso, con sugerencias tomadas de los datos del agente;
   - `--reconfigure` permite cambiarlo.
3. **Resolución:** `exo capabilities --json --tier <n> --role <rol>` devuelve:
   - el nivel;
   - el modelo concreto;
   - el mecanismo (parámetro por invocación, frontmatter o sesión);
   - un aviso si cae al modelo de la sesión.
4. **Skills:**
   - `sdd-orchestrator` y las skills de fase pasan el modelo al delegar, según la resolución;
   - si `subagent_model` no está disponible, declaran la degradación;
   - los subagentes canónicos versionados no llevan modelo concreto (sin campo o `inherit`, según lo que confirme F10).
5. **`exo doctor`:**
   - mapa incompleto;
   - en Claude Code, `CLAUDE_CODE_SUBAGENT_MODEL` definido (según la sección 6, pisaría la elección por invocación; confirmalo en F10).
6. **AI Usage Record:**
   - `models_used`: `{phase, role, level, model_requested, model_reported, mechanism}`;
   - `model_reported` lo informa el agente y es advisory, porque exo no puede observarlo.
7. **Doc de usuario** "Models and tiers", en inglés.

**Criterios de aceptación:**

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Resolución | Golden tests por tier × rol × agente simulado |
| 2 | Política sin modelos concretos | `exo validate` (o la carga de la config) falla si `.exo/config.json` trae un nombre de modelo en lugar de un nivel |
| 3 | Migración de config | Una config sin `models` recibe los defaults; correrla dos veces no cambia nada |
| 4 | Degradación | Con un agente simulado sin `subagent_model`: modelo de la sesión, aviso y `mechanism: session` en el registro |
| 5 | Agente real | Con Claude Code, un cambio Tier 3 corre design, verify y los jueces con el modelo mapeado a `deep`, y apply con el de `balanced`. Evidencia: AI Usage Record y transcript de los subagentes |

### F12 — Puntos de decisión y segunda opinión

**Objetivo.** En los Tiers 2 y 3, el agente se detiene en los tres puntos, consulta por el camino que corresponde, respeta el tope y deja el registro. En el Tier 3, deja también lo aconsejado por escrito.

**Depende de.** F11.

**Tareas, en orden:**

1. **Contrato `content/shared/second-opinion.md`**, en inglés:
   - los tres puntos (3.4) y en qué fase cae cada uno;
   - el orden de resolución por tier;
   - el tope y la reserva de los puntos obligatorios.
   - **El briefing:**
     - la pregunta concreta;
     - un resumen corto del contexto;
     - las rutas a los artefactos y al diff;
     - lo que ya se intentó.

     Antes de armarlo se aplica `prompt-hygiene`: nada de secretos ni datos personales.
   - **El formato de respuesta:** `Verdict` (`proceed`, `adjust` o `stop`), `Why`, `Recommendations`, `Risks` y `Confidence`.
2. **Subagente canónico `exo-advisor`:**
   - solo lectura: no edita ni ejecuta comandos que escriban;
   - corre con el modelo `deep` resuelto por invocación;
   - lee el briefing y los archivos citados y responde en el formato del contrato.
3. **CLI `exo advice`:**
   - `budget <change> --json`: usadas, límite, obligatorias pendientes y lo que queda para `stuck`.
   - `record <change> --checkpoint approach|stuck|done --provider native|exo|human [--model <m>] [--stdin]`:
     - registra en el AI Usage Record;
     - con `--stdin`, guarda la respuesta en `<change-root>/advice/NN-<checkpoint>.md`;
     - rechaza una consulta a modelo por encima del tope (las de la persona no cuentan).
   - `list <change> --json`.
4. **Skills:**
   - `sdd-apply`: `approach` en Tier 2, `stuck` y `done`;
   - `sdd-design`: `approach` en Tier 3;
   - `sdd-orchestrator` y `phase-skill-map.md`;
   - en Tier 1, solo si la persona lo pide.
5. **Camino nativo (solo Tier 2, y solo si la persona lo aceptó y está disponible):**
   - **Claude Code:** la skill le pide al agente, en lenguaje natural, que consulte a su advisor sobre el punto, y después corre `exo advice record --provider native` sin contenido.
   - **Copilot CLI:** lo mismo con Rubber Duck, con el mecanismo que confirme F10.
   - **Configuración del advisor nativo en Claude Code, por máquina:**
     - si F10 confirma un lugar no versionado donde se acepta `advisorModel`, `exo init` ofrece setearlo con el modelo `deep` del mapa;
     - si no, imprime `/advisor <modelo>`.
6. **`exo check`:**
   - **Tier 2:** `approach` y `done` registrados, con cualquier proveedor.
   - **Tier 3:** `approach` y `done` registrados con proveedor `exo` o `human`, cada uno con su archivo en `advice/`.
   - **Tiers 2 y 3:** las consultas a modelos no superan el tope.
   - **Tier 1:** nada obligatorio.
7. **Config `second_opinion.max_per_change`**, con los defaults de 3.5, y su migración.
8. **`exo doctor`**, solo si la persona eligió el advisor nativo de Claude Code:
   - proveedor distinto de la API de Anthropic;
   - telemetría o feature flags desactivados;
   - `CLAUDE_CODE_DISABLE_ADVISOR_TOOL` definido;
   - el modelo `deep` del mapa por debajo del `balanced` (el advisor tiene que estar a la par o por encima del modelo principal).

**Criterios de aceptación:**

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Contenido válido | `exo validate` y el test de consistencia del mapa fase → skills, en verde, con el contrato y el subagente nuevos |
| 2 | Tope con reserva | Tests de `exo advice budget/record`. En Tier 2 con tope 3: `approach` y `done` reservados, una `stuck` permitida, la segunda rechazada, y una consulta a la persona siempre aceptada |
| 3 | Check | Un Tier 3 sin el archivo de `done` da rojo y completo da verde. Un Tier 2 con registros `native` da verde |
| 4 | Tier 3 real | Con Claude Code, un cambio Tier 3 deja dos archivos en `advice/` escritos a partir de `exo-advisor` con el modelo `deep`, y `exo check` en verde |
| 5 | Tier 2 real | Con el advisor nativo aceptado, queda registrado como `native`. Si no está disponible, cae a `exo-advisor` y lo registra |
| 6 | Sin hooks | Ningún adaptador escribe hooks de agente para esto (D-31) |

### F13 — Medición y ajuste

**Objetivo.** Tener datos para decidir si la segunda opinión y los modelos por tier bajan el retrabajo y cuánto cuestan, y ajustar los defaults con un ADR.

**Depende de.** F12.

**Tareas, en orden:**

1. **Rondas de verify.** Si todavía no se registran, `sdd-verify` anota en el AI Usage Record cada ronda con su veredicto. Revisá primero lo que ya existe.
2. **`exo report [--json] [--since <fecha>]`.** Recorre los cambios activos y archivados, y reporta por tier:
   - cantidad de cambios;
   - rondas de verify hasta `ready` (promedio y máximo);
   - consultas por punto y por proveedor;
   - veces que se llegó al tope;
   - resultados de `judgment-day`;
   - modelos por rol.

   Tiene que ser determinista.
3. **Evals `agent_e2e`**, con presupuesto acotado: cambios Tier 2 y Tier 3 sobre los fixtures, con y sin segunda opinión (por config). La cantidad de corridas se define en plan mode según el costo.
4. **Regla de decisión, escrita antes de correr** (como en F3). Por ejemplo: la segunda opinión queda activada por defecto si baja las rondas de verify y los hallazgos de los jueces sin subir el costo por encima de un límite que se fija antes.
5. **Reporte** en `docs/evals/second-opinion-<fecha>.md` y **ADR** que confirme o ajuste los defaults de 3.5 y D-54.

**Criterios de aceptación:**

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Reporte determinista | `exo report --json` dos veces sobre el mismo fixture da salidas idénticas |
| 2 | Evals | `docs/evals/second-opinion-<fecha>.md` con la tabla de resultados y la regla de decisión escrita antes |
| 3 | Decisión | ADR con los defaults confirmados o ajustados, y `04-DECISIONES.md` actualizado |

---

## 6. Hechos externos: punto de partida para la verificación de F10

Relevados el 2026-11-22. **No se dan por ciertos:** F10 los verifica contra la fuente oficial y anota URL y fecha.

**Claude Code: advisor.** Fuente: https://code.claude.com/docs/en/advisor. Leído en la doc oficial.
- **Configuración:** con `/advisor`, con el setting `advisorModel` o con el flag `--advisor`. El flag no aparece en `--help`.
- **Orden de modelos:** el advisor tiene que estar a la par o por encima del modelo principal.
- **Subagentes:** heredan el advisor y se les aplica el mismo chequeo contra su propio modelo.
- **Cuándo consulta:** no hay setting para limitar ni forzar las consultas; se pide en las instrucciones.
- **Disponibilidad:** solo con la API de Anthropic, no con Bedrock, Claude Platform on AWS, Agent Platform de Google Cloud ni Foundry. Lo apagan `DISABLE_TELEMETRY` (que corta la descarga de feature flags) y `CLAUDE_CODE_DISABLE_ADVISOR_TOOL`.
- **Fallo silencioso:** si la API rechaza la combinación de modelos, reenvía sin advisor y no muestra error.
- **Costo:** cada consulta procesa el transcript completo, sin caché del lado del advisor.
- **Estado:** experimental. `/advisor` funciona en `-p` y en el Agent SDK desde la v2.1.260. La guía se lee con Ctrl+O cuando es legible.

**Advisor tool en la API.** Fuente: https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool. Leído en la doc oficial.
- Los advisors más nuevos devuelven el resultado encriptado y el cliente no lo puede leer.

**Claude Code: modelo por subagente.** Fuentes: https://code.claude.com/docs/en/sub-agents y https://code.claude.com/docs/en/agent-sdk/subagents.md.
- **Leído en la doc del SDK:** el campo `model` acepta alias (`sonnet`, `opus`, `haiku`, `inherit`) o un ID completo.
- **[No verificado] en la doc oficial**, citado en los issues de GitHub anthropics/claude-code #68392 y #61328:
  - el parámetro `model` por invocación tiene prioridad sobre el modelo de la sesión;
  - `CLAUDE_CODE_SUBAGENT_MODEL` pisa tanto ese parámetro como el frontmatter;
  - en 2.1.177, `CLAUDE_CODE_SUBAGENT_MODEL=inherit` rompía la elección por invocación.

**Copilot CLI: Rubber Duck.** Fuentes: https://github.blog/changelog/2026-06-02-copilot-cli-improved-ui-rubber-duck-prompt-scheduling-and-voice-input y https://github.blog/ai-and-ml/github-copilot/github-copilot-cli-combines-model-families-for-a-second-opinion/. Leído en anuncios oficiales.
- Es un agente crítico incorporado; la CLI decide cuándo usarlo y también se invoca con `/rubber-duck`.
- Usa un modelo de otra familia y corre por la herramienta de subagentes.
- **[No verificado]:** cómo activarlo o configurarlo desde archivos, y su disponibilidad en VS Code.

**Copilot: modelo por subagente.** [No verificado].

**Referencia, fuera del alcance (otros agentes con segunda opinión o modelo por rol):**
- Cursor, plugin oficial Advisor: https://github.com/cursor/plugins/pull/314
- Amp, herramienta `oracle`: https://ampcode.com/docs/tools
- OpenHands, `ask_oracle`: https://docs.openhands.dev/sdk/guides/agent-ask-oracle.md
- Aider, modo architect: https://aider.chat/docs/usage/modes.html
- Cline, Plan/Act con modelos distintos: https://docs.cline.bot/core-workflows/plan-and-act
- OpenCode, modelo por agente: https://opencode.ai/docs/agents.md
- Codex, subagentes con modelo: https://developers.openai.com/codex/concepts/subagents

---

## 7. Fuera de alcance

- Adaptadores propios para Cursor, Codex, Antigravity/Gemini y Devin (D-04): en este paquete resuelven todo como `exo` o `human`.
- Segunda opinión con otra familia de modelos (3.5).
- Que el runtime de exo llame a modelos o APIs de IA.
- Hooks de agente (D-31).
- Cambiar los defaults de 3.5 sin los datos de F13.

---

## 8. Definición de terminado del paquete

1. F9 a F13 terminadas, con sus criterios en verde, la CI verde en los tres sistemas y `PROGRESO.md` al día.
2. Versión de salida según la sección 0 (1.x antes del tag, o 2.0.0), con `CHANGELOG.md` actualizado.
3. Docs de usuario en inglés actualizados:
   - tiers;
   - capacidades y pregunta única;
   - modelos;
   - segunda opinión;
   - troubleshooting: advisor no disponible, caída al modelo de la sesión, tope alcanzado.
4. Threat model actualizado con dos superficies nuevas:
   - el perfil por máquina;
   - el contenido que viaja en el briefing de la segunda opinión, protegido por `prompt-hygiene`.
