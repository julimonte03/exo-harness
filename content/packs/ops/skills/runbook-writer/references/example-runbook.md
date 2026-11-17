# Example runbook (synthetic)

A complete runbook for an invented service, to show the level of detail. Names, thresholds and commands are examples; a real runbook takes them from the project.

```markdown
# Runbook: OrdersQueueBacklog

- **Service:** orders-worker
- **Owner:** orders team
- **Alert:** `OrdersQueueBacklog`: messages waiting in the `orders` queue above 5,000 for 10 minutes
- **Dashboards:** "Orders pipeline" (queue depth, consumer rate, worker errors)
- **Last tested:** 2026-02-10, GameDay in staging (consumers paused for 15 minutes)
- **Last updated:** 2026-02-11

## What it means

Orders are accepted but not processed. Customers see "order received" and no confirmation email; warehouse picking is delayed.

## Impact and urgency

- All new orders are delayed; none are lost while the queue keeps them (retention: 4 days).
- Suggested severity: SEV3; SEV2 if the backlog is above 50,000 or growing for 30 minutes.
- At the usual evening rate the backlog grows by about 3,000 messages every 10 minutes.

## First checks (5 minutes)

1. Consumers running: `kubectl get deploy orders-worker -n <namespace>` (read-only). Expected: READY equals the desired replicas.
2. Worker errors: dashboard "Orders pipeline", panel "Worker errors per minute". Expected: under 5 per minute.
3. Recent deploys: the deploy pipeline's history for orders-worker in the last hour.

## Diagnosis

1. Are the worker pods ready?
   - No, some or all are crash-looping: go to M1.
   - Yes: go to 2.
2. Are workers logging errors on most messages?
   - Yes, and a deploy finished in the last hour: go to M2.
   - Yes, errors are timeouts to the inventory service: escalate to the inventory rotation, then M3.
   - No: go to 3.
3. Is the consumer rate normal but the incoming rate much higher (a traffic peak)?
   - Yes: go to M3.
   - No: escalate to the orders team rotation.

## Mitigations

### M1. Recover crash-looping workers [changes state]

Run only with the incident commander's go-ahead.

1. Read why they crash: `kubectl logs deploy/orders-worker -n <namespace> --previous --tail=50` (read-only).
   Expected: the last error before the restart. An out-of-memory kill shows in `kubectl describe pod <pod> -n <namespace>` as `OOMKilled`.
2. If the cause is a bad release: go to M2. If it is memory: go to M3 and escalate to the orders team.
3. If the cause is unknown and only some pods crash, restart them: `kubectl rollout restart deploy/orders-worker -n <namespace>`
   Expected: new pods READY within 3 minutes.
4. Verify: consumer rate above the incoming rate on the dashboard within 10 minutes; the backlog starts falling.
Undo: no undo needed; a restart does not change configuration.

### M2. Roll back orders-worker [changes state]

Run only with the incident commander's go-ahead.

1. Use the deploy pipeline's "rollback" job for orders-worker, choosing the previous successful release.
   Expected: the job finishes green; pods run the previous image tag.
2. Verify: worker errors under 5 per minute within 10 minutes, and the backlog falls.
Undo: run the deploy job again with the newer release.

### M3. Scale out consumers [changes state]

Run only with the incident commander's go-ahead.

1. Scale with the project's scale job (pipeline "scale orders-worker"), from the current replicas to at most 12.
   Expected: new pods READY within 3 minutes.
   Do not go beyond 12: the inventory service allows 12 concurrent consumers.
2. Verify: the consumer rate rises in proportion and the backlog falls.
Undo: scale back to the usual replicas (6) once the backlog is under 500 for 30 minutes.

## Rollback

If a mitigation made things worse, undo it with its Undo line, in reverse order, and escalate.

## Escalation

| When | To | Hand over |
|---|---|---|
| No improvement 20 minutes after a mitigation | orders team rotation | Checks done, steps run, times |
| Errors are timeouts to inventory | inventory rotation | Error counts and the first error time |
| Backlog above 200,000 or older than 2 days | orders team lead and the incident commander | Risk of exceeding retention |

## Prerequisites

- Access: read access to the `<namespace>` namespace for the first checks; the deploy pipeline's rollback and scale jobs for mitigations.
- Credentials: the cluster login and the pipeline's own permissions; nothing to paste.

## Background

orders-worker consumes the `orders` queue, reserves stock in the inventory service and emits confirmation events. Each message takes about 120 ms. Past incidents: a release with a slow query (postmortem 2025-11-03), and an inventory outage (postmortem 2026-01-19).

## Open questions

- None.

## Changelog

| Date | Change | Why |
|---|---|---|
| 2026-02-11 | Added the limit of 12 consumers to M3 | GameDay showed inventory throttling at 14 |
```
