# R4 Resilience

**The question:** when something around the change fails, does it degrade safely, and will anyone know?

Only failure modes, observability, service levels and rollout. Whether the happy path works is R3's.

## Failure modes

Walk each dependency the change touches (network, database, files, queues, other services, the clock) through this table:

| When it is... | Look for |
|---|---|
| Slow | A timeout on every call; a sensible total time for the user |
| Down | A clear error or a fallback; no hang, no crash with a stack trace, no silent success |
| Flaky | Retries that are bounded, back off, and only repeat operations that are safe to repeat (idempotent, or with an idempotency key) |
| Returning garbage | The response is checked before it is used |
| Partially done | What happens to the work already done: rolled back, resumed, or reported |

## Resources

- Limits on sizes, counts, memory, connections, file handles and threads; inputs that can grow without bound are capped or streamed.
- Resources are released on every path, errors included.
- Under load, the change sheds or queues work instead of falling over.

## Observability

- Logs at the boundaries (calls out, requests in, failures) with enough context to act, and never secrets or personal data.
- Error messages say what failed and what to do.
- New paths that matter are measured: rate, errors and duration, or the project's equivalent.
- A request or a job can be followed across components (a correlation ID or a trace) when the project has that pattern.

## Service levels

- Whether the change touches something users feel: latency, availability, correctness of what they see.
- If the project has service level objectives, what the change does to them, and whether an alert would fire on the symptom users notice.

## Rollout and rollback

- A risky change can be turned off or released in stages (a flag, a configuration, a canary) when the project supports it.
- Data and format changes are backward compatible during the rollout (expand first, contract later); migrations can be reversed or are safe to run twice.
- Configuration has safe defaults and is checked at startup, not at the first request.

## Severity

- Critical: a failure of a dependency corrupts data or takes down more than the change.
- High: a call that can hang forever; an error turned into a silent success; a migration with no way back.
- Medium: a retry without a limit or backoff; a failure that is not logged; a missing metric on a path that matters.
- Low: log wording, extra context that would help.
