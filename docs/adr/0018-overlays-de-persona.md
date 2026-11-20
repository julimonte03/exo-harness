# ADR-0018 — Overlays de persona

- **Estado:** Propuesta (se confirma antes del código, D-17)
- **Fecha:** 2026-11-19
- **Decisiones:** D-17 (`docs/plan/04-DECISIONES.md`)

## Contexto

Las mismas reglas y skills llegan a todas las personas del equipo, pero no todas necesitan lo mismo:
- quien programa quiere el próximo paso y los tests;
- quien lidera técnicamente, los gates escalados y los riesgos aceptados;
- quien hace QA, los escenarios y la cobertura;
- quien lleva el producto, el problema, el valor y el alcance.

El reporte de referencia proponía overlays por persona; el plan los dejó como opcionales para F8, y el dueño los sumó.

## Decisión

### Qué es un overlay

- Un contrato corto por rol, en inglés, en `content/packs/core/shared/personas/<rol>.md`. Los roles son `dev`, `tech-lead`, `qa` y `product`. Cada uno tiene a lo sumo 40 líneas.
- **Dice:**
  - qué resaltar al final de cada fase;
  - qué decisiones le corresponden a esa persona, por ejemplo la aprobación de `tech_lead` en un gate escalado (`governance.roles`);
  - qué hallazgos de qué jueces mostrarle primero;
  - el nivel de detalle de las respuestas.
- **Nunca relaja nada:**
  - una regla, un gate, un tier o una aprobación siguen igual;
  - una persona no aprueba lo que su rol de `governance.roles` no aprueba;
  - el overlay cambia qué se muestra primero y cómo, no qué se exige.

### Cómo se elige

- **Por persona, no por proyecto:** `exo persona set <rol>` guarda el rol en la carpeta de datos del usuario (`persona.json`, con su `schema`). Nunca va al repo.
- **Consultar y borrar:** `exo persona show [--json]` dice el rol activo (o ninguno), y `exo persona clear` lo borra.
- **El agente lo lee:** las reglas base (`AGENTS.base.md`) suman una línea: "si `exo persona show --json` devuelve un rol, leé `.exo/shared/personas/<rol>.md` y seguilo por encima de estas reglas, sin relajar ninguna". Sin rol, nada cambia.
- **Variables de entorno:** no deciden nada de seguridad (ADR-0006), y acá tampoco hacen falta.

## Consecuencias

- **Reglas base:** suman una línea de las 60 que permite `exo validate`.
- **Overlays:** cuatro contratos nuevos en `core`, que se instalan siempre y se leen solo si hay rol.
- **Comando nuevo:** `exo persona`. Como escribe, no es una tool del registro (ADR-0005).
- **Si un rol nuevo hace falta,** es un archivo más y su nombre en la lista de roles válidos.
