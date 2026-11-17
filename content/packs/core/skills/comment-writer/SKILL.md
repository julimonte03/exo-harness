---
name: comment-writer
description: >-
  Drafts collaboration text that is clear, actionable and kind: code
  comments that explain why, pull request review comments with their
  severity (blocking or not) and a concrete suggestion, replies to review
  feedback and to issues, and messages for the team's chat (questions,
  status updates, hand-offs, announcements). It keeps the tone warm and
  direct, talks about the code and never about the person, and keeps
  secrets, personal data and production data out of every text. It drafts;
  the person posts. Use it when writing or answering review comments, adding
  or cleaning up comments in code, replying on an issue, or writing an async
  message for the team. Triggers: "write a review comment", "how do I say
  this in the PR", "reply to this review", "comment this code", "this
  comment sounds harsh, rewrite it", "write a message to the team", "status
  update for the channel".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: read-only
---

# comment-writer

## Result

A draft ready to post, in the shape of where it goes: a code comment, a review comment, a reply, an issue reply or a team message. Every draft has one purpose, the context its reader needs, the ask or the information, the severity or urgency when it matters, and a tone that fits. The person posts it: this skill never posts, sends or edits anything outside the conversation.

## When

- **Reviewing a pull request,** or answering the review of yours.
- **Adding or cleaning up comments** in code.
- **Replying** on an issue or a discussion thread.
- **Writing to the team:** a question, a status update, a hand-off, an announcement.
- **Rewriting a draft** that sounds harsh, vague or too long.
- **Not for:** judge findings and gates, which have their own formats (`.exo/shared/judge-common.md` and the gate template); PR descriptions (skill:branch-pr); commit messages (skill:work-unit-commits); bug reports and feature requests (skill:issue-creation); documentation (skill:cognitive-doc-design).

## Inputs

1. **What it is about:** the code or the diff (`path:line`), the thread so far, the item or the channel.
2. **The reader:** the author of the code, a reviewer, the team, a stakeholder; what they know, and whether they read in their second language.
3. **The purpose:** ask, inform, request a change, praise, or get a decision.
4. **The team's conventions:** the review labels they use, the language of their comments, the docstring style, the TODO format. Look at recent reviews and at the code; the team's habits win over the defaults here.

## Steps

Before-and-after examples for every kind of text are in `references/examples.md`; the tone substitutions and the severity scale in `references/tone-and-severity.md`.

1. **Purpose and reader.** One line: "`<reader>` needs to `<know or do>` because `<why>`."
2. **Shape.** Pick the kind below and follow its rules.
3. **Draft.** The point first, then the context, then the ask and its severity or deadline.
4. **Tone pass.** Remove blame and condescension ("obviously", "just", "simply", "why didn't you"), sarcasm and absolutes. Talk about the code ("this function"), not the person ("you"). Ask when you are not sure. Stay firm and clear when something blocks: kind is not vague.
5. **Clarity pass.** Short, specific (`path:line`, numbers, the exact error), one ask per message, no jargon the reader does not share, no idioms for readers in their second language.
6. **Safety pass.** No secrets, no personal data, no customer identifiers, no raw production logs: point at `path:line` or describe the data. Review hosts, trackers and chat are external systems: Internal data only on the organization's own (`.exo/shared/data-protection.md`, section C).
7. **Deliver** the draft, with one line on any choice the person may want to change (the severity, a softer or firmer option).

## Code comments

- **Why, not what.** The code says what it does; the comment says why: the intent, a constraint, a non-obvious decision, a workaround and its reason, with a link to the spec, the decision record or the ticket.
- **Delete** comments that repeat the code, are out of date, or are commented-out code: version control keeps the history.
- **TODO and FIXME** say what, why and when it can go. With a ticket pattern (`tickets.pattern` in `.exo/config.json`), use an ID the person confirmed: `TODO(PROJ-123): drop the fallback once all clients send the version header`. Never invent an ID; without a pattern, write the condition instead.
- **Docstrings** follow the project's style (Google, NumPy, JSDoc, Javadoc) and state the contract: parameters, return value, errors raised, side effects.
- **Language:** the one the code's comments already use.

## Review comments

- **One comment, one point,** anchored to its line.
- **A label and a severity** first, in the team's convention. By default: `issue (blocking):`, `suggestion (non-blocking):`, `question:`, `nitpick (non-blocking):`, `praise:`.
- **Then:** what you see (at `path:line`), why it matters (a bug, a security hole, data loss, a broken contract, readability), and a concrete suggestion: the code, when the host supports suggestion blocks.
- **Blocking** only for correctness, security, data loss, a broken contract or missing tests for the change. Style a linter could catch is a suggestion to add the rule, not a comment per line.
- **Praise** what is good, specifically.
- **Many comments:** open with a summary that lists the blocking points, so they are not lost among nitpicks.

## Replies to review feedback

- Thank briefly, then answer the point: agreed and done (with the commit), a disagreement with its reason and an option (a follow-up item, a short call), or a question.
- After two rounds on the same point, propose a call or a decision by the code owner, instead of a third long reply.
- Resolve a thread when the reviewer agrees, or as the team's convention says.

## Issue replies

Acknowledge, say what is known and what is not, the next step and who takes it (a role), and when the next update comes. Ask for what is missing to reproduce it (the version, the steps, the expected and actual result), never for credentials or personal data.

## Team messages

- **Async first:** the message stands on its own, with the context, the ask or the information, the deadline or urgency, and a link to the item or thread.
- **The point in the first line:** "Need a reviewer for PR `<ref>` by Thursday: 120 lines, rounding in payments."
- **One topic per message,** replies in a thread, and mentions only for people who must act.
- **Status update:** done, next, blocked (with what would unblock it).
- **Hand-off:** where things stand, what is in progress, what comes next, the risks, where everything is, and who to ask.
- **Announcement:** what changes, for whom, from when, what they have to do, and where to ask.
- Plain Markdown that most chat tools render: short lines, bullets, code spans; no tables in chat.

## Return

```markdown
Before:
> Why are you catching Exception here? This is wrong.

After:
> **issue (blocking):** `src/billing/export.py:42` catches every exception and returns an empty list, so a
> database outage looks like "no invoices" to the caller and the export uploads an empty file.
> Could we catch only `RecordNotFound` here and let the rest propagate? The retry in `jobs/export.py:18`
> already handles connection errors.
```

Note: kept it blocking because it can upload an empty export; a softer option is to ask first ("Is the empty list intended when the database is down?").

## Rules

- **Draft only.** Never post, send, resolve or edit comments, issues or messages; the person does.
- **About the code, never the person.**
- **Severity is explicit** in every review comment.
- **No secrets, personal data or customer data** in any text; point at the location instead.
- **The team's conventions win** over the defaults of this skill.

## Record

Usually there is nothing to record: the drafts live in the conversation. When a phase of an SDD change loaded this skill (for example to answer review comments before archive), add it before that phase's envelope (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "comment-writer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The draft has one purpose, and its first line says it.
- [ ] Review comments carry a label and a severity, the reason, and a concrete suggestion.
- [ ] The tone talks about the code, asks when unsure, and is firm only where something blocks.
- [ ] No secrets, personal data, customer identifiers or raw production logs.
- [ ] TODOs use a confirmed ticket ID or a condition, never an invented ID.
- [ ] The person knows the draft is theirs to post.
