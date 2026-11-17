---
name: refinement-assistant
description: >-
  Refines one backlog item until a team can build it: a clear title and
  outcome, who it is for and why, scope and out of scope, acceptance criteria
  in Given/When/Then, dependencies, risks, open questions with who answers
  each, an INVEST check, a split into smaller items when it is too big, and
  an estimate proposal the team confirms. It works with any tracker, speaks
  plain language to non-technical people, never invents an ID or a business
  rule, and hands the refined item on to work item creation or to a new SDD
  change. Use it when a story, a ticket or an idea is vague, too big or has
  no acceptance criteria, before a refinement or planning session, or when
  someone asks whether an item is ready. Triggers: "refine this story", "is
  this ticket ready", "write acceptance criteria for this item", "this story
  is too big, split it", "prepare this for backlog refinement", "help me
  write a user story", "estimate this item".
metadata:
  exo-pack: product
  exo-execution: inline
  exo-permissions: write-specs
---

# refinement-assistant

## Result

One refined item, written so that anyone on the team reads it the same way:

1. **Title and story:** the outcome in the title; "As a `<role>`, I want `<capability>`, so that `<outcome>`".
2. **Context:** the problem today, with its evidence.
3. **Scope and out of scope.**
4. **Acceptance criteria** in Given/When/Then: the main path, the failures and the edge cases.
5. **Dependencies:** other items, teams, systems or decisions it waits for.
6. **Risks,** each with a mitigation or a spike.
7. **Open questions,** each with the role that answers it and the default you would assume.
8. **INVEST check:** six lines, pass or fail, with the reason.
9. **Split proposal,** when the item is too big or mixes goals.
10. **Estimate proposal,** in the team's unit, for the team to confirm.
11. **Readiness verdict:** `Ready`, `Ready with open questions` or `Not ready`, with what is missing.

The person approves the text and updates the item in their tracker. This skill never touches the tracker.

## When

- **Before a refinement or planning session,** to prepare the items.
- **An item is vague,** too big, or has no acceptance criteria.
- **A non-technical person** brings an idea or a request and wants it written as an item the team can build.
- **Someone asks** "is this ready?" or "can you split this?".
- **Not for:** deciding whether the idea is worth building (skill:product-discovery); turning an approved plan into several items (skill:work-item-creator); a bug report (`issue-creation`, pack `core`); the technical design (`sdd-design`, pack `sdd`).

## Inputs

1. **The item:** the text the person pastes, or a file they point at. Clean it first: no secrets, no personal data, no customer identifiers (`.exo/shared/data-protection.md`). Users are roles, never names.
2. **Its ID,** when it has one: check it against `tickets.pattern` in `.exo/config.json`. If it does not match, say so with `tickets.example`. Never invent an ID; without a pattern, the project has no IDs.
3. **Context:** `.exo/context.md`, the code the item touches (`path:line`, skill:context-retrieval), and the living specs of the capability when the project has them (`exo specs list --json`).
4. **Memory:** `exo mem search "<topic>"` for earlier decisions about the same feature (skill:memory-protocol).
5. **Team conventions,** when they exist: the estimate unit, a Definition of Ready, a story format. Ask once, or look for them in the project's docs; without them, use the defaults of `references/invest-and-splitting.md`.

## Steps

The refined item template, with a before-and-after example, is in `references/refined-item.md`. INVEST, the split patterns, estimates and the default Definition of Ready are in `references/invest-and-splitting.md`.

### 1. Restate it

Say the item back in two lines: who it is for, what they get, and why it matters. If you cannot name the who or the why, that is your first question; do not go on guessing.

### 2. Find the gaps

Walk the template and note what is missing or unclear:

- the user role and the outcome;
- what is in and out of scope;
- the behaviors to test, including failures and edge cases;
- the needs beyond behavior: performance, security, accessibility, data protection, audit;
- what it depends on, and what could go wrong.

### 3. Ask the person

- One message, at most five questions, in plain language: no jargon with a non-technical person.
- Each question says why it matters and the default you would assume. Offer options when you can ("A: refund to the card, B: store credit, C: either, the customer chooses").
- In an unattended run, write the defaults, label them `Assumed:` and list them in your answer.

### 4. Write the refined item

