# ADR template

The structure of an ADR that `architecture-decision-record` writes. Replace the example values with the project's own; keep the header lines and the four sections, in this order. When the folder's existing ADRs follow another template, follow theirs instead.

## A decided ADR

~~~markdown
# 0007. PostgreSQL for orders

Status: Accepted
Date: 2026-11-16
Change: PROJ-123-orders-store
Supersedes: 0003

## Context

Orders are kept in JSON files on the API's disk (src/orders/store.py:18), which cannot be shared by two instances. The team needs to run two API instances behind the load balancer, and order totals must never be lost after a crash.

## Decision

Orders are stored in PostgreSQL 16, in one schema owned by the orders service. Other services read orders through its API, never from its tables.

## Alternatives

- **Keep the files on a shared volume:** no transactions, and concurrent writes corrupt them.
- **MongoDB:** fits the JSON shape, but the team runs no MongoDB today and reports need joins with billing.

## Consequences

- Positive: two instances can run; writes are transactional.
- Negative: a database to operate, back up and migrate.
- Follow-ups: a migration from the files (task 4 of the change), and the connection settings in `.exo/context.md`.
~~~

## What goes in each part

| Part | What goes there |
|---|---|
| Title | `NNNN.` and the decision in a few words, not the problem: "PostgreSQL for orders", not "Order storage" |
| `Status:` | `Proposed`, `Accepted`, `Superseded by NNNN` or `Recovered` |
| `Date:` | The day the status last changed, as `YYYY-MM-DD` |
| `Change:` | The SDD change that made the decision, when there is one. Optional |
| `Supersedes:` | The number of the ADR it replaces. Optional |
| Context | The forces: the problem, the constraints and the quality attributes at stake, with `path:line` where the code shows them. Two to five sentences, neutral, without the decision |
| Decision | What was decided, in the active voice and the present tense, and its scope: what it covers and what it does not |
| Alternatives | Each option really considered, and why it was not chosen. With only one option, say so and why |
| Consequences | What becomes easier and what becomes harder, and the follow-ups it creates: migrations, docs, tasks |

- One decision per ADR, about a page. Two decisions that can be reversed separately are two ADRs.
- Name roles and teams, never people. Say where a secret or a setting lives, never its value.
- A superseded ADR keeps its text: only its status line changes, to `Superseded by NNNN`.

## A recovered ADR

The decisions that reverse engineering finds in the code. Each claim carries its evidence marker; the overall confidence goes in the header.

~~~markdown
# 0012. Recovered: one PostgreSQL database for every module

Status: Recovered
Confidence: medium
Source: exo discover; units: src-db, src-orders
Date: 2026-11-16

## Context

The orders and billing modules share tables and transactions [Code] src/orders/repo.py:40-58. Why one database was chosen is not documented [Inferred: low].

## Decision

Every module reads and writes through the same connection pool [Code] src/db/pool.py:12-30, configured from the environment [Code] src/config.py:8.

## Alternatives

Unknown: neither the code nor the docs show what was considered. Open question for the person.

## Consequences

- Reports join tables of several modules [Code] src/reports/sales.py:22-41.
- A schema change in billing can break orders [Inferred: medium].
~~~

### Confidence

| Confidence | When |
|---|---|
| `high` | The Decision has `[Code]` evidence in every place it applies, and a `[Doc]` explains the Context |
| `medium` | The Decision has `[Code]` evidence, but the reason behind it is inferred |
| `low` | The Decision itself is inferred: a pattern seen in some places and not in others |

- A recovered ADR with `low` confidence may be better as an open question for the person than as a record.
- When the person confirms it, change `Status: Recovered` to `Status: Accepted`, update `Date:`, and keep the file name and the evidence. Their corrections and the reasons they gave go in the text.
