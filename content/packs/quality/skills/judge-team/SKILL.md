---
name: judge-team
description: >-
  Advisory, read-only team and execution judge: reviews an implementation
  plan (tasks.md, or a breakdown or backlog) as a team coach would: whether
  several people can share it without two of them editing the same files,
  whether each unit carries its own tests, explicit dependencies, a
  reasonable size per task, coordination risks and knowledge concentrated in
  one place. Returns JTEAM-n findings with severity and the task or line,
  plus an APPROVED or ESCALATED verdict; it judges the plan, never the
  people, and never edits it. Runs in the sdd-judge subagent in the tasks
  phase of Tier 4. Use it also when someone wants to know whether a plan is
  ready to split across a team. Triggers: "team judge", "can we split this
  plan", "can several developers work on this in parallel", "judge the task
  breakdown", "will we step on each other", "is this plan ready for the
  team".
metadata:
  exo-pack: quality
  exo-execution: subagent
  exo-subagent: sdd-judge
  exo-permissions: read-only
---

# judge-team

## Result

The findings of one review in the format of the `sdd-judge` subagent: a Verdict (`APPROVED` or `ESCALATED`), a Findings table with IDs `JTEAM-n`, and a Not reviewed section, followed by the envelope of `.exo/shared/sdd-phase-common.md`, section D. You write nothing and fix nothing: the orchestrator, or the agent when there is none, records the outcome.

## Contract

`.exo/shared/judge-common.md` rules this judge: advisory first (A), independence (B), no cascade (C), findings (D), verdict (E) and recording (F). When this skill and the contract disagree, the contract wins.

## Where it runs

- **With subagents:** in `sdd-judge`, read-only (it reads, searches and lists files; it has no shell and launches no subagent). The delegation gives this skill's path, the change name and root, the phase, the tier, what to review and the stage before it. If something you need is missing, return `status: needs-input` and say what.
- **Without subagents:** a separate pass after the plan is written, with only these criteria, saying "no isolation". Judge the files as they are on disk, not what you remember of writing them.
- This judge owns no gate. Its findings go to the person, who fixes or dismisses each one before the plan is approved and frozen.

| Phase | What you review | Against (the stage before) |
|---|---|---|
| tasks (Tier 4) | `tasks.md`, and `test-spec.md` for who owns each test | `spec.md` and `design.md` (Modules / Files, Test Plan, Risks & Mitigations) |
| outside SDD | the plan, breakdown or backlog the person gives | the design or the goal the person gives |

In lower tiers the phase map does not call it; the person may ask for it on any plan.

## Criteria

Only how a team can execute the plan; other judges cover correctness, security, product, business and the UI. There is no other skill to reuse: your criteria are the coach's rubric.

Read `references/team-coach-rubric.md` in full before you start, and apply its seven dimensions:

| Dimension | Look for |
|---|---|
| 1. Split without overlap | Units with disjoint file sets; every shared hot spot (routes, index files, configuration, migrations, lockfiles, shared types) with one owner or an order; no file of the design without a task |
| 2. Each unit carries its tests | Every unit names the tests that prove it and the `S-n` it covers; no test file edited by two units without an order |
| 3. Explicit dependencies | No task uses what a later task builds; contracts (types, interfaces, schemas) fixed in an early task; no cycles; a short, known critical path; needs from outside the team named |
| 4. Reasonable size | One behavior and its tests per task, one reviewable commit; no task hiding several behaviors; the change within its forecast budget, or a split |
| 5. Coordination risk | Integration early and owned, not all in the last task; few, explicit handoffs; review load spread over time |
| 6. Concentrated knowledge | A unit only one person could do, without pairing, a walkthrough, notes or an outside reviewer |
| 7. Clear enough to pick up | Each task names files, tests, scenarios and its done condition; unknowns first, as time-boxed spikes |

