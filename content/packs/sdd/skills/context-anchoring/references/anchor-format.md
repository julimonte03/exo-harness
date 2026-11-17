# Anchor format

The format of `<change-root>/context-anchor.md`. Keep the sections in this order, and keep Now at the top: it is what a new reader needs first.

## Template

```markdown
# Context anchor: <change-name>

## Now

- Status: active | paused | closed
- Tier and phase: Tier <n>, <phase just finished> -> next: <phase>
- Next step: <one concrete action>, by <who>; start by reading <file or section>
- Last updated: <YYYY-MM-DD> by <who>

## Decisions

### D-1: <the decision in one line>

- Date and who: <YYYY-MM-DD>, <@handle or role>
- Why: <the reason>
- Landed in: <artifact and section, or "not yet">
- Status: active | superseded by D-<n>

## Ruled out

- <alternative> (for D-<n>): <why it was rejected>

## Assumptions

- A-1: <what is taken as true>. Check: <how>. Status: open | confirmed | wrong (<what changed>)

## Open questions

- Q-1: <the question>. Who can answer: <@handle or role>. Needed by: <phase>. Status: open | answered (D-<n>)

## Log

- <YYYY-MM-DD>, <phase>, <who>: <what happened in the session>
```

## Field rules

| Field | Rule |
|---|---|
| IDs | `D-n`, `A-n` and `Q-n`, numbered in order and never reused. Never `S-n`, `T-n` or `TM-n`, which belong to the spec, the test spec and the threat model |
| Date | The day it happened, `YYYY-MM-DD`. When it comes from an artifact and the day is unknown, write the source instead: `from design.md` |
| Who | A handle or role as the team writes them in commits (`@<handle>`, `tech_lead`, `developer`); never an email or phone number. `agent` only in Assumptions and the Log |
| Decision | Only a person decides. Each one says where it landed, so a reader can check that the artifacts agree |
| Superseded | A changed decision is never deleted: mark it and point at the new one |
| Next step | One action, small enough to start right away, with who does it |
| Log | One line per session. Past about 30 lines, fold the oldest ones into one summary line |

## Example

A synthetic change, `add-volume-discount` (invoices get a discount by total quantity), after its design phase.

```markdown
# Context anchor: add-volume-discount

## Now

- Status: active
- Tier and phase: Tier 3, design -> next: tasks
- Next step: break the design into tasks, by @dev-a; start by reading design.md, Modules / Files
- Last updated: 2026-11-17 by @dev-a

## Decisions

### D-1: The discount applies per invoice, on the total quantity

- Date and who: 2026-11-16, @dev-a, with finance's rule from the proposal
- Why: the business rule rewards the size of the order, not of each line
- Landed in: spec.md, CAP-billing-FR-7; design.md, Architecture Overview
- Status: active

### D-2: Discount tiers are constants in code

- Date and who: from design.md (2026-11-17), confirmed by @dev-b
- Why: nobody edits them today, and a table needs a migration
- Landed in: design.md, Data Shapes
- Status: active

## Ruled out

- A discount per line (for D-1): not the business rule.
- Tiers in a database table (for D-2): a migration and an admin screen for values that do not change.

## Assumptions

- A-1: credit lines never reach `close()` with a negative quantity. Check: read the import path of credit notes. Status: open

## Open questions

- Q-1: does the discount show on the printed invoice, or only in the total? Who can answer: @dev-b with finance. Needed by: tasks. Status: open

## Log

- 2026-11-16, spec, @dev-a: spec delta written; per-invoice rule agreed.
- 2026-11-17, design, @dev-a: design and threat model done; Q-1 raised for @dev-b.
```
