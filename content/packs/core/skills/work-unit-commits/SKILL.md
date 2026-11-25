---
name: work-unit-commits
description: >-
  Commits a change as reviewable work units with Conventional Commits: one
  commit per task of tasks.md or per coherent part, with only that unit's
  files, the ticket as a Refs footer when the change has one, no secrets and
  the hooks always run. Use it whenever you are about to commit, when a task
  or scenario is done, or when splitting work into commits. Triggers:
  "commit this", "make a commit", "split into commits", "commit message",
  "what goes in each commit".
metadata:
  exo-pack: core
  exo-execution: inline
---

# work-unit-commits

## Result

Every reviewable unit of the change is one commit: a Conventional Commits message, only that unit's files, its tests in the same commit, the hooks run and passed, no secrets, and the exact ticket as a `Refs:` footer when the change has one. A reviewer can read the commits one by one and follow the change.

## When

- In the apply phase: when a task's tests pass, commit that task.
- Outside an SDD change: only when the person asks.
- Never on a protected branch (`governance.protected_branches` in `.exo/config.json`): switch to the change's branch first (skill:branch-pr).

## The unit

- **Tier 3:** one task of `tasks.md`. Join tasks only when they cannot pass their tests apart.
- **Tier 1 and 2:** one coherent part: a scenario with its test and code, a refactor the plan asked for that prepares it, the docs update.
- **The change's artifacts** (`proposal.md`, `spec.md`, `design.md`, `tasks.md`, `test-spec.md`, `verify-record.md`, `ai-usage-record.json`) belong to the change: commit them in their own `docs` unit, or with the unit they describe.
- Each commit leaves the build and the tests green: run the test command before committing.
- The tests go in the same commit as the code they test.
- One unit, one purpose. Formatting of code you did not change, unrelated fixes and generated files nobody asked for stay out.
- Keep it small enough to review in one sitting. When a unit grows past a few hundred changed lines, split it.

## The message

```text
feat(auth): add SSO sign-in endpoint

Redirect employees to the identity provider and create the session
on the callback. Covers S-1 and S-2 (task 1.2 of tasks.md).

Refs: PROJ-123
```

- **Subject:** `<type>(<scope>): <summary>`.
  - Type: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore` or `revert`.
  - Scope: the area or module, as named in `.exo/context.md` (Areas). It is optional.
  - Summary: in the imperative, starting lowercase, without a final period; the whole subject up to 72 characters.
- **Body:** why the unit exists and which task or scenarios it covers. Wrap it at 72 characters.
- **Breaking change:** `!` after the type or scope (`feat(api)!: …`) and a `BREAKING CHANGE: <what breaks>` footer.
- **Language:** English, unless the Conventions of `.exo/context.md` say otherwise.

## The ticket

- When the change has a ticket, its `ticket_key` is in the record (`exo change ai-usage <change> --json`). Add it as the last footer with the exact ID the person confirmed: `Refs: AB#77`, not the normalized `AB-77` of the folder.
- No ticket pattern (`tickets.pattern` is null in `.exo/config.json`): no ID anywhere in the message.
- A pattern, but `ticket_key` is null: the change has no ticket, so no ID.
- Never infer the ticket from the branch name, earlier commits or the conversation.
- Outside an SDD change, with a pattern, ask once: "Is there a ticket for this commit? It looks like `<tickets.example>`. Leave it empty if not." (Ask in the person's language.)

## Staging

```bash
git status
git diff
git add src/auth/sso.py tests/test_sso.py
git diff --staged
```

- Stage by path. Use `git add -A` or `git add .` only when every changed file belongs to the unit.
- Files that do not belong to the change stay unstaged; mention them to the person.
- Read `git diff --staged` before every commit: it is exactly what goes in. With the quality pack, run `pre-commit-review` on it first; without it, re-read it for scope, debug leftovers, secrets and personal data.

## Secrets

- In the staged diff, look for credentials, tokens, private keys, `.env` files, connection strings with passwords and personal data.
- If you find any: unstage it, tell the person, and do not commit.
- If a secret is already in a commit: stop and tell the person. It has to be rotated, and rewriting history needs their confirmation.

## Commit

```bash
git commit -m "feat(auth): add SSO sign-in endpoint" -m "Redirect employees to the identity provider and create the session on the callback. Covers S-1 and S-2." -m "Refs: PROJ-123"
```

Or write the message to a file and use `git commit -F <file>`.

- **Never skip the hooks:** no `--no-verify`, no `-n`. Never bypass signing.
- If a hook fails, the commit was not made: read its output, fix the cause, stage again and commit again.
- Do not amend or rebase commits that were already pushed without the person's confirmation.

## Rules

- One reviewable unit per commit, with its tests.
- Only the change's files; nothing that is not part of the unit.
- The exact ticket as `Refs: <ticket>` only when the change has one; never an inferred or invented ID.
- No secrets, ever.