- **Judge the plan, never the people.** Speak of units, tasks and roles. Never name, rate or guess at individuals, their skills or their motivation, even when the plan or the person names them.
- **Against the stage before:** the units must build what `design.md` describes and cover the scenarios of `spec.md`. A plan that cannot be split because the design couples everything is a finding against `design.md` (`no cascade: design.md`).
- `sdd-tasks` already checks the plan's format and its size forecast; do not repeat those checks except where they decide whether people can share the work.

## Findings

- **ID:** `JTEAM-1`, `JTEAM-2`, and so on, unique in the change and never reused. Start at the next free number the delegation gives; the orchestrator takes it from `exo change followups <change> --status all`.
- **Severity** (contract, section D; for a plan before code):
  - Critical: the plan cannot be carried out as written: a circular dependency, a task that needs something no task builds, or units that contradict the design so the team would build the wrong thing.
  - High: the next stage needs it fixed: two units edit the same file with no owner or order; a unit with no tests; a task that uses what a later task builds; a file of the design or a scenario of the spec that no task covers.
  - Medium: a hot spot with an owner but no order; knowledge concentrated in one unit with no mitigation; integration left to the last task; an outside dependency not named; a task too large for one reviewable commit.
  - Low: order, naming, wording of a task.
- **Location:** `path:line` of the plan, with the task number (`specs/<change>/tasks.md:24`, task 3).
- **Criterion:** the dimension of the rubric (`rubric 1: split without overlap`, `rubric 3: dependencies`), or `no cascade: <artifact>`.
- **Suggested fix:** as text: the split, the order, the owner or the task to add. Never edit the plan. Never copy personal data into a finding.

## Verdict

- `APPROVED`: no finding is Critical or High.
- `ESCALATED`: one is, the plan contradicts the stage before, or you could not review something you needed (say what in Not reviewed).

## Return

```markdown
# Judge Findings: judge-team on PROJ-123-add-login

## Verdict

ESCALATED

## Findings

| ID | Severity | path:line | Finding | Criterion | Suggested fix |
|---|---|---|---|---|---|
| JTEAM-1 | High | specs/PROJ-123-add-login/tasks.md:14 | Task 2 (Unit A) and task 5 (Unit B) both edit src/auth/routes.py, with no order between them | rubric 1: split without overlap | Give the route table to Unit A and make task 5 come after task 2, or move both route changes into one task |
| JTEAM-2 | Medium | specs/PROJ-123-add-login/tasks.md:30 | Only the session store task touches the legacy token code, and nothing spreads what it needs | rubric 6: concentrated knowledge | Add a short note on the token format to design.md, or plan a walkthrough before task 4 starts |

## Not reviewed

None.
```

Then, as the last thing in the answer:

```yaml
status: ok
phase: tasks
change_name: PROJ-123-add-login
artifacts: []
notes: >-
  Isolation: subagent (sdd-judge). Skills: judge-team (paths-injected).
  Verdict: ESCALATED. Findings: 0 Critical, 1 High, 1 Medium, 0 Low.
next: none
```

`next: none` because the judge does not decide the next phase: the orchestrator does.

## What the orchestrator records

Never run these yourself. The orchestrator records each finding as a followup, the verdict, and the judge in `capabilities_used` (`.exo/shared/judge-common.md`, section F):

```bash
exo change record <change> --followup '{"id": "JTEAM-1", "judge": "judge-team", "rule": "rubric 1: split without overlap", "severity": "high", "summary": "Tasks 2 and 5 edit src/auth/routes.py in different units with no order; give the file to one unit or order the tasks", "location": "specs/PROJ-123-add-login/tasks.md:14"}'
exo change record <change> --add judges_invoked '{"name": "judge-team", "result": "escalated: JTEAM-1 open"}'
exo change record <change> --add capabilities_used '{"name": "judge-team", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
```

Accepted findings are fixed in `tasks.md` by `sdd-tasks` before the plan is frozen; the dismissed ones go to `dismissed_followups` with the person's reason.
