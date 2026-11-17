# Load testing and readiness

## Before the test

- [ ] **Approval** from the owner of the target environment, with a time window. Production or a shared environment needs it explicitly, and the people on call there are informed.
- [ ] **Environment** production-like: same instance types, configuration and data volume where possible; differences written down.
- [ ] **Dependencies:** third parties are stubbed or their owners agreed to the load (a payment provider's sandbox has its own limits; never load a real payment flow).
- [ ] **Test data** synthetic: generated users, products and orders; no copies of customer data.
- [ ] **Observability:** dashboards for the bar (latency and errors per journey) and for saturation (CPU, memory, pools, queues, database), open during the run.
- [ ] **Abort conditions** written (below) and someone watching them.
- [ ] **Tool** already in the project; nothing installed for the test.

## Profiles

| Profile | Shape | Answers |
|---|---|---|
| Baseline | Steady at today's peak for 10 minutes | Does the environment behave like production? Compare with production metrics |
| Ramp | From 0 to the pessimistic multiple over 20 to 30 minutes | Where latency starts to rise; the first saturation point |
| Steady at expected | Steady at 1.0 times the expected peak for 30 minutes | Does the plan meet the bar at the expected load? |
| Steady at pessimistic | Steady at the pessimistic multiple for 15 to 30 minutes | Is there margin? |
| Spike | From the baseline to the peak in under a minute | Does autoscaling react in time? Do caches and pools cope with the burst? |
| Soak | The expected peak for several hours | Leaks: memory, connections, disk, log volume |

Use the journey mix of the scenario, with think time between steps for user-like traffic. An open model (arrivals per second, independent of response time) shows overload honestly; a closed model (a fixed number of virtual users) slows down with the system and hides it. Prefer the open model when the tool supports it.

## Pass and fail

Write them before the run, from the bar:

| Criterion | Example |
|---|---|
| Latency per journey | checkout p99 under 800 ms at the expected peak |
| Errors per journey | checkout errors under 0.1% |
| Saturation | no component above its target utilization; no pool exhausted; consumer lag stable |
| Autoscaling | new units ready before latency breaks the bar during the spike |

## Abort conditions

Stop the test at once when any holds, and say who can call it (anyone watching):

- error rate above 5% for 2 minutes, or any error on a system outside the test's scope;
- a shared dependency degrades for other users (a shared database, a shared cache, a third party);
- data integrity alarms, disk above 90%, or memory pressure killing processes in a shared cluster;
- the window ends.

Know the stop command before starting: the tool's stop, or killing the load generator.

## Tool commands

Use what the project already has; these are the usual forms. Point them at the test environment's address, never at production unless approved.

```bash
# k6 (script in JavaScript; thresholds in the script decide pass or fail)
k6 run --out json=<work>/k6-result.json loadtest/checkout.js

# Gatling (Maven or Gradle plugin, simulation class in the project)
./mvnw gatling:test -Dgatling.simulationClass=<package>.CheckoutSimulation

# Locust (headless)
locust -f loadtest/locustfile.py --headless -u 500 -r 50 --run-time 30m --host <test-environment-url>

# JMeter (non-GUI mode)
jmeter -n -t loadtest/checkout.jmx -l <work>/results.jtl -e -o <work>/report

# vegeta (open model: a constant rate)
echo "POST <test-environment-url>/checkout/confirm" | vegeta attack -rate=480 -duration=10m -body=loadtest/cart.json -header="Content-Type: application/json" | vegeta report

# hey (quick and simple)
hey -z 5m -q 10 -c 50 <test-environment-url>/search?q=shoes
```

A k6 skeleton for the scenario, with an open model and thresholds:

```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    checkout: {
      executor: 'ramping-arrival-rate',
      startRate: 120, timeUnit: '1s', preAllocatedVUs: 200, maxVUs: 1000,
      stages: [
        { target: 480, duration: '10m' },   // ramp to the expected peak
        { target: 480, duration: '30m' },   // steady
        { target: 720, duration: '5m' },    // step to the pessimistic multiple
        { target: 720, duration: '15m' },
      ],
    },
  },
  thresholds: {
    'http_req_duration{journey:checkout}': ['p(99)<800'],
    'http_req_failed{journey:checkout}': ['rate<0.001'],
  },
};

const BASE = __ENV.TARGET_URL; // the test environment, set by the person

export default function () {
  const res = http.post(`${BASE}/checkout/confirm`, JSON.stringify({ cart: '<synthetic-cart-id>' }), {
    headers: { 'Content-Type': 'application/json' },
    tags: { journey: 'checkout' },
  });
  check(res, { 'status is 200': (r) => r.status === 200 });
  // no sleep: the arrival-rate executor starts the iterations; a sleep only holds VUs
}
```

The load test script is code: inside an SDD change it is written in the apply phase when the plan lists it; outside one, put it where the project keeps load tests (for example `loadtest/`) when the person asks for it.

## Reading the results

- Find the load at which p99 latency starts to rise steeply: that is the practical capacity, not the point where errors appear.
- Match the first saturated resource with the model's order of saturation. A different first bottleneck means the model missed something: update it.
- Compare the environment with production at the baseline profile; scale the results if the environment is smaller, and say so.
- Repeat the test after each fix; one change between runs.

## Readiness checklist (go or no-go)

| Item | Owner | Date | Done |
|---|---|---|---|
| Scaling changes applied and verified (autoscaling limits, instance sizes) | | | |
| Quotas and third-party limits raised and confirmed in writing | | | |
| Pre-scaling scheduled for the event window, and scale-back scheduled after | | | |
| Load test passed at the pessimistic multiple | | | |
| Dashboards for the SLOs and saturation, shared with on-call | | | |
| Alerts on the SLOs (burn rate) active | | | |
| Runbooks for the likely failures, linked from the alerts | | | |
| Feature flags to shed optional load, tested | | | |
| On-call staffed and briefed for the event, escalation by role | | | |
| Rollback plan for every change made for the event | | | |
| Change freeze window agreed and announced | | | |

Go when every item is done or explicitly accepted as a risk by the service owner, with the reason written in the plan.
