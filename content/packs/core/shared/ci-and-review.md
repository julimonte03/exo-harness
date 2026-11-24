# CI and review contract

How a project makes the engine's checks effective on its repository host. The engine integrates with no platform: CI runs one command, and publishing gates runs a command the project configures. Every host-specific example here is **[Not verified]**: adapt it and test it in the project before relying on it.

## A. Three lines of control

| Line | Where | What it stops | Can it be skipped? |
|---|---|---|---|
| Git hooks | Each developer's machine: `.exo/githooks/` through `core.hooksPath`, or husky | Invalid commit messages, staged secrets and personal data, `.env` and key files, pushes to protected branches, force pushes | Yes: `--no-verify`, or not installing them |
| `exo check` in CI | Every PR | The same scan on the branch diff, plus artifacts, verdicts, judgment-day and gates per tier | No, once the host requires the pipeline to pass |
| Branch protection | The host | Merging without green CI and without the required approvers | Only by host admins |

CI is the real gate. `exo doctor` says whether the hooks are active on a machine; `exo p0` checks the scanner, the input validation and the hooks.

## B. The CI step

The pipeline needs Python 3.10 or later, the engine installed, and enough git history for `--base` to find the merge base (full history, or at least the target branch fetched). Run the project's own tests in the same pipeline: the engine does not replace them.

```sh
pip install "exo-harness @ git+<engine repository URL>@<release tag>"   # or from your internal package index
exo check --base origin/<target branch>
```

Exit code 0 is green; anything else fails the pipeline. Add `--json` for machine-readable output.

Pin the engine to a release tag (`@v1.0.0`) or to a version of your package index: without one, CI installs whatever the engine's default branch has that day, and the pipeline changes without a review.

### GitHub Actions [Not verified]

```yaml
name: exo-check
on:
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install "exo-harness @ git+<engine repository URL>@<release tag>"
      - run: exo check --base "origin/${{ github.base_ref }}"
```

### Azure Pipelines [Not verified]

```yaml
trigger: none
pool:
  vmImage: ubuntu-latest
steps:
  - checkout: self
    fetchDepth: 0
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.12"
  - script: pip install "exo-harness @ git+<engine repository URL>@<release tag>"
    displayName: Install the engine
  - script: |
      target="${SYSTEM_PULLREQUEST_TARGETBRANCH#refs/heads/}"
      git fetch origin "$target"
      exo check --base "origin/$target"
    displayName: exo check
```

In Azure Repos the YAML `pr:` trigger does not apply: add the pipeline to each protected branch as a **Build validation** branch policy.

### GitLab CI [Not verified]

```yaml
exo-check:
  image: python:3.12
  variables:
    GIT_DEPTH: 0
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - pip install "exo-harness @ git+<engine repository URL>@<release tag>"
    - git fetch origin "$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    - exo check --base "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
```

## C. The host

`exo init` reads the `origin` remote and saves the host in `review.host` in `.exo/config.json`: `github`, `azure-devops`, `gitlab` or `other` (`--review-host` overrides it). The host only decides which examples to suggest; the engine behaves the same on every host.

## D. Publishing gates

`exo gate publish [--change <change>] [--dry-run]` builds one text per gate of the change: each `<change-root>/gates/<gate>.md`, plus the Gate summary of `verify-record.md` as `contract_check`. Each text carries its marker, `<!-- exo-gate:<gate> -->`.

- **Without `review.publish_command`** (the default), it prints the texts. Paste each one as a PR comment, or put them in the PR description.
- **With it**, it runs the command once per gate, from the project root, in the system shell (`sh` on Linux and macOS, `cmd` on Windows), with these variables in the environment: `EXO_GATE` (the gate name), `EXO_GATE_MARKER`, `EXO_GATE_BODY` (the path to a file with the text) and `EXO_CHANGE`. The command must edit the PR comment that carries the marker, or create it when there is none: one comment per gate, never a new one on each run.
- `--dry-run` never runs the command. Nothing reaches the host until the project sets the command, with `exo init --publish-command "<command>"` or by editing `review.publish_command`.
- **The command runs only if this machine approved it.** The approval is the SHA256 of the exact command, kept in the user's data folder, never in the repo. In a terminal, `exo gate publish` shows the command and asks; without one, it refuses and names the command: review it, then run `exo gate publish --approve-command`. A different command, even by one space, asks again. An agent never approves it for the person: it asks them to run it. In CI, pass `--approve-command` only in a trusted pipeline (see the next point).
- **In CI, the command comes from the branch under review** (its `.exo/config.json`) and runs in a shell: never run `exo gate publish` with a write token on pull requests from forks or under `pull_request_target`. Publish from a trusted pipeline, or from the person's machine.

