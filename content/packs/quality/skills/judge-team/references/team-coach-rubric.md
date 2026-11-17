# judge-team: the team coach's rubric

How a coach of high-performing teams, with a background in organizational psychology, reads a work plan before a team starts on it. The coach asks one thing: can several people pick this up tomorrow and finish it without stepping on each other, waiting on each other, or depending on one person? Seven dimensions; every finding still needs the task or the line and a suggested fix.

## Principles behind the rubric

- **Autonomy needs boundaries.** A person owns a unit when they can finish it and prove it without asking anyone. Shared files and hidden dependencies take that away.
- **Interdependence has a price.** Work that only shares a goal is cheap to coordinate; work where one step waits for another costs a handoff; work where two people must keep adjusting to each other costs the most. A good plan turns the last kind into the second by agreeing the contract (a type, an interface, a schema) first.
- **Small batches, early feedback.** Small units merge sooner, get reviewed better, and surface surprises while there is still time.
- **Clarity lowers coordination.** Every question a task leaves open becomes a meeting. A task that names its files, tests and done condition needs none.
- **Knowledge spreads or it concentrates.** When only one person can do a part, the plan has a single point of failure, whatever its other qualities.
- **A plan that names its risks is a safe plan.** Unknowns written as spikes, and risks written next to the task they threaten, let people raise problems early instead of hiding them.
- **Judge the plan, never the people.** Speak of units, tasks and roles. Never name, rate or guess at individuals, their skills or their motivation.

## 1. Split without overlap

- Group the tasks into units (the `### Unit` headings, or the groups the tasks form) and list the files each unit touches.
- **Disjoint file sets:** two units that edit the same file will conflict. Name the file and both units.
- **Hot spots:** route tables, index or barrel files, dependency injection setup, configuration, migrations, lockfiles, shared types and fixtures. Each one needs a single owner, or an order (one unit edits it, the other comes after).
- **Nothing ownerless:** every file in `design.md`, Modules / Files, belongs to some task.

## 2. Each unit carries its tests

- A unit names the tests that prove it, so its owner can finish and show it works alone.
- Test files follow the same rule as code: two units do not edit the same test file without an order.
- Each unit says which scenarios (`S-n`) it covers. A scenario covered only by "the integration at the end" leaves every unit unproven.

## 3. Explicit dependencies

- The order is visible: a task says what it needs ("after task 2"), and no task uses what a later task builds.
- **Contracts first:** when units meet at an interface (a function signature, a type, an API shape, a schema), one early task fixes it, so the others build on it in parallel.
- **No cycles:** unit A waiting on B while B waits on A.
- **Critical path:** the longest chain of dependent tasks is short and known. A plan that is a single chain cannot be shared, whatever its number of units.
- **Outside the team:** environments, data, access, another team's change or an approval the plan needs, named with what it blocks.

## 4. Reasonable size

- One task is one behavior with its tests: one reviewable commit, small enough for one sitting of review.
- A task that hides several behaviors, or touches unrelated files, should be split.
- Tasks so small that they only add handoffs should be merged.
- The whole change keeps to the budget of its forecast (about 400 changed lines), or the plan says how it splits into smaller changes.

## 5. Coordination risk

- **Integration:** who joins the units, and when. Integration left entirely to the last task is a big bang: the plan should integrate early and often.
- **Handoffs:** each handoff is a place to lose time and context. Fewer is better; each one says what is handed over.
- **Review load:** the units arrive for review spread out, not all on the last day, and no reviewer must hold the whole change in their head at once.
- **Work in progress:** the plan does not start every unit at once when the team cannot finish them at once.

## 6. Concentrated knowledge

- A unit only one person can do (a module nobody else knows, legacy code without tests, a specialist domain, a tool only one person uses) is a single point of failure.
- Mitigations the plan can carry: pairing on that unit, a short walkthrough before it starts, notes in `design.md`, a reviewer from outside the unit, or a first task that writes down what is known.
- The riskiest unit should not also be the least shared.

## 7. Clear enough to pick up

- Someone new to the change could start a task with `design.md` and the task alone: it names its files, its tests, its scenarios and when it is done.
- Vague verbs ("handle", "improve", "clean up") without a done condition are findings.
- **Unknowns first:** a part nobody knows how to do yet goes early, as a time-boxed spike with a question to answer, so surprises come while there is time to react.

## Reading a plan in practice

1. List the units and, for each, its files, tests and scenarios.
2. Cross the file lists: every file in two units is a candidate finding.
3. Draw the dependencies in your head (or in a short list): earlier tasks first, contracts first, no cycles, and the longest chain.
4. Check each task's size and clarity.
5. Look for the parts only one person could do, and for what the plan needs from outside the team.
6. Write the findings, starting with what would stop the team from working in parallel.
