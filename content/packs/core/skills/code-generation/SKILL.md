---
name: code-generation
description: >-
  Implements the frozen plan of a change, and only that plan: a test-first loop
  per scenario, the project's conventions and the stack router, secure-coding
  criteria and small diffs. Runs the tests with the exact command and ticks the
  tasks.md boxes; anything outside the plan becomes a follow-up note, not code.
  Use it in the apply phase of an SDD change, or when asked to implement an
  approved plan. Triggers: "implement the tasks", "apply the change", "write
  the code", "make the tests pass", "sdd apply", "implement this plan".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: write-code
---

# code-generation

## Result

Code and tests that do what the frozen plan says and nothing else. Every scenario in scope has a test that failed first and passes now, the test command from `.exo/context.md` passes, every finished task has its box ticked in `tasks.md`, and whatever came up outside the plan is a follow-up note, not code.

## The frozen plan

| Tier | The plan |
|---|---|
| 1 | `proposal.md` (Scope and Out of Scope), plus the scenarios of `spec.md` when the change alters behavior |
| 2 | `proposal.md`, with the delta `spec.md` and `test-spec.md` |
| 3 | `tasks.md`, with `spec.md`, `design.md` and `test-spec.md` as reference |

- Frozen means approved: start only when the person approved the plan or the orchestrator delegated the apply phase.
- Read the plan, the delta and `test-spec.md` in full before writing code.
- Write only the code and tests the plan calls for, and tick boxes in `tasks.md`. Never edit `proposal.md`, `spec.md`, `design.md`, `test-spec.md` or the text of the tasks (`.exo/shared/sdd-phase-common.md`, section C).
- If the plan is wrong or cannot be done as written (a file it does not mention has to change, a scenario contradicts the code, a test cannot be written as specified), stop and return `status: needs-input` with what is wrong and what you propose.

## Before the first line

1. **Skills.** The apply phase loads this skill with `secure-coding-baseline`, skill:work-unit-commits and the stack router (`.exo/shared/phase-skill-map.md`). Resolve each one as `.exo/shared/skill-resolver.md` says and read it in full.
2. **Secure coding.** `secure-coding-baseline` ships in the `security` pack. When it does not resolve, say `security/secure-coding-baseline not installed — applying inline criteria`, apply the criteria in Secure coding below, and record the degradation (skill:ai-usage-record).
3. **Stack router.** The router skill of the project's stack pack, when one is installed. Without it, follow the commands and conventions in `.exo/context.md`.
4. **Branch.** Never write on a protected branch (skill:branch-pr).
5. **Baseline.** Run the test command once before you change anything. Failures that exist before your change are pre-existing: write them down and do not fix them. If they stop you from working, return `status: blocked`.

## The loop

Go task by task in the order of `tasks.md` (Tier 3), or scenario by scenario of the scope (Tier 1 and 2). For each scenario:

1. **Red.** Write the test: the `T-n` of `test-spec.md` that covers the scenario or, in Tier 1, a test for it. Run it with its exact command. It must fail for the expected reason, an assertion, not an import or syntax error.
2. **Green.** Write the minimum code that makes it pass. Run it again.
3. **Refactor.** Clean up what you just wrote, with the tests green. Only your code, not the code around it.

When the task is done, run its tests and then the full test command, tick its box (`- [ ]` becomes `- [x]`), and commit the unit (skill:work-unit-commits).

With strict TDD (`.exo/context.md` declares `TDD: strict`, or the person asked for it), Red is mandatory for every scenario, and your report says that each new test failed first.

## How to write the code

- **Follow what is there.** Read the neighbouring code and follow its structure, naming, error handling, logging and test layout. The stack router and the Conventions of `.exo/context.md` win over your habits.
- **Reuse.** Use the project's helpers, components and libraries before writing new ones. Add a dependency only if the plan names it; otherwise it is a follow-up.
- **Small diffs.** Touch only the lines the task needs. No reformatting, renaming or reordering of code you did not change, and keep other people's `TODO`s.
- **Errors.** Handle the error cases the scenarios name, fail with a clear message, and never swallow an exception.
- **No leftovers.** No debug prints, commented-out code, skipped or focused tests.
- **Comments** say why, not what.

## Secure coding

Apply `secure-coding-baseline` when it is installed. Without it, apply its inline criteria from the last table of `.exo/shared/phase-skill-map.md` to every line you write:

- validate and encode untrusted input at the boundary;
- use parameterized queries;
- keep secrets out of code and logs: read them from the environment or the project's secret store, and never log tokens, passwords or personal data;
- check authorization on every entry point you add or change;
- fail closed: on an error or missing data, deny.

When logs, tickets or production data are going to the model, the apply phase also loads `prompt-hygiene`.

## Outside the plan

Whatever you notice that the plan does not cover (a bug nearby, a refactor, a missing check in other code, a dependency to update) is a follow-up, not code:

- do not implement it;
- list it under `Follow-ups:` in the envelope notes, with `path:line` and why it matters;
- if it blocks the plan, stop with `status: needs-input`.

## Tests

- Run them with the exact command from `test-spec.md` or `.exo/context.md`. Never a command you made up.
- Report the command, how many passed and failed, and the pre-existing failures.
- Never delete, skip or weaken a test to make it pass. If a case of `test-spec.md` cannot pass as specified, return `status: needs-input`.

## Report

The apply phase returns the envelope of `.exo/shared/sdd-phase-common.md`, section D. Its notes say the isolation, the skills and how each one resolved, the degradations, the test command with its result, and the follow-ups:

```text
Isolation: subagent. Skills: sdd-apply, code-generation (paths-injected), work-unit-commits (paths-injected),
secure-coding-baseline (none: security/secure-coding-baseline not installed — applying inline criteria).
Tests: pytest -q, 48 passed, 0 failed; each new test failed first (strict TDD).
Follow-ups: src/billing/totals.py:88 rounds before summing; outside the plan.
```
