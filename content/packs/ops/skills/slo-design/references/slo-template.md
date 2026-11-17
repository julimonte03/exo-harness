# SLO document template

One document per service. Copy it into the SLO file and fill every section; a section with nothing to say keeps its heading and says why.

```markdown
# SLOs: <service>

- **Owner:** <team or role>
- **Status:** proposed | agreed | under review
- **Agreed on:** YYYY-MM-DD, by <roles>
- **Next review:** YYYY-MM-DD

## Users and journeys

| Journey | User | What "working" means | Priority |
|---|---|---|---|
| Confirm an order | Customer in the web shop | The order is confirmed within a second | 1 |

## SLIs

### SLI-1: confirm availability

- **Specification:** the share of order confirmations answered without a server error.
- **Implementation:** load balancer metrics; good = status other than 5xx; valid = every request to `/checkout/confirm`.
- **Query:** <exact query>
- **Exclusions:** health checks; requests from load tests (header `<name>`); 4xx except 429.
- **Misses:** network failures between the customer and the load balancer.

### SLI-2: confirm latency

- **Specification:** the share of order confirmations answered in under 800 ms.
- **Implementation:** server histogram `<metric>`, bucket `le="0.8"`.
- **Query:** <exact query>

## Baseline

| SLI | Period | Value | Worst day | Source |
|---|---|---|---|---|
| SLI-1 | YYYY-MM-DD to YYYY-MM-DD | 99.96% | 99.71% | <dashboard or query> |

## Objectives

| SLI | Target | Window | Error budget |
|---|---|---|---|
| SLI-1 | 99.9% | rolling 30 days | 0.1%: 43 min of full outage, about <n> failed requests at current traffic |
| SLI-2 | 99% | rolling 30 days | 1% of confirmations slower than 800 ms |

Dependencies that limit these targets: <service and its own SLO, or "none">.
Contractual SLA: <none | the SLA and its value; the SLO is stricter>.

## Alerts

| Alert | SLI | Burn rate | Windows | Severity | Runbook |
|---|---|---|---|---|---|
| <name> | SLI-1 | 14.4 | 1 h and 5 min | page | <relative link> |
| <name> | SLI-1 | 6 | 6 h and 30 min | page | <relative link> |
| <name> | SLI-1 | 1 | 3 days and 6 h | ticket | <relative link> |

Rules: <path of the alerting configuration, or "proposed in this document">.

## Error budget policy

- **Budget left:** releases and planned risk as usual.
- **Budget exhausted over the window:** risky releases pause; reliability work comes first until the SLI is back above target. Exceptions (urgent fixes, security patches) need the approval of <role>.
- **One incident spends more than 20% of the budget:** postmortem required.
- **Budget untouched for a quarter:** review whether the target is too loose.
- **Who decides when the policy applies:** <role>.

## Review log

| Date | Change | Reason |
|---|---|---|
```
