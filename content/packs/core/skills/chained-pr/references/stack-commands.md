# Stack commands

Git commands for each step of `chained-pr`, and host examples. The examples use the change `PROJ-123-add-coupons`, the target `main`, and three parts. Show every command to the person before running anything that pushes or changes a branch they already have.

## Measure

```bash
git fetch origin
git diff --shortstat origin/main...HEAD
git diff --stat origin/main...HEAD -- . ':!package-lock.json' ':!**/__snapshots__/**'
```

- Changed lines are insertions plus deletions. The three dots compare against the merge base, so commits that reached `main` meanwhile do not count.
- Per task, when each task is one commit: `git log --reverse --format='%h %s' --shortstat origin/main..HEAD`.

## Build the parts from scattered commits

When the commits are not in part order, build new branches and keep the original one as the reference:

```bash
git switch -c feat/PROJ-123-add-coupons-part-1 origin/main
git cherry-pick <commits of part 1, oldest first>
git switch -c feat/PROJ-123-add-coupons-part-2
git cherry-pick <commits of part 2, oldest first>
git switch -c feat/PROJ-123-add-coupons-part-3
git cherry-pick <commits of part 3, oldest first>
git diff feat/PROJ-123-add-coupons feat/PROJ-123-add-coupons-part-3   # must print nothing
```

- A cherry-pick conflict means a commit depends on one in a later part: `git cherry-pick --abort`, then move that commit or its task to the earlier part and show the new plan.
- The original branch stays untouched until the person decides what to do with it.

## Carry a fix up the stack (pushed branches)

After a new commit on part 1:

```bash
git switch feat/PROJ-123-add-coupons-part-2
git merge feat/PROJ-123-add-coupons-part-1
# run the tests on part 2
git switch feat/PROJ-123-add-coupons-part-3
git merge feat/PROJ-123-add-coupons-part-2
# run the tests on part 3
git push origin feat/PROJ-123-add-coupons-part-1 feat/PROJ-123-add-coupons-part-2 feat/PROJ-123-add-coupons-part-3
```

Every push is a fast-forward, so the pre-push hook lets it through. On a conflict, `git merge --abort` returns the branch to where it was; resolve it with the person.

## Rebase a stack that was never pushed

With git 2.38 or later, from the top part:

```bash
git switch feat/PROJ-123-add-coupons-part-3
git rebase --update-refs feat/PROJ-123-add-coupons-part-1
git log --oneline --graph origin/main..feat/PROJ-123-add-coupons-part-3
```

- The commits of parts 2 and 3 move on top of the new tip of part 1, and the `part-2` branch moves with them.
- Check `git branch -vv` afterwards: no part may have an upstream yet. Once a branch is pushed, use the merge flow above instead.

## After a squash merge of part 1

```bash
git fetch origin
git switch feat/PROJ-123-add-coupons-part-2
git merge origin/main
# run the tests, then push (fast-forward)
git push origin feat/PROJ-123-add-coupons-part-2
```

Git usually resolves the duplicated changes of part 1 on its own; if it reports a conflict, stop and resolve it with the person. Do the same with part 3 after merging part 2 into it.

## Host examples [Not verified]

Use them only when the project has that CLI installed and authenticated; otherwise open each PR from the link `git push` prints and pick the base branch in the form. Check each command in the project before relying on it.

### GitHub, with gh

```bash
gh pr create --base main --head feat/PROJ-123-add-coupons-part-1 \
  --title "feat(coupons): add coupon rules (part 1/3)" --body-file specs/PROJ-123-add-coupons/pr-part-1.md
gh pr create --draft --base feat/PROJ-123-add-coupons-part-1 --head feat/PROJ-123-add-coupons-part-2 \
  --title "feat(coupons): store coupons and expiry (part 2/3)" --body-file specs/PROJ-123-add-coupons/pr-part-2.md
gh pr edit <number of PR 2> --base main        # after PR 1 merged, if the host did not retarget it
```

### GitLab, with glab

```bash
glab mr create --source-branch feat/PROJ-123-add-coupons-part-1 --target-branch main \
  --title "feat(coupons): add coupon rules (part 1/3)" --description "$(cat specs/PROJ-123-add-coupons/pr-part-1.md)"
glab mr create --draft --source-branch feat/PROJ-123-add-coupons-part-2 --target-branch feat/PROJ-123-add-coupons-part-1 \
  --title "feat(coupons): store coupons and expiry (part 2/3)" --description "$(cat specs/PROJ-123-add-coupons/pr-part-2.md)"
```

### Azure DevOps, with az

```bash
az repos pr create --source-branch feat/PROJ-123-add-coupons-part-1 --target-branch main \
  --title "feat(coupons): add coupon rules (part 1/3)" --description "$(cat specs/PROJ-123-add-coupons/pr-part-1.md)"
az repos pr create --draft --source-branch feat/PROJ-123-add-coupons-part-2 --target-branch feat/PROJ-123-add-coupons-part-1 \
  --title "feat(coupons): store coupons and expiry (part 2/3)" --description "$(cat specs/PROJ-123-add-coupons/pr-part-2.md)"
```

Retarget a PR in the host's page when its CLI cannot change the target branch.
