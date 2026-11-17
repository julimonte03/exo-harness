# SLI menu

Every SLI is a ratio of good events to valid events. Pick the types that match what users of the journey care about; one or two per journey is usually enough.

## Types

| Kind of system | SLI | Good event | Valid event |
|---|---|---|---|
| Request and response (APIs, web) | Availability | A request answered without a server error | Every request, minus the exclusions |
| | Latency | A request answered faster than a threshold (for example 300 ms) | Every successful request, or every request |
| | Quality | A request answered without degradation (no fallback, full results) | Every request |
| Pipelines and batch jobs | Freshness | A read of data updated within a threshold (for example 15 minutes) | Every read; or a run that finished on time out of every scheduled run |
| | Correctness | An output record that passes validation against a known answer | Every record checked |
| | Coverage | An input record that was processed | Every input record received |
| Storage | Durability | An object that can be read back as written | Every object written |
| Streaming and queues | Processing latency | A message processed within a threshold after it was produced | Every message |

- **Latency thresholds,** not averages: "99% of requests under 300 ms" is an SLI; "average 120 ms" hides the slow tail users feel.
- **Two latency thresholds** are common: one for "fast enough" (for example 300 ms at 99%) and a looser one for "not broken" (for example 2 s at 99.9%).
- **Correctness** needs a source of truth: a known input with a known output (a probe), or a reconciliation job.

## Where to measure

| Point | Sees | Misses | Notes |
|---|---|---|---|
| Client (browser or app telemetry) | What users really get, network included | Users who never loaded the client | Noisy; needs sampling and privacy care |
| Load balancer or gateway | Every request that reached the system, with status and time | Failures before it (DNS, network), time in the client | Usually the best first choice |
| Server metrics | Requests the application handled | Requests dropped before the application (crashes, overload) | Easy; undercounts outages |
| Synthetic probes | Availability even with no traffic | Real user diversity | Good for low traffic and for correctness |
| Logs | Anything logged | Requests that were not logged | Fine when there are no metrics (log-analysis) |

Measure as close to the user as is reliable, and say what the chosen point misses.

## Exclusions to decide

- Health checks and readiness probes.
- Requests the client got wrong (most 4xx). Count 429 (rate limited) as bad if the limit is ours to raise; 499 or client disconnects depend on whether slowness caused them.
- Load tests and synthetic traffic, unless the SLI is built from probes.
- Planned maintenance windows, only if users were told in advance and the policy says so.

Write each exclusion in the SLO document with its reason.

## Example queries

Prometheus, availability over 5 minutes (adapt the metric and label names):

```text
sum(rate(http_requests_total{service="checkout", route="/confirm", code!~"5.."}[5m]))
/
sum(rate(http_requests_total{service="checkout", route="/confirm"}[5m]))
```

Prometheus, latency under 300 ms (the bucket boundary `le="0.3"` must exist in the histogram):

```text
sum(rate(http_request_duration_seconds_bucket{service="checkout", route="/confirm", le="0.3"}[5m]))
/
sum(rate(http_request_duration_seconds_count{service="checkout", route="/confirm"}[5m]))
```

Freshness of a table, as a probe that runs every minute and records whether the newest row is younger than 15 minutes:

```text
good = 1 if now() - max(updated_at) < 15 min else 0
SLI  = sum(good) / count(probes) over the window
```

From access logs, when there are no metrics (fields of the combined log format):

```bash
awk '$7 ~ /^\/checkout\/confirm/ { total++; if ($9 !~ /^5/) good++ } END { printf "%.4f%%\n", 100 * good / total }' access.log
```

## Dependencies set a ceiling

If a journey calls services A and B on every request, with no fallback, its availability is at most about A times B: two dependencies at 99.9% give at most about 99.8%. Either the target accepts that, or the design adds a fallback, a cache or a retry with a budget. Say which dependencies limit each SLO.