- **Title:** the outcome, not the task: "Customers can reschedule a delivery", not "Delivery date endpoint".
- **Story:** one role, one capability, one outcome. Two roles or two outcomes usually mean two items.
- **Context:** the problem today and its evidence (`path:line`, a document, the person's words).
- **Acceptance criteria:** Given/When/Then, observable from outside, usually three to seven. Cover the main path, each failure the gaps showed, and the edge cases. A need beyond behavior gets a criterion with a number only when the person gives the number; otherwise it is an open question.
- **Dependencies, risks and open questions,** each with its owner role.

### 5. Check INVEST

Independent, Negotiable, Valuable, Estimable, Small, Testable: one line each, pass or fail, with the reason. A fail is not a verdict on the person's work; it says what to fix.

### 6. Split it when needed

Split when the item fails Small or Independent, has more than about seven criteria, or serves two goals:

- Pick a pattern (by workflow step, business rule, data variation, channel, happy and unhappy path, operation, simple then complex, or a spike first).
- Every slice is valuable on its own, end to end. Never split by layer (frontend, backend, database): a layer alone delivers nothing anyone can try.
- Show each slice with its title, its story, the criteria it takes, and the order, with the first slice the one that tests the riskiest assumption or delivers the most value.

### 7. Propose an estimate

- Only in the team's unit (story points, t-shirt sizes), and only if the team estimates.
- Compare with a reference item when the team gives one. State the basis: complexity, uncertainty, effort.
- When the uncertainty is high, propose a time-boxed spike first instead of a big number.
- Label it a proposal. The team estimates together; your number only starts the conversation.

### 8. Give the readiness verdict

- **Ready:** INVEST passes, every criterion is testable, the dependencies are known, and no open question blocks the work.
- **Ready with open questions:** the same, with questions that do not block starting; say which ones and who answers them.
- **Not ready:** say exactly what is missing, and what would make it ready.

### 9. Hand it on

- **To the tracker:** the person updates the item with the refined text, from your answer or from the file they name.
- **To several items:** when the refinement became a plan with several pieces, skill:work-item-creator writes them.
- **To an SDD change:** when the project has the `sdd` pack and the item is ready, start it with `sdd-new` and the refined text. `sdd-new` asks for the ticket once and checks it against the pattern.
- **Back to discovery:** when the value is still unclear, skill:product-discovery comes first.

## Return

The refined item, then the verdict. An excerpt:

```markdown
## INVEST

| Criterion | Result | Why |
|---|---|---|
| Independent | pass | Uses the existing delivery slots; no other item has to land first |
| Negotiable | pass | The criteria fix the outcome, not the screen |
| Valuable | pass | Support handles about 40 reschedule calls a week (support log summary the person gave) |
| Estimable | fail | Unknown whether the carrier accepts date changes after dispatch |
| Small | fail | Covers rescheduling and cancelling: two goals |
| Testable | pass | Every criterion is observable on the order page |

## Split

1. Customers can reschedule a delivery before dispatch (criteria 1-4). First: it covers most calls.
2. Customers can cancel a delivery before dispatch (criteria 5-6).
3. Spike, two days: can the carrier change the date after dispatch? (answers the Estimable fail)

## Verdict

Not ready: split it as above; slice 1 is ready once the product owner confirms the latest change time (open question 1, default: 18:00 the day before).
```

## Rules

- **Plain words.** Write in the person's terms; explain a technical term the first time, or leave it out.
- **Evidence or a question.** Never invent a business rule, a limit, a date or a number. Unknowns are open questions with a default.
- **No invented IDs.** Check the ones you get against the pattern; never create one.
- **Estimates belong to the team.** You propose; they decide.
- **Any tracker, no playbooks.** The refined item is plain text that fits any tracker; the team's own Definition of Ready wins over the defaults.
- **Roles, not people.** Never assign the item to a named person.

## Record

Refinement usually happens before a change exists. When it runs inside one (for example while `sdd-new` or `sdd-propose` writes the proposal), record it before that phase's envelope (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "refinement-assistant", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"refinement-assistant"'
exo change record <change> --add decisions '{"summary": "Item split in three: reschedule, cancel, carrier spike", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record; save decisions the person made to memory as skill:memory-protocol says, without personal data.

## Before you finish

- [ ] The item names one role, one capability and one outcome.
- [ ] The criteria are Given/When/Then, observable, and cover failures and edge cases.
- [ ] Every open question has an owner role and a default; nothing was invented.
- [ ] INVEST is checked line by line; a too-big item has a split by value, not by layer.
- [ ] The estimate is in the team's unit and labeled as a proposal, or left out.
- [ ] The verdict says what is missing, and the hand-off is clear.
