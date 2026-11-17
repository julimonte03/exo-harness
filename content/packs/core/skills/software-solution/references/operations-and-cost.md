# Operations, cost and risks

Steps 10 to 12 of `software-solution`, for the option the person chose: how the solution runs, what it costs, and what could go wrong.

## Deployment and environments

| Question | The architecture says |
|---|---|
| Where does each component run? | The organization's platform (a container platform, serverless functions, virtual machines, a managed service) |
| Which environments exist? | For example development, test, staging, production; which ones hold real data (only production, by default) |
| How is it deployed? | Through the project's pipeline, from version control; infrastructure described as code where the organization does so |
| How are releases made safe? | Feature flags, canary or blue-green releases, database changes that are backward compatible (expand, migrate, contract) |
| How is a release undone? | The rollback path and its limits (a migration that cannot be reversed is a one-way door) |

## Observability

- **Logs:** structured, with a correlation ID across components; no secrets or personal data in the text.
- **Metrics:** per component, the four signals: traffic, errors, latency, saturation.
- **Traces:** across the integration points of step 7, to find where time goes.
- **Service level objectives:** one to three per user-facing flow, each with an indicator, a target and a window: "99.5% of return submissions succeed, over 28 days". Targets come from the person; propose them as proposals. When the project has `slo-design` (pack `ops`), use it for the full definition.
- **Alerts** on the objectives and on the failure paths (a growing dead-letter queue), each with a runbook.

## Resilience

One row per dependency that can fail:

| Failure | Effect on users | Detection | Response |
|---|---|---|---|
| Carrier API down | Labels delayed | Error rate on the adapter, queue depth | Requests wait in the queue; customers told the label comes by email; alert after 30 minutes |
| Payments provider declines or times out | Refund delayed | Refund error metric | Retry with the same idempotency key; after 24 hours, a support case |
| Returns database unavailable | Returns cannot be created | Health check | Fail over to the replica; the web shop shows "try again in a few minutes" |
| Order events delayed | New deliveries not returnable yet | Consumer lag | Catch up automatically; alert when the lag passes one hour |

- **Recovery objectives,** agreed with the business: the recovery time objective (how long the solution may be down) and the recovery point objective (how much data may be lost). They decide replication and backup choices.
- **Backups** that are restored in a test on a schedule; a backup never restored is a hope, not a control.
- **Degraded modes:** what still works when a dependency is down; prefer a reduced service to a full outage.

## Capacity

- The volumes from the drivers (step 3): normal, peak, and expected growth over the horizon of step 1.
- Which component saturates first, and how it scales (more instances, a bigger instance, partitioning).
- Limits that protect the solution: rate limits per caller, queue sizes, timeouts.

## Runbooks

List the runbooks that must exist before go-live: one per alert, plus deployment, rollback, restore from backup and the replay of dead-lettered messages. When the project has `runbook-writer` (pack `ops`), it writes them; otherwise list their titles and owners as a pre-release task.

## Cost

| Driver | Questions |
|---|---|
| Compute | How many instances or invocations at normal and peak load? |
| Storage | How much data per month, kept how long, with how many copies? |
| Data transfer | What crosses regions or leaves the provider? |
| Licenses and vendors | Per user, per transaction, per instance? |
| Operations | Who runs it, on call, and how much of their time? |
| Build | Rough effort to build and to migrate, in the team's terms |

- **Order of magnitude, not a quote:** use the figures the person gives (current bills, vendor prices). Without them, compare the options as low, medium or high, and say that it is a relative estimate.
- **Unit cost:** the cost per business unit (per return, per order, per customer) shows whether growth is healthy.
- **Guardrails:** budgets and alerts on spend, and the cost metric next to the technical ones.
- **Never invent prices** or present an estimate as a quote.

## Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R-1 | The carrier's rate limit is lower than the peak needs | medium | high: labels delayed for hours after a sale | Queue with a controlled rate; confirm the limit with the vendor before release | delivery team lead |
| R-2 | Refund requests duplicated by retries | low | high: money paid twice | Idempotency key per return; a reconciliation report | delivery team lead |
| R-3 | The team has never run an event consumer in production | medium | medium | Pair with the platform team; runbooks before go-live | engineering manager |

- Likelihood and impact as low, medium or high, with the reason when it is not obvious.
- **Every High impact risk** has a mitigation in the design or an explicit acceptance by the person, recorded as a decision.
- Inside a change, the top risks go to Risks & Mitigations through `sdd-design`; the threats of the threat model go there too.
