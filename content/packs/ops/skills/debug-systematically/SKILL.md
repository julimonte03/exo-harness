---
name: debug-systematically
description: >-
  Debugs with a method instead of changing things until it works: reproduce
  the failure with one command, read the first real error, isolate the
  smallest failing case, test one hypothesis at a time, bisect the input, the
  code path or the history (git bisect included), add temporary
  instrumentation when the evidence is not enough, and confirm the cause
  before touching the fix. Then the smallest fix at the cause, with a test
  that fails without it, applied after the person approves the diff, and the
  instrumentation removed. Use it for any bug investigation: a failing or
  flaky test, a wrong result, an error nobody understands, a regression since
  a release, or something that only fails in CI. Triggers: "it doesn't
  work", "this is broken", "I don't understand why it fails", "debug this",
  "find the bug", "this test is flaky", "it worked yesterday", "regression
  since the last release", "only fails in CI", "why does this return".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-code
---

# debug-systematically

Guessing is slow. Each change made without a hypothesis adds noise, and a fix without a confirmed cause often hides the bug instead of removing it. This skill turns a bug hunt into a sequence of small experiments with a log.

## Result

- **A reproduction:** one command that shows the failure, and how often it fails when it is not deterministic.
- **The cause,** stated as a chain from the defect to the symptom, with the evidence that confirms it, including why it did not fail before or elsewhere.
- **A fix** at the cause, with a regression test that fails without it and passes with it. Applied once the person approves the diff, or proposed when they or the phase do not allow edits.
- **Verification:** the reproduction and the related tests pass, with the exact commands and their result; temporary instrumentation removed.
- **A debug log** in the answer: each hypothesis, its test, its result.

## When

- A test fails or flakes, a result is wrong, an error makes no sense, a regression appeared, or something works locally and fails in CI or in another environment.
- **Not first in a production incident with users affected:** mitigate with skill:incident-response, then debug.
- **Not for** a build or dependency failure in a JVM project when `java-build-resolver` (pack `java`) is installed; not for capacity limits under load (skill:capacity-planning).
- **Flaky browser or component tests** go first to the skill of their tool when it is installed: `playwright` (pack `frontend`) for end-to-end and browser tests, `react-testing` (pack `frontend`) for React component tests. They know the waits, locators and isolation of their tools; come back here when the cause is outside the test (the code under test, the data, the environment).

## Rules

- **No fix before the cause is confirmed.** If the person needs a quick workaround first, label it as a workaround, and keep debugging.
- **One change at a time,** and undo an experiment that did not help before trying the next one.
- **Never get green by hiding the failure:** no skipped or deleted tests, weakened assertions, catch-all handlers, blind retries, longer timeouts or sleeps that only make it rarer.
- **Your working tree is the person's.** Never run `git reset --hard`, `git clean`, `git checkout -- <path>` or `git stash` on your own. If you need a clean tree (bisect), ask the person how they want to set their changes aside.
- **Install nothing.** If a debugger, profiler or tool is missing, say which command you would run and continue with what the project has.
- **Instrumentation is temporary,** marked so you can find it (`DEBUG(<your-marker>)`), and removed before you finish.
- **No secrets or personal data in debug output.** Do not print tokens, passwords or customer records; mask what you paste (skill:prompt-hygiene; when the security pack is not installed: `security/prompt-hygiene not installed — applying inline criteria`, with the inline criteria of `.exo/shared/phase-skill-map.md`).
- **Inside an SDD change,** only the apply phase writes code, and only what the frozen plan covers. A fix outside the plan, a new dependency, or a change in behavior the spec does not describe is a question: return `status: needs-input` with the cause and the fix you propose. In other phases, report the cause and propose; do not edit.

## Steps

Keep the debug log as you go (format in Return). Heuristics for common kinds of bugs (flaky tests, "works on my machine", time, caching, concurrency) are in `references/heuristics.md`.

### 1. State the problem

One sentence with what was expected, what happened instead, where (environment, version, commit) and since when. If you cannot write it, ask the person the one question that is missing.

### 2. Reproduce

- Find the **smallest command** that shows the failure: one test (`pytest tests/test_orders.py::test_refund -x`), one request, one script with fixed input. Use the commands of `.exo/context.md` or the project's README.
- **Not deterministic?** Run it N times and write the failure rate (`for i in $(seq 1 30); do <command> || echo FAIL; done`). A fix is confirmed only when the rate drops to zero over enough runs.
- **Cannot reproduce?** List what differs between where it fails and where it does not: versions (runtime, dependencies, OS), configuration and environment variables (names only), data, time zone and locale, clock, concurrency, network, file system case. Ask for the logs of the failing run and read them with skill:log-analysis.

### 3. Read the evidence

