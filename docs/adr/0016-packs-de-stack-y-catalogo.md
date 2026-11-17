# ADR-0016 — Packs de stack y resto del catálogo: gates condicionales, canvas SPDD, jueces y evals

- **Estado:** Aceptada
- **Fecha:** 2026-11-17
- **Decisiones:** D-12 (resto), D-18 y D-38 a D-44 (`docs/plan/04-DECISIONES.md`)

## Contexto

F7 escribe las 65 skills del reporte que faltan, por pack y prioridad (`docs/plan/fases/F7-packs.md`). El reporte no trae cuerpos: cada skill se escribe de cero desde su rol (capítulo 03) y su lugar en el mapa fase → skills.

Cuatro piezas no entran en lo que ya existe:
- **Gates sin tier:** el gate de accesibilidad (§6.7) y el gate humano del Canvas SPDD (§6.8) dependen de que el change tenga UI o canvas, no de su tier. `exo check` solo revisa los gates que exige el tier.
- **Canvas:** el artefacto `canvas.md` no tiene plantilla, ni tipo en speclint, ni lugar en el contrato de estado.
- **Jueces:** el contrato común solo contempla JCR y JSEC, en design, tasks y verify. Los jueces nuevos revisan también propose y spec.
- **Evaluación de skills:** no hay forma de medir si una skill se activa cuando corresponde.

## Decisión

### Packs

| Pack | Prioridad | Contenido |
|---|---|---|
| `sdd` | 1 | Overlay SPDD: `reasons-canvas-author`, `prompt-spec-review`, `prompt-code-sync`, `context-anchoring`, `sdd-onboard`, con el contrato `spdd-common.md` |
| `quality` | 1 | Jueces `judge-product`, `judge-business`, `judge-frontend`, `judge-team`; `excellence-committee` y `review-4r` |
| `product` (nuevo) | 1 y 4 | `product-discovery`; después `functional-flow-designer`, `work-item-creator`, `refinement-assistant`, `roadmap-generator` |
| `frontend` (nuevo) | 1 y 2 | `accessibility-audit`; después el stack TypeScript/React |
| `core` | 1 y 4 | `parallel-dispatch`, `chained-pr`; después `cognitive-doc-design`, `comment-writer`, `issue-creation`, `skill-creator`, `skill-improver`, `software-solution` |
| `java`, `python` (nuevos) | 2 | Los stacks del equipo (D-38) |
| `ops` (nuevo) | 3 | Operación y SRE |
| `security` | 3 | `secure-diagram-sanitizer` |
| `design` | 4 | Diagramas y estilo ejecutivo |
| `agentic` (nuevo) | 4 | Revisión de sistemas agénticos |

- **Los packs de stack se sugieren por la detección de stack,** también en monorepos (workspaces de `package.json` y manifiestos en subcarpetas). `product`, `design` y `agentic` nunca se sugieren: no hay señal en el repo.
- **Una skill de un pack opcional** que nombra el mapa tiene su fila de degradación. Una skill de `core` o `sdd` no la tiene: si falta, la instalación está incompleta.

### Nombres (D-39, D-40, D-42)

- Todo nombre instalado va en inglés: `comite-excelencia` pasa a `excellence-committee`.
- Las skills de Jira se generalizan: `work-item-creator` y `refinement-assistant`, con el ID según `tickets.pattern` (ADR-0012).
- La skill `review` de F5 pasa a `pre-commit-review`, porque chocaba con el `/review` integrado de Claude Code.

### Gates condicionales (D-43)

- **`exo check` revisa todo gate presente** en `gates/`, aunque el tier no lo exija: sin veredicto legible es un error; `ESCALATED` pide la aprobación del `tech_lead`, como los requeridos.
- **`accessibility_review`:** lo escribe `accessibility-audit` en verify cuando el change toca UI (html, tsx, jsx, vue, svelte, css, scss). Un hallazgo Critical (impide completar la tarea) o High bloquea `ready`, salvo que se descarte con su motivo. Sin el pack `frontend` no se escribe: el criterio inline va a Issues Found, y `harness-review` ya cubre accesibilidad en `code_review`.
- **`prompt_spec_review`:** lo escribe `prompt-spec-review`. Con `canvas.md` en el change, `exo check` lo exige.
- Un proyecto puede sumar cualquiera de los dos a `governance.gates` para exigirlo siempre en un tier.

### Canvas SPDD

- `canvas.md` es un artefacto opcional del change, después de `design.md`, con las siete dimensiones REASONS: Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards. speclint exige las siete secciones.
- **Cuándo aplica** (`spdd-common.md`): Tier 3 o 4 con lógica de dominio que conviene fijar antes del código, o cuando la persona lo pide.
- **Orden de los cambios:** una corrección de lógica cambia primero el canvas y después el código; un refactor, primero el código y después el canvas.

### Jueces

- Prefijos nuevos de followups: `JPRD` (producto), `JBIZ` (negocio), `JFE` (frontend) y `JTEAM` (equipo).
- `sdd-judge` corre también en propose y spec.
- Los jueces siguen sin gate propio. `excellence-committee` reúne a los seis con un moderador, a pedido; `review-4r` es una revisión de cinco lentes, también a pedido.

### Marca e integraciones (D-12)

- **Estilo:** neutro por defecto. Un `.exo/brand.json` opcional lo reemplaza; su forma está en `executive-style.md` (pack `design`).
- **Herramientas corporativas:** SonarQube, Fortify y Kibana son pasos opcionales. Sin ellas, las skills usan herramientas abiertas.

### Evals de skills (D-41)

- Cada skill de prioridad 1 y 2 tiene `tests/skill_evals/<skill>/evals.json` con tres casos:
  - `trigger`: el pedido debería cargarla;
  - `no-trigger`: un pedido parecido no debería cargarla;
  - `output`: un resultado que se verifica.
- La suite normal valida su esquema.
- `tests/test_skill_evals.py` (`agent_e2e`, fuera de la suite normal) los corre con Claude Code real:
  - sobre una copia de un fixture con `exo init`;
  - con los datos aislados;
  - detecta el uso de la skill en la salida `stream-json`.

## Consecuencias

- **El mapa fase → skills cambia junto con cada pack:** las filas de degradación de `software-solution`, `parallel-dispatch` y `context-anchoring` salen cuando esas skills existen, y `sdd` suma `python`, `ops` y `agentic` como opcionales.
- **Un gate presente que no exige el tier ahora puede dar error** en `exo check`, si no tiene un veredicto legible.
- **Los evals de "no dispara" dependen de cómo el agente elige skills por su `description`.** Si uno falla, se ajusta la description.
- **El costo de los evals** son unas 114 corridas cortas de Claude Code. Por eso están fuera de la suite normal.
