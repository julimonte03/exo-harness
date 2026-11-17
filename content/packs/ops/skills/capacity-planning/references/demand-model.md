# Demand model

The formulas behind `capacity-planning`, with one synthetic example carried through. Every input is either measured (with its source) or labeled `Assumed:`.

## Inputs

| Input | Example | Source |
|---|---|---|
| Baseline peak rate (busiest minute) | 120 checkout requests/s | dashboard "Checkout", 2026-03-02 |
| Expected multiplier for the event | 4x | business owner |
| Pessimistic multiplier | 6x | 1.5 times the expected, agreed with the person |
| Mean latency of a checkout request | 250 ms | server metrics, same period |
| Database queries per checkout request | 3 | traces of 100 sampled requests |
| Mean database query time | 10 ms | database metrics |
| Payment calls per checkout request | 1 | code: one authorization per order |
| checkout-api CPU at the baseline peak | 45% on 6 pods | dashboard |
| Database connection pool per pod | 30 | application configuration |
| Database connection limit | 500 | database configuration |
| Payment provider rate limit | 600 requests/s | provider contract |
| Autoscaling maximum | 10 pods | deployment configuration |

## Peak rate

```text
peak = baseline peak × multiplier
expected:    120 × 4 = 480 req/s
pessimistic: 120 × 6 = 720 req/s
```

When the baseline is an hourly average, convert it to the busiest minute first: the busiest minute is commonly two to three times the hourly average, but measure it, because flash events (a push notification, a countdown) make it much higher.

## Fan-out to each component

```text
database queries/s = peak × queries per request = 720 × 3 = 2,160 queries/s
payment calls/s    = peak × payment calls per request = 720 × 1 = 720 calls/s
```

Add the other journeys that hit the same component (browse and search also query the database) with their own peaks and mix.

## Concurrency (Little's Law)

```text
concurrent requests = arrival rate × time in the system
checkout-api in flight at 6x: 720 × 0.25 s = 180 requests
database queries in flight at 6x: 2,160 × 0.010 s = about 22 queries
```

Concurrency tells you how many threads, workers and connections are really busy. Here, 22 queries in flight need far fewer than the 780 connections that 26 pods × 30 would open: the connection limit is a configuration problem, not a database capacity problem.

## Utilization and queueing

```text
utilization = arrival rate / capacity
```

As utilization approaches 100%, waiting time grows without bound. For a simple single-server queue, the mean response time is the service time divided by `(1 - utilization)`:

| Utilization | Response time relative to the service time |
|---|---|
| 50% | 2x |
| 70% | 3.3x |
| 80% | 5x |
| 90% | 10x |

Real systems differ, but the shape holds: this is why the target utilization at the peak is well below 100%, and lower for components that serialize work (databases, single consumers, locks).

## Units needed

```text
pod-equivalents at the baseline = pods × CPU utilization = 6 × 0.45 = 2.7
pod-equivalents at 6x           = 2.7 × 6 = 16.2
pods at a 65% target            = 16.2 / 0.65 = 24.9, rounded up to 25
plus one spare unit             = 26 pods
```

This assumes CPU is what limits a pod and that CPU grows linearly with requests. Check both in the load test: memory, thread pools or a downstream call often limit first.

## Saturation points under today's limits

For each component, the multiple of today's load at which it hits a limit:

```text
checkout-api: autoscaling stops at 10 pods; 10 pods at 85% CPU hold 10 × 0.85 / 2.7 = 3.1x
database connections: pods × 30 must stay at or under 500, so at most 16 pods;
  17 pods are needed from about 3.6x (with the spare unit), once autoscaling allows them
payment provider: 600 / 120 = 5x
```

Order of saturation: checkout-api (3.1x), database connections (3.6x), payment provider (5x). The plan raises the autoscaling maximum, which moves the bottleneck to the connections, which the smaller pool fixes, which leaves the payment provider: a non-scalable limit that needs a raise from the provider or a queue in front of it.

## Amplifiers to add

- **Retries:** with a 2% timeout rate and up to 3 retries, a dependency sees up to about 6% extra calls in normal times, and much more when it slows down. Use the retry budget from the code.
- **Cold caches:** after a deploy or a scale-out, the hit ratio drops; the database sees the misses. Use the miss rate after the last deploy.
- **Batch jobs** scheduled during the event: move them, or add their load.
- **Bots and abuse:** a sale attracts scrapers; check the share of automated traffic in the last event.

## Growth instead of an event

For sustained growth, replace the multiplier with a growth curve from the business plan or the trend of the last months, and compute when each component reaches its target utilization:

```text
months until saturation = log(limit / current load) / log(1 + monthly growth)
example: database at 35% CPU, target 65%, growth 5% per month:
log(65 / 35) / log(1.05) = about 12.7 months
```

Plan the change before that date minus the lead time of the fix (procurement, a migration, a quota request).
