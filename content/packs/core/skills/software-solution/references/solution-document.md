# Solution document

Step 13 of `software-solution`: the shapes of what it delivers. Outside a change, a solution document of its own. Inside a change, text blocks that `sdd-design` places into design.md; this skill never writes design.md.

## Outside a change: the solution document

In the file the person names (default `docs/architecture/<slug>.md`). Keep the headings; write `Open question:` where the answer is missing, and `None` with the reason when a section does not apply.

````markdown
# Solution: <name>

- Owner: <team or role> · Status: <draft | proposed | approved> · Version: <n>, <date>
- Regime: <regulated | not regulated | regulated (assumed)>

## Summary

<Five lines: the problem, the recommended option, why it wins, what it gives up, the top risk.>

## Problem and scope

<The problem, for whom, the scope and what is out of it, the horizon.>

## Drivers

| # | Quality | Scenario | Measure | Source |
|---|---|---|---|---|

## Constraints and assumptions

<Constraints with their source; assumptions with how and when they are checked.>

## Context

```mermaid
<the context view of references/context-and-drivers.md>
```

## Options

<Each option in the same five parts: shape, drivers, cost, risks, reversibility.>

## Comparison and decision

<The weighted matrix, the recommendation, and the decision with who made it and when.>

## Architecture

<Containers of the chosen option: the diagram and the components table.>

## Integration

<One block per integration point: style, contract, versioning, timeouts and retries, idempotency, failure path, consistency, data and level.>

## Data

<The data table: writer, readers, level, store and region, retention, minimization. Migrations.>

## Security and compliance

<The baseline; in a regulated regime, the controls table with how each is supported and its evidence.>

## Operation

<Deployment and environments, releases and rollback, observability and objectives, resilience and recovery objectives, capacity, runbooks.>

## Cost

<Drivers, order of magnitude per option, unit cost, guardrails.>

## Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|

## Decision records

<The one-way doors, each with its record (proposed or approved) and its path.>

## Open questions

1. <question>: <why it matters>. Default: <assumption>.
````

## Inside a change: text for sdd-design

`sdd-design` owns design.md and its eight sections. Return these blocks in your answer, each labeled with the section it is meant for; the phase merges them with its own work, edits them as it needs, and runs speclint.

| design.md section | What this skill gives |
|---|---|
| Architecture Overview | The option chosen and who chose it, the context and container diagrams, the components table, the integration points in one paragraph, and why the option beats the others |
| Data Shapes | The data sets with their writer, level, store and retention; the event and API contracts at the level of fields that cross a boundary |
| Error Handling | The failure path of each integration point, and what the user sees |
| Migration / Backwards Compatibility | The data migration strategy and the versioning of public contracts |
| Risks & Mitigations | The top risks of the register, and the trust boundaries for the threat model |

The Modules / Files, Sequence Of Operations and Test Plan sections stay with `sdd-design`: they are module-level design.

### Example block

```markdown
For design.md, Architecture Overview:

**Option chosen:** B, a returns service with its own store, fed by order events. Chosen by the person on <date>; A (extend the order platform) and C (vendor product) compared in docs/architecture/returns.md.

| Component | Responsibility | Owner | Owns data |
|---|---|---|---|
| Web shop | Shows orders and collects return requests | web team | none new |
| Returns service | Creates returns, labels and refund requests | delivery team | returns (Internal), refund requests (Restricted) |
| Order platform | Publishes `OrderDelivered` | orders team | orders |
| Carrier (external) | Issues labels, scans parcels | vendor | none of ours |
| Payments provider (external) | Refunds the original payment | vendor | none of ours |

The web shop calls the returns service synchronously (REST, version in the path). The returns service consumes `OrderDelivered` and publishes `ReturnReceived`; label and refund requests go through a queue with retries and an idempotency key per return.

Why B: isolates the Restricted refund data and keeps working when the carrier is down; it costs one new deployable and an event consumer. One-way doors with draft records: the returns store, and `ReturnReceived` as a contract for other teams.

For design.md, Risks & Mitigations:

- The carrier's rate limit may be lower than peak demand (medium, high impact): queue with a controlled rate; confirm the limit with the vendor.
- Refund requests duplicated by retries (low, high impact): idempotency key per return; daily reconciliation.
- Trust boundaries for the threat model: web shop to returns service; returns service to carrier and payments provider (Restricted data leaves the organization).
```

## Checks before delivering

- The summary alone tells a reader what was decided and why.
- Every driver has a measure or a labeled proposal; every number has a source.
- The diagrams use roles and kinds of systems; no hostnames, IP addresses, URLs or personal data.
- Inside a change, the blocks name their target section and nothing was written to design.md.
- Nothing claims compliance; regulated controls name their evidence.
