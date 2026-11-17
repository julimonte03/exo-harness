---
name: sdd-apply
description: >-
  Implements an SDD change exactly as its frozen plan says, tests first: the
  tasks in tasks.md in Tier 3 and 4, or the proposal (with the spec delta and
  test-spec.md when they exist) in Tier 1 and 2. Writes the code and the
  tests, ticks the task boxes, commits each work unit and runs the tests with
  the project's exact command. Runs in the sdd-implementer subagent, or inline
  without subagents. Use it when the plan is approved and the person asks to
  implement, apply, code or build the change, or runs /sdd-apply, when the
  orchestrator reaches the apply phase, and to fix a needs-rework verdict.
metadata:
  exo-pack: sdd
  exo-execution: subagent
  exo-subagent: sdd-implementer
  exo-phase: apply
  exo-permissions: write-code
---

# sdd-apply

## Result

- Code and tests that do what the frozen plan says, and nothing else.
- Each work unit committed and, in Tier 3 and 4, every finished task ticked in tasks.md.
- The tests run with the project's exact command, with no new failures.
- When the tier's gates (`governance.gates`) include `secure_coding_check` (Tier 4 by default): after the last task, the gate of `secure-coding-baseline` over the full diff. In `sdd-implementer`, return its full text before the envelope and the orchestrator writes `<change-root>/gates/secure_coding_check.md`; inline, write it yourself.
- The envelope of `.exo/shared/sdd-phase-common.md`, section D, listing the files changed and the test results, with `next: verify`.

## Who runs it

- **With subagents:** the orchestrator delegates to `sdd-implementer` (section G). The prompt starts with `## Skills to load before work` (this `SKILL.md` and the apply skills) and gives the change name, the change root, the tier, the plan, the test command and what to return.
- **Without subagents:** run it inline, in the same session, with the same steps, and write `Isolation: no isolation (inline)` in the notes (`.exo/shared/agent-capabilities.md`).
- **One unit of a parallel plan:** when skill:parallel-dispatch delegates a single unit with its own worktree folder, implement only that unit's tasks, there.
- **Rework:** after a `needs-rework` verdict, the input is what the person accepted from verify-record.md (Issues Found, Out-of-Scope Drift) and from the judges' findings. Fix it only inside the plan; then the change goes to verify again.

## The frozen plan

| Tier | The plan |
|---|---|
| 3 and 4 | tasks.md, approved in `sdd-tasks`: the files, tests and scenarios of each task |
| 2 | the proposal's Scope and Out of Scope, spec.md and test-spec.md |
| 1 | the proposal's Scope and Out of Scope; spec.md when the change alters behavior |

With the SPDD overlay, `canvas.md` joins the plan at any tier: the orchestrator's session writes it and asks for its approval before apply (in Tier 1 and 2 too), and skill:prompt-code-sync holds each task to it.

## What it writes and what it never touches

Permissions are denied by default (section G).

- **Writes:** the code and test files the plan names, and the boxes of tasks.md (only the box: never reword, reorder or add tasks). With the SPDD overlay, canvas.md only through skill:prompt-code-sync, under its rules.
- **Never touches:** proposal.md, spec.md, design.md, test-spec.md, verify-record.md, the living specs, the engine files under `.exo/`, or the AI Usage Record by hand. Nor anything else outside the plan: dependencies and lockfiles it does not name, CI, configuration.

## Load the skills

Section A, with these skills (`.exo/shared/phase-skill-map.md`, row apply), each `SKILL.md` read in full:

- **Required:** `code-generation`, `secure-coding-baseline`, `work-unit-commits`, and the stack router. Without a stack router, follow the commands and conventions in `.exo/context.md`.
- **Conditional:** `pre-commit-review` before each commit; `prompt-hygiene` when logs, tickets or production data go to the model; `frontend-design` when the change touches UI; skill:prompt-code-sync when the change has `canvas.md` (before each task it reads the Operations and Safeguards the task implements, and keeps canvas and code in sync; in `sdd-implementer` it never edits canvas.md, and the edit comes back in the envelope); skill:parallel-dispatch when tasks.md has two or more units (`### Unit A:`), to run them in the mode the person picks.
- **Degraded:** a skill from a pack that is not installed degrades as `.exo/shared/skill-resolver.md` says. For example: `security/secure-coding-baseline not installed — applying inline criteria`, then validate and encode untrusted input at the boundary, use parameterized queries, keep secrets out of code and logs, check authorization on every entry point and fail closed.
- `code-generation` and `work-unit-commits` ship in `core`, which `sdd` requires. If one is missing, the installation is incomplete: say so, suggest `exo doctor`, and return `status: blocked`.

