# Description and triggers

The description is the only part of a skill the agent sees before deciding to load it. It decides whether the skill runs when it should, and stays quiet when it should not.

## The formula

1. **What it does,** in one or two sentences: the result and its main parts. Concrete nouns ("a findings table with severity and path:line"), not adjectives ("a thorough review").
2. **What it never does,** when that prevents misuse ("It never edits the code", "It calls no tracker API").
3. **Use it when** followed by the situations, in the words of the people who will ask.
4. **Triggers:** five to eight quoted phrases a real person would type.

Up to 1024 characters, in English, without line breaks inside a sentence that would break the YAML (use the folded `>-` block).

## Good and weak

Weak:

```yaml
description: Helps with documentation tasks and improves docs quality.
```

- No result, no situations, no triggers. It loads on any mention of docs, or on none.

Better:

```yaml
description: >-
  Writes and reviews documentation that is understood on the first read:
  it starts from the reader's question, leads with the answer, and makes
  the page scannable. Use it when a document has to be written or feels
  long, dense or confusing. Triggers: "write the README", "make this doc
  easier to read", "this documentation is too dense", "restructure this
  guide".
```

Weak triggers:

```text
"docs", "help", "skill", "review"
```

- Single words match everything; nobody asks like that.

Better triggers:

```text
"write the README", "this guide is confusing", "turn this into a how-to", "nobody reads this page"
```

- Full phrases, varied verbs, the way people actually ask, including complaints ("is confusing") as well as requests.

## Checking overlap with neighbors

Before settling the description:

1. List the installed skills whose job is close (`exo skills list`, `.exo/skill-registry.md`).
2. For each trigger, ask: would a neighbor's description also claim it? If yes, either drop the trigger, or make the difference explicit in both descriptions.
3. Write the non-triggers (step 2 of the skill) as requests that belong to a neighbor, and check that the new description does not claim them.

| New skill | Neighbor | The line between them |
|---|---|---|
| A skill that writes work items | A skill that refines one backlog item | Approved plan to many items, against one vague item to a ready one |
| A skill that writes review comments | A judge skill | Text a person posts, against findings in the judge format |
| A skill that creates skills | A skill that improves skills | A folder that does not exist yet, against an existing one |

## Triggers for phase and conditional skills

A skill that the SDD phase map loads is chosen by the map, not only by its description. Its description still says when a person would call it directly, and names the phase and the trigger of the map ("Conditional in design for large architectures").

## Words that cause trouble

| Avoid | Why |
|---|---|
| "Always use this skill", "use for all tasks", "must be used" | Tries to load on everything; a reviewer flags it |
| Brand names as requirements ("for Jira") | Ties the skill to one tool; name it as an example ("Jira, Azure Boards or any tracker") |
| Internal jargon or project code names | The agent and new people do not know them |
| Promises about quality ("perfect", "best") | Say what it produces instead |

## Length budget

| Part | Characters, roughly |
|---|---|
| What it does and never does | 300 to 600 |
| Use it when | 150 to 250 |
| Triggers | 150 to 250 |

The validator rejects more than 1024. When a description runs long, cut adjectives and the second example of each thing first; keep the situations and the triggers.
