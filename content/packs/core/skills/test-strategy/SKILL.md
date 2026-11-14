---
name: test-strategy
description: >-
  Chooses the test levels a change needs, in proportion to its risk tier, and
  writes test-spec.md, mapping every requirement and every scenario of the spec
  delta to test cases with the exact command that runs each one. Applies strict
  TDD when the project declares it. Use it in the spec phase of Tier 2 and the
  tasks phase of Tier 3 and 4, or whenever someone asks how to test a change.
  Triggers: "test strategy", "test plan", "write the test spec", "what should
  we test", "which tests do we need", "how do we test this", "TDD".
metadata:
  exo-pack: core
  exo-execution: inline
---

# test-strategy

## Result

A `test-spec.md` in the change root, started from `.exo/shared/templates/test-spec.md`, in which every requirement (`CAP-<capability>-FR-n` or `CAP-<capability>-NFR-n`) and every scenario (`S-n`) of the delta `spec.md` has at least one test case `T-n`, with its level and the exact command that runs it. `exo speclint <change-root>` passes.

Outside an SDD change (someone asks how to test something), the same plan goes in the answer and no file is written.

## Who writes test-spec.md

| Tier | test-spec.md | Written in |
|---|---|---|
| 1 | not required | no file: skill:code-generation writes a test for each scenario |
| 2 | required | the spec phase: `sdd-spec`, with this skill |
| 3 and 4 | required | the tasks phase: `sdd-tasks`, with this skill |

This skill owns no phase (`.exo/shared/sdd-phase-common.md`, section C). It writes `test-spec.md` only inside the phase that owns it, and never edits `spec.md`, `design.md` or any other artifact. If the delta cannot be tested as written (a scenario without a clear Then, a requirement without scenarios), stop and return `status: needs-input` saying which one and why.

## Inputs

1. The delta `spec.md`: its ADDED, MODIFIED and REMOVED requirements and their scenarios.
2. In Tier 3 and 4, `design.md`, section Test Plan: test-spec.md details it and must not contradict it.
3. The tier: `exo change status <change> --json`.
4. `.exo/context.md`: the test commands (Commands) and whether strict TDD applies (Conventions).
5. The existing tests next to the code that changes: framework, layout, fixtures, naming. Follow them.

## Choose the levels

| Tier | Levels |
|---|---|
| 1 | Unit tests for the behavior that changes. For a bug, a regression test that fails before the fix. |
| 2 | A unit test for each scenario; integration tests where the change crosses a boundary the project owns (database, HTTP, files, queues). |
| 3 | Tier 2, plus contract tests for every public interface that changes (API, event, CLI) and the error and edge cases of each scenario. |
| 4 | Tier 3, plus a negative test for each risk in `design.md`, section Risks & Mitigations, and end-to-end tests of the critical path. |

- Use the lowest level that proves the scenario. Go up a level only when the behavior lives in the integration.
- Unit: one behavior, no I/O. Integration: the real collaborators the project owns (a test database, temporary files), with fakes only for third parties. End-to-end: through the user's entry point; few and stable.
- An NFR gets a measurable check (a time budget, a size limit, a log assertion). If it cannot be automated, use the level `manual`, with the steps and the reason.
- UI checks for accessibility belong to `accessibility-audit`, which the phase map loads when the change has UI.

## Write test-spec.md

Start from `.exo/shared/templates/test-spec.md` and fill its three sections:

- **Scope:** what is tested and at which levels; what is not tested, and why.
- **Test Cases:** one row per test case.
- **Traceability:** every requirement and scenario of the delta, with the test cases that cover it.

```markdown
## Test Cases

| ID | Covers | Level | Description | Command |
|---|---|---|---|---|
| T-1 | S-1, CAP-auth-FR-3 | unit | An employee email redirects to the identity provider | pytest tests/test_sso.py::test_redirects_employee |
| T-2 | S-2, CAP-auth-FR-3 | integration | The callback creates a session in the database | pytest tests/integration/test_sso_callback.py |
| T-3 | S-3, CAP-auth-FR-1 | unit | A non-employee email keeps the password form | pytest tests/test_login.py::test_password_form_for_guests |

## Traceability

| Spec item | Test cases |
|---|---|
| CAP-auth-FR-3 (added) | T-1, T-2 |
| CAP-auth-FR-1 (modified) | T-3; tests/test_login.py::test_login_page updated |
| CAP-auth-FR-2 (removed) | tests/test_login.py::test_remember_me deleted |
| S-1 | T-1 |
| S-2 | T-2 |
| S-3 | T-3 |
```

- **Full IDs:** write `CAP-auth-FR-3`, not `FR-3`. `exo speclint` checks that every full requirement ID and every `S-n` you cite exists in the delta or in the living specs; a short ID escapes that check.
- **Coverage:** every ADDED and MODIFIED requirement and every scenario has at least one test case. A scenario whose Then rejects or fails gets its own case for each error.
- **MODIFIED and REMOVED:** say which existing tests change, and which ones are deleted, so that nothing keeps asserting removed behavior.
- **Command:** the exact command that runs that case alone, built from the test command in `.exo/context.md`. Never a runner or a flag you did not see in the project. If `.exo/context.md` has no test command, take it from the CI config or the manifest scripts, run it once to confirm it, say that the wiki lacks it (a wiki update for the end of the change) and suggest skill:project-onboarding.
- **Names:** a test name says the behavior (`test_rejects_expired_token`) and follows the project's naming.
- **Data:** synthetic fixtures only; never secrets or production data.

## Good tests

- One behavior per test. Arrange, Act and Assert follow the Given, When and Then of the scenario.
- Deterministic: no real network, clock or randomness; inject them or fake them.
- They assert what can be observed (output, state, calls at the boundary), not private details.
- Test doubles only at the boundaries; never mock the code under test.
- Independent: each test sets up its own data and passes alone and in any order.
- Coverage follows from the scenarios and their error paths; it is not a percentage to reach.

## Strict TDD

When `.exo/context.md` declares strict TDD (the line `TDD: strict` under Conventions), or the person asks for it:

- order the test cases so that each one is written before the code it covers, and say in Scope that strict TDD applies;
- in apply, skill:code-generation writes each case first, runs it, and sees it fail for the expected reason (an assertion, not an import or syntax error) before it writes code.

Without that declaration, the tests still go with the code in the same task, and writing them first is recommended.

## Check

```bash
exo speclint <change-root>
```

- It passes when `test-spec.md` has its three sections with content and every requirement ID and scenario it cites exists.
- Then check what speclint does not: every requirement and scenario of the delta appears in Traceability, and, in Tier 3 and 4, the cases agree with the Test Plan of `design.md`.

Record this skill in the change's AI Usage Record (skill:ai-usage-record).
