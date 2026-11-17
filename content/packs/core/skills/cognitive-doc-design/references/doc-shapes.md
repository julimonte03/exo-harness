# Document shapes

Skeletons for the documents `cognitive-doc-design` writes most often. Each one starts with the reader's question and leads with the answer. Adapt the headings to the project's conventions; drop a section that has nothing real to say rather than filling it.

## README

Reader: someone who just found the repository. Question: "What is this, and how do I run it?"

```markdown
# <name>

<One sentence: what it does and for whom.>

## Quick start

<The fewest commands from a fresh clone to something working, each with its expected result.>

## Requirements

<Versions, tools, accounts; nothing that the quick start already shows.>

## Common tasks

- Run the tests: `<command>`
- Lint: `<command>`
- Build: `<command>`

## How it is organized

<Three to six lines: the main folders and what lives in each.>

## Learn more

- <Link with what the reader gets>: <path>
- How to contribute: <path>
```

## How-to guide

Reader: someone with a task. Question: "How do I do X?"

```markdown
# <Task, as an imperative: "Rotate the signing key">

<One sentence: when you need this, and what you end up with.>

**Before you start:** <prerequisites, permissions, time it takes>.

1. <Action>. `<command>`
   <What you should see.>
2. ...

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|

## Related

- <Next task or reference, as a link with what it gives>
```

## Reference page

Reader: someone looking up a fact. Question: "What exactly is X?"

```markdown
# <Thing>: reference

<One sentence: what this page lists.>

| Name | Type | Default | Description |
|---|---|---|---|

## <Group>

<Same table shape for each group; no tutorials, no opinions.>
```

Complete, consistent and dry: every item has the same fields in the same order. Explanations go to their own page and are linked.

## Explanation, design note or RFC

Reader: someone who must understand or decide. Question: "Why is it like this?" or "What should we do?"

```markdown
# <Topic or proposal>

**Summary:** <three to five lines: the problem, the proposal or the answer, and the main trade-off.>

**Status:** <draft | under review | accepted | superseded by <link>> · <date> · <owner role>

## Context

<What a reader must know to follow the rest, and no more.>

## The problem

<What hurts, for whom, with evidence.>

## Proposal

<The idea from the big picture down: the overview first, then the parts.>

## Alternatives

| Option | Pros | Cons | Why not |
|---|---|---|---|

## Risks and open questions

- <risk or question>: <owner role>, <by when>

## Decision needed

<What the reader is asked to decide, by when.>
```

A decision that is hard to reverse also deserves a decision record: `architecture-decision-record` (pack `design`) when the project has it.

## Onboarding guide

Reader: a newcomer in their first days. Question: "What do I need to know and do to become productive?"

```markdown
# Welcome to <team or project>

<Two lines: what the team builds and for whom.>

## Your first day

1. <Access and tools, with how to get each; never credentials in the document>
2. <Clone, run, run the tests: link to the README quick start>

## Your first week

- <A small, real first task and who reviews it (a role)>
- <The three concepts everyone uses, each in one line, linked to more>

## How we work

- <Branches, reviews, releases: links to the project's rules>

## Where to find things

| You need | Look at |
|---|---|

## Who to ask

<Roles and channels, never personal contact details.>
```

## Troubleshooting page

Reader: someone with something broken. Question: "Why does X fail, and how do I fix it?"

```markdown
# Troubleshooting <area>

## <Symptom, as the reader would describe it or the exact error text>

**Cause:** <one or two lines>.
**Fix:** <numbered steps with expected results>.
**Prevent it:** <optional>.
```

One section per symptom, titled with what the reader sees (the error message they would search for), never with the cause they do not know yet.

## Long PR description

The sections come from the project's PR template: in an SDD change, `pr.md`, owned by `branch-pr`, with exactly Summary, Ticket, Changes, Test Plan and Checklist. Inside them:

- **Summary:** the first line says what changes for the user or the system; the second, why.
- **Ticket:** the ticket key, or `none`.
- **Changes:** grouped by what they do, not by file; the risky part first. When the diff is large, end with a short reviewer guide: where to start reading, and what can be skimmed.
- **Test Plan:** the exact commands and their results.
- **Checklist:** tick only what is true.
