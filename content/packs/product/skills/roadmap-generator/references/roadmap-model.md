# Roadmap model

The detailed roadmap of `roadmap-generator`: the template, the meaning of each field, and a worked example. The example is synthetic: the delivery team of an online shop.

## Fields

| Element | Fields |
|---|---|
| Header | Owner (team or area), audience, scope, time range and format, version, date, status (draft or approved) |
| Objective `O-n` | Outcome, metric (baseline, target, date, source), the strategy it serves |
| Initiative `I-n` | Name, objectives, expected result, confidence, size, owner team or role, status, workstream, horizon or quarter, depends on |
| Milestone `M-n` | Name, date, `committed` (with its source) or `target`, the initiatives it needs |
| Risk `R-n` | Risk, likelihood, impact, mitigation, owner role |
| Assumption `A-n` | What must be true, how and when it is checked, riskiest or not |

**Confidence:**

| Level | Means | Where it usually sits |
|---|---|---|
| High | Shaped, owned, capacity reserved, few unknowns | Now |
| Medium | Shaped enough to size, some unknowns, no capacity reserved yet | Next |
| Low | A problem worth exploring; the solution is open | Later |

**Status:** `idea`, `discovery`, `in progress`, `done`. A `done` initiative stays one version, with its result against the metric, then leaves the roadmap.

## Template

```markdown
# Roadmap: <scope>

- Owner: <team or area>
- Audience: <who reads it>
- Time range: <range>, in <now/next/later or quarters>
- Version: <n>, <date>, <draft | approved>

## Objectives

| ID | Outcome | Metric | Baseline | Target | By | Source |
|---|---|---|---|---|---|---|
| O-1 | ... | ... | ... | ... | ... | ... |

## Now

| ID | Initiative | Serves | Expected result | Confidence | Size | Owner | Status | Depends on |
|---|---|---|---|---|---|---|---|---|
| I-1 | ... | O-1 | ... | high | M | <team> | in progress | - |

## Next

<same columns>

## Later

<same columns, without dates>

## Milestones

| ID | Milestone | Date | Kind | Needs |
|---|---|---|---|---|
| M-1 | ... | ... | committed: <source> | I-3 |

## Dependencies

- I-3 depends on <team or vendor>: <what is needed, by when>.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|

## Assumptions

| ID | Assumption | Checked by | When | Riskiest |
|---|---|---|---|---|

## Not on this roadmap

- <initiative or request>: <why, and when it will be reconsidered>

## Parking lot

- <initiative without an objective>: <the question to answer>

## Changes since the last version

- <what moved, and why>
```

## Example

```markdown
# Roadmap: delivery experience

- Owner: delivery team
- Audience: leadership and the delivery team
- Time range: 2027, in now, next and later
- Version: 2, 2027-01-08, approved

## Objectives

| ID | Outcome | Metric | Baseline | Target | By | Source |
|---|---|---|---|---|---|---|
| O-1 | Customers solve delivery changes on their own | Share of reschedules done without support | 0% | 50% | end of Q3 | order events |
| O-2 | Support time goes to complex cases | Delivery calls per week | 40 | 15 | end of Q3 | weekly support summary |
| O-3 | The order pages are accessible | WCAG 2.2 AA audit of the order pages | not audited | passed | 2027-06-30 | contract with the audit firm |

## Now

| ID | Initiative | Serves | Expected result | Confidence | Size | Owner | Status | Depends on |
|---|---|---|---|---|---|---|---|---|
| I-1 | Reschedule a delivery before dispatch | O-1, O-2 | A third of reschedules self-served within a month of release | high | M | delivery team | in progress | - |
| I-2 | Spike: can the carrier change the date after dispatch? | O-1 | A yes or no, with the carrier's conditions | high | S | delivery team | idea | - |
| I-3 | Accessibility fixes on the order pages | O-3 | No AA failure left on the audited pages | medium | M | web team | discovery | - |

## Next

| ID | Initiative | Serves | Expected result | Confidence | Size | Owner | Status | Depends on |
|---|---|---|---|---|---|---|---|---|
| I-4 | Proactive delay notices | O-2 | Delay calls drop by half | medium | M | delivery team | idea | - |
| I-5 | Reschedule after dispatch | O-1 | Covers the remaining reschedules | low | L | delivery team | idea | I-2 |

## Later

| ID | Initiative | Serves | Expected result | Confidence | Size | Owner | Status | Depends on |
|---|---|---|---|---|---|---|---|---|
| I-6 | Choose a delivery time window at checkout | O-1 | Fewer reschedules needed at all | low | L | delivery team | idea | I-5 |

## Milestones

| ID | Milestone | Date | Kind | Needs |
|---|---|---|---|---|
| M-1 | Accessibility audit | 2027-06-30 | committed: contract with the audit firm | I-3 |
| M-2 | Reschedule before dispatch released | end of Q1 | target | I-1 |

## Dependencies

- I-5 depends on the carrier: an answer from the spike I-2, and a contract change if they say yes.
- I-3 depends on the design system team: accessible versions of the date picker and the dialog, by May.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R-1 | The carrier does not accept changes after dispatch | medium | I-5 and part of O-1 drop | Spike I-2 in Now; O-1 target reviewed after it | product owner |
| R-2 | The design system fixes arrive late | medium | M-1 at risk | Agree a date with that team in January; fall back to local fixes | web team lead |

## Assumptions

| ID | Assumption | Checked by | When | Riskiest |
|---|---|---|---|---|
| A-1 | Customers prefer self-service to calling for a reschedule | Share of reschedules through I-1 | a month after release | yes |
| A-2 | Delay calls are mostly about late notice, not the delay itself | Call reasons in the support summary | before starting I-4 | no |

## Not on this roadmap

- Changing the delivery address: has its own fraud checks; reconsidered in the next version.

## Parking lot

- Loyalty points for on-time pickups: which objective does it serve?

## Changes since the last version

- I-5 moved from Now to Next: it depends on the carrier spike I-2.
- O-3 added: the audit date became a contract commitment.
```

## Quarterly variant

The same tables with a `Quarter` column instead of the Now, Next and Later sections. Keep the rules:

- the current and the next quarter carry initiatives; quarters further out carry problems or goals;
- confidence falls with distance and is shown on every row;
- a quarter is not a date: only milestones carry dates, labeled committed or target.
