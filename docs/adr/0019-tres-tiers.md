# ADR-0019 — Tres tiers de riesgo

- **Estado:** Aceptada
- **Fecha:** 2026-11-25. El dueño la decidió el 2026-11-22 y la completó el 2026-11-25.
- **Decisiones:** D-52
- **Reemplaza en parte:** D-27 (lo que toca a los Tiers 3 y 4) y el contrato de "tiers 1–4" de la v1.0.

## Contexto

El ciclo SDD tiene cuatro tiers:
- **Clasificación:** FM-01, FM-02 y FM-03 (seguridad o datos, reversibilidad e impacto regulatorio en 3) dan Tier 4, y la evidencia faltante o ilegible (FM-00) también.
- **Ceremonias:** son tres (`minimal`, `light`, `full`, `full`) para cuatro tiers.
- **Lo que distingue al Tier 4 del 3** es solo `judgment-day` y el gate `secure_coding_check`. `classification-rules.md` lo marcaba como "piso duro" frente a "piso".

El paquete de capacidades suma una segunda opinión en los Tiers 2 y 3, y jueces más `judgment-day` siempre en el más alto. Con eso, el Tier 4 deja de aportar algo propio.

Los proyectos instalados con la 1.0 tienen:
- la clave `"4"` en `governance.gates` de `.exo/config.json`, que el instalador escribe con los defaults;
- cambios activos y archivados con `"tier": 4` en `fitness-assessment.json`.

## Decisión

### Tiers

| Tier | Nombre | Para qué | Artefactos obligatorios | Chequeo |
|---|---|---|---|---|
| 1 | Small | Cambio pequeño, sin riesgo | `proposal.md`; `spec.md` solo si cambia el comportamiento (D-27) | `verify` |
| 2 | Spec | Riesgo leve | `proposal.md`, `spec.md` y `test-spec.md` (lo escribe `sdd-spec` con `test-strategy`) | `verify` y segunda opinión en los tres puntos (D-55) |
| 3 | Full | Riesgo alto o crítico | `proposal.md`, `spec.md`, `design.md`, `tasks.md` y `test-spec.md` (lo escribe `sdd-tasks`) | `verify`, segunda opinión en los tres puntos, jueces y `judgment-day` **siempre** |

Todos los tiers exigen un `ai-usage-record.json` válido. Hay una ceremonia por tier: `minimal`, `light` y `full`.

### Fitness

| Regla | Condición | Antes | Ahora |
|---|---|---|---|
| FM-00 | Evidencia faltante o ilegible | Tier 4 | **Tier 3** |
| FM-01, FM-02, FM-03 | Seguridad o datos, reversibilidad o impacto regulatorio == 3 | Tier 4 | **Tier 3** |
| FM-10 a FM-13 | Criticidad, blast radius o footprint == 3, o ≥ 3 dimensiones ≥ 2 | Tier 3 | Tier 3 |
| FM-20 | ≥ 1 dimensión ≥ 2 | Tier 2 | Tier 2 |
| FM-30 | Todas ≤ 1 | Tier 1 | Tier 1 |

- No hay marca de "piso duro". La regla que disparó el tier queda en `fitness-assessment.json`, como hoy.
- `compare_tiers` conserva su semántica.
- Bajar de tier sigue pidiendo la confirmación literal de la persona.

### Gates del Tier 3 (2026-11-25)

- Los gates del Tier 3 son la **unión** de los del Tier 3 y el Tier 4 de la 1.0: `contract_check`, `code_review`, `security_review`, `threat_model` y `secure_coding_check`.
- Así, lo que antes era Tier 4 no pierde ningún control. Es el mismo criterio que pone `judgment-day` siempre en el Tier 3.

### Migración

- **Config:** la migración de esquema de `exo update` une las listas `"3"` y `"4"` de `governance.gates` de cada proyecto, conservando el orden y lo personalizado, y borra la clave `"4"`.
  - Sin esa migración, la clave `"4"` quedaría como valor inválido y cortaría `sync`, `update` y `check`.
- **Cambios activos:** `exo update` los pasa al esquema nuevo de `fitness-assessment.json`.
  - Un Tier 4 queda en Tier 3 con `migrated_from: 4`.
  - Un Tier 3 sigue en Tier 3 y **adopta las reglas nuevas** (2026-11-25): necesita `judgment-day` y los gates nuevos antes de archivar.
  - Se recalculan `ceremony` y `judgment_day`, en el mismo snapshot que la config y con vista previa por defecto.
- **Cambios archivados:** no se reescriben.
  - Al leerlos, un 4 se interpreta como 3 (lectura tolerante).
  - Si su assessment es del esquema viejo, `exo check` los valida solo por estructura: record, artefactos y speclint (2026-11-25). No les exige gates ni `judgment-day` con las reglas nuevas, porque ya pasaron `exo check` cuando se archivaron.

### Versión

`v1.0.0` ya tiene tag, así que el paquete sale como **2.0.0**, con una entrada BREAKING en `CHANGELOG.md` que explica la migración.

## Alternativas

- **Mantener cuatro tiers y solo sumar la segunda opinión.** Deja dos tiers que difieren en una revisión y un gate, con tres ceremonias para cuatro tiers.
- **Tier 3 sin `secure_coding_check`.** Lo que antes era Tier 4 (FM-01 a FM-03) pierde un control.
- **`secure_coding_check` solo cuando el tier lo disparó FM-01, FM-02 o FM-03.** Vuelve a meter la distinción de "piso duro" que esta decisión saca.
- **Cambios activos en Tier 3 con las reglas viejas hasta archivar.** Obliga a `exo check` a tener dos juegos de reglas mientras quede algún cambio viejo abierto.
- **Archivados con las reglas nuevas.** Un PR que toque un archivado viejo quedaría en rojo sin que nada haya cambiado en él.

## Consecuencias

- **Más ceremonia en lo que hoy es Tier 3** (FM-10 a FM-13): `judgment-day` siempre y un gate más. F13 mide lo que cuesta.
- **Cambia la salida de `exo fitness` y `exo check`:** el tier va de 1 a 3, `judgment_day` es verdadero en el Tier 3 y los mensajes dicen otra cosa. Por eso la versión mayor.
- **El contenido instalado cambia en unos 73 archivos** (`risk-tiering`, el orquestador, `phase-skill-map.md`, `judgment-day`, los jueces, los contratos y `AGENTS.base.md`). Llega a los proyectos con `exo update`.
- **El escenario `agent_e2e` del Tier 3** tiene que retomar la corrida con la aprobación de la persona en `judgment-day`, porque la skill nunca aprueba por ella en una corrida desatendida.
- **La implementación es F9.**
