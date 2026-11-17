# Integration and data

Steps 7 and 8 of `software-solution`, for the option the person chose: the components, how they talk to each other and to external systems, and where each piece of data lives.

## Components

One row per component (a deployable, a data store, an external system):

| Component | Responsibility | Owner | Owns data | Interfaces |
|---|---|---|---|---|
| Returns service | Creates returns, labels and refund requests | delivery team | returns, refund requests | REST API for the web shop; consumes `OrderDelivered`; publishes `ReturnReceived` |

- **One responsibility,** in one sentence without "and also". Two responsibilities with different owners or release rhythms are two components.
- **One owner** per component: a team or a role, never a person.
- **Owned data** is data only this component writes.

## Integration styles

| Style | Good for | Watch out for |
|---|---|---|
| Request and response (REST, gRPC) | A caller that needs the answer now: reads, validations, commands with immediate feedback | Coupled availability: if the callee is down, the caller fails. Timeouts, retries, circuit breakers |
| Messages or events (queue, topic) | Work that can happen later, several consumers, smoothing peaks, decoupling release cycles | Eventual consistency, ordering, duplicates, poison messages, schema evolution |
| Batch and files | Large volumes on a schedule, partners that only support files | Latency, partial failures, reprocessing, file validation |
| Streams | Continuous high-volume data, near-real-time analytics | Operational weight; rarely needed for business workflows |
| Shared database | Almost never between teams | Hidden coupling: any schema change breaks someone. Prefer an interface or events |

Pick per integration point, not once for the whole system.

## Per integration point

For each arrow between components or to an external system, write:

| Field | Example |
|---|---|
| From, to, style | Returns service to carrier, REST, synchronous with a queue in front |
| Contract | The carrier's label API, version 3; our side wrapped in an adapter |
| Versioning | Our public APIs: version in the path, old version kept for 6 months; events: additive changes only, a new event name for breaking ones |
| Timeouts and retries | 5-second timeout; 3 retries with exponential backoff and jitter; then the request waits in the queue |
| Idempotency | An idempotency key per return, so a retried label or refund request never runs twice |
| Failure path | After the retries, a dead-letter queue and an alert; the customer is told the label will come by email |
| Consistency | The return exists before the label; the label arrives later (eventual) |
| Data and level | Delivery address (Restricted), order number (Internal) |

## Reliability patterns

| Pattern | Use it when |
|---|---|
| Timeout on every remote call | Always. No call waits forever |
| Retry with exponential backoff and jitter | Transient failures (timeouts, 503). Never retry what is not idempotent |
| Idempotency key | Any command that may be retried: payments, refunds, label requests, emails |
| Circuit breaker | A dependency that fails often enough to slow everything down |
| Transactional outbox | A database change and the event that announces it must never diverge |
| Dead-letter queue | Messages that keep failing; someone must look at them, with an alert |
| Saga with compensations | A business transaction across several services; each step has an undo |
| Bulkhead | One slow dependency must not exhaust the resources of the others |

## Consistency

- **Strong** consistency inside one component's data store, where a transaction can cover it.
- **Eventual** consistency across components: say how long "eventually" is allowed to be, what the user sees meanwhile, and how drift is detected and repaired.
- Never a distributed transaction across services owned by different teams.

## Data

One row per data set:

| Data set | Writer | Readers | Level | Store and region | Retention | Personal data minimized? |
|---|---|---|---|---|---|---|
| Returns | Returns service | Web shop (via API), reporting copy | Internal | Returns database, the organization's main region | 7 years (accounting, confirmed by the person) | yes: references the order, does not copy the address |
| Refund requests | Returns service | Payments provider | Restricted | Returns database, encrypted column | 7 years | payment reference only, no card data |

- **One writer** per data set. Readers use its interface, its events, or a read-only copy it publishes.
- **Level** follows `.exo/shared/data-protection.md`, section A. With `data-classification` (pack `security`) installed, apply it; otherwise apply its inline criteria from the phase map.
- **Residency:** where the data is stored and processed, and whether any flow takes it elsewhere (a vendor, a backup region, a support tool).
- **Retention and deletion:** how long, who decided it, and how it is deleted (including backups and copies).
- **Minimization:** store a reference instead of a copy of personal data whenever the workflow allows it.
- **Copies:** every reporting or analytics copy is listed, with its level and who may read it.

## Migrations

When data moves from an existing system:

1. **Inventory:** what moves, how much, its level, and who owns it after the move.
2. **Strategy:** a one-time move with a cut-over window, or both systems in parallel with a sync until the old one is retired (expand, migrate, contract).
3. **Validation:** counts and checksums before and after; a sample checked by the owners.
4. **Rollback:** what happens if the cut-over fails, and until when it is possible.
5. **Personal data:** a migration is a new processing of it: the same level, residency and retention rules apply to every intermediate file and environment; test environments get synthetic or masked data.
