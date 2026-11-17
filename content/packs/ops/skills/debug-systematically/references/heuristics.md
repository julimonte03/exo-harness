# Debugging heuristics

Where to look first, by kind of symptom. Each heuristic is a hypothesis to test, never a conclusion.

## Flaky tests

| Cause | Sign | Test it by |
|---|---|---|
| Order dependence (shared state between tests) | Passes alone, fails in the suite | Run it alone, then with the test before it; randomize the order if the runner supports it |
| Time and dates | Fails near midnight, month end, DST change, or in another time zone | Freeze the clock in the test; run with `TZ=UTC` and another zone |
| Concurrency | Fails more often on a loaded machine or in CI | Run with more workers, or in a loop under load; look for shared mutable state and missing awaits |
| Network or external services | Timeouts, connection errors | Replace the dependency with a fake; check whether the test needs the network at all |
| Randomness | Fails for some seeds | Fix and print the seed; replay the failing one |
| Resource leaks | Fails after many tests (open files, ports, connections) | Run the suite in halves; watch open handles |
| Asynchronous waits | Fixed sleeps, polling with short timeouts | Replace sleeps with waiting on the condition |
| Floating point | Off by a tiny amount | Compare with a tolerance; check the sum order |

Measure the failure rate before and after any fix; a flaky test is fixed only when it stops failing over enough runs.

## Works here, fails there

Compare, one by one, what differs between the two places:

- runtime and dependency versions (the lockfile honored or not, a cached build);
- operating system, file system case sensitivity, path separators, line endings;
- environment variables and configuration files (compare names and non-secret values, never paste secrets);
- locale, encoding and time zone;
- data: a database with different rows, migrations not applied, a seed that differs;
- permissions, user, working directory;
- parallelism, CPU count, memory limits;
- network: proxies, DNS, blocked hosts, TLS certificates.

CI often runs with a clean cache, a different user, no TTY, UTC, and less memory. Reproduce those conditions locally before guessing.

## It worked yesterday

1. What changed since: commits (`git log --since=yesterday`), dependencies (lockfile diff), configuration, data, infrastructure, the clock (a date-based feature flag, a certificate, a license, a token that expired).
2. If a commit is the suspect, bisect (`references/bisect.md`).
3. If no commit changed, look outside the code: data, time, quotas, third parties.

## Wrong result, no error

- Check the inputs first: is the function getting what you think? Log or assert at the entry.
- Then the boundaries: serialization, unit conversions (cents and units, milliseconds and seconds), time zones, rounding, encoding, null versus empty, default values.
- Caches: stale entries, keys missing a dimension (user, locale, currency, tenant), invalidation that never runs.
- Off-by-one: ranges inclusive or exclusive, pagination, the first or the last element.
- Copies versus references: shared mutable defaults, objects modified after being cached.

## Errors that make no sense

- Read the exact message and search the code for it: who raises it, under which condition.
- The first error in the log, not the last; the deepest cause in the stack trace.
- A stale build or cache: clean the project's build output (with its own command) and rebuild before chasing a phantom.
- Two versions of a library on the path, or the code you are reading is not the code that runs (a different branch, an old container image, a cached artifact).

## Performance bugs

- Measure before changing anything: a profile, timings at the boundaries, query counts.
- N+1 queries, missing indexes, unbounded loops over data that grew, synchronous calls in a loop, locks held across I/O.
- Compare with a known-good version on the same data before blaming the environment.

## Heisenbugs (disappear when observed)

Adding logs or a debugger changes timing. Prefer low-overhead observation: counters, assertions that record instead of print, a ring buffer dumped on failure. Suspect races, uninitialized state, and optimizations that depend on timing.

## When you are stuck

- Re-read the problem statement: are you debugging the right thing?
- Write down what you know for sure and how you know it; one of those "facts" is often an assumption.
- Explain the problem step by step to someone, or in the answer: the gap shows up.
- Shrink the case further, or start the bisection from a different end.
- Ask the person for the one piece of information that would split the remaining hypotheses.
