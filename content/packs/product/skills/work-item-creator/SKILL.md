---
name: work-item-creator
description: >-
  Turns an approved plan into work items ready for any tracker: the units or
  tasks of an SDD tasks.md, an approved proposal or spec, or a list the person
  gives. Each item gets a title, a description with its goal and scope,
  acceptance criteria in Given/When/Then, an optional estimate, its
  dependencies and optional suggested test cases. It never invents IDs:
  drafts use local references, and the IDs the person brings back from the
  tracker are checked against tickets.pattern in .exo/config.json. It calls
  no tracker API: it writes the text, or a file to import, and the person
  loads it. Use it when a plan has to become stories, tasks or tickets in
  Jira, Azure Boards, GitHub Issues or any other tracker, or when the units
  of a plan are split among people. Triggers: "create the tickets for this
  plan", "turn tasks.md into work items", "write the stories for the
  backlog", "break this into tasks for the board", "export the plan to CSV
  for import", "one card per unit".
metadata:
  exo-pack: product
  exo-execution: inline
  exo-permissions: write-specs
---

# work-item-creator

## Result

- **One work item per piece of the plan,** each with: kind, title, description (goal, scope, out of scope, links to the artifacts), acceptance criteria in Given/When/Then, dependencies, and, when the team wants them, an estimate and suggested test cases.
- **Local references** (`WI-1`, `WI-2`) that tie the items together until the tracker assigns real IDs, and later the map from each reference to the ID the person brings back, checked against `tickets.pattern`.
- **The format the person chose:** Markdown in the answer (the default), a Markdown file, or a CSV file to import.
- **Nothing reaches the tracker from here.** The person creates the items, by import or by hand.

## When

- **After the tasks phase** of an SDD change, when the team tracks the plan: each unit (or each task) of tasks.md becomes an item.
- **When `parallel-dispatch` splits the units among people** (its mode 3): one item per unit, with its branch and its "done when".
- **On request,** from an approved proposal or spec (Tier 1 and 2 have no tasks.md), or from a list the person gives: "create the tickets for this".
- **Not for:** a vague backlog item that still needs work (skill:refinement-assistant); a bug report or a feature request about the product (`issue-creation`, pack `core`); deciding what to build (skill:product-discovery); a plan nobody approved yet (finish the plan first: `sdd-tasks`, pack `sdd`).

## Inputs

1. **The plan.** In a change, `exo change status <change> --json` gives the tier, the phase and the paths. Read tasks.md (units `### Unit <letter>: <name>`, tasks with Files, Tests and Covers, `Depends on:` lines), test-spec.md (test cases `T-n`), spec.md (scenarios `S-n`) and the Intent of proposal.md. Outside a change, the list or document the person gives.
2. **The ticket settings.** `tickets.pattern` and `tickets.example` in `.exo/config.json`, and the change's own ticket, `ticket_key`, from `exo change ai-usage <change> --json` (null when there is none).
3. **The team's conventions,** asked once (step 2): the tracker and the format, the granularity, the item kinds, the estimate unit, and whether they want test cases.

## Steps

The fields in detail, with a full example, are in `references/item-format.md`; the import formats of Jira, Azure Boards and GitHub Issues in `references/tracker-formats.md`.

### 1. Check that the plan is approved

- **In a change:** the tasks phase is done (`exo change status`), so tasks.md is the frozen plan. In Tier 1 and 2, the proposal (and the spec, when there is one) is approved. If not, stop and say which phase is missing.
- **Outside a change:** ask the person to confirm the list is the approved one. Items that are vague (no clear outcome, no way to test them) go to skill:refinement-assistant first; say which ones.
- Never add scope. A piece of work the plan does not have is a question for the person, not an item.

### 2. Ask the conventions once

One message, at most five questions, each with its default:

| Question | Default |
|---|---|
| Which tracker, and which format: Markdown, or a file to import? | Markdown in the answer |
| One item per unit, or one per task? | One per unit, with its tasks as a checklist; without units, one per task |
| Which kinds does the team use (story, task, sub-task, spike)? | Story for a unit a user can see, task for the rest |
| Do you estimate, and in which unit? | No estimate: the team estimates |
| Do you want suggested test cases per item? | Yes, two: the main path and the most likely failure |

If the person already said it in this conversation, confirm instead of asking. In an unattended run, take the defaults and say so.

### 3. Cut the items

- **From tasks.md:** one item per unit, or per task when the person chose it. A plan without units and with one or two tasks may be a single item; ask.
- **Parent:** the change's `ticket_key` when it has one, written exactly as the person confirmed it (`AB#77`, not the normalized `AB-77`). Otherwise the parent is `none`, or an epic the person names.
- **Traceability:** each item keeps the `S-n` scenarios and requirement IDs its tasks cover, so a reader of the tracker can find the spec.
- **Technical plan item (optional):** some teams track the design work itself. When the person asks, add one item that links design.md and tasks.md, with the decisions to review, and no code tasks.

