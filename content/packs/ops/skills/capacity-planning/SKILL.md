---
name: capacity-planning
description: >-
  Plans capacity for an expected peak event (a sale, a launch, a campaign, a
  seasonal spike, a migration of traffic, a new region) or for sustained
  growth: measures the baseline from real metrics, models the demand at the
  peak, finds the component that saturates first, sets the headroom, sizes
  the resources with their cost, and designs the load test that validates
  the plan, with go/no-go criteria for the event. Proposes scaling changes
  and load tests; never runs a load test against production or a shared
  environment, and never changes infrastructure, without the person's
  approval. Use it before a peak event or a launch, when traffic is expected
  to grow, or when someone asks whether the system will hold. Triggers:
  "capacity planning", "will we handle the traffic", "prepare for the
  peak", "load test plan", "how many instances do we need", "scale for the
  launch", "traffic is going to double", "size the database for growth",
  "headroom", "new region launch".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-specs
---

# capacity-planning

Capacity planning answers "will it hold, and what does it cost to make sure" with numbers. The numbers come from the system's own history, the demand comes from the people who know the event, and a load test checks the model before the real users do.

## Result

- **A capacity plan** (`references/load-testing.md` has the readiness checklist that closes it) with:
  - the event or growth scenario, its date and the bar it must meet (an SLO or latency and error targets);
  - the baseline, each number with its source and period;
  - the demand model at the peak, with its assumptions labeled;
  - per component: capacity per unit, required units at the peak with headroom, and the order in which components saturate;
  - non-scalable limits (quotas, connection limits, licenses, third-party rate limits) and how each is handled;
  - the sizing (current and proposed) with its cost delta, labeled as an estimate;
  - the load test design and, once run, its results compared with the model;
  - go/no-go criteria and the follow-ups with owners.
- It goes in the file the project uses for capacity plans or the one the person names, or in the answer.

## When

- Before a peak event or a launch; when traffic is expected to grow (a new customer, a new market, a marketing push); before a migration that moves traffic; when a component runs hot every week and nobody knows how much room is left.
- **Not for:** a live slowdown or outage (skill:incident-response first); a single slow request or a slow function (skill:debug-systematically); defining the reliability targets themselves (skill:slo-design, whose SLOs are the bar here).

## Rules

