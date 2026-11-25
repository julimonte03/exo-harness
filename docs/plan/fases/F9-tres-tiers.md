# F9 — Tres tiers

> Fase del paquete de capacidades y tiers (`docs/plan/paquete-capacidades.md`, sección 5). Decisiones: D-52 → ADR-0019. Rama: `feat/F9-tres-tiers`.
>
> Cada fase va en su propia rama, arranca en plan mode, tiene los tests primero y se cierra con cada criterio corrido con su comando exacto y anotado en `PROGRESO.md`. La cobertura de `src/exo` sigue en ≥ 85 % y la CI tiene que estar verde en los tres sistemas operativos. La rama llega a `main` por un PR que abre y mergea el dueño (D-51).
>
> Los números de sección que cita este archivo ("3.1", "3.5", "sección 0", "sección 6") son los del paquete.

## Objetivo

Pasar de 4 tiers a 3 sin perder ningún control, con una migración para los proyectos que ya tienen cambios en Tier 4.

## Depende de

El paso 0 cerrado.

## Tareas, en orden

1. **Fitness** (`sdd/fitness.py` o donde viva):
   - remapear las reglas según 3.1;
   - la evidencia faltante o ilegible da Tier 3;
   - el mapeo de ceremonias queda `minimal`, `light`, `full`;
   - `compare_tiers` conserva su semántica.
2. **`classification-rules.md`** de `risk-tiering`, actualizado, con el test de paridad en verde.
3. **Esquema de `fitness-assessment.json`:**
   - el tier pasa a 1–3;
   - se suma el campo opcional `migrated_from`;
   - se sube la versión del esquema.
4. **`exo check`:**
   - artefactos por tier según 3.1;
   - en el Tier 3, `judgment-day` registrado siempre;
   - en el Tier 3, los gates de la unión de los Tiers 3 y 4 de la 1.0, con `secure_coding_check` incluido (D-52, 2026-11-25);
   - un archivado cuyo `fitness-assessment.json` es del esquema viejo se valida solo por estructura (record, artefactos y speclint), sin gates ni `judgment-day` de las reglas nuevas (D-52, 2026-11-25).
5. **Contenido.** Buscá "Tier 4", "Tier ≥ 3", "tier 4" y "piso duro" en `content/` y actualizá lo que encuentres. Como mínimo:
   - `risk-tiering`, `sdd-orchestrator` y `phase-skill-map.md` (jueces y `judgment-day` en Tier 3);
   - `sdd-verify` (el "Judgment Day Handoff" pasa a Tier 3);
   - `judgment-day`;
   - los contratos `sdd-phase-common.md` y `agent-capabilities.md`;
   - en la adopción, los tests de caracterización para Tier 3.
6. **Migración:**
   - un paso de migración, dentro del mecanismo que ya use `exo update`, que pase de 4 a 3 los cambios activos y registre `migrated_from: 4`;
   - los cambios activos en Tier 3 pasan también al esquema nuevo del assessment y adoptan las reglas nuevas (D-52, 2026-11-25);
   - la migración de la config une las listas `"3"` y `"4"` de `governance.gates`, conservando el orden y lo personalizado, y borra la clave `"4"`. Es obligatoria: sin ella, la clave `"4"` queda inválida y corta `sync`, `update` y `check` (D-52, 2026-11-25);
   - lectura tolerante en la observabilidad y en `exo check`, para que un archivado con tier 4 se lea como 3 sin reescribirlo.
7. **Docs de usuario en inglés** (README, QUICK-START y guías), CHANGELOG con entrada **BREAKING** y la versión según la sección 0.
8. **Tests:** tabla de reglas, fixtures de migración y el escenario `agent_e2e` de Tier 3 actualizado.

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Las reglas críticas dan Tier 3 | `exo fitness classify --evidence-json '{"security_data_sensitivity":3, …}'` devuelve Tier 3 con la regla FM-01 |
| 2 | Tabla completa y paridad | `pytest tests/test_fitness.py` cubre FM-01 a FM-30 y la evidencia ilegible (Tier 3); la paridad con el Markdown, en verde |
| 3 | Check estricto en Tier 3 | `exo check` falla en un Tier 3 sin `design.md`, sin `tasks.md`, sin `test-spec.md` o sin el registro de `judgment-day`, y pasa cuando está completo |
| 4 | Migración | Sobre un fixture con un cambio activo en Tier 4 y otro archivado en Tier 4: después de migrar, el activo queda en Tier 3 con `migrated_from: 4`, el archivado queda idéntico byte a byte, y `exo check` y `exo change status` funcionan con los dos |
| 5 | Sin restos | `grep -rn "Tier 4" content/ src/` solo devuelve el código de migración y de lectura tolerante |
| 6 | Agente real | Con Claude Code, un cambio con `security_data_sensitivity: 3` queda en Tier 3 y corre `judgment-day` |

## Referencias

Paquete (`docs/plan/paquete-capacidades.md`): §3.1 (D-52).
