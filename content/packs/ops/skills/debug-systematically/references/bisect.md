# Bisection

Bisection finds the change that broke something in about log2(N) steps: 1,000 commits take about 10 tests. It works on anything with a good end, a bad end and an order between them: commits, input rows, dependency versions, configuration keys.

## git bisect

### Before you start

1. **A clean working tree.** `git status` must show no changes, because bisect checks out other commits. If the person has work in progress, ask them how to set it aside (a commit on their branch, a stash they run themselves, or a separate worktree). Never stash, reset or clean on your own.
2. **A separate worktree is the safest place** when the person agrees: `git worktree add ../<repo>-bisect HEAD` and bisect there, so their checkout never moves.
3. **A good and a bad commit.** Bad is usually `HEAD`. Good is a tag or commit where the reproduction passed: the last release, or a commit from before the symptom was reported. Check both with the reproduction before starting; a "good" commit that also fails wastes the whole run.
4. **A reproduction command** that exits 0 when the behavior is good and non-zero when it is bad, and that does not depend on files the bisect will change underneath it. Keep the script outside the repository, or untracked.

### Manual run

```bash
git bisect start
git bisect bad HEAD
git bisect good v3.1.0
# git checks out a commit in the middle; run the reproduction, then one of:
git bisect good
git bisect bad
git bisect skip      # this commit cannot be tested (does not build, unrelated breakage)
# repeat until git prints "<sha> is the first bad commit"
git bisect log > <work-folder>/bisect.log   # keep the evidence
git bisect reset     # always: returns to the original branch and commit
```

### Automated run

```bash
git bisect start HEAD v3.1.0
git bisect run <path-outside-repo>/repro.sh
git bisect reset
```

Exit codes that `git bisect run` understands:

| Exit code | Meaning |
|---|---|
| 0 | good |
| 1 to 127, except 125 | bad |
| 125 | skip: this commit cannot be tested |
| 128 or more | abort the bisect |

A reproduction script that tells "cannot test" apart from "bad":

```bash
#!/bin/sh
# repro.sh: exit 0 good, 1 bad, 125 skip
<install-or-build-command> >/dev/null 2>&1 || exit 125
<test-command-for-the-bug>
```

Use the project's own build and test commands; the install step must not reach the network for packages the lockfile does not already pin, and it must not install anything new on the machine.

### Flaky failures

A bug that fails one run in ten breaks a naive bisect: a "good" verdict may just be luck. Repeat the test inside the script and call the commit bad on the first failure:

```bash
#!/bin/sh
<build-command> >/dev/null 2>&1 || exit 125
i=0
while [ "$i" -lt 20 ]; do
  <test-command-for-the-bug> >/dev/null 2>&1 || exit 1
  i=$((i + 1))
done
exit 0
```

Choose the repeat count from the failure rate measured in step 2: with a 10% failure rate, 20 passing runs leave about a 12% chance of a false "good"; 40 runs bring it near 1.5%.

### Narrowing further

- `git bisect start -- <path>` only considers commits that touch that path.
- `git bisect start --first-parent` follows merges on the main line only, useful when feature branches have broken intermediate commits.
- After finding the commit, read its diff with `git show <sha>` and confirm the cause with the toggle test of `SKILL.md`, step 8: revert just that hunk in a scratch copy and see the reproduction pass.

## Bisecting other things

### Input

1. Run with the first half of the input. Fails? Keep that half. Passes? Try the second half.
2. If both halves pass, the bug needs elements from both: keep one half and bisect the other while the first half stays in.
3. Stop when removing any single element makes the failure disappear: that is the minimal case. Turn it into the regression test.

### Dependency versions

1. Note the versions in the lockfile at the good and the bad commit (`git diff <good>..<bad> -- <lockfile>`).
2. If several packages changed, revert half of them in a scratch branch and test.
3. Within one package, test the versions between the two, in the middle first. Read its changelog for the version that broke it.

Do this only with versions already available to the project's package manager; do not add registries or install tools.

### Configuration

Copy the good and the bad configuration, apply half of the differing keys to the good one, and test. Repeat on the half that breaks it. Never copy secret values into a scratch file: compare key names and non-secret values only.

## After the bisect

- `git bisect reset` ran, and `git status` shows the person's tree as it was.
- The first bad commit is in the debug log with its subject and the evidence (`bisect.log` in your work folder, outside the repository).
- The first bad commit is where the bug became visible, not always where it was written: a commit can expose an older defect. Confirm with step 8 before blaming the diff.
