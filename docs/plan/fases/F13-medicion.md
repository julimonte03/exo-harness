# F13 — Medición y ajuste

> Fase del paquete de capacidades y tiers (`docs/plan/paquete-capacidades.md`, sección 5). Decisiones: D-53 a D-55 → ADR-0020 (defaults revisables). Rama: `feat/F13-medicion`.
>
> Cada fase va en su propia rama, arranca en plan mode, tiene los tests primero y se cierra con cada criterio corrido con su comando exacto y anotado en `PROGRESO.md`. La cobertura de `src/exo` sigue en ≥ 85 % y la CI tiene que estar verde en los tres sistemas operativos. La rama llega a `main` por un PR que abre y mergea el dueño (D-51).
>
> Los números de sección que cita este archivo ("3.1", "3.5", "sección 0", "sección 6") son los del paquete.

## Objetivo

Tener datos para decidir si la segunda opinión y los modelos por tier bajan el retrabajo y cuánto cuestan, y ajustar los defaults con un ADR.

## Depende de

F12.

## Tareas, en orden

1. **Rondas de verify.** Si todavía no se registran, `sdd-verify` anota en el AI Usage Record cada ronda con su veredicto. Revisá primero lo que ya existe.
2. **`exo report [--json] [--since <fecha>]`.** Recorre los cambios activos y archivados, y reporta por tier:
   - cantidad de cambios;
   - rondas de verify hasta `ready` (promedio y máximo);
   - consultas por punto y por proveedor;
   - veces que se llegó al tope;
   - resultados de `judgment-day`;
   - modelos por rol.

   Tiene que ser determinista.
3. **Evals `agent_e2e`**, con presupuesto acotado: cambios Tier 2 y Tier 3 sobre los fixtures, con y sin segunda opinión (por config). La cantidad de corridas se define en plan mode según el costo.
4. **Regla de decisión, escrita antes de correr** (como en F3). Por ejemplo: la segunda opinión queda activada por defecto si baja las rondas de verify y los hallazgos de los jueces sin subir el costo por encima de un límite que se fija antes.
5. **Reporte** en `docs/evals/second-opinion-<fecha>.md` y **ADR** que confirme o ajuste los defaults de 3.5 y D-54.

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Reporte determinista | `exo report --json` dos veces sobre el mismo fixture da salidas idénticas |
| 2 | Evals | `docs/evals/second-opinion-<fecha>.md` con la tabla de resultados y la regla de decisión escrita antes |
| 3 | Decisión | ADR con los defaults confirmados o ajustados, y `04-DECISIONES.md` actualizado |

## Referencias

Paquete (`docs/plan/paquete-capacidades.md`): §3.5 (defaults revisables), §7 (fuera de alcance) y §8 (definición de terminado del paquete).
