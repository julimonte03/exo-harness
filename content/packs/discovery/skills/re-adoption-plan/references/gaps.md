# Adoption gaps and the backlog

## The checklist

Check every row. A row with no gap gets no item; say so in your report. The suggested tier is a hint for the person: `sdd-new` classifies each change with `risk-tiering`, and that tier is the one that counts.

| Gap | Where to look | It is a gap when | Typical item | Suggested tier |
|---|---|---|---|---|
| Test runner | `inventory.json` (`tests.frameworks`, `tests.files`), the manifests' test scripts, the CI steps | there is no test framework or no test files, or tests exist and nothing runs them | set up the runner and one test command | 1 |
| Test baseline | the test command from the manifests or the CI | it was never measured | measure it once, with the person's confirmation (SKILL.md, The test baseline); the result goes in the item, no change | none |
| Linters and formatters | `inventory.json` (`config_files`), the lint sections of the manifests (`pyproject.toml`, `package.json`), `.editorconfig`, the CI steps | none is configured, or CI does not run them | add the linter the stack uses, starting from today's code as the baseline | 1 |
| CI | `inventory.json` (`ci`) | there is no pipeline, it does not run the tests, or it does not run `exo check --base` | add the step of `.exo/shared/ci-and-review.md`, section B, and make the host require it | 2 |
| Git hooks | `git config --get core.hooksPath`, `.husky/`, `.pre-commit-config.yaml`; `exo doctor` says whether the engine's hooks are active | the engine's hooks are not active | activate `.exo/githooks/` or call them from the existing hook manager, as `.exo/shared/ci-and-review.md` says | 1 |
| CODEOWNERS | `CODEOWNERS`, `.github/CODEOWNERS`, `.gitlab/CODEOWNERS`, `docs/CODEOWNERS` | it is missing, or it does not give the specs folder and `.exo/` to the tech leads | add the lines that `exo codeowners` prints (it needs `governance.roles.tech_lead` in `.exo/config.json`) and require code-owner review on the host | 1 |
| Minimum docs | `README.md`, `CONTRIBUTING.md`, `.exo/context.md` | there is no README that says how to run and test the project, or the wiki lacks Stack, Commands, Conventions, Areas or Risks | complete the profile with skill:project-onboarding, and the README | 1 |
| Commit conventions | `git log --oneline -30`, a commit-lint configuration | the messages follow no convention | adopt Conventional Commits, which the engine's commit-msg hook checks | 1 |
| Secret ignores | `.gitignore`, `inventory.json` (`sensitive_files`: sensitive files that git tracks), `.exo/discovery/debt.md` | `.env` files, keys or dumps are not ignored, a sensitive file is tracked, or a credential is in the code | ignore them, and remove the tracked file or the credential; the person rotates what was exposed and decides whether to clean the history | 1, higher in a critical path |
| ADRs | `inventory.json` (`adr_dir`, `adr_dir_exists`), the recovered ADRs | there is no ADR folder, or the recovered ADRs are the only record of the decisions | adopt ADRs for new decisions with `architecture-decision-record` (pack `design`) | 1 |
| Agent configuration | the findings of `context-config-audit` | it reports rules that conflict with the engine, are stale, or hold secrets | align or remove that configuration | 1 |
| Characterization tests | the critical capabilities: their FRs without a scenario, the units' Tests sections | a critical capability has behavior that no test pins | tests that pin today's behavior, defects included, with no change to it | 2 |
| Blocking debt | `.exo/discovery/debt.md` | a debt item blocks the adoption (a credential, a critical path without tests) | the item's suggested action | as the item needs |

Every item cites its evidence like the specs do: `[Code] path:line`, `[Doc] path`, or the command and what it showed (`git log --oneline -30`: no convention in 30 commits).

## The backlog

`.exo/discovery/adoption-backlog.md`:

```markdown
# Adoption backlog

Gaps found when adopting this project (R6). Each item becomes an SDD change only when the person confirms it; `sdd-new` classifies its tier.

| ID | Item | Suggested tier | Status |
|---|---|---|---|
| ADOPT-1 | Characterization tests for room-booking | 2 | change `room-booking-characterization-tests` |
| ADOPT-2 | Remove the hard-coded calendar credential | 1 | confirmed |
| ADOPT-3 | Measure the test baseline | none | done: 2 passed, 0 failed, 0 skipped, 1 s |
| ADOPT-4 | Run exo check in CI | 2 | proposed |

## ADOPT-1: Characterization tests for room-booking

- **Gap:** four of the six FRs of room-booking have no test.
- **Evidence:** speclint warns that CAP-room-booking-FR-2, FR-4, FR-5 and FR-6 have no scenario; [Code] tests/test_booking.py:1-24
- **Why:** the person named room-booking critical, and it comes before ADOPT-2, which touches it.
- **Change:** tests that pin today's behavior of FR-2, FR-4, FR-5 and FR-6, without changing it.
- **Suggested tier:** 2
- **Status:** change `room-booking-characterization-tests`

## ADOPT-2: Remove the hard-coded calendar credential

- **Gap:** a credential for the calendar service is in the code.
- **Evidence:** [Code] src/rooms/calendar_sync.py:7; DEBT-1
- **Why:** anyone with the repository can use it. The person already rotated it.
- **Change:** read the credential from the environment and remove it from the code.
- **Suggested tier:** 1
- **Status:** confirmed
```

- **IDs:** `ADOPT-<n>`, never reused. A declined item stays, with its reason.
- **Status:** `proposed`, `confirmed`, `change <name>` once `sdd-new` created it, `declined: <reason>`, or `done: <result>` for an item that needs no change, such as the test baseline.
- **Order:** characterization tests of critical capabilities before any other item that touches them.
