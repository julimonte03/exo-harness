# F11 — Modelo por tier y por rol

> Fase del paquete de capacidades y tiers (`docs/plan/paquete-capacidades.md`, sección 5). Decisiones: D-54 → ADR-0020. Rama: `feat/F11-modelos`.
>
> Cada fase va en su propia rama, arranca en plan mode, tiene los tests primero y se cierra con cada criterio corrido con su comando exacto y anotado en `PROGRESO.md`. La cobertura de `src/exo` sigue en ≥ 85 % y la CI tiene que estar verde en los tres sistemas operativos. La rama llega a `main` por un PR que abre y mergea el dueño (D-51).
>
> Los números de sección que cita este archivo ("3.1", "3.5", "sección 0", "sección 6") son los del paquete.

## Objetivo

Que cada fase corra con el modelo que pide su tier, con la política en el repo y los modelos concretos en la máquina de cada persona.

## Depende de

F10 (perfil y verificación de `subagent_model`).

## Tareas, en orden

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

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Resolución | Golden tests por tier × rol × agente simulado |
| 2 | Política sin modelos concretos | `exo validate` (o la carga de la config) falla si `.exo/config.json` trae un nombre de modelo en lugar de un nivel |
| 3 | Migración de config | Una config sin `models` recibe los defaults; correrla dos veces no cambia nada |
| 4 | Degradación | Con un agente simulado sin `subagent_model`: modelo de la sesión, aviso y `mechanism: session` en el registro |
| 5 | Agente real | Con Claude Code, un cambio Tier 3 corre design, verify y los jueces con el modelo mapeado a `deep`, y apply con el de `balanced`. Evidencia: AI Usage Record y transcript de los subagentes |

## Referencias

Paquete (`docs/plan/paquete-capacidades.md`): §3.3 (D-54), §4 y §6.