## Before the first task

1. **Branch.** Run `git status` and `git branch --show-current`. On a protected branch (`governance.protected_branches` in `.exo/config.json`), write nothing and return `status: blocked`: the branch is chosen when the change starts (`.exo/shared/project-wiki-guard.md`). Uncommitted changes that are not part of this change mean `needs-input`.
2. **Test command.** Take the exact command from the delegation, from `.exo/context.md` or from the Command column of test-spec.md. If there is none, return `needs-input`: never guess one.
3. **Baseline.** Run the test command once before changing anything and keep the failures: they are pre-existing, and the verify needs to know them.
4. **TDD mode.** Strict when `.exo/context.md` declares strict TDD: no production code without a failing test first, in every task. Otherwise, write the tests first wherever the project can run them.

## For each task, in order

1. Read the task: its files, its tests and its scenarios. Read those files and only what you need around them.
2. **Red.** Write the task's tests for its scenarios and run them: they must fail, for the expected reason. In strict TDD, keep the failing line as evidence for the notes.
3. **Green.** Write the least code that makes them pass, only in the task's files, following `code-generation`, the secure coding criteria and the stack's conventions.
4. Run the full test command: no failure that the baseline did not have.
5. Tick the box: `- [ ] 2.` becomes `- [x] 2.`.
6. Commit the work unit as `work-unit-commits` says: Conventional Commits, with the ticket when the project has one. Never push, never use `--no-verify`, never rewrite history.

In Tier 1 and 2 there are no boxes: the work units come from the Scope of the proposal, each with its tests.

### When to stop

- A task needs a file, a dependency or a behavior the plan does not name: stop before writing it and return `needs-input` with what is needed and why.
- A test fails and the fix is outside the task: stop and return `needs-input`, or `blocked` when nothing in the change can fix it, with the failing output.
- The plan contradicts the code (a function that does not exist, a design that cannot work): return `needs-input`. The fix belongs to `sdd-design` or `sdd-tasks`.

## Nothing outside the plan

Whatever you notice and the plan does not cover (a nearby bug, a refactor, a missing test elsewhere) is a **follow-up**, not a change. List each one in the notes with `path:line` and why it matters; the orchestrator shows them to the person.

Send a `fitness_signal` in the envelope when the evidence contradicts the tier: the code handles sensitive data or money, the module is more critical than assessed, the change touches more files than the forecast, or the area has no tests. Give the dimension, the evidence with `path:line` and the suggested score. Only the orchestrator re-classifies the tier.

## Record

- **In a subagent:** report how you resolved each skill in the notes (`.exo/shared/skill-resolver.md`); the orchestrator copies it into the AI Usage Record and adds `sdd-implementer`.
- **Inline:** record it yourself before the envelope (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-apply", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "secure-coding-baseline", "type": "skill", "activation": "auto", "resolution": "none", "note": "security/secure-coding-baseline not installed — applying inline criteria"}'
exo change record <change> --add skills_used '"sdd-apply"'
exo change record <change> --add skills_used '"code-generation"'
exo change record <change> --add skills_used '"work-unit-commits"'
```

Bugs you fixed and conventions you found go to memory as skill:memory-protocol says; in a subagent, put them in the notes for the orchestrator to save. In every mode the state artifact is updated when the phase ends (`.exo/shared/memory-convention.md`).

## End

```yaml
status: ok
phase: apply
change_name: PROJ-123-add-login
artifacts:
  - path: src/auth/login.py
    summary: password check and lockout (tasks 2 and 3)
  - path: tests/test_login.py
    summary: 4 tests for S-1, S-2 and S-3
  - path: specs/PROJ-123-add-login/tasks.md
    summary: 5 of 5 boxes ticked
notes: >-
  Isolation: subagent. Skills: sdd-apply (paths-injected), code-generation (paths-injected),
  work-unit-commits (paths-injected), secure-coding-baseline (none: security/secure-coding-baseline
  not installed — applying inline criteria). TDD: strict, red then green in every task.
  Tests: `pytest -q`, 48 passed, 0 failed; pre-existing failures: none (baseline 44 passed).
  Commits: 5. Follow-ups: src/auth/session.py:88 never expires remember-me tokens.
next: verify
```

Then skill:sdd-verify checks the change in a fresh context.
