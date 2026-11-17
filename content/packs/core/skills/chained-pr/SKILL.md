---
name: chained-pr
description: >-
  Splits a change that is too big for one review (over about 400 changed
  lines, by the sdd-tasks forecast or the real diff) into chained pull
  requests, each one built on the previous: a cut plan along tasks or units,
  branches named <type>/<change>-part-<n>, the base and merge order of each
  PR, how to carry a fix in an earlier part up the stack without rewriting
  pushed branches, and the body of each PR from the pr.md template. Host
  agnostic: plain git, and the host's CLI only when the project has it. Use
  it when a change or a branch is too large to review in one go, when the
  forecast is over budget and the person keeps a single change, or when
  someone asks for stacked or chained PRs. Triggers: "split the PR", "this PR
  is too big", "stacked PRs", "chained PRs", "break this into smaller PRs",
  "PR over 400 lines", "review in slices", "smaller pull requests".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: read-write
---

# chained-pr

## Result

- **A cut plan the person approved:** the parts, each with its tasks, its size (about 400 changed lines or less), its branch, its base and its place in the merge order.
- **The branches** `<type>/<change-name>-part-<n>`, each on top of the previous one, built from the existing commits or as the work goes, only when the person asks.
- **A body per PR** from `.exo/shared/templates/pr.md`, with the part's place in the stack, passing `exo speclint`.
- Pushes, PRs and merges happen only when the person asks, after you show the commands (skill:branch-pr).
- The plan recorded as a decision in the change's AI Usage Record.

## When

- The size forecast of tasks.md (`sdd-tasks`, Size forecast) is over about 400 changed lines and the person keeps a single change.
- The real diff is over budget: `git diff --shortstat origin/<target>...HEAD` gives insertions plus deletions above about 400.
- skill:branch-pr offers it before opening a PR that is over budget.
- On request: "split this PR", "stacked PRs".
- **Not for:** parts that deliver value on their own and could ship apart, which are better as separate changes (`sdd-new`); a change within budget.

**Measure what a reviewer reads.** Leave lockfiles, generated files and snapshots out of the count, and say so:

```bash
git diff --shortstat origin/main...HEAD -- . ':!package-lock.json' ':!**/__snapshots__/**'
```

## Plan the cuts

1. **Cut between tasks, never through one.** Each task is one commit (skill:work-unit-commits), so the cuts fall on commit boundaries.
2. **One theme per part,** small enough for one sitting: a unit of tasks.md, or a layer (data, logic, interface). About 400 changed lines or less.
3. **Dependencies first:** follow the order of tasks.md and the `Depends on` lines of its units. Foundations (data model, pure modules) go early; wiring and UI go last.
4. **Each part works alone,** on top of the previous parts: it builds, its tests pass, and merging it leaves the target branch working. New code stays unreachable until the part that wires it, or behind a flag the design names. If a part cannot be safe alone, say so: the stack then merges into the change's branch instead (Strategy).
5. **Where the SDD artifacts go:**
   - **Part 1** carries the change root (proposal, spec, design, tasks, test-spec, the fitness assessment and the AI Usage Record), so reviewers start from the plan and `exo check --base` passes from the first PR.
   - **The last part** carries the verify record, the gates, the archive and `pr.md` (skill:branch-pr). The verify runs on the whole change, at the top of the stack (`git diff origin/<target>...<last part>`). Parts can be reviewed earlier, but none merges before that verify says `ready`.
6. **Two to five parts.** More than five suggests separate changes.

Show the plan and ask for approval before creating anything:

```text
Cut plan for PROJ-123-add-coupons: about 960 changed lines -> 3 parts

| Part | Branch | Base | Tasks | Lines | A reviewer checks |
|---|---|---|---|---|---|
| 1 | feat/PROJ-123-add-coupons-part-1 | main | the change root; 1-4 (Unit A) | ~330 | the plan and the coupon rules |
| 2 | feat/PROJ-123-add-coupons-part-2 | part 1 | 5-8 (Unit B) | ~340 | storage and expiry |
| 3 | feat/PROJ-123-add-coupons-part-3 | part 2 | 9-11 (Unit C); verify, archive, pr.md | ~290 | the checkout endpoint |

Merge order: 1, 2, 3. Each part leaves main working: the endpoint is wired only in part 3.
```

The type in the branch is the change's Conventional Commits type, as skill:branch-pr names branches; the change name is the one `exo change new` built.

## Strategy

| Strategy | PR bases | Use it when |
|---|---|---|
| **Stacked onto the target** (default) | PR 1 targets the target branch; PR n targets part n-1 | every part is safe to merge alone |
| **Into the change's branch** | PR 1 targets `<type>/<change-name>`, created from the target; PR n targets part n-1; once all are merged there, one final PR takes that branch to the target | a part cannot be safe alone in the target |

Ask when it is not obvious. With the second strategy, the final PR holds no new code: its description lists the reviewed parts.

## Build the branches

**The work is done,** on one branch, with one commit per task in plan order: point a branch at the last commit of each part. Nothing is rewritten.

