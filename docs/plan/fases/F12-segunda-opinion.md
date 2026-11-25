# F12 — Puntos de decisión y segunda opinión

> Fase del paquete de capacidades y tiers (`docs/plan/paquete-capacidades.md`, sección 5). Decisiones: D-55 → ADR-0020. Rama: `feat/F12-segunda-opinion`.
>
> Cada fase va en su propia rama, arranca en plan mode, tiene los tests primero y se cierra con cada criterio corrido con su comando exacto y anotado en `PROGRESO.md`. La cobertura de `src/exo` sigue en ≥ 85 % y la CI tiene que estar verde en los tres sistemas operativos. La rama llega a `main` por un PR que abre y mergea el dueño (D-51).
>
> Los números de sección que cita este archivo ("3.1", "3.5", "sección 0", "sección 6") son los del paquete.

## Objetivo

En los Tiers 2 y 3, el agente se detiene en los tres puntos, consulta por el camino que corresponde, respeta el tope y deja el registro. En el Tier 3, deja también lo aconsejado por escrito.

## Depende de

F11.

## Tareas, en orden

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

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Contenido válido | `exo validate` y el test de consistencia del mapa fase → skills, en verde, con el contrato y el subagente nuevos |
| 2 | Tope con reserva | Tests de `exo advice budget/record`. En Tier 2 con tope 3: `approach` y `done` reservados, una `stuck` permitida, la segunda rechazada, y una consulta a la persona siempre aceptada |
| 3 | Check | Un Tier 3 sin el archivo de `done` da rojo y completo da verde. Un Tier 2 con registros `native` da verde |
| 4 | Tier 3 real | Con Claude Code, un cambio Tier 3 deja dos archivos en `advice/` escritos a partir de `exo-advisor` con el modelo `deep`, y `exo check` en verde |
| 5 | Tier 2 real | Con el advisor nativo aceptado, queda registrado como `native`. Si no está disponible, cae a `exo-advisor` y lo registra |
| 6 | Sin hooks | Ningún adaptador escribe hooks de agente para esto (D-31) |

## Puntos abiertos (ADR-0020)

- **Antes de empezar:** decidir si Rubber Duck cuenta como camino nativo de Copilot en el Tier 2. El default 3.5 deja afuera la segunda opinión con otra familia de modelos, pero la tarea 5 lo usa.
- Los cambios activos al actualizar a 2.0 no tienen registrado el punto `approach`. Con el criterio de D-52 (los activos adoptan las reglas nuevas), hay que definir en el plan mode si se puede registrar tarde.

## Referencias

Paquete (`docs/plan/paquete-capacidades.md`): §3.4 (D-55), §3.5 y §6.