Keep the command a single call to a script in the repo, such as `sh scripts/publish-gate.sh`. Example scripts:

### GitHub, with gh [Not verified]

```sh
#!/bin/sh
# gh authenticated (GH_TOKEN in CI). In Actions, also pass PR_NUMBER: ${{ github.event.pull_request.number }}.
set -eu
pr="${PR_NUMBER:-$(gh pr view --json number --jq .number)}"
id=$(gh api "repos/{owner}/{repo}/issues/$pr/comments" --paginate \
  --jq ".[] | select(.body | contains(\"$EXO_GATE_MARKER\")) | .id" | head -n 1)
if [ -n "$id" ]; then
  gh api --method PATCH "repos/{owner}/{repo}/issues/comments/$id" -F "body=@$EXO_GATE_BODY" > /dev/null
else
  gh pr comment "$pr" --body-file "$EXO_GATE_BODY"
fi
```

### Azure DevOps, with az and jq [Not verified]

```sh
#!/bin/sh
# az with the azure-devops extension. In a pipeline, map the build token to AZURE_DEVOPS_EXT_PAT
# and let the build identity contribute to pull requests.
set -eu
org="$SYSTEM_COLLECTIONURI"
route="project=$SYSTEM_TEAMPROJECT repositoryId=$BUILD_REPOSITORY_ID pullRequestId=$SYSTEM_PULLREQUEST_PULLREQUESTID"
thread=$(az devops invoke --org "$org" --area git --resource pullRequestThreads \
  --route-parameters $route --api-version 7.1 -o json \
  | jq -r --arg m "$EXO_GATE_MARKER" '[.value[] | select(.comments[0].content // "" | contains($m))][0].id // empty')
payload=$(mktemp)
if [ -n "$thread" ]; then
  jq -Rs '{content: .}' "$EXO_GATE_BODY" > "$payload"
  az devops invoke --org "$org" --area git --resource pullRequestThreadComments \
    --route-parameters $route threadId="$thread" commentId=1 \
    --http-method PATCH --in-file "$payload" --api-version 7.1 > /dev/null
else
  jq -Rs '{comments: [{parentCommentId: 0, content: ., commentType: 1}], status: 1}' "$EXO_GATE_BODY" > "$payload"
  az devops invoke --org "$org" --area git --resource pullRequestThreads \
    --route-parameters $route --http-method POST --in-file "$payload" --api-version 7.1 > /dev/null
fi
rm -f "$payload"
```

### GitLab, with glab and jq [Not verified]

```sh
#!/bin/sh
# glab authenticated (GITLAB_TOKEN in CI). Run it in a merge request pipeline.
set -eu
mr="${CI_MERGE_REQUEST_IID:?run it in a merge request pipeline}"
id=$(glab api "projects/:id/merge_requests/$mr/notes?per_page=100" \
  | jq -r --arg m "$EXO_GATE_MARKER" '[.[] | select(.body | contains($m))][0].id // empty')
if [ -n "$id" ]; then
  glab api --method PUT "projects/:id/merge_requests/$mr/notes/$id" -F "body=@$EXO_GATE_BODY" > /dev/null
else
  glab api --method POST "projects/:id/merge_requests/$mr/notes" -F "body=@$EXO_GATE_BODY" > /dev/null
fi
```

## E. Branch protection and approvers

- Require a PR to merge into each protected branch (`governance.protected_branches`), and forbid force pushes and deletion.
- Require the CI check of section B to pass before merging.
- Make the `tech_lead` role an effective approver. `exo codeowners` prints CODEOWNERS lines that give the specs folder and `.exo/` to the `tech_lead` entries of `governance.roles`; add them to the project's CODEOWNERS file.
  - **GitHub:** a branch protection rule or ruleset with "Require review from Code Owners".
  - **GitLab:** code owner approval on the protected branch, or merge request approval rules.
  - **Azure DevOps:** Azure Repos does not read CODEOWNERS. Add an "Automatically included reviewers" branch policy with path filters (`/specs/*`, `/.exo/*`) and the tech leads as required reviewers.
- The engine never checks roles: these host settings are what make an approval effective.