### 4. Write each item

- **Title:** imperative, the outcome first, up to about 80 characters, unique in the set, without an ID: "Reject expired coupons at checkout".
- **Description:** the goal in one sentence (who benefits and why, from the Intent), the scope (its tasks and files), what is out of scope, and the paths of the artifacts in the repository (`specs/<change-name>/tasks.md`).
- **Acceptance criteria:** Given/When/Then, observable from outside, taken from the scenarios the item covers, with their `S-n`. At least one failure path per item.
- **Estimate** (only when the team estimates): in the team's unit, labeled as a proposal, with its basis (the size forecast of tasks.md, the unknowns). Never days or hours unless the person asks for them.
- **Dependencies:** by local reference, from the `Depends on:` lines and from shared files: "Blocked by: WI-1, WI-2".
- **Suggested test cases** (when wanted): two per item by default, the main path and the most likely failure, each with its steps or Given/When/Then and the expected result. Link the test that automates it (`T-n` of test-spec.md, or the test name in tasks.md); without one, mark it `manual`. A team with a test management tool imports them there; otherwise they stay in the item.
- **Done when:** the exact test command passes and only the item's files changed.
- **Branch** (for work split among people): `<change-branch>-unit-<letter>`, from the change's branch, as `parallel-dispatch` names them.

### 5. References and IDs

- Drafts use local references, `WI-1`, `WI-2`, in plan order. **Never write an ID that looks like a tracker's** (`PROJ-101`, `#45`): only the tracker assigns IDs.
- **When the person brings the IDs back,** check each one against `tickets.pattern` (the whole ID has to match):
  - it matches: map it, for example `WI-1 → PROJ-201`;
  - it does not: say so and show `tickets.example`, then ask once more. If it still does not match, keep the local reference for that item and say so.
- With the map complete, offer the items again with real IDs in their dependencies.
- **Without a pattern** (`tickets.pattern` is null), the project has no tickets: do not ask for IDs. The local references and the list are the hand-off.
- Never change the pattern: that is the person's decision in `.exo/config.json` (`.exo/shared/sdd-phase-common.md`, section E).

### 6. Format the output

- **Markdown** (default): one section per item, in plan order (`references/item-format.md`).
- **A file to import:** CSV or Markdown, in the shape of `references/tracker-formats.md`. Field names and required columns change with each tracker's configuration: tell the person to compare them with their import screen before loading.
- **Where:** in the answer, or in the file the person names, outside the change folder (for example `work-items/<change-name>.csv`); never inside `<change-root>`, which belongs to the phases. Ask before committing an import file: it is usually a one-off. Committed during a change, it is a project document: only with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C).
- **Data protection:** the items go to an external system. Only Public data, and Internal data only to the organization's own tracker (`.exo/shared/data-protection.md`, section C). No secrets, no personal data, no customer identifiers, no production log excerpts: point at `path:line` instead.

### 7. Hand off

Show a summary table, then the items or the path of the file, and what the person does next: import the file or paste each item, then send back the IDs if the project has a ticket pattern.

## Return

```text
Work items for PROJ-123-add-coupons: 3 items, parent PROJ-123, Markdown

| Ref | Kind | Title | Blocked by | Test cases |
|---|---|---|---|---|
| WI-1 | story | Apply percentage coupons to the cart total | - | 2 |
| WI-2 | story | Reject expired coupon codes | - | 2 |
| WI-3 | story | Accept a coupon code at checkout | WI-1, WI-2 | 2 |

Next: create them in your tracker (or import work-items/PROJ-123-add-coupons.csv), then send me
the IDs; I will check them against the project's pattern (like PROJ-123) and map them.
```

## Rules

- **No tracker access.** Never call a tracker's API or CLI, and never create, update or close an item: the person does.
- **No invented IDs.** Local references until the person brings real IDs, and those are checked against the pattern.
- **Only the approved plan.** Nothing outside it, and no item that changes its scope.
- **Estimates belong to the team.** You propose one only when asked, in their unit.
- **Roles, not people.** Never assign an item to a named person: that is the team's call in the tracker.

## Record

Inside a change, an inline phase records it before its envelope (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes and the orchestrator records it. `activation` is `requested` when the person asked for the items:

```bash
exo change record <change> --add capabilities_used '{"name": "work-item-creator", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"work-item-creator"'
exo change record <change> --add decisions '{"summary": "Work items created by the person: WI-1 -> PROJ-201, WI-2 -> PROJ-202, WI-3 -> PROJ-203", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record.

## Before you finish

- [ ] The plan is approved, and no item adds scope.
- [ ] Every item has a title, a goal, its scope, Given/When/Then criteria with at least one failure path, and its dependencies.
- [ ] Estimates and test cases follow what the team chose.
- [ ] No ID was invented; IDs brought back were checked against `tickets.pattern`.
- [ ] The output is in the chosen format, outside the change folder, with no secrets or personal data.
- [ ] The person knows how to load the items and what to send back.
