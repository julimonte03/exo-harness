---
name: parallel-dispatch
description: >-
  Coordinates the implementation of an approved plan whose tasks.md groups
  the work into two or more units (### Unit A: ...). It always starts by
  asking the person how to run them: sequentially inline, in parallel with
  one sdd-implementer subagent per unit in waves built from a dependency
  graph (declared dependencies and files the units share), or split among
  people as work items. Then it integrates the finished units in order on the
  change's branch, runs the tests after each integration, and stops at the
  first conflict or failure. In the tasks phase it checks that the units are
  really independent. Use it when a frozen plan has several units and the
  person wants them implemented at the same time, by subagents or by several
  developers, or asks how to split the work. Triggers: "run the units in
  parallel", "implement the plan in parallel", "split the work between
  agents", "dispatch the units", "divide the tasks among the team", "work on
  both units at once".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: read-write
---

# parallel-dispatch

## Result

- The person chose how to run the units, and the choice is recorded.
- **Sequential or parallel:** every unit implemented as `sdd-apply` says and integrated on the change's branch in the order of the dependency graph, with the test command green after each integration and every box of tasks.md ticked. Or a stop at the first conflict or failure, with `status: needs-input` and exactly what happened.
- **Split among people:** one work item per unit, ready to create in the tracker, with its dependencies; later, the developers' branches integrated in the same order and with the same checks.
- A summary table of the units, and the apply envelope of `.exo/shared/sdd-phase-common.md`, section D.

## When

- **Tasks phase,** Conditional when two or more units are independent (`.exo/shared/phase-skill-map.md`): `sdd-tasks` loads it to check the units (next section).
- **Apply,** once the plan is approved: coordinate the units, from the orchestrator's session.
- **On request:** "run these units in parallel", "split this among the team".
- **Not for:** a plan with a single unit, or whose tasks all touch the same files (plain `sdd-apply`); a plan not approved yet (back to `sdd-tasks`); Tier 1 and 2, which have no tasks.md.

## In the tasks phase

`sdd-tasks` owns tasks.md; this skill gives it the checks for units:

- Units are `### Unit <letter>: <name>` headings inside `## Tasks`, and the task numbers continue across units.
- **Disjoint files:** two units never name the same file, tests and fixtures included.
- **Dependencies:** a unit that needs what another builds says so in a plain line under its heading, `Depends on: Unit A`, with no box.
- **Shared files** that cannot be split (a lockfile or package manifest, a route or plugin registry, numbered migrations, package exports such as `__init__.py` or `index.ts`, snapshots, generated files): keep the tasks that touch one of them in a single unit, or make the other units depend on it.
- **Own tests:** each unit has tests of its own and passes the test command without the others.
- Units that fail a check are not independent: say so, and `sdd-tasks` merges them or orders them with `Depends on`.
- In this phase, stop after the checks: the mode is asked when apply starts, on the approved plan.

```markdown
## Tasks

### Unit A: Coupon rules

- [ ] 1. Apply a percentage coupon to a cart total
  - Files: src/coupons/rules.py, tests/test_rules.py
  - Tests: tests/test_rules.py::test_percentage_off_total
  - Covers: S-1 (CAP-coupons-FR-1)

### Unit B: Coupon storage

- [ ] 2. Load a coupon by code and reject expired ones
  - Files: src/coupons/store.py, tests/test_coupon_store.py
  - Tests: tests/test_coupon_store.py::test_rejects_expired_code
  - Covers: S-3 (CAP-coupons-FR-2)

### Unit C: Checkout endpoint

Depends on: Unit A, Unit B

- [ ] 3. Accept a coupon code at checkout
  - Files: src/api/checkout.py, tests/test_checkout.py
  - Tests: tests/test_checkout.py::test_checkout_with_coupon, tests/test_checkout.py::test_checkout_with_expired_coupon
  - Covers: S-2, S-4 (CAP-coupons-FR-1, CAP-coupons-FR-2)
```

## Read the plan

1. `exo change status <change> --json`: the tier, the phase and the task count. The tasks phase must be done: tasks.md is the frozen plan.
2. Read tasks.md, design.md (Modules / Files, Sequence Of Operations) and test-spec.md. Change nothing yet.

## Build the graph

1. **Nodes:** one per unit, with its tasks, files and tests.
2. **Edges,** from the unit that must come first:
   - each `Depends on` line;
   - a unit that uses a module, a function or a field another unit creates (Modules / Files, Sequence Of Operations), even if undeclared: add the edge and tell the person;
   - two units that name the same file or the same shared file: they cannot run at the same time; add an edge in plan order and tell the person the plan overstates the independence.
3. **A cycle** means the plan is wrong: stop with `needs-input` for `sdd-tasks`.
4. **Waves:** wave 1 holds the units with no incoming edge; each later wave, the units whose dependencies are all in earlier waves. Inside a wave, keep plan order. Keep a wave to at most four units so the integration stays reviewable.
5. **Integration order:** wave by wave, plan order inside each wave.

Show it before asking anything:

```text
Units of PROJ-123-add-coupons: 3 units, 3 tasks, about 280 changed lines

| Unit | Tasks | Files | Depends on | Wave |
|---|---|---|---|---|
| A: Coupon rules | 1 | src/coupons/rules.py, tests/test_rules.py | - | 1 |
| B: Coupon storage | 2 | src/coupons/store.py, tests/test_coupon_store.py | - | 1 |
| C: Checkout endpoint | 3 | src/api/checkout.py, tests/test_checkout.py | A, B | 2 |

Shared files: none besides the boxes of tasks.md.
Integration order: A, B, C.
```

## Ask the mode

Always ask before changing anything, in one message, with the graph above:

> How do you want to run the 3 units of `PROJ-123-add-coupons`?
> 1. **Sequential, inline:** one unit after the other in this session, in the order A, B, C.
> 2. **Parallel, with subagents:** one `sdd-implementer` per unit, each in its own worktree, in waves (A and B together, then C), integrated in order with the tests after each one.
> 3. **Split among people:** one work item per unit for your tracker; each developer works on a branch of their own and the branches are integrated in the same order.

- If the person already chose in this conversation ("run them in parallel"), show the graph and confirm instead of asking again.
- Parallel needs subagents (`.exo/shared/agent-capabilities.md`). Without them, offer options 1 and 3 and say why.
- In an unattended run (`sdd.mode: auto`) with nobody to answer, take option 1 and say so in the envelope notes.
- Record the choice as a decision with `"by": "human"` (Record).

## Before running (modes 1 and 2)

1. `git status` and `git branch --show-current`: you are on the change's branch, it is not protected (`governance.protected_branches` in `.exo/config.json`), and nothing uncommitted is outside this change. Otherwise stop with `needs-input`.
2. **Parallel only:** worktrees see committed files only. If the change root (tasks.md and the other artifacts) is not committed, commit it first as skill:work-unit-commits says, once the person agrees.
3. The exact test command, from `.exo/context.md` or the Command column of test-spec.md. Without one, `needs-input`: never guess it.
4. A baseline run of the test command, so later failures can be told apart from pre-existing ones.

## Mode 1: sequential, inline

Run `sdd-apply` inline for each unit in integration order, with its tests first and one commit per task (skill:work-unit-commits). After each unit, run the full test command and show one line: "Unit A done: 1 task, 1 commit, 42 tests passed." In interactive mode, ask "Continue with Unit B?" before the next one.

## Mode 2: parallel, with subagents

The commands, the delegation prompt and the recovery steps are in `references/parallel-mode.md`.

1. **A worktree per unit** of the wave, each on its own branch from the change branch's current commit: `git worktree add <folder> -b <change-branch>-unit-<letter>`, with the folder outside the project. If your agent gives each subagent an isolated worktree of its own, use that instead.
2. **Delegate every unit of the wave at once,** each to its own `sdd-implementer`, with the prompt of the reference: the skills to load as exact paths, the change, only that unit's tasks, its worktree folder, the test command and the baseline. The implementer touches only its unit's files and boxes, commits each task in its worktree, and never pushes.
3. **Wait for the whole wave,** then integrate its units (Integrate in order). Units that returned `needs-input` or `blocked` are not integrated: integrate the others, then stop before the next wave and bring the question to the person.
4. **The next wave** branches from the change branch after the integration, so it sees what its dependencies built.

## Mode 3: split among people

Work items come from `work-item-creator` (pack `product`). While it is not installed, say `product/work-item-creator not installed — applying inline criteria` and write one item per unit, in the answer or in the file the person names:

```markdown
### Unit B: Coupon storage

- Parent: PROJ-123 (the change's ticket, or "none")
- Goal: shoppers get a clear refusal for an expired coupon (proposal.md, Intent)
- Tasks: 2. Load a coupon by code and reject expired ones
- Files: src/coupons/store.py, tests/test_coupon_store.py
- Covers: S-3 (CAP-coupons-FR-2)
- Depends on: none
- Branch: feat/PROJ-123-add-coupons-unit-b, from feat/PROJ-123-add-coupons
- Done when: tests/test_coupon_store.py::test_rejects_expired_code passes with `python -m pytest -q`, only the files above changed, one commit per task as the project's commit rules say
```

- **The tracker assigns the IDs.** Never invent one. When the person gives them back, check each against `tickets.pattern` in `.exo/config.json` (`.exo/shared/sdd-phase-common.md`, section E) and record the mapping as a decision. Without a pattern, the items have no IDs: the list is the hand-off.
- **Never create tickets:** the engine does not connect to any tracker.
- When the person says a unit's branch is ready, integrate it as below, in the same order; a unit whose dependencies are not integrated yet waits.

## Integrate in order

For each finished unit, in integration order, on the change's branch:

1. `git switch <change-branch>` in the main working folder.
2. `git cherry-pick <start>..<unit-branch>`, where `<start>` is the commit the unit branched from: each task keeps its own commit, and the change branch only gains commits.
3. **A conflict:** run `git cherry-pick --abort` and stop. Report the unit, the files in conflict, the units already integrated and the last good commit, with `status: needs-input`. Never resolve it yourself: a conflict means the units were not independent, and the plan or the code needs the person's decision.
4. **Tests:** run the exact test command on the change branch. In the orchestrator's session, tests within apply run in `sdd-implementer` (`.exo/shared/sdd-phase-common.md`, section G): ask one to run only that command and report the counts; without subagents, run it yourself.
5. **A failure the baseline did not have:** stop, name the unit whose integration broke it, and show the output. Do not fix it here: the fix is a decision for the person (a new task through `sdd-tasks`, or undoing that integration, which needs their confirmation).
6. **Green:** go to the next unit.

After the last unit: `exo change status <change> --json` shows every box ticked, and the tests are green. Remove the worktrees (`git worktree remove <folder>`). Keep the unit branches until the verify passes; deleting them takes `git branch -D`, because git does not see cherry-picked commits as merged, so ask the person first.

## Return

```text
| Unit | Mode | Result | Commits | Tests after integration |
|---|---|---|---|---|
| A: Coupon rules | parallel, wave 1 | integrated | 1 | 42 passed |
| B: Coupon storage | parallel, wave 1 | stopped: conflict in src/coupons/__init__.py | 0 | - |
| C: Checkout endpoint | parallel, wave 2 | not started: depends on B | 0 | - |
```

```yaml
status: needs-input
phase: apply
change_name: PROJ-123-add-coupons
artifacts:
  - path: src/coupons/rules.py
    summary: Unit A, task 1
  - path: specs/PROJ-123-add-coupons/tasks.md
    summary: 1 of 3 boxes ticked
notes: >-
  Mode: parallel, chosen by the person. Unit A integrated, tests green (42 passed).
  Unit B not integrated: its cherry-pick conflicts with Unit A in src/coupons/__init__.py, a
  package export file both implementers edited although tasks.md names it in neither unit.
  Cherry-pick aborted; last good commit 1a2b3c4. Unit C waits for B. Decide: add the export
  file to one unit in tasks.md, or run Unit B again in sequential mode on top of Unit A.
  Skills: parallel-dispatch (fallback-registry); sdd-apply (paths-injected) in each implementer.
next: apply
```

With every unit integrated and green, the status is `ok` and `next: verify`.

## Record

Inside the change, before the envelope (`.exo/shared/capability-attribution.md`). The implementers list their skills in their envelope notes, and you record them:

```bash
exo change record <change> --add capabilities_used '{"name": "parallel-dispatch", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "sdd-implementer", "type": "subagent", "activation": "auto"}'
exo change record <change> --add skills_used '"parallel-dispatch"'
exo change record <change> --add decisions '{"summary": "Apply mode: parallel, waves A+B then C", "by": "human"}'
```

Log the phase with `exo change record <change> --phase-done apply` only when every unit is integrated and green. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Rules

- Never start implementing before the person chose the mode (an unattended run takes the sequential one).
- Nothing outside the frozen plan: a unit never touches another unit's files.
- Never push, never `--force`, never `--no-verify`, never rewrite the change branch.
- Never resolve a conflict or fix a failed integration on your own: stop and ask.
- Only you launch subagents; an implementer never launches another one.

## Before you finish

- [ ] The graph, the waves and the shared files were shown, and the person chose the mode.
- [ ] Each unit ran with only its own tasks and files.
- [ ] Units were integrated in graph order, with the test command after each integration.
- [ ] Any conflict or new failure stopped the run, with the unit, the files and the last good commit.
- [ ] Worktrees removed; unit branches kept until the verify, or deleted with the person's approval.
- [ ] The mode, the subagents and the result are in the AI Usage Record.
