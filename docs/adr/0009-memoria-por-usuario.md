# ADR-0009 — Memoria por usuario: sin guard, sin perfiles, sin Qdrant y sin hooks

- **Estado:** Aceptada
- **Fecha:** 2026-11-13
- **Decisiones:** D-12 (parcial), D-20, D-24 y D-25

## Contexto

El plan de F3 proponía cuatro cosas:
- un guard S1 con perfiles de organización (`legacy-profile`) que rechaza secretos y PII al guardar y los redacta al exportar;
- un backend Qdrant en servidor para experimentar memoria de equipo;
- hooks de sesión en Claude Code y Copilot;
- descarga de modelos de embeddings.

Al planificar la fase aparecieron dos datos:

- **El dueño definió el uso:** la memoria es **por máquina de usuario**, sin auth ni perfiles, para que cada persona la use con el agente que prefiera.
- **La política de la organización bloquea los hooks de proyecto en Claude Code.** La config administrada de esta máquina (`~/.claude/remote-settings.json`) tiene `"allowManagedHooksOnly": true`. Según https://code.claude.com/docs/en/hooks (consultada el 2026-11-13), eso bloquea los hooks de usuario, de proyecto, locales y de plugins.
- **Además, los contratos de salida difieren:**
  - Claude Code inyecta el stdout de `SessionStart` como texto plano.
  - Copilot inyecta solo un JSON con `additionalContext` (https://docs.github.com/en/copilot/reference/hooks-reference, misma fecha).
  - En ninguno de los dos `PreCompact` ni `SessionEnd` pueden pedirle algo al agente.

## Decisión

- **Memoria por usuario:**
  - Una base SQLite en `<datos de usuario>/exo-harness/memory.db` (ADR-0001), con override `EXO_MEMORY_DB`.
  - Sin auth y sin perfiles.
  - Cualquier agente la usa por el CLI (`exo mem …`, ADR-0005). El servidor MCP la expone solo si está habilitado.
- **Sin guard S1 en la memoria:** no rechaza ni redacta nada.
  - `exo mem export` exporta el contenido tal cual.
  - La regla de `AGENTS.md` («nunca guardes secretos ni datos personales») queda como pauta para el agente.
  - `src/exo/core/secrets.py` no cambia: lo usa `exo validate` y lo retoma el `pre-commit` de F5.
- **Solo sqlite-vec para vectores** (extra `[vector]`): es la opción más liviana, un archivo y sin procesos extra.
  - Se mantiene la interfaz de backends para sumar otro después.
  - Qdrant sale de F3, porque la memoria de equipo no entra en la v1 (D-20).
- **Sin hooks de sesión:** la sección «Memoria» de `AGENTS.base.md` y la skill `memory-protocol` le dicen al agente que corra `exo mem context` al empezar y que cierre la sesión con un resumen.
- **Modelos de embeddings:** se bajan de Hugging Face **solo** con un comando explícito, `exo mem model pull`. Corren locales y no mandan datos afuera.

## Alternativas

- **Guard S1 con perfil `legacy-profile`** (default del plan): descartado por el dueño. La memoria es personal.
- **Guard solo de secretos, sin PII:** descartado por el dueño, que eligió no tener guard.
- **Otras bases vectoriales sin servidor**, comparadas por peso el 2026-11-13:

  | Opción | Peso | Motivo para descartarla |
  |---|---|---|
  | Qdrant en modo local | Suma qdrant-client y sus dependencias | Toma un lock de proceso único sobre la carpeta |
  | LanceDB | ~60 MB, con pyarrow | Más pesada |
  | Chroma | Pesada | Más pesada |
  | DuckDB VSS | Liviana | Baja su extensión al correr |

  sqlite-vec es la más liviana (~150 KB) y vive en el mismo archivo SQLite.
- **Hooks más regla, con aviso de `exo doctor`:** descartado por el dueño. Con la política actual, los hooks no corren en Claude Code.

## Consecuencias

- **F3:**
  - El criterio 1 (guard sin fugas) sale del alcance.
  - El experimento (criterio 5) compara `lexical` contra `hybrid-sqlite` con dos modelos multilingües, sin Qdrant.
  - Las tareas 2 (guard) y 7 (Qdrant) y la parte de hooks de la tarea 9 no se hacen.
- **Riesgo aceptado:** nada en el código impide que un agente guarde un secreto en la memoria. Un export lo comparte sin redactar.
- **La configuración de la memoria vive en la base, no en el proyecto.** Como hay una base por usuario compartida por todos sus proyectos, el proveedor, el modelo, la dimensión y el permiso remoto de los embeddings se guardan en la `meta` de la base. Se cambian con `exo mem reindex --provider … [--allow-remote]`. Si dependieran del `config.json` de cada proyecto, dos proyectos con modelos distintos se pisarían el índice. La sección `memory` de `.exo/config.json` queda sin efecto.
- **F5:** el escáner de secretos para el `pre-commit` parte de `core/secrets.py`, como estaba previsto.
- **D-12:** queda abierta para el resto de su alcance (estilo, matriz DPA y herramientas corporativas en F5).
