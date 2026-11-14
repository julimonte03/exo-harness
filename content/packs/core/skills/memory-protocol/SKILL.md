---
name: memory-protocol
description: >-
  Persistent memory protocol with `exo mem`: search before solving, save
  decisions, fixed bugs and discoveries, and close the session with a summary.
  Use it at session start, when making a decision, after fixing a bug, or when
  closing the session.
metadata:
  exo-pack: core
  exo-execution: inline
---

# memory-protocol

Memory belongs to the user: one per machine, shared by all their projects. Each observation belongs to a project, detected automatically from `git remote origin`. Observations with scope `personal` are visible from any project. Everything runs from the terminal with `exo mem …`; add `--json` when you need to process the output.

## At session start

1. Run `exo mem context`: it returns the project's recent observations and the latest session summary.
2. If the request touches something that may be in memory, search before investigating: `exo mem search "<words or identifier>"`.
3. Results are previews. For the full content, run `exo mem get <id>`.

`exo mem search` uses hybrid search if the user configured the semantic index (`exo mem reindex --provider local`), and lexical search otherwise. Lexical search finds exact identifiers (`PAY-1234`, `RefundService`). For concepts that share no words, try synonyms or the technical names.

## What to save

Save without being asked, as soon as it happens:

| Type | When | What to include |
|---|---|---|
| `decision` | An approach was chosen | What was decided, why, and what was ruled out |
| `bugfix` | A bug was fixed | Symptom, root cause and fix; the ticket if there is one |
| `discovery` | Something non-obvious about the system | The fact and how it was verified |
| `gotcha` | A trap that will happen again | When it happens and how to avoid it |
| `convention` | A team rule | The rule and an example |

```bash
exo mem save --type bugfix --title "Double charge on retry" \
  --content "PAY-1234: the client retried on timeout. Cause: … Fix: …"
```

For long content, `--content -` reads it from stdin.

Do not save what is already in the code, the git history or the repo documentation, nor temporary task state.

## Update instead of duplicating

- **With `--topic-key`:** if the topic has a stable key, a second `save` updates the same observation. For example:
  - `project/profile`
  - `arch/queues`
  - `sdd/<change>/<artifact>`
- **Without `topic_key`:** if the save response includes `similar` (with the semantic index), review those observations.
  - If it is the same thing, update the existing one: save again with its `topic_key`, or delete it with `exo mem delete <id>`.
  - If it **contradicts** what was saved, do not pick one yourself: ask the user which one holds.

## At session close

Before finishing, or when the context is about to be compacted:

```bash
exo mem session summary --content "Done: … Pending: … Decisions: …"
```

The summary goes to the project's open session, or to a new one if there is none. The next `exo mem context` shows it first.

## Rules

- **Never save secrets, credentials or personal data.** Memory has no filter and can be exported as is.
- Do not make up memories: if `exo mem search` returns nothing, say so and keep investigating.
- If `exo` is unavailable or fails, say so in your answer and continue without memory. Do not simulate it with loose files.