```bash
git log --oneline --reverse origin/main..feat/PROJ-123-add-coupons
git branch feat/PROJ-123-add-coupons-part-1 <last commit of task 4>
git branch feat/PROJ-123-add-coupons-part-2 <last commit of task 8>
git branch feat/PROJ-123-add-coupons-part-3 feat/PROJ-123-add-coupons
```

**The commits are not in part order** (fixups, a task spread over several commits): build new branches with `git cherry-pick`, part by part, and leave the original branch as it is. Then `git diff feat/PROJ-123-add-coupons feat/PROJ-123-add-coupons-part-3` must be empty. The commands are in `references/stack-commands.md`.

**The work is not done:** create part 1 from the target, implement its tasks (`sdd-apply`), then create part 2 from part 1, and so on.

**Check each part alone** before pushing it: `git switch` to it and run the exact test command of `.exo/context.md`. In a change, an `sdd-implementer` can run it for you; the read-only `sdd-verifier` never switches branches. A part that fails alone means the cut is wrong: move tasks between parts and show the new plan. CI then runs on every PR.

## PR bodies

Start each one from `.exo/shared/templates/pr.md`, with real content in every section:

- **Title:** `<type>(<scope>): <description> (part <n>/<N>)`, up to 72 characters.
- **Summary:** first line `Part <n> of <N> of <change-name>. Base: <branch of part n-1>. Merge after part <n-1>.` (part 1: `Base: <target>.`), then what this part adds and why.
- **Ticket:** the same exact `ticket_key` in every part (`exo change ai-usage <change> --json`), or `none`. Never infer it from the branch.
- **Changes:** the tasks of this part by number and title; part 1 also lists the change's artifacts.
- **Test Plan:** the commands run on this part's branch and their results.
- **Checklist:** the template items, ticked only when true for this part.

Save each body as `pr-part-<n>.md` in the change root and check it with `exo speclint <change-root>/pr-part-<n>.md --type pr`. The last part's body is the change's `pr.md`, which skill:branch-pr writes, with the whole stack listed in its Summary. Commit the `pr-part-<n>.md` files in the last part, together with `pr.md`; until then, stage files by name so they do not slip into an earlier part.

## Push and open the PRs

Only when the person asks. Show the exact commands first, then run them in order:

```bash
git push -u origin feat/PROJ-123-add-coupons-part-1
git push -u origin feat/PROJ-123-add-coupons-part-2
git push -u origin feat/PROJ-123-add-coupons-part-3
```

- Open PR 1 against the target and PR n against part n-1, each with its body. Use the host's CLI only when the project has it (`references/stack-commands.md` has examples per host); otherwise use the link `git push` prints and pick the base branch in the host's form.
- Open the PRs after the first as drafts when the host supports it, so nobody merges them out of order.
- Publish the gates on the last PR, as skill:branch-pr says.

## When an earlier part changes

Review feedback on part k:

1. **Fix it on part k** with a new commit. Never amend or rebase a pushed commit.
2. **Carry it up, in order:** for each later part, `git switch <part j>` then `git merge <part j-1>`. The pushes stay fast-forward, which the engine's pre-push hook allows.
3. **A conflict stops you:** show the files and resolve them with the person; then run the tests on that part before going on.
4. **Not pushed yet?** A rebase keeps the history linear: from the top part, `git rebase --update-refs <part k>` moves every later part at once (git 2.38 or later; `references/stack-commands.md`). Never on pushed branches: rewriting them needs a force-push, which the hook blocks and the project rules leave to the person, who runs it themselves if they decide to.
5. Re-run the verify at the top of the stack when the fix changes behavior.

## After a part merges

- **Merge in order:** part n only after part n-1.
- **Retarget the next PR** to the target branch. Some hosts do it when the merged base branch is deleted; otherwise change the base in the PR or with the host's CLI.
- **Merge commit or fast-forward:** the next PR now shows only its own commits.
- **Squash merge:** the target holds part n as one new commit while the next part still carries the original ones. Update without rewriting: `git switch <part n+1>`, `git fetch origin`, `git merge origin/<target>`; the PR then shows only its own changes. A conflict stops you, as above. Prefer a merge strategy that keeps the commits when the project allows it.
- Delete merged part branches through the host, or with the person's approval.

## Record

Inside a change (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "chained-pr", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"chained-pr"'
exo change record <change> --add decisions '{"summary": "Review split into 3 chained PRs: Unit A; Unit B; Unit C with verify and archive", "rationale": "about 960 changed lines", "by": "human"}'
```

`activation` is `requested` when the person asked for chained PRs. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Rules

- Never push, open a PR or merge without the person asking; show the commands first.
- Never force-push, never `--no-verify`, never push to a protected branch, never rewrite a pushed branch.
- Never cut through a task; every part builds and passes its tests alone.
- The same ticket in every part, exactly as the person confirmed it.

## Before you finish

- [ ] The plan shows each part's tasks, size, branch, base and merge order, and the person approved it.
- [ ] Part 1 carries the change root; the last part carries the verify, the archive and `pr.md`.
- [ ] Each part was checked alone, or the check is listed as pending.
- [ ] Each PR body follows the template and passes speclint.
- [ ] Nothing was pushed, opened or merged without the person asking; no pushed branch was rewritten.
- [ ] The plan is recorded as a decision.
