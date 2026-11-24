# ADR-0005 — El CLI es la interfaz del agente con el motor; el MCP es opcional

- **Estado:** Aceptada
- **Fecha:** 2026-10-30
- **Decisión:** D-23 (`docs/plan/04-DECISIONES.md`)

## Contexto

El plan supone que los agentes usan las funciones del motor a través de un servidor MCP (`exo mcp`), con cuatro grupos de tools: skills, observabilidad SDD, memoria y discovery (`docs/plan/02-ARQUITECTURA.md` §2.10).

En la prueba de F0 (`docs/spikes/agent-probe.md`), Claude Code respondió `MCP server blocked by enterprise policy`: la organización solo permite servidores MCP de una lista. Además, la verificación de agentes (`docs/agent-matrix.md`) mostró que la config MCP cambia en cada agente. Codex y Gemini solo la cargan en carpetas confiables, y el cloud agent de Copilot la toma de los settings del repo, no de un archivo.

## Decisión

- **Cada capacidad es una función del runtime expuesta como subcomando del CLI** con salida `--json`, que es el contrato estable. Por ejemplo, `exo mem save`, `exo mem search` y `exo change status`. Las skills y las reglas le indican al agente que use esos comandos con su terminal, igual que `git` o `pytest`.
- **Las skills nunca dependen del servidor MCP.**
- **El servidor `exo mcp` es un adaptador fino y opcional** sobre las mismas funciones, con los mismos nombres y la misma validación de entradas (S2). Los adaptadores solo escriben la config MCP si el proyecto lo habilita en `.exo/config.json` con `"mcp": {"enabled": true}`; **por defecto está apagado**.
- La validación S2 vive en las funciones compartidas, así que protege igual al CLI y al MCP.

## Alternativas

- **Solo pedir que la organización habilite `exo` (D-23 b).** Depende de un tercero y no resuelve los otros agentes con MCP condicionado.
- **MCP por defecto con el CLI como respaldo (D-23 c).** Obliga a cada skill a describir dos caminos y a detectar cuál está disponible. Es más complejo y más frágil.

## Consecuencias

- **F1:**
  - Las tools de los grupos Skills y Observabilidad tienen su subcomando, `exo skills {list,info,diff}` y `exo change {list,status,followups,ai-usage}` (en singular, para que F4 sume `exo change new`). Las tools se definen una sola vez en `src/exo/tools/registry.py`, que consumen el CLI y `src/exo/mcp/server.py`.
  - El servidor MCP se construye igual, porque es barato y el criterio 5 de F1 lo pide, pero es opcional.
  - El esquema de config suma `mcp.enabled` (`false` por defecto).
- **F2:**
  - Los adaptadores no generan config MCP salvo que esté habilitado.
  - En Claude Code, el instalador agrega el permiso para ejecutar `exo` (por ejemplo `Bash(exo:*)` en `.claude/settings.json`), y lo equivalente en los demás agentes donde exista.
  - `exo doctor` verifica que `exo` esté en el `PATH`.
  - **A verificar:** que la política de la organización no bloquee también los hooks ni esas reglas de permiso.
  - **Resultado de F2:**
    - Claude Code recibe `Bash(exo:*)` y `PowerShell(exo:*)`. Las reglas aplican recién cuando el workspace es confiable; `exo doctor` lo avisa (`docs/checklists/F2-agentes.md`).
    - **Actualizado en F8 (threat model, TM-21):** el permiso ya no es `exo:*`, sino un ítem por subcomando de los que las skills corren solas (`AGENT_COMMANDS` en `src/exo/adapters/claude_code.py`). Con `exo:*`, un agente con prompt injection podía reescribir `review.publish_command` con `exo init --publish-command` y ejecutarlo con `exo gate publish` sin preguntar. Lo que cambia la instalación, borra o exporta memoria, o ejecuta un comando configurado lo aprueba la persona. `exo sync` reemplaza el permiso viejo en los proyectos instalados.
    - En Copilot queda diferido: no se verificó una regla de permiso a nivel de proyecto que Copilot lea, y la licencia todavía no está confirmada. Hasta entonces, Copilot puede pedir confirmación para ejecutar `exo`. Se revisa con el checklist manual de F2.
- **F3:**
  - La memoria se usa con `exo mem …`. La skill `memory-protocol` y `AGENTS.base.md` dicen cuándo guardar y cuándo buscar.
  - El contexto al iniciar sesión se inyecta con un hook que corre `exo mem context`.
  - **Resultado de la planificación de F3 (ADR-0009):** la política de la organización sí bloquea los hooks de proyecto de Claude Code (`allowManagedHooksOnly: true`). No se generan hooks: la regla de `AGENTS.base.md` le dice al agente que corra `exo mem context` al empezar.
- **F6:** el bucle de discovery usa `exo discover next|claim|done`. El estado sigue en el motor (`state.json`), así que sobrevive a la compactación de contexto y a cortes.
- **Costo aceptado:** sin MCP, las herramientas no aparecen en la lista del agente, y puede usar la memoria con menos iniciativa propia. Se compensa con reglas explícitas y se mide en los evals de F8.
- La salida `--json` de cada comando lleva un campo de versión de esquema, para poder evolucionarla sin romper skills.
