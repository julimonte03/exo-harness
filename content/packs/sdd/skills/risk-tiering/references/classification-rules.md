# Risk classification rules (fitness)

Shared source of truth for the `risk-tiering` skill and the runtime. `exo fitness classify` implements exactly this table: an engine parity test compares rule, condition and tier, and fails if they diverge.

## Dimensions

Each dimension is an integer from 0 to 3.

| Dimension | What it measures |
|---|---|
| `blast_radius` | How many users, services or flows are affected if the change fails |
| `component_criticality` | How critical the touched component is |
| `security_data_sensitivity` | Sensitivity of the data or the security surface involved |
| `reversibility` | How hard it is to roll back (3 = irreversible) |
| `files_modules_footprint` | Number of files and modules touched |
| `test_maturity_gap` | How much test coverage is missing in the area of the change |
| `regulatory_compliance_impact` | Regulatory or compliance impact |

## Rules

They are evaluated in this order and **the first match wins**. Missing or unreadable evidence is not compensated: it gives Tier 3.

| Rule | Condition | Tier | Notes |
|---|---|---|---|
| FM-00 | `missing or unreadable evidence` | 3 | Invalid JSON, missing or unknown dimension, value not an integer or outside 0–3 |
| FM-01 | `security_data_sensitivity == 3` | 3 | Floor, not compensable |
| FM-02 | `reversibility == 3` | 3 | Floor, not compensable |
| FM-03 | `regulatory_compliance_impact == 3` | 3 | Floor, not compensable |
| FM-10 | `component_criticality == 3` | 3 | Floor |
| FM-11 | `blast_radius == 3` | 3 | Floor |
| FM-12 | `files_modules_footprint == 3` | 3 | Floor |
| FM-13 | `>= 3 dimensions with value >= 2` | 3 | Accumulated risk |
| FM-20 | `>= 1 dimension with value >= 2` | 2 | Only if no previous rule applies |
| FM-30 | `all dimensions <= 1` | 1 | Default |

## Tier → ceremony

The rule that decided the tier (FM-01, FM-10…) is recorded in `fitness-assessment.json`.


| Tier | Ceremony | Judgment Day |
|---|---|---|
| 1 | `minimal` | no |
| 2 | `light` | no |
| 3 | `full` + fresh-context verification | yes, always |

## Tier changes

- An unknown or unreadable tier is treated as Tier 3. A Tier 4 recorded by engine 1.0 is read as Tier 3.
- Only the orchestrator reclassifies: an **upgrade** is automatic and a **downgrade** requires literal human confirmation.
