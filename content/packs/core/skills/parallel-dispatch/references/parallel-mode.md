# Parallel mode: worktrees, delegation and recovery

The mechanics of mode 2 of `parallel-dispatch`. Every command runs from the project's main working folder unless it says otherwise. The examples use the change `PROJ-123-add-coupons` on the branch `feat/PROJ-123-add-coupons`, in a project folder named `shop`.

## Why worktrees

Subagents of one session share the disk. If several implementers worked in the same folder, each one's test runs would see the others' half-written files, and their commits would fight over the same git index. A worktree gives each unit its own folder and branch over the same repository: the units cannot see each other until you integrate them.

## Create the worktrees of a wave

```bash
git status                                   # clean, on the change branch
git rev-parse HEAD                           # the start commit of this wave: note it
git worktree add ../shop-PROJ-123-unit-a -b feat/PROJ-123-add-coupons-unit-a
git worktree add ../shop-PROJ-123-unit-b -b feat/PROJ-123-add-coupons-unit-b
git worktree list
```

- The folder goes **outside** the project folder (a sibling), so the project's tools, tests and searches never pick it up.
- The branch is `<change-branch>-unit-<letter>`, created from the change branch's current commit.
- The engine's git hooks are shared through the repository config, so they also run in the worktrees.
- If your agent can give each subagent an isolated worktree by itself, use that instead of creating them, and note each worktree's branch and start commit from the subagent's answer.

## The delegation prompt

One per unit, all the units of a wave in the same message so they run at the same time. Take the skill paths from `.exo/skill-registry.md`: `sdd-apply` and the Required and Conditional skills of the apply row of `.exo/shared/phase-skill-map.md`.

```markdown
## Skills to load before work

- <path to sdd-apply/SKILL.md>
- <path to code-generation/SKILL.md>
- <path to work-unit-commits/SKILL.md>
- <paths of the other apply skills of the map>

## Task

Change: PROJ-123-add-coupons (Tier 3). Change root: specs/PROJ-123-add-coupons/.
Implement only Unit B of tasks.md: task 2.

Work only in the folder ../shop-PROJ-123-unit-b, a git worktree on the branch
feat/PROJ-123-add-coupons-unit-b. Run every command from that folder.

Test command: python -m pytest -q. Baseline: 40 passed, 0 failed.

Rules:
- Touch only the files of Unit B (src/coupons/store.py, tests/test_coupon_store.py) and the boxes of
  Unit B in tasks.md. Another unit is working on the other files at the same time.
- Tests first. Commit each task as work-unit-commits says. Never push, never use --no-verify.
- Stop with needs-input if the unit needs a file, a dependency or a behavior outside it.

Return the envelope of sdd-apply, with the commits (hash and subject) and the test counts.
```

- The implementer does not know about the other units beyond that warning: pass nothing else from the conversation.
- It does not run `exo change record`; you record its skills from its envelope notes.

## Integrate a wave

With the start commit of the wave noted:

```bash
git switch feat/PROJ-123-add-coupons
git cherry-pick <start>..feat/PROJ-123-add-coupons-unit-a
# run the test command (see the skill, Integrate in order, step 4)
git cherry-pick <start>..feat/PROJ-123-add-coupons-unit-b
# run the test command again
```

- `<start>..<branch>` takes exactly the unit's commits, in order.
- The boxes of different units sit on different lines of tasks.md, so their ticks apply cleanly one after the other. Any conflict, in tasks.md or anywhere else, stops the run.
- The next wave starts from the new tip: note `git rev-parse HEAD` again before creating its worktrees.

## When an integration stops

**A conflict:**

```bash
git cherry-pick --abort                      # the change branch is back where it was
git log --oneline -3                         # the last good commit, for the report
```

Report the unit, the conflicting files (from the cherry-pick output) and the last good commit. The person decides: change the plan (`sdd-tasks`), or run that unit again in sequential mode on top of the integrated ones.

**Tests fail after an integration:** leave the branch as it is and report the unit, the failing tests and the output. Undoing it (`git reset --hard <last good commit>`) discards that unit's commits from the change branch; their copy stays on the unit branch. Run it only with the person's explicit confirmation.

**An implementer returns needs-input or blocked:** do not integrate that unit. Integrate the others of the wave, then bring its question to the person before the next wave. Its worktree stays for the retry.

## Clean up

```bash
git worktree remove ../shop-PROJ-123-unit-a
git worktree remove ../shop-PROJ-123-unit-b
git worktree prune
```

- `git worktree remove` refuses a folder with uncommitted changes: report what is there instead of forcing it.
- Keep the unit branches until the verify passes. Then, with the person's approval, `git branch -D feat/PROJ-123-add-coupons-unit-a`: git sees cherry-picked commits as unmerged, so `-d` refuses.
- Unit branches are local: never push them.