- **Numbers have a source,** or are labeled `Assumed:` with who should confirm them. Never invent a baseline, a growth factor or a price.
- **The event's demand comes from people.** Expected traffic, the marketing plan, last year's peak: ask the person, who asks the business owner. Write the scenario they give, and a pessimistic variant.
- **No load test against production or a shared environment** without the explicit approval of its owner, a time window, the people on call informed, and abort conditions. Prefer a production-like, isolated environment.
- **No infrastructure changes.** Scaling, quota requests and configuration changes are proposed, with their undo, for the person to apply through the project's normal flow.
- **Install nothing.** Use the load testing tool the project already has (k6, Gatling, Locust, JMeter, wrk, hey, vegeta, or the cloud provider's); if there is none, name the one you would suggest and the command, and continue with the model.
- **Synthetic test data only.** Never replay real customer data or real payment details in a load test.
- **Costs are estimates,** with the price source and its date, from the project's own bills or the provider's price list the person points at.

## Steps

The formulas with a worked example are in `references/demand-model.md`. Load test profiles, tool commands, abort conditions and the readiness checklist are in `references/load-testing.md`.

### 1. Frame the scenario

- **What:** the event or the growth, its date or horizon, and when changes must be done by (a change freeze before the event).
- **How big:** the expected peak as a multiple of today, or in absolute numbers (orders per minute, concurrent users, requests per second), from the business owner. Add a pessimistic variant (for example 1.5 times the expected).
- **Which journeys:** the ones that carry the event (browse, search, add to cart, checkout) and their mix.
- **The bar:** the SLO of each journey (skill:slo-design), or explicit latency and error targets.

### 2. Measure the baseline

For each journey and component, from the last comparable peak and from a normal week:

- **Demand:** requests per second at the busiest minute and the busiest hour; the journey mix.
- **Performance:** latency p50, p95 and p99; error rate.
- **Saturation:** CPU, memory, connection pools, thread pools, queue depth and consumer lag, database queries per second and slow queries, cache hit ratio, disk and network I/O.
- **Limits:** autoscaling minimum and maximum, cloud quotas, database connection limits, third-party rate limits, licenses.

Write the source of each number (dashboard, query, period). Without metrics, derive request rates from access logs (skill:log-analysis) and say how.

### 3. Model the demand

- **Peak rate** = baseline peak × growth × event multiplier, per journey.
- **Burstiness:** the peak minute is often two to three times the hourly average; size for the minute.
- **Fan-out:** one user action becomes N calls to backends; one page view becomes M queries. Multiply through to each component.
- **Amplifiers:** retries on timeouts, cache misses on cold caches, batch jobs that run during the event.
- **Concurrency** with Little's Law: concurrent requests = rate × latency.

### 4. Capacity per component

- **Capacity per unit:** the throughput one unit (an instance, a pod, a database node) sustains while staying inside the bar, from a past load test or the measured peak with its utilization. Not the throughput at 100% CPU: latency rises sharply well before that.
- **Required units** = peak rate / (capacity per unit × target utilization), rounded up, plus what is needed to survive losing one unit or one zone.
- **Scale-up time:** if autoscaling takes 5 minutes and the peak arrives in 1, pre-scale before the event.
- **Non-scalable limits:** database connections (units × pool size must stay under the limit), quotas, rate limits of third parties, single-writer databases, locks. These usually decide the plan.

### 5. Find the order of saturation

List the components by the multiple of today's load at which each one hits its limit. The first one is the bottleneck; plan for it, then check the next. A component with no measured limit is a risk to test, not an assumption of infinite capacity.

### 6. Set the headroom

The target utilization at the peak, with its reason: for stateless services commonly 60 to 70% of CPU, so a zone loss or a surprise burst still fits; lower for components that degrade sharply (databases, queues near their limits). Write what the headroom protects against.

### 7. Size and cost

A table per component: current units, proposed units, the option chosen and its cost delta for the event window or per month. Options, roughly from cheapest:

1. Remove waste: a missing index, an N+1 query, a cache with a poor hit ratio.
2. Pre-scale for the event window and scale back after.
3. Raise autoscaling maximums and quotas (quota requests can take days: start early).
4. Scale out or up permanently.
5. Protect the core: queue or shed non-critical work, degrade optional features behind flags, rate-limit abusive clients.

### 8. Design and run the load test

- **Goal:** validate the model at 1.0 times and the pessimistic multiple of the expected peak, and find the real first bottleneck.
- **Environment:** production-like and isolated; the same instance types, data volume and configuration where possible.
- **Profile:** ramp up, steady at the expected peak, a step to the pessimistic multiple, a spike, and a soak for leaks; with the journey mix of step 1.
- **Pass and fail** from the bar: p99 latency and error rate per journey, plus saturation limits.
- **Abort conditions** and who is informed, before starting.
- Give the command for the project's tool; the run happens only with the person's approval. Compare the results with the model, update it, and repeat after each fix.

### 9. Go or no-go

Close the plan with the readiness checklist of `references/load-testing.md`: scaling and quotas done and verified, pre-scaling scheduled, load test passed at the pessimistic multiple, dashboards and alerts on the SLOs, runbooks for the likely failures (skill:runbook-writer), on-call staffed and briefed (skill:on-call-handoff), feature flags to shed load tested, a rollback plan, and the change freeze. Each item has an owner and a date.

## Where it goes

- The folder the project uses for capacity plans (look for `docs/capacity/`, `docs/ops/` or `docs/reliability/`), as `<event-or-scenario>.md`. If there is none, propose `docs/capacity/` and create it only after the person says yes; until then, keep the plan in the answer.
- **Inside an SDD change,** the capacity plan is a project document, never a file of the change root: any phase may write it with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3 and 4; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C). Until then, return the plan's numbers as text, also for the phase that owns an artifact that needs them (for example the NFRs of the spec, or the design's Risks & Mitigations). A load test script is code: it belongs to the apply phase when the plan lists it.

## Return

```markdown
Scenario: spring sale, 2026-04-15, expected peak 4x today's busiest minute (business owner), pessimistic 6x.
Bar: checkout SLO 99.9% availability, p99 under 800 ms.
Baseline (last peak, 2026-03-02, dashboard "Checkout"): 120 req/s busiest minute; p99 420 ms; checkout-api at 45% CPU on 6 pods (autoscaling max 10), pool of 30 database connections per pod; database at 35% CPU, 180 of 500 connections.

| Component | Saturates at (today's limits) | Today | Needed at 6x (65% target, one unit spare) | Proposal | Cost delta |
|---|---|---|---|---|---|
| checkout-api | 3.1x (autoscaling max 10) | 6 pods | 26 pods | Autoscaling max 10 to 30; pre-scale to 20 at 06:00 | Estimate: +<amount> for the day |
| Database connections | 3.6x, once autoscaling allows 17 pods (17 × 30 > 500) | 180 / 500 | 780 (26 × 30) | Pool per pod 30 to 10 (about 22 queries in flight at 6x); or a connection pooler | Estimate: none |
| Payment provider | 5x (rate limit 600 req/s) | 120 req/s | 720 req/s | Ask the provider for a temporary raise; queue retries | — |

Load test: k6 script designed (profile in the plan); not run: needs staging approval.
Go/no-go: 4 of 11 checklist items done; open items have owners and dates.
Assumed: the journey mix of last year's sale (business owner to confirm).
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "capacity-planning", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add decisions '{"summary": "Pre-scale checkout-api to 20 pods for the spring sale", "rationale": "load test at 4x passed with 20 pods at 54% CPU; autoscaling up to 30 covers 6x", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change, save the measured capacity per unit with skill:memory-protocol as a `discovery`: it is the number the next plan needs.

## Before you finish

- [ ] Every number has a source or an `Assumed:` label with who confirms it.
- [ ] The demand model includes burstiness, fan-out and amplifiers, for the expected and the pessimistic scenario.
- [ ] Every component has its saturation point, and non-scalable limits are listed with a plan.
- [ ] No load test or infrastructure change ran without the person's approval; tools were not installed.
- [ ] The go/no-go checklist has an owner and a date for each open item.