- The **first** error, not the last one: later errors often cascade from it. In a stack trace, the deepest `Caused by:` and the first frame in the project's own code.
- The logs around the failure time, with request or trace IDs.
- What changed: `git log --oneline --since=<date>`, `git diff <last-good>..HEAD -- <paths>`, lockfile changes, configuration and environment changes, data changes.

### 4. Isolate

Shrink the case until every remaining piece matters:

- **Input:** remove fields, rows, steps; keep the failure.
- **Path:** split the flow (input, parsing, logic, storage, output) and check the intermediate values at each boundary. The bug lives between the last correct value and the first wrong one.
- **Components:** replace a dependency with a fake, turn off caches, run single-threaded, use an empty database. If the failure disappears, the removed piece is involved.

### 5. Hypothesize and test

- Write candidate causes, ranked by likelihood and by how cheap they are to test.
- For each, a **prediction** that would tell it apart from the others: "If the cache serves stale data, the second call returns the old price even after the update; with the cache off it returns the new one."
- Test one, write the result, keep or discard it. A surprising result is information: update the list.

### 6. Bisect

When you know a good state and a bad state, halve the space between them:

- **Input:** half the data set, then half of the failing half.
- **Code path:** comment out or short-circuit half of the suspect logic in a scratch copy, never in the person's work in progress.
- **History:** `git bisect` between a good commit and a bad one, automated with `git bisect run <command>` when the reproduction is a script that exits non-zero on failure. It needs a clean working tree and ends with `git bisect reset`, always.
- **Dependencies and configuration:** bisect versions in the lockfile, or configuration keys, the same way.

The full `git bisect` procedure, with scripts for flaky failures and skipped commits, is in `references/bisect.md`.

### 7. Instrument when the evidence is not enough

Targeted logs with a marker at the boundaries of step 4, assertions on the invariants you believe hold, the project's debugger, or tracing. Log shapes and IDs, never secrets or personal data. Each instrument answers one question; remove it once answered.

### 8. Confirm the cause

The cause is confirmed when all three hold:

1. **It explains every observation:** the symptom, why it did not fail before (or elsewhere), and why it is intermittent if it is.
2. **Toggle test:** with the cause present the reproduction fails; with the cause removed (in the smallest way, even a hack in a scratch copy) it passes.
3. **The chain is written:** "the price cache key omits the currency, so a EUR request after a USD one returns the USD price; it started when currency support shipped in v3.2".

If one does not hold, go back to step 5.

### 9. Fix

1. Write a **regression test** at the right level (skill:test-strategy) that fails for the confirmed cause. Run it and see it fail.
2. Make the **smallest fix at the cause,** not at the symptom: fix the cache key, not the caller that happened to notice.
3. Show the diff and wait for the person's approval before applying it, unless they already asked you to fix it. Inside the SDD apply phase, follow the plan (Rules).
4. Look for **siblings:** the same pattern elsewhere in the code. Report them; fix them only when the person agrees.

### 10. Verify and clean up

- Run the reproduction, the regression test and the related suite with the exact commands, and report the result. A flaky failure needs N clean runs.
- Remove every instrument (`git diff` and a search for your marker show none left).
- Save the bug with skill:memory-protocol: `exo mem save --type bugfix` with the symptom, the cause and the fix.

## Return

```markdown
Problem: refund total is wrong for EUR orders after a USD order in the same process (expected 40.00 EUR, got 43.50).
Reproduce: pytest tests/test_refunds.py::test_refund_eur_after_usd -x (fails 30/30)

| # | Hypothesis | Test | Result |
|---|---|---|---|
| 1 | Rounding in the refund calculator | Unit test with EUR only | passes: discarded |
| 2 | Price cache returns the USD entry | Cache disabled in the test | passes: cache involved |
| 3 | Cache key omits the currency | Log the key (DEBUG marker) | key is "sku-123" for both: confirmed |

Cause: src/pricing/cache.py:22 builds the key from the SKU only; since v3.2 added currencies, a EUR lookup after a USD one returns the USD price. Toggle test: with the currency in the key, the test passes.
Fix (applied after approval): src/pricing/cache.py:22 includes the currency in the key. Regression test: tests/test_refunds.py::test_refund_eur_after_usd.
Verify: pytest tests/test_refunds.py tests/test_pricing.py: 41 passed. Instrumentation removed.
Siblings: src/pricing/tax_cache.py:15 builds its key the same way (reported, not changed).
```

When you could not run something, say `not run` and why; never claim a pass you did not see.

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "debug-systematically", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"debug-systematically"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The failure reproduces with one command, or the answer says why it could not and what was compared.
- [ ] The cause passed the three checks of step 8 before any fix.
- [ ] The regression test failed before the fix and passes after it.
- [ ] No test, assertion or check was skipped or weakened; no temporary instrument is left.
- [ ] The person approved the diff, or the fix is marked as proposed; inside a change, nothing outside the plan.
- [ ] After any `git bisect`, `git bisect reset` ran and the working tree is as the person left it.
