---
name: branch-pr
description: >-
  Names the branch of a change as <type>/<change-name>, keeps work off the
  protected branches, runs the checks that come before a pull request (the
  project wiki checkpoint, exo check and the fresh review), writes the PR
  description from the pr.md template, and pushes and opens the PR only when
  the person asks, showing the commands first. Use it when a change starts on
  a protected branch, when the work is ready for review, or when asked to
  create a branch or a pull request. Triggers: "create a branch", "open a
  PR", "create PR", "prepare the pull request", "ready for review", "push
  this".
metadata:
  exo-pack: core
  exo-execution: inline
---

# branch-pr

## Result

The change lives on its own branch, `<type>/<change-name>`, created from the target branch and holding only the change's commits. Before the pull request, the wiki checkpoint, `exo check` and the fresh review have passed. The PR description follows `.exo/shared/templates/pr.md` and passes `exo speclint`. The push and the PR happen only when the person asks, after you show the exact commands.

## Branch

- **Name:** `<type>/<change-name>`. The type is the Conventional Commits type of the main change: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci` or `chore`. The change name is the one `exo change new` built, with the ticket already normalized:
  - `feat/PROJ-123-add-login`
  - `fix/AB-77-null-total` (the ticket `AB#77`, normalized)
  - `docs/update-setup-guide` (no ticket)
- Outside an SDD change, use `<type>/<slug>`, with a lowercase kebab-case slug.
- **Never work on a protected branch.** The list is `governance.protected_branches` in `.exo/config.json` (by default `main`, `master`, `prod`, `production`). If the current branch is protected, propose the change's branch before writing anything:

```bash
git status
git branch --show-current
git fetch origin
git switch -c feat/PROJ-123-add-login origin/main
```

- Create it from the branch the PR will target, up to date. With uncommitted changes that are not part of the change, ask the person what to do with them before switching.
- Never push to a protected branch, never use `--force` on one, and never use `--no-verify`.
- This section is step 1 (Branch) of the checkpoint At the start of a change in `.exo/shared/project-wiki-guard.md`.

## Before the PR

Run the checkpoint Before the PR of `.exo/shared/project-wiki-guard.md`, in this order:

1. **Wiki update.** If the change altered something `.exo/context.md` describes (a command, a dependency, a convention, an area), update it in the same change, or ask the person to. With `.exo/discovery/` in the project, also run `exo discover update --json` and propose the update of the stale units and capabilities, as the guard says.
2. **Branch clean.** `git status`: everything that belongs to the change is committed (skill:work-unit-commits), and nothing else is.
3. **Fresh review done.** `verify-record.md` exists and its Verdict is `ready`. In Tier 3 it comes from a verify in fresh context; without subagents, from a new session (`.exo/shared/agent-capabilities.md`). `exo change followups <change> --json` shows no open findings.
4. **Checks pass.** `exo check --change <change>` exits with 0. In CI, the same check runs as `exo check --base <target branch>`, for example `exo check --base origin/main`.
5. **Size.** `git diff --shortstat <target branch>...HEAD`. Over about 400 changed lines, offer skill:chained-pr to deliver the change as a chain of smaller PRs; the person decides. When the plan already chose a chain (the Forecast of tasks.md), follow it.

- `exo check --change <change>` finds the change before and after `sdd-archive` moves it to `archive/`, and `exo check --base <target branch>` checks what the branch touched, archived changes included.
- If a step fails, stop: fix it in the phase that owns it, or ask the person.
- Report each checkpoint in the envelope notes, for example: `wiki guard: branch feat/PROJ-123-add-login, up to date; context.md updated (Commands); exo check passed`.

## PR description

Start from `.exo/shared/templates/pr.md`. Every section needs real content; the template comments do not count.

- **Title:** `<type>(<scope>): <description>`, with the same type as the branch, in the imperative, up to 72 characters: `feat(auth): add SSO sign-in for employees`.
- **Summary:** what changes and why, in 2 to 4 lines, from the Intent of `proposal.md`.
- **Ticket:** the exact `ticket_key` of the change (`exo change ai-usage <change> --json`), for example `AB#77` and not the normalized `AB-77`. If it is null, write `none`. Never infer it from the branch.
- **Changes:** bullets with the relevant changes, and the change's artifacts (the spec delta, the design).
- **Test Plan:** the exact commands and their results, as in the Tests section of `verify-record.md`.
- **Known followups:** every finding deferred to a followup, with its ID or `path:line`, severity and one line: the dismissals of `exo change followups <change> --status dismissed --json` whose reason starts with `deferred to a followup`, and the decisions of `exo change ai-usage <change> --json` that start the same way. Write `None` when there are none.
- **Checklist:** the template items as real lines, ticked only when true:

```markdown
- [x] Tests added or updated
- [x] speclint and check green
- [x] AI Usage Record updated
```

Save it as `pr.md` in the change root (`exo change status <change> --json` gives its `path`; after `sdd-archive`, the archived folder) and commit it with the change. Check it:

```bash
exo speclint <change-root>/pr.md
```

## Push and open the PR

Only when the person asks. Show the commands first, with the real values, and run them only after they agree:

```bash
git push -u origin feat/PROJ-123-add-login
gh pr create --base main --head feat/PROJ-123-add-login \
  --title "feat(auth): add SSO sign-in for employees" \
  --body-file specs/archive/2026-11-14-PROJ-123-add-login/pr.md
```

- `gh` is the GitHub CLI. On another host, use its CLI or the link that `git push` prints, with the same title and body.
- Give the person the full URL of the PR.
- **Publish the gates** once the PR exists: `exo gate publish --change <change>`. With `review.publish_command` configured, it keeps one PR comment per gate; without it, it prints one text per gate: give them to the person to paste as PR comments. If it answers that the command is not approved on this machine, show the person that command and the project files the message lists, and ask them to approve it themselves (`exo gate publish --change <change> --approve-command '<the exact command>'`); never pass that flag for them. Host examples are in `.exo/shared/ci-and-review.md`.
- The work is done when CI is green. If CI fails, fix it with new commits on the same branch. Never force-push: the pre-push hook blocks it, and rewriting a pushed branch is the person's decision, which they carry out themselves.

Record this skill and the checks that ran in the change's AI Usage Record (skill:ai-usage-record).

## Rules

- Never push or open a PR without the person asking for it.
- Never push directly to a protected branch, never `--force`, never `--no-verify`.
- One change per branch; the PR carries only that change's commits.
