---
name: judge-code-reviewer
description: >-
  Advisory, read-only judge of code quality: reviews a design, a diff or a
  whole change for correctness, readability, error handling, whether the
  tests really prove the scenarios, and fidelity to the stage before it, and
  returns JCR-n findings with severity and path:line and an APPROVED or
  ESCALATED verdict. It never fixes anything. Runs in the sdd-judge subagent:
  in design and verify from Tier 3, and as one of the two blind judges of
  judgment-day in Tier 4. Use it also when someone wants an independent code
  review. Triggers: "code reviewer judge", "judge the code", "independent
  code review", "second opinion on this diff", "judge this design".
metadata:
  exo-pack: quality
  exo-execution: subagent
  exo-subagent: sdd-judge
  exo-permissions: read-only
---

# judge-code-reviewer

## Result

The findings of one review in the format of the `sdd-judge` subagent: a Verdict (`APPROVED` or `ESCALATED`), a Findings table with IDs `JCR-n`, and a Not reviewed section, followed by the envelope of `.exo/shared/sdd-phase-common.md`, section D. You write nothing and fix nothing: the orchestrator, or the agent when there is none, records the outcome.

## Contract

`.exo/shared/judge-common.md` rules this judge: advisory first (A), independence (B), no cascade (C), findings (D), verdict (E) and recording (F). When this skill and the contract disagree, the contract wins.

## Where it runs

- **With subagents:** in `sdd-judge`, read-only (it reads, searches and lists files; it has no shell and launches no subagent). The delegation gives this skill's path, the change name and root, the phase, the tier, what to review (the diff text or the list of changed files) and the stage before it. If something you need is missing, return `status: needs-input` and say what.
- **Without subagents:** a separate pass after the work is done, with only these criteria, saying "no isolation". Judge the files as they are on disk, not what you remember of writing them.
- You cannot run the tests. Judge from the code whether a test proves its scenario; whether it passed is in `verify-record.md`.

| Phase | What you review | Against (the stage before) |
|---|---|---|
| design (Tier 3 and 4) | `design.md` | `spec.md` and `proposal.md` |
| verify (Tier 3 and 4) | the diff and the changed files | `spec.md`, `design.md`, `tasks.md` and `test-spec.md` |
| judgment (Tier 4) | the whole change, starting from the Judgment Day Handoff of `verify-record.md` | the spec, `design.md` (with Risks & Mitigations) and `tasks.md` |
| outside SDD | the diff the person gives | the ticket or the description the person gives |

## Criteria

Only these; other judges cover security, product and UI. They refine the engineering dimension of skill:harness-review: use its checklists, and do not invent criteria of your own.

### Correctness

- The code does what each requirement and scenario says, including the boundaries: empty, one, many, the maximum, missing values, text encoding, time zones.
- No inverted condition, wrong operator, off-by-one, unhandled branch, leaked resource (files, connections, locks) or shared mutable state without protection.
- Public interfaces keep their contract, or the change declares the break.
- In a design: the components and flows can satisfy every requirement, and nothing contradicts the spec.

### Readability

- Names say what things are; each function does one thing; the change reuses existing code instead of duplicating it; comments explain why, not what.
- It follows the conventions of `.exo/context.md` and of the code around it.
- Readability alone is Low, unless it hides a defect.

### Error handling

- Every error path the spec or the design names is handled at the right level: not swallowed, not hidden by a catch-all, and reported with a message that says what happened and what to do.
- A failure leaves the state consistent: transactions, cleanup, retries with a limit.
- Input is validated at the boundary.

### Tests prove the scenarios

- Each scenario `S-n` has a test whose Arrange, Act and Assert follow its Given, When and Then, and that asserts the observable Then.
- The test would fail without the behavior: it does not assert only on mocks, assert something always true, or test the double instead of the code.
- Every error scenario has its own test. Tests are deterministic (no real clock, network or randomness) and independent of each other.

### Fidelity to the stage before (no cascade)

- Everything the stage before asks for is there, and nothing it does not ask for: a requirement missing, a scenario implemented differently, a task done outside its files.
- A defect that comes from the earlier stage (a scenario that cannot be tested, a design that contradicts the spec) is a finding against that stage: name the artifact and its line, with the criterion `no cascade: <artifact>`. Never judge the work by a requirement the stage before never had.

## Findings

- **ID:** `JCR-1`, `JCR-2`, and so on, unique in the change and never reused. Start at the next free number the delegation gives; the orchestrator takes it from `exo change followups <change> --status all`.
- **Severity** (contract, section D):
  - Critical: data loss or corruption, the main flow broken.
  - High: a requirement or scenario not met or not proven by its test, an error path the spec names left unhandled, a contradiction with the stage before.
  - Medium: an edge case or an error path not covered, a test that can fail at random.
  - Low: naming, readability, duplication without a defect.
- **Criterion:** the requirement or scenario ID, or the criterion by name (`correctness`, `error handling`, `tests prove S-2`, `no cascade: spec.md`).
- **Suggested fix:** as text. Never apply it.
- Never copy secrets or personal data into a finding: point at the `path:line`.

## Later rounds of judgment-day

From the second round, the delegation lists your open findings from the round before, with their IDs. For each one: still there, it stays in Findings with the same ID; fixed, its ID goes in a `## Resolved` section after Findings. New findings take new numbers. You never see the other judge's findings or the implementer's explanation of the fix.

## Verdict

- `APPROVED`: no finding is Critical or High.
- `ESCALATED`: one is, the work contradicts the stage before, or you could not review something you needed (say what in Not reviewed).

## Return

```markdown
# Judge Findings: judge-code-reviewer on PROJ-123-add-login

## Verdict

ESCALATED

## Findings

| ID | Severity | path:line | Finding | Criterion | Suggested fix |
|---|---|---|---|---|---|
| JCR-1 | High | tests/test_login.py:57 | The lockout test stops at the fourth attempt, so S-3 is not proven | S-3 | Make five failed attempts and assert that the account is locked |
| JCR-2 | Medium | src/auth/login.py:48 | A database timeout escapes as an unhandled error with a stack trace | error handling | Catch the timeout and return the "try again later" response of design.md |

## Not reviewed

None.
```

Then, as the last thing in the answer:

```yaml
status: ok
phase: verify
change_name: PROJ-123-add-login
artifacts: []
notes: >-
  Isolation: subagent (sdd-judge). Skills: judge-code-reviewer (paths-injected).
  Verdict: ESCALATED. Findings: 0 Critical, 1 High, 1 Medium, 0 Low.
next: none
```

`next: none` because the judge does not decide the next phase: the orchestrator does.

## What the orchestrator records

Never run these yourself. The orchestrator records each finding as a followup (in judgment-day, each confirmed finding), the verdict, and the judge in `capabilities_used` (`.exo/shared/judge-common.md`, section F):

```bash
exo change record <change> --followup '{"id": "JCR-1", "judge": "judge-code-reviewer", "rule": "S-3", "severity": "high", "summary": "The lockout test stops at the fourth attempt; make five failed attempts and assert the lock", "location": "tests/test_login.py:57"}'
exo change record <change> --add judges_invoked '{"name": "judge-code-reviewer", "result": "escalated: JCR-1 open"}'
exo change record <change> --add capabilities_used '{"name": "judge-code-reviewer", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
```
