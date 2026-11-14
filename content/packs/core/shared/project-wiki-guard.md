# Project wiki guard

Two checkpoints that keep the branch and the project wiki (`.exo/context.md`) honest: one when a change starts, one before its PR. The orchestrator runs them inline; a phase skill used on its own runs the one that applies.

`.exo/context.md` is the project profile: stack, how to build and test, conventions, areas and their owners, known risks. The `project-onboarding` skill writes it. The engine never generates or overwrites it.

## At the start of a change

1. **Branch.** `git status` and `git branch --show-current`. On a protected branch (`governance.protected_branches` in `.exo/config.json`, by default `main`, `master`, `prod`, `production`), propose a branch for the change before writing anything (`branch-pr`). With uncommitted changes that are not part of this change, ask what to do with them.
2. **Up to date.** If the branch has an upstream, compare it (`git status -sb`). If it is behind, say so and ask before going on.
3. **Wiki present.** If `.exo/context.md` does not exist, suggest running `project-onboarding` first. Tier 1 can go on without it; Tier 3 and 4 should not.
4. **Wiki fresh.** Read it. If the change touches an area the wiki does not describe, or what it says contradicts the code you read, note it: it is a wiki update for the end of the change.

## Before the PR

1. **Wiki update.** If the change altered something the wiki describes (a command, a dependency, a convention, an area), update `.exo/context.md` in the same change, or ask the person to.
2. **Branch clean.** `git status`: everything that belongs to the change is committed (`work-unit-commits`) and nothing else is.
3. **Fresh review done.** In Tier 3 and 4, `verify-record.md` comes from a fresh-context verify: a subagent, or a new session when the agent has none. If the person chose an inline verify instead, the record says `no isolation`, as `.exo/shared/agent-capabilities.md` allows (in Tier 4, only with their approval recorded as a decision).
4. **Checks pass.** `exo check --change <change>` passes.

Report the result of each checkpoint in the envelope notes, for example: `wiki guard: branch feat/PROJ-123-add-login, up to date; context.md fresh`.
