# ADR-0020 — Capacidades del agente, modelo por tier y segunda opinión

- **Estado:** Aceptada. Los defaults de la sección «Defaults revisables» se confirman o ajustan en F13.
- **Fecha:** 2026-11-25. El dueño la decidió el 2026-11-22.
- **Decisiones:** D-53, D-54 y D-55 (`docs/plan/04-DECISIONES.md`); paquete `docs/plan/paquete-capacidades.md`, §3.2 a §3.5

## Contexto

- **Funcionalidades propias de cada agente.** Claude Code y Copilot traen subagentes, elección de modelo por subagente, un advisor o un crítico incorporado, modo de solo lectura y ejecución sin interfaz. exo resuelve varias de esas cosas a su manera.
  - Hoy las skills suponen qué hay, o lo prueban una vez (`content/packs/core/shared/agent-capabilities.md`).
  - El `capabilities()` de los adaptadores existe, pero nadie lo llama.
- **Modelo único.** Todas las fases corren con el modelo de la sesión. La selección de modelo por niveles se diseñó antes de la versión actual del plan y nunca entró.
- **Retrabajo.** En el escenario Tier 3 de F8, Claude Code pasó cuatro rondas de verify en `needs-rework` antes del arreglo de convergencia (`docs/checklists/F8-v1.md`). Una consulta temprana, en el enfoque y al terminar `apply`, podría evitar parte de ese retrabajo.
- **Restricciones que no cambian:**
  - exo no llama a modelos ni a APIs de IA (invariante 11);
  - sin hooks de agente (D-31);
  - CLI primero (ADR-0005);
  - lo instalado va en inglés (ADR-0011);
  - adaptadores propios solo para Claude Code y Copilot (ADR-0006).

## Decisión

### Catálogo de capacidades (D-53)

- **Catálogo completo desde la primera versión**, como datos dentro del paquete; no se instala en los proyectos. Cada capacidad tiene una política:
  - **`native`:** la del agente, si la trae y la persona la aceptó; si no, la de exo; si tampoco hay, la persona.
  - **`exo`:** siempre la de exo. Es el caso de todo lo que gobierna o deja prueba: gates, jueces, `judgment-day`, fitness, `exo check`, AI Usage Record, specs, memoria y enforcement. Nunca se ofrece como nativa.
  - **`complement`:** la nativa suma información, pero no reemplaza a la de exo. Por ejemplo, un revisor incorporado que aporta hallazgos al gate.
- **Datos por agente:** soporte de cada capacidad, desde qué versión, cómo se activa, cómo se comprueba, restricciones y fuente oficial con fecha (`verified_at`). Lo que no se puede confirmar queda `[No verificado]` y degrada. La verificación es el spike de F10, con el resultado en `docs/capabilities-matrix.md`.
- **Perfil por máquina:**
  - vive en la carpeta de datos del usuario (ADR-0001), nunca en el repo ni en el lock;
  - guarda el agente y su versión, la elección por capacidad (`native` o `exo`, con `chosen_by`), la versión de los datos y el mapa de modelos.
- **Pregunta única:**
  - En `exo init`, si no hay perfil para el agente, se ofrecen tres opciones: usar todas las nativas, elegir una por una o ninguna. Sin terminal, se aplica la política con `chosen_by: default`.
  - Solo se vuelve a preguntar si cambia el agente o si aparece una capacidad nativa nueva, y en ese caso solo por esa.
- **`exo capabilities --json`** informa a las skills, por capacidad, la resolución (`native`, `exo` o `human`), el motivo y cómo usarla. Las skills lo corren al empezar cada fase en lugar de suponer.

### Modelo por tier y por rol (D-54)

- **Niveles abstractos:** `fast`, `balanced` y `deep`.
  - La política por tier y por rol vive en el repo (`.exo/config.json`) y solo admite niveles.
  - El mapa de nivel a modelo concreto vive en el perfil de cada máquina, porque depende del agente y de la cuenta de cada persona.
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

- **Al delegar,** el orquestador pasa el modelo que corresponde al rol y al tier. Si el agente no permite elegir el modelo de un subagente, se usa el de la sesión, se avisa y se registra.
- **Nunca se escribe un modelo concreto en un archivo versionado.** Eso incluye los subagentes canónicos: Copilot lee los mismos `.claude/agents/` que Claude Code, y cada persona tiene su propio mapa.

### Segunda opinión (D-55)

| Punto | Cuándo | Obligatorio |
|---|---|---|
| `approach` | Una vez por cambio, antes de comprometer el enfoque. Tier 2: al empezar `apply`, antes de escribir. Tier 3: al cerrar `design` | Sí |
| `stuck` | Cuando el mismo error aparece por segunda vez, o tras dos intentos fallidos de arreglar algo | Solo si pasa |
| `done` | Al terminar `apply`, antes de `verify` | Sí |

