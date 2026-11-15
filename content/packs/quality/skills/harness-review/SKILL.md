---
name: harness-review
description: >-
  Reviews a finished change in four dimensions: engineering (the diff against
  the spec and the tasks, a passing test for every scenario, nothing out of
  scope, no debug leftovers, tests and linters run with their exact
  commands), a light security pass, UX/UI, and accessibility (WCAG 2.2 AA)
  when the change has UI. Read-only apart from running the tests. From Tier 2
  it produces the code_review gate. Required in the verify phase from Tier 1,
  where sdd-verify loads it; use it also when someone asks for a full review
  of a branch or a PR before merging. Triggers: "harness review", "full
  review", "review the change", "review this branch", "is this ready to
  merge", "code review gate".
metadata:
  exo-pack: quality
  exo-execution: inline
  exo-phase: verify
  exo-permissions: read-only+tests
---

# harness-review

## Result

- Findings in four dimensions (engineering, security, UX/UI, accessibility), each with a severity, its `path:line`, the rule it breaks and a suggested fix as text, backed by tests that actually ran.
- When the tier has the `code_review` gate (`governance.gates` in `.exo/config.json`; by default from Tier 2): the full text of `<change-root>/gates/code_review.md`, started from `.exo/shared/templates/gate.md`, which passes `exo speclint`.
- Outside an SDD change: the same findings in the answer, with the gate text when the person wants one. No file is written.

## Where it runs

`sdd-verify` loads this skill as the Required skill of the verify phase (`.exo/shared/phase-skill-map.md`), so it runs wherever the verify runs:

| Situation | Runs in | Writes `gates/code_review.md` |
|---|---|---|
| Verify with subagents | `sdd-verifier`, in fresh context | the orchestrator, verbatim from the verifier's answer |
| Verify without subagents, or from `handoff.md` in a new session | the session that runs the verify | that session |
| A review the person asks for outside SDD | inline | nobody: the text goes in the answer |

Its findings feed `verify-record.md` (Issues Found, Tests, Out-of-Scope Drift), which `sdd-verify` writes. This skill owns only the `code_review` gate file. It never writes the `contract_check` summary of `verify-record.md`, nor the `security_review`, `threat_model` or `secure_coding_check` gates, which belong to the skills of the `security` pack.

## Permissions

- Read-only. Run only the test, lint and build commands of `.exo/context.md` or of the delegation, and read-only git (`git diff`, `git log`, `git show`, `git status`).
- Never edit, stage, stash, check out, reset or commit; no formatter or linter in fix mode, no dependency installs, no snapshot updates. If a check needs a change, report it as not done.
- In a read-only subagent, return the gate text in the answer; never write it.

## Inputs

1. The diff against the base (`git diff <base>...HEAD`, or the base the delegation names) and the changed files in full, not only their hunks.
2. The stage before: the proposal's Scope in Tier 1 and 2; `spec.md` and `test-spec.md` from Tier 2; `design.md` and `tasks.md` in Tier 3 and 4.
3. `.exo/context.md`: the test, lint and build commands, the conventions, and whether the project has UI.
4. The tier, from the delegation or from `exo change status <change> --json`.

Read in batches and take notes as you go. The detailed checklists of each dimension are in `references/dimensions.md`.

## 1. Engineering

