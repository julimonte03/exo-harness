# Project wiki guard

Two checkpoints that keep the branch and the project wiki (`.exo/context.md`) honest: one when a change starts, one before its PR. The orchestrator runs them inline; a phase skill used on its own runs the one that applies.

`.exo/context.md` is the project profile: stack, how to build and test, conventions, areas and their owners, known risks, and optionally the architecture, modules, main flows and integrations. The `project-onboarding` skill writes it; in an adoption with reverse engineering, `re-synthesize` (pack `discovery`) fills its optional sections. The engine never generates or overwrites it: the agent edits it, with the person's approval.

## At the start of a change

1. **Branch.** `git status` and `git branch --show-current`. On a protected branch (`governance.protected_branches` in `.exo/config.json`, by default `main`, `master`, `prod`, `production`), propose a branch for the change before writing anything (`branch-pr`). With uncommitted changes that are not part of this change, ask what to do with them.
2. **Up to date.** If the branch has an upstream, compare it (`git status -sb`). If it is behind, say so and ask before going on.
3. **Wiki present.** If `.exo/context.md` does not exist, suggest running `project-onboarding` first. Tier 1 can go on without it; Tier 3 and 4 should not.
4. **Wiki fresh.** Read it. If the change touches an area the wiki does not describe, or what it says contradicts the code you read, note it: it is a wiki update for the end of the change.
5. **Discovery fresh.** If the project has `.exo/discovery/` (it was adopted with reverse engineering), run `exo discover update --json`. It recomputes the inventory and the structure, and reports:
   - `stale_units`: closed units whose files changed since they were extracted;
   - `stale_capabilities`: capability specs with a `Status:` preamble whose cited files changed or were deleted since they were last recorded (`exo discover synthesized`). They stay stale until they are synthesized again;
   - `unrecorded_capabilities`: capability specs with a `Status:` preamble that were never recorded, so the engine cannot tell whether they are stale;
   - `changed_skipped_units`: units the adoption skipped whose files changed;
   - `new_files` and `deleted_files`.

   What to do with the report:
   - **A stale unit or capability that the change will touch** (its files or its capabilities, from the request and the code you read): note it, like a stale wiki. The wiki sections and those specs are an update for the end of the change.
   - **A change to a capability that is still `Status: as-is`:** tell the person now. `exo specs merge` refuses a delta on it until they validate the capability (`Status: as-is-validated`).
   - **Rewritten files:** `update` rewrites the inventory and structure files of `.exo/discovery/` when they changed. They are committed, so commit them with the change.
   - **No plan:** if it answers that there is no plan yet, skip the rest of this step.

## Before the PR

1. **Wiki update.** If the change altered something the wiki describes (a command, a dependency, a convention, an area, a module, a flow, an integration), update `.exo/context.md` in the same change, or ask the person to.
   - **Stale discovery.** In a project with `.exo/discovery/`, run `exo discover update --json` again: the change's own edits make their units stale too.
   - **Propose the update** of what it reports and the start noted: extract the stale units again and re-synthesize their `as-is` capabilities with the discovery skills (`exo-adopt` resumes from `exo discover status`), then update the wiki sections they feed. Do it after the change's commit: until then, the change's own files show up as changes outside discovery's paths, and `exo-adopt` would stop. A validated capability changes only through the change's own delta.
   - **Who does it:** do it in this change when the person agrees, or leave it to them as a note in the PR.
2. **Branch clean.** `git status`: everything that belongs to the change is committed (`work-unit-commits`) and nothing else is.
3. **Fresh review done.** In Tier 3 and 4, `verify-record.md` comes from a fresh-context verify: a subagent, or a new session when the agent has none. If the person chose an inline verify instead, the record says `no isolation`, as `.exo/shared/agent-capabilities.md` allows (in Tier 4, only with their approval recorded as a decision).
4. **Checks pass.** `exo check --change <change>` passes.

Report the result of each checkpoint in the envelope notes, for example: `wiki guard: branch feat/PROJ-123-add-login, up to date; context.md fresh`.