- **Tier 1:** solo si la persona lo pide.
- **Orden de resolución:**
  - **Tier 2:** nativa (si la persona la aceptó y está disponible) → `exo-advisor` → persona.
  - **Tier 3:** `exo-advisor` → persona. Va siempre por el camino propio para que lo aconsejado quede escrito, porque el advisor nativo puede no dejar leer lo que dijo.
- **`exo-advisor`:**
  - es un subagente canónico de solo lectura que el agente corre con el modelo `deep`;
  - recibe un briefing con la pregunta, un resumen corto, las rutas a los artefactos y al diff, y lo que ya se intentó;
  - antes de armar el briefing se aplica `prompt-hygiene`;
  - responde con `Verdict` (`proceed`, `adjust` o `stop`), `Why`, `Recommendations`, `Risks` y `Confidence`.
- **Tope por tier** (`second_opinion.max_per_change`):
  - cuenta todas las consultas a modelos, pero reserva lugar para los puntos obligatorios que falten, y `stuck` solo usa lo que sobra;
  - al llegar al tope no se consultan más modelos: se registra y, si el agente sigue trabado, le pregunta a la persona;
  - las respuestas de la persona no cuentan para el tope.
- **Registro:**
  - cada consulta queda en el AI Usage Record: punto, quién la resolvió (`native`, `exo` o `human`), modelo pedido y modelo informado;
  - en el Tier 3, además, deja un archivo de consejo en el change.
- `exo check` verifica los puntos obligatorios y el tope.

### Defaults revisables (paquete, §3.5)

Se aplican desde F10 a F12 y se confirman o ajustan con un ADR posterior, con los datos de F13:

1. **Topes:** Tier 2 = 3 consultas por cambio; Tier 3 = 6.
2. **Exploración** y búsquedas de solo lectura en `fast`.
3. **Misma familia:** la segunda opinión usa un modelo más fuerte del mismo agente. Usar otra familia de modelos queda fuera del paquete.
4. **`exo init` sin terminal:** se aplica la política (nativas donde corresponde) y se registra `chosen_by: default`.
5. **Datos viejos:** `exo doctor` avisa cuando los datos de capacidades tienen más de 60 días desde `verified_at`.
6. **Cambios archivados:** no se reescriben.

### Puntos abiertos (se resuelven como D-xx en la fase que corresponde)

- **Rubber Duck en Copilot.** El default 3 deja fuera del paquete la segunda opinión con otra familia de modelos y pone a Rubber Duck como ejemplo. Pero F12 usa Rubber Duck como camino nativo de Copilot en el Tier 2. Antes de F12 hay que decidir si se acepta como nativa (es la herramienta del agente, no una elección de exo) o si en Copilot se va directo a `exo-advisor`.
- **A qué agentes pregunta `exo init`** cuando el proyecto tiene más de uno (F10).
- **Cambios activos al actualizar:** los que están en curso no tienen el punto `approach` registrado, y hay que definir si se puede registrar tarde (F12, con el criterio de D-52 de que los activos adoptan las reglas nuevas).

## Alternativas

- **Que exo llame al modelo, por API, para la segunda opinión.** Rompe la invariante 11 y el agnosticismo. Quien consulta es siempre el agente.
- **Modelos concretos en la config del repo.** Dependen del agente, del plan y de la cuenta de cada persona, y cambian seguido.
- **Hooks de agente para forzar los puntos de decisión.** D-31: la política de la organización los bloquea en Claude Code y no son portables. Los puntos van en el texto de las skills, y lo verificable va a `exo check`.
- **Advisor nativo también en el Tier 3.** Lo aconsejado podría no quedar escrito ni legible, y el Tier 3 lo exige.
- **Preguntar las capacidades en cada sesión.** Cansa y no aporta: la elección depende de la persona y de su máquina, que cambian poco.

## Consecuencias

- **Dos superficies nuevas en el threat model:** el perfil por máquina y el contenido que viaja en el briefing de la segunda opinión, protegido por `prompt-hygiene`.
- **Subcomandos nuevos:** `exo capabilities`, `exo advice` y `exo report`, más un subagente canónico nuevo, `exo-advisor`.
- **AI Usage Record:** suma `provided_by`, `models_used` y el registro de las consultas, todos opcionales para que un record v1 siga siendo válido.
- **Config:** suma `models.policy` y `second_opinion.max_per_change`, con su migración en `exo update`.
- **Costo:** las consultas `deep` y la segunda opinión cuestan más por cambio. F13 mide si bajan el retrabajo y cuánto cuestan.
- **Implementación:** F10 (catálogo y perfil), F11 (modelos), F12 (segunda opinión) y F13 (medición).
