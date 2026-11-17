# R3 Reliability

**The question:** does the change do what it should, every time, and do the tests prove it?

Only behavior and its proof. Security exposure is R1's; how the change copes with failures around it is R4's.

## Behavior

- It does what the spec, the design or the person's description says, including the boundaries: empty, one, many, the maximum, missing or malformed values, text encoding, dates, time zones.
- No inverted condition, wrong operator, off-by-one, unhandled branch or unintended fall-through.
- Input is validated where it enters; invalid input gets a clear error instead of a crash or a silent wrong result.
- Errors are handled at the right level: not swallowed, not turned into a success, not hidden by a catch-all.
- A failure halfway leaves the data consistent: nothing half-written, nothing saved twice.
- Shared state and concurrency: no race between readers and writers, no lost update.
- Callers keep working: public functions keep their contract, and files or data written before the change still load.

## Determinism

- No hidden dependency on the real clock, randomness, the order of a set or a directory listing, the machine's locale or time zone. When the code needs the current time, it can be given one.

## Tests

- Each new or changed behavior has a test whose arrange, act and assert follow the scenario, and which asserts the observable outcome.
- The test would fail without the change: it does not assert only on mocks, or something always true.
- Error paths have their own tests.
- Tests are deterministic and independent of each other and of the environment.
- No test was deleted or weakened to make the change pass.

You cannot run the tests. Judge from the code whether they prove the behavior; say in Not reviewed what only a run can tell.

## Severity

- Critical: data loss or corruption; the main flow broken.
- High: a required behavior missing or wrong; an error turned into a silent success; a behavior with no test that proves it.
- Medium: an edge case or an error path not handled or not tested; a test that can fail at random.
- Low: a test that could be clearer or tighter.
