# Example: verify-record.md

A Tier 3 change whose lockout scenario is not proven by its test. The delta defines `CAP-auth-FR-3`, `CAP-auth-FR-4` and the scenarios S-1 to S-3. This is the text the verifier returns, and what the orchestrator writes verbatim.

```markdown
# Verify Record: PROJ-123-add-login

## Verdict

needs-rework

The test of the lockout scenario S-3 would pass without a lockout.

## Spec Coverage

| Requirement | Test that proves it | Result |
|---|---|---|
| CAP-auth-FR-3 | tests/test_login.py::test_signs_in_with_valid_password, tests/test_login.py::test_rejects_wrong_password | pass |
| CAP-auth-FR-4 | tests/test_login.py::test_locks_after_five_failures | pass, but it does not prove the requirement (issue 1) |

## Scenario Coverage

| Scenario | Test | Result |
|---|---|---|
| S-1 | tests/test_login.py::test_signs_in_with_valid_password | pass |
| S-2 | tests/test_login.py::test_rejects_wrong_password | pass |
| S-3 | tests/test_login.py::test_locks_after_five_failures | pass; it asserts the 401 of the sixth attempt, not the lock (issue 1) |

## Issues Found

| # | Severity | path:line | Impact | Suggested fix |
|---|---|---|---|---|
| 1 | High | tests/test_login.py:57 | S-3 is not proven: the test passes even if the account never locks | After five failures, assert that the right password is rejected too |
| 2 | Medium | src/auth/login.py:31 | A debug print writes the user's email to the logs | Remove the print |

## Tests

- Command: `pytest -q`. Result: 48 passed, 0 failed.
- Pre-existing failures: none (the implementer's baseline: 44 passed, 0 failed).
- Lint: `ruff check .`, no findings. Build: none declared in `.exo/context.md`.
- Isolation: subagent in fresh context.

## Out-of-Scope Drift

None.

## Judgment Day Handoff

N/A

## Gate summary

<!-- exo-gate:contract_check -->

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| High | tests/test_login.py:57 | S-3 not proven by its test | S-3 |
| Medium | src/auth/login.py:31 | Personal data written to the logs | CWE-532, A09:2025 Security Logging and Alerting Failures |

Requires tech_lead approval: yes
Source: skill
```

## Notes on the example

- The Verdict section uses one verdict word only; the reason does not repeat the other two.
- Every scenario and requirement cited is defined in the delta, so `exo speclint <change-root>` passes.
- In Tier 4, Judgment Day Handoff would list, for example: `src/auth/login.py:40-75` (the lockout counter, the riskiest code), the brute-force risk of design.md's Risks & Mitigations, and anything the verifier could not check.
