# ADR-0007 — Skills por proyecto y copias según los agentes destino

- **Estado:** Aceptada
- **Fecha:** 2026-10-30
- **Decisiones:** D-05 y D-06 (`docs/plan/04-DECISIONES.md`)

## Contexto

Cada agente busca las skills en carpetas distintas (`docs/agent-matrix.md`). Claude Code solo lee `.claude/skills/`. Copilot lee `.github/skills/`, `.agents/skills/` y `.claude/skills/`, y si una skill aparece en más de una, gana la primera que encuentra. Cursor, Codex, Gemini y Devin leen `.agents/skills/`. Los symlinks son frágiles en Windows.

## Decisión

- **D-05 — Por proyecto:** las skills se copian dentro del repo del proyecto y se versionan con él. Todo el equipo usa la misma versión, el lock registra qué versión del motor las generó y sus hashes, y la CI puede validarlas. La instalación por usuario (`--scope user`) queda fuera de la v1.
- **D-06 — Copias gestionadas, solo las necesarias:**
  - Si los agentes destino son solo Claude Code y/o Copilot, va **una sola copia en `.claude/skills/`**, que leen los dos.
  - Si hay algún otro agente (detectado o elegido), se suma **`.agents/skills/`**. Las copias son idénticas, así que la sombra de Copilot no cambia nada.
  - Son copias byte a byte gestionadas por el lock, nunca symlinks. Si alguien edita una a mano, `exo sync` lo informa como conflicto y no la pisa sin `--force`.

## Alternativas

- **Instalación global por usuario.** Cada persona tendría una versión distinta y la CI no podría validarla.
- **Siempre `.agents/skills/` más un espejo para Claude Code.** Duplica sin necesidad en el caso más común del equipo.
- **Symlinks.** Requieren privilegios en Windows y algunos agentes no los siguen.

## Consecuencias

- El adaptador genérico ya no escribe `.agents/skills/` siempre: depende de los agentes destino. El bloque de reglas en `AGENTS.md` sí va siempre.
- Agregar un agente nuevo puede sumar `.agents/skills/` (`exo add-agent`), y quitar el último que la necesitaba la borra (`exo remove-agent`), en ambos casos con snapshot previo.
- `CLAUDE.md` solo se toca si hace falta: si el proyecto no lo tiene y Claude Code es ≥ 2.1.281 con el plugin de `AGENTS.md` activo, no se crea; si ya existe, se le agrega el bloque con `@AGENTS.md`. Se define en detalle en F2.
