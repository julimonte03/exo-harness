---
name: sdd-tasks
description: >-
  Turns an approved SDD design into the frozen implementation plan: tasks.md,
  an ordered checklist of small tasks that each name their files, tests and
  scenarios, with a size forecast against a budget of about 400 changed lines;
  and test-spec.md, the test cases and their traceability. A Tier 3 and 4
  phase that runs inline, after sdd-design and before sdd-apply. Use it when
  the person asks to plan or break down the work, write tasks.md or the test
  spec, estimate the size of a change, or runs /sdd-tasks, and when the
  orchestrator reaches the tasks phase.
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: tasks
  exo-permissions: write-specs
---

# sdd-tasks

## Result

- `<change-root>/tasks.md`: the plan `sdd-apply` implements, and nothing more. An ordered checklist of small tasks, each with the files it touches, its tests and the `S-n` it covers, plus a size forecast.
- `<change-root>/test-spec.md`, started from `.exo/shared/templates/test-spec.md` and written with `test-strategy`.
- `exo speclint <change-root>` passes and the person approved the plan.
- The phase ends with the envelope of `.exo/shared/sdd-phase-common.md`, section D, with `next: apply`.

## What it writes and what it never touches

- **Writes** only tasks.md and test-spec.md in the change root, plus their memory mirror in `hybrid` and `memory` persistence (section C).
- **Never touches** proposal.md, spec.md, design.md, the living specs or the code. If the design cannot be cut into tasks (a file missing from Modules / Files, a scenario without a test in the Test Plan), stop and return `status: needs-input`: the fix belongs to skill:sdd-design.

## Before you start

1. Run `exo change status <change> --json` for the tier, the phase and the artifacts. An unknown tier is Tier 4.
2. Tasks is a Tier 3 and 4 phase. In Tier 2 there is no tasks.md and `sdd-spec` writes test-spec.md; in Tier 1 neither exists. Say so if the person asks for this phase in those tiers.
3. design.md must exist and `exo speclint <change-root>` must pass.
4. Load the skills (section A): `test-strategy` (Required) and `parallel-dispatch` when two or more units are independent; at most 5, each `SKILL.md` read in full. Both ship in the `core` pack, which `sdd` requires: if one is missing, the installation is incomplete. Say so, suggest `exo doctor`, and return `status: blocked`.
5. Read proposal.md, spec.md, design.md (Modules / Files, Test Plan, Risks & Mitigations) and `.exo/context.md` (how to build and test, whether TDD is strict).

## Write tasks.md

```markdown
# Tasks: PROJ-123-add-login

## Forecast

About 260 changed lines (150 code, 110 tests) in 5 files: within the 400-line budget.

## Tasks

- [ ] 1. Reject empty or malformed login input
  - Files: src/auth/forms.py, tests/test_forms.py
  - Tests: tests/test_forms.py::test_rejects_empty_email
  - Covers: S-4 (CAP-auth-FR-3)
- [ ] 2. Sign in with a valid password
  - Files: src/auth/login.py, tests/test_login.py
  - Tests: tests/test_login.py::test_signs_in_with_valid_password, tests/test_login.py::test_rejects_wrong_password
  - Covers: S-1, S-2 (CAP-auth-FR-3)
```

- **Ordered.** Dependencies first: a task only uses what earlier tasks built. Number them `1.`, `2.`, and so on.
- **Small.** A task is one work unit: one behavior and its tests, small enough for one reviewable commit (`work-unit-commits`). Split a task that touches unrelated files or several groups of scenarios.
- **Named.** Every task names the files it creates or modifies (from Modules / Files), the tests that prove it (from the Test Plan), and the `S-n` and requirement IDs it covers. `sdd-apply` will not touch a file that no task names.
- **Tests first.** Each task starts with its tests. A task that cannot have a test (configuration, docs) says why.
- **Complete.** Every file in Modules / Files and every `S-n` of the delta appears in at least one task.
- **Boxes only on tasks.** The details are plain sub-bullets: `sdd-apply` ticks the boxes and `exo change status` counts them.
- **Nothing extra.** No task outside the design. A refactor or cleanup that seems needed is a question for the person: it goes into the design, or out of the change.