- **Spec and scenarios:** every ADDED and MODIFIED requirement and every scenario `S-n` has a test that asserts its Then and passes. A REMOVED requirement leaves no test that still expects it. A test that would pass without the behavior proves nothing.
- **Tasks and scope:** every ticked box of `tasks.md` has its work in the diff (in Tier 1 and 2, the proposal's Scope). A hunk that no task or Scope item explains is drift: unrelated refactors, reformatting, files of another change, dependencies the plan does not name.
- **Leftovers:** debug prints and logs, breakpoints, commented-out code, focused or skipped tests without a reason, temporary files, hard-coded local paths.
- **Errors and edges:** the error paths that the spec and the design name are handled and tested.
- **Tests and linters, with the exact command:** run the test command, then the lint and the build when `.exo/context.md` has them. Write each exact command with its passed and failed counts. A failure is pre-existing only with evidence: the implementer's baseline in the delegation, or the same failure on the base branch in CI. Never switch branches to find out.

## 2. Security (light pass)

A quick pass over the diff, not a security review. The deep review is `security-code-review` (pack `security`), which writes the `security_review` gate when the tier has it (by default from Tier 3). Look for:

- secrets or personal data in code, tests, fixtures, logs or messages (`.exo/shared/data-protection.md`): point at `path:line`, never copy the value;
- untrusted input that reaches a query, a shell command, a file path, a template or a deserializer without validation or encoding;
- a new entry point without authentication or without an authorization check;
- error messages or logs that expose internals, tokens or personal data;
- a new or upgraded dependency: name it, so that the stack's dependency audit covers it.

Report each one with its OWASP ID when one applies (`OWASP A03:2021`), and say which parts need `security-code-review`. If that skill is not installed and the tier has the `security_review` gate, say that the gate will be missing and that `exo check` fails without it.

## 3. UX/UI

For every change a person uses: screens, and also command-line output, error messages and API responses.

- Consistent with the existing components, design tokens and patterns; no new visual style without the person's approval.
- Every state handled: loading, empty, error, success and partial results.
- Messages say what happened and what to do next; destructive actions ask for confirmation; no dead ends.
- Command-line tools and APIs keep their help text, exit codes and error formats consistent with the rest of the project.

Without a user-facing change, write `N/A: no user-facing change`.

## 4. Accessibility (WCAG 2.2 AA)

Only when the diff touches UI. Check the changed UI against WCAG 2.2 level AA, starting with the success criteria in `references/dimensions.md`: keyboard access, visible and unobscured focus, names and labels, contrast, text alternatives, target size, error identification and status messages. Each failure cites its criterion (`WCAG 2.2 SC 2.4.7`). A full audit is `accessibility-audit` (pack `frontend`), which the phase map adds when the diff touches UI. Without UI, write `N/A: no UI in the diff`.

## Severity and verdict

Severities as in `.exo/shared/judge-common.md`, section D: **Critical** (data loss, a security hole, the main flow broken), **High** (a requirement or scenario not met or not proven, a mitigation missing, failing tests), **Medium** (an edge case or error path, drift, leftovers that change behavior), **Low** (readability, naming, harmless leftovers).

- `APPROVED`: no finding is Critical or High.
- `ESCALATED`: one is, or a check that matters could not run (the tests, for example).

## The code_review gate

When the tier has the `code_review` gate, write its text from `.exo/shared/templates/gate.md`:

```markdown
# Gate: code_review

<!-- exo-gate:code_review -->

## Verdict

ESCALATED: S-3 is not proven by its test.

## Findings

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| High | tests/test_login.py:57 | The lockout test stops at the fourth attempt, so S-3 is not proven | S-3 |
| High | src/auth/login.py:31 | The user's email is written to the log | OWASP A09:2021, CWE-532 |
| Low | src/auth/login.py:12 | A debug print is left in | engineering: leftovers |

## Approval

Requires tech_lead approval: yes
Source: skill harness-review
```

- Keep the marker exactly as `<!-- exo-gate:code_review -->`, in a file named `code_review.md`.
- One row per finding of the four dimensions; a single row `| - | - | No findings | - |` when there are none.
- `Requires tech_lead approval: yes` when the verdict is `ESCALATED` or a Critical or High finding stays open; `no` otherwise.
- Cite only requirement and scenario IDs that the delta or the living specs define.
- Check it with `exo speclint <change-root>/gates/code_review.md`. A verify that runs again rewrites the gate.

A gate that is not `APPROVED` needs the `tech_lead` role: `exo check` warns about it, and `exo gate publish` publishes it with the other gates (`.exo/shared/ci-and-review.md`, section D).

## Record

A subagent lists `harness-review` and its resolution in its envelope notes, and the orchestrator records it. Inline, record it before the envelope of the verify (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "harness-review", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"harness-review"'
exo change record <change> --add gates '{"name": "code_review", "status": "fail", "detail": "ESCALATED: S-3 not proven"}'
```

`status` is `pass` for `APPROVED` and `fail` for `ESCALATED`. In Windows PowerShell 5.1, pass the JSON as `@<file>` (`.exo/shared/sdd-phase-common.md`, section I).

## Outside an SDD change

The base is the target branch, and the stage before is what the person gives: a ticket or the PR description. Without one, judge the scope against what the person says the change does, and ask when it is unclear. Give the findings, the commands you ran and the verdict in the answer, with the gate text when the person wants to paste it in the PR.
