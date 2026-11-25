# ADR-0011 — Inglés para lo que va a los proyectos y para el CLI

- **Estado:** Aceptada
- **Fecha:** 2026-11-13
- **Decisión:** D-10

## Contexto

El default de D-10 mezclaba idiomas: chat en el idioma de la persona, artefactos SDD en inglés y skills en español con disparadores bilingües. Hasta F3, el motor quedó casi todo en español:
- el contenido que se instala en los proyectos (reglas de `AGENTS.md`, skills, subagentes);
- las plantillas SDD;
- los mensajes del CLI.

El dueño prefiere que «cuanto más esté en inglés, mejor», sin contenido bilingüe ni en español.

## Decisión

- **En inglés, y solo en inglés:**
  - Todo lo que el motor instala o genera en un proyecto: reglas de `AGENTS.md`, skills (cuerpo y `description`, con disparadores solo en inglés), subagentes, plantillas y artefactos SDD, registro de skills y contratos compartidos.
  - Los mensajes del CLI `exo` (salida, errores, ayuda) y las descripciones de las tools del registro, que también ven los agentes por MCP.
- **Sigue en español:** la documentación de desarrollo de este repo (el plan y los ADR) y los comentarios y docstrings del código.
- **El agente** responde en el idioma en que le habla la persona: eso no lo fija el motor. El campo `project.chat_language` de la config queda como preferencia opcional.

## Alternativas

- **Default de D-10 (mixto):** descartado por el dueño.
- **También los docs del repo en inglés:** el dueño eligió no hacerlo por ahora. Se puede revisar más adelante.

## Consecuencias

- **Antes de F4:** una rama de refactor pasa al inglés el contenido de `content/`, las plantillas de `src/exo/sdd/templates/`, los mensajes del CLI y las descripciones de las tools. Se regeneran los goldens y se ajustan los tests que verifican textos.
- **El contenido nuevo** de F4 en adelante se escribe directamente en inglés. Donde el plan pide disparadores «en español e inglés» (`AGENTS.md`, F4, `02-ARQUITECTURA.md` §2.6), se lee «en inglés».
- **Validación:** `exo validate` deja de exigir disparadores bilingües, si los exigía.
