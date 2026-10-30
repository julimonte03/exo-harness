# Reglas de clasificación de riesgo (fitness)

Fuente de verdad compartida entre la skill `risk-tiering` y el runtime. `exo fitness classify` implementa exactamente esta tabla: un test de paridad del motor compara regla, condición y tier, y falla si divergen.

## Dimensiones

Cada dimensión vale un entero de 0 a 3.

| Dimensión | Qué mide |
|---|---|
| `blast_radius` | Cuántos usuarios, servicios o flujos se ven afectados si el cambio falla |
| `component_criticality` | Qué tan crítico es el componente que se toca |
| `security_data_sensitivity` | Sensibilidad de los datos o de la superficie de seguridad involucrada |
| `reversibility` | Qué tan difícil es volver atrás (3 = irreversible) |
| `files_modules_footprint` | Cantidad de archivos y módulos tocados |
| `test_maturity_gap` | Cuánta cobertura de tests falta en la zona del cambio |
| `regulatory_compliance_impact` | Impacto regulatorio o de cumplimiento |

## Reglas

Se evalúan en este orden y **gana la primera que coincide**. La evidencia faltante o ilegible no se compensa: da Tier 4.

| Regla | Condición | Tier | Notas |
|---|---|---|---|
| FM-00 | `evidencia faltante o ilegible` | 4 | JSON inválido, dimensión ausente o desconocida, valor no entero o fuera de 0–3 |
| FM-01 | `security_data_sensitivity == 3` | 4 | Piso duro, no compensable |
| FM-02 | `reversibility == 3` | 4 | Piso duro |
| FM-03 | `regulatory_compliance_impact == 3` | 4 | Piso duro |
| FM-10 | `component_criticality == 3` | 3 | Piso |
| FM-11 | `blast_radius == 3` | 3 | Piso |
| FM-12 | `files_modules_footprint == 3` | 3 | Piso |
| FM-13 | `>= 3 dimensiones con valor >= 2` | 3 | Riesgo acumulado |
| FM-20 | `>= 1 dimensión con valor >= 2` | 2 | Solo si ninguna regla anterior aplica |
| FM-30 | `todas las dimensiones <= 1` | 1 | Default |

## Tier → ceremonia

| Tier | Ceremonia | Judgment Day |
|---|---|---|
| 1 | `minimal` | no |
| 2 | `light` | no |
| 3 | `full` | no |
| 4 | `full` + verificación en contexto fresco | sí, obligatorio |

## Cambios de tier

- Un tier desconocido o ilegible se trata como Tier 4.
- Solo el orquestador re-clasifica: el **upgrade** es automático y el **downgrade** requiere confirmación humana literal.
