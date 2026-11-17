---
name: pre-commit-review
description: >-
  Reviews what is about to be committed, read-only: the staged diff (or the
  working diff when nothing is staged), checked for scope, debug leftovers,
  secrets and personal data, whether the commit is one reviewable unit, and
  the message with its Refs footer. Returns findings and a result (ready to
  commit, or fix before committing); it never edits, stages or commits. Run
  it before every commit that work-unit-commits makes, and whenever someone
  wants a diff checked before committing. Triggers: "review my diff",
  "review before committing", "check the staged changes", "is this ready to
  commit", "pre-commit review", "look at my changes before I commit".
metadata:
  exo-pack: quality
  exo-execution: inline
  exo-permissions: read-only
---

# pre-commit-review

## Result

A list of findings on what is about to be committed, each with a severity, where it is (`path:line`, or `message`), what is wrong and the fix as text, and a last line with the result: `Result: ready to commit`, `Result: fix before committing`, or `Result: nothing to commit` when nothing is staged nor changed. Nothing changes: no file, no index, no commit.

## When

- Before every commit of skill:work-unit-commits: after staging the unit, before `git commit`. When the result is `fix before committing`, the caller fixes, stages again and runs this skill again.
- When someone asks to check their changes before committing.

It is not the review of the whole change (skill:harness-review, in verify) and it does not replace the git hooks: it runs earlier, and it reads intent and context that a hook cannot.

## Permissions

- Read-only: `git status`, `git diff --staged`, `git diff`, `git log`, `git show`, `git branch --show-current`, reading files, and `exo hook pre-commit`, which checks the staged lines and changes nothing.
- Never `git add`, `git restore`, `git reset`, `git stash` or `git commit`, and never edit a file. Say what to do; the caller does it.

## Read

1. `git status`: what is staged, unstaged and untracked.
2. `git diff --staged`. If nothing is staged, `git diff`, and say that you reviewed the working diff. Open the changed files where a hunk needs context.
3. The unit: the task of `tasks.md` (Tier 3 and 4), the proposal's Scope (Tier 1 and 2), or what the person asked for outside SDD.
4. The proposed commit message, when there is one.
5. `.exo/config.json`: `tickets.pattern`, `tickets.example` and `governance.protected_branches`. Inside an SDD change, its `ticket_key` (`exo change ai-usage <change> --json`).

## Checks

### 1. Scope

- Every staged hunk belongs to the unit. Flag unrelated refactors, reformatting of code the unit did not touch, files of another task, generated files nobody asked for, and lockfile changes the unit does not need.
- The unit is complete: the code and its tests are both staged, and no staged file depends on an unstaged one (that commit would not build).
- The current branch is not a protected branch.

### 2. Debug leftovers

Prints and logs added for debugging, `breakpoint()`, `debugger`, commented-out code, focused or skipped tests without a reason (`.only`, `fit`, a bare skip), hard-coded local paths or ports, temporary files, and a new `TODO` without an owner or a ticket. Existing `TODO`s are not yours to remove.

### 3. Secrets and personal data

- Run `exo hook pre-commit`: the same scan the hook runs on the staged lines (credentials always, personal data with the detectors of `data_protection.pii`, the waivers in force), plus the block on credential files and the speclint of staged SDD artifacts. Each error it prints is a finding.
- Then read for what a scanner misses: real-looking names, emails, account or ID numbers in fixtures, logs and examples; credentials split across lines or hidden in config; content copied from a `.env` file. The levels and the rules are in `.exo/shared/data-protection.md`.
- Never copy the value into a finding: give `path:line` and the kind. A credential has to be removed, and rotated if it was real. Never suggest `--no-verify`, and never add or widen a waiver: only the `tech_lead` role approves one.

### 4. One reviewable unit

- One purpose: the subject can say it without "and". The tests go in the same commit as the code they test.
- The test command of `.exo/context.md` ran for this unit and passed (skill:work-unit-commits runs it before committing). If it did not run, say so.
- Small enough to review in one sitting. Past a few hundred changed lines, propose a split by task or by scenario.
- The change's artifacts (`proposal.md`, `spec.md`, `ai-usage-record.json` and the rest) go in their own `docs` unit or with the unit they describe.

### 5. Message and `Refs:`

- Subject `<type>(<scope>): <summary>`, with a type from skill:work-unit-commits, in the imperative, starting lowercase, without a final period, up to 72 characters. The body says why the unit exists and which task or scenarios it covers. A breaking change has `!` and a `BREAKING CHANGE:` footer.
- With a ticket pattern and a `ticket_key` in the record, the last footer is `Refs: <ticket>` with the exact ID the person confirmed. Without a pattern, or without a `ticket_key`, no ID appears anywhere in the message.
- A ticket in the subject instead of the footer, an ID that does not match `tickets.pattern`, or an ID taken from the branch name or from earlier commits is a finding.
- When the message is already in a file, `exo hook commit-msg <file>` checks it with the hook's rules.

## Severity and result

| Severity | Examples |
|---|---|
| Critical | A secret or a credential file in the diff |
| High | Personal data without a waiver; a commit on a protected branch; a commit that would not build or leaves the unit's tests out; a message the `commit-msg` hook would reject; an inferred or invented ticket |
| Medium | Out-of-scope hunks; debug leftovers; a unit too large to review |
| Low | Wording of the message, a body without the why, naming |

- Any Critical or High finding: `Result: fix before committing`.
- Medium: fix them, unless the person accepts one explicitly; say which.
- Only Low, or nothing: `Result: ready to commit`, with the Low findings as suggestions.

## Answer

```markdown
## Review of the staged diff

| Severity | Where | Finding | Fix |
|---|---|---|---|
| Critical | config/settings.py:14 | A database password is assigned in code | Read it from `${DB_PASSWORD}`; rotate it if it was real |
| Medium | src/auth/sso.py:88 | `print(response)` left from debugging | Remove the line |
| Low | message | The body does not say which task this covers | Add "Task 1.2 of tasks.md" |

Result: fix before committing (1 Critical, 1 Medium).
```

When nothing is wrong, say so in one line and end with `Result: ready to commit`. When there is nothing to review (no staged, unstaged or untracked changes), say so and end with `Result: nothing to commit`.

## Record

Inside an SDD change, add this skill to the AI Usage Record once (`.exo/shared/capability-attribution.md`); later runs do not duplicate it:

```bash
exo change record <change> --add capabilities_used '{"name": "pre-commit-review", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
```

In a subagent (the implementer commits during apply), list it in the envelope notes instead: subagents never run `exo change record`.
