# Skill template

Skeletons for a new skill. Replace every `<...>`; delete a section only when it truly does not apply (a skill that never runs inside an SDD change has no Record section). Keep the order: readers and agents find things where they expect them.

## Folder

```text
<name>/
  SKILL.md                 the contract the agent reads, at most 500 lines
  references/              optional: details loaded on demand, one level deep
    <topic>.md
```

No other folders unless the skill needs them. Scripts are a last resort: small, readable, no network, and described in `SKILL.md`.

## Frontmatter

An inline skill of a pack:

```yaml
---
name: <name>
description: >-
  <What it does, in one or two sentences: the result and its main parts.>
  <What it never does, when that prevents misuse.> Use it when <the
  situations>. Triggers: "<phrase>", "<phrase>", "<phrase>", "<phrase>",
  "<phrase>".
metadata:
  exo-pack: <pack>
  exo-execution: inline
  exo-permissions: <read-only | read-only+tests | read-only+record | read-only+gate | write-code | write-specs | write-specs+git>
---
```

A skill that runs in a subagent (here, a read-only judge):

```yaml
metadata:
  exo-pack: <pack>
  exo-execution: subagent
  exo-subagent: sdd-judge
  exo-permissions: read-only
```

A project skill (in the agent's skills folder, not in a pack): the same, without `exo-pack`.

```yaml
metadata:
  exo-execution: inline
  exo-permissions: write-specs
```

The values are strings. Keys outside the standard fields go inside `metadata`, never at the top level.

## SKILL.md body

````markdown
# <name>

## Result

<What exists when the skill is done: the files it writes, the answer it gives, the gate or the record.
A short numbered list when the result has parts.>

## When

- **<Situation>:** <when it applies>.
- **On request:** "<phrase a person would say>".
- **Not for:** <similar requests and the skill that handles each> (skill:<name> when it resolves, or `<name>` with its pack).

## Inputs

1. <Input>: <where it comes from>. <What to do when it is missing: ask once with a default, or stop.>
2. ...

## Steps

<Optional: the references and what each holds, cited by exact path.>

### 1. <Step, as an imperative>

<One to five bullets or sentences. Exact commands in backticks. A default for each question.
What to do when it fails.>

### 2. ...

## Return

<The format of the output, then a short, synthetic example in a code block.>

## Rules

- **<Rule>:** <what is never done, or always done, and why in a few words>.

## Record

<Inside an SDD change: the exo change record commands, as in the other skills.
A subagent lists the skill in its envelope notes instead; the orchestrator records it.>

## Before you finish

- [ ] <A check the agent can verify>
- [ ] ...
````

## A reference file

```markdown
# <Topic>

<One sentence: what this file holds and which step of the skill uses it.>

## <Section>

<Tables, catalogs, long examples, templates. Synthetic data only.>
```

## Sizes that work

| Part | Aim |
|---|---|
| Description | 400 to 1000 characters, five to eight triggers |
| `SKILL.md` | 150 to 300 lines; never above 500 |
| A step | Up to about ten lines; longer goes to a reference |
| An example in `SKILL.md` | Up to about twenty lines; the full one in a reference |
| A reference file | One topic; split it when it passes about 250 lines |