### Size forecast

1. Estimate the changed lines (added plus removed, code and tests) of each task and add them up.
2. If the whole change is expected to exceed about 400 changed lines, say so and propose one of two splits: smaller changes that each deliver something on their own (each one becomes its own change with `sdd-new`), or one change delivered as a chain of PRs (skill:chained-pr), with the cut points in the Forecast.
3. The person decides. Record the decision; if they keep a single change and a single PR, write the reason in the Forecast.

### Independent units

When two or more groups of tasks touch disjoint files, apply skill:parallel-dispatch: units under `### Unit A: <name>` headings inside `## Tasks`, numbering across units, and a plain `Depends on: Unit A` line under a unit that needs another. In apply, the same skill asks the person how to run them (in sequence, in parallel subagents, or handed out to people).

## Write test-spec.md

Follow `test-strategy` and the template's three sections:

| Section | What goes there |
|---|---|
| Scope | What is tested and at which levels (unit, integration, e2e), and what is not tested and why. |
| Test Cases | One row per test: `T-n`, the `S-n` and requirement IDs it covers, the level, a description, and the exact command that runs it (from `.exo/context.md`). |
| Traceability | Every requirement and every `S-n` of the delta, with the `T-n` that cover it. None is left without a test case. |

- Use the full requirement IDs (`CAP-auth-FR-3`): speclint checks every ID against the delta and the living specs.
- The test names match the Test Plan of design.md and the tasks.
- If test-spec.md already exists because `sdd-spec` wrote it while the change was Tier 2, complete it instead of starting over.

## Judge (Tier 4)

Run `judge-team` as its own read-only delegation to `sdd-judge`, with `## Skills to load before work` and its `SKILL.md` path, the change root, tasks.md and test-spec.md, the stage before it (spec.md and design.md), and the first free `JTEAM` ID (from `exo change followups <change> --status all`). When it is not installed, say `quality/judge-team not installed — applying inline criteria` and pass its criteria: tasks.md can be split among people without overlapping files, and each unit has its own tests. Without subagents, run it inline after writing the plan and say "no isolation".

Record each finding with `exo change record <change> --followup '<json>'` (`.exo/shared/judge-common.md`, section F) and show them to the person; fix the accepted ones in tasks.md and mark them with `--fixed <id>`; the dismissed ones go to `dismissed_followups` with their `id`.

## Check and approve

1. `exo speclint <change-root>` passes (it checks test-spec.md and every ID it cites).
2. Show a short summary: the number of tasks, the forecast, the units, and anything the person must decide.
3. Approval follows `.exo/shared/sdd-phase-common.md`, section H. In interactive mode, ask "Adjust anything or continue?" and wait.
4. When the phase ends, tasks.md is the **frozen plan**: `sdd-apply` implements exactly what it says, and any change to the plan comes back to this skill.

## Record

Before the envelope (`.exo/shared/capability-attribution.md`); `activation` is `requested` when the person called this skill by name:

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-tasks", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "test-strategy", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"sdd-tasks"'
exo change record <change> --add skills_used '"test-strategy"'
exo change record <change> --add decisions '{"summary": "Plan approved: 5 tasks in 2 units, about 260 changed lines", "by": "human"}'
```

A decision to keep an oversized change goes in `decisions` too, with the person's reason as `rationale`.

In `hybrid` and `memory` persistence, save tasks.md and test-spec.md with the topic keys `sdd/<change-name>/tasks` and `sdd/<change-name>/test-spec`. In every mode, update the state artifact (`.exo/shared/memory-convention.md`), as skill:memory-protocol says.

## End

```yaml
status: ok
phase: tasks
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/tasks.md
    summary: 5 tasks in 2 units, about 260 changed lines
  - path: specs/PROJ-123-add-login/test-spec.md
    summary: 6 test cases covering 4 scenarios
notes: >-
  Isolation: inline. Skills: sdd-tasks (fallback-registry), test-strategy (fallback-registry),
  parallel-dispatch (fallback-registry).
next: apply
```

Then skill:sdd-apply implements the plan.
