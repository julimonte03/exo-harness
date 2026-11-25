# Quick start

From nothing to a first spec-driven change, in a new project and in one that already has code.

You need git, an AI coding agent (the examples use Claude Code; the [guides](docs/guides/) cover the others) and exo:

```sh
curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh | sh
```

```powershell
irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 | iex
```

The [README](README.md#install) explains what the installer does, how to pin a version and how to read it before running it. Check the installation:

```sh
exo --version
exo doctor
```

## 1. Install exo in a new project

```sh
mkdir my-app
cd my-app
git init
exo init
```

`exo init` asks three things, each with a default you accept with Enter, and a fourth when you give a ticket pattern:

1. **Agents:** the ones it detected (by environment, files in the repo and executables on the `PATH`). Known: `claude-code`, `copilot`, `cursor`, `codex`, `gemini`, `devin` and `generic`.
2. **Packs:** the ones it suggests for the stack. An empty repo gets `core` and `sdd`; the [README](README.md#packs) lists the rest.
3. **Ticket pattern:** a regular expression for your ticket IDs (for example `[A-Z][A-Z0-9]*-\d+` for `PROJ-123`, or `#\d+`), or empty, the default, if you do not use tickets.
4. **Example ticket ID,** only with a pattern: one ID that matches it. For a suggested pattern the default is its example (`PROJ-123`); for your own pattern, type one.

Then it shows the files it would write and asks `Continue? [y/N]`. Answer `y` to write them: Enter cancels. Without questions:

```sh
exo init --agents claude-code --yes
```

What it writes, with Claude Code as the agent:

| Path | What it is |
|---|---|
| `AGENTS.md` | The always-on rules, inside a marked block; anything you write outside the block is yours |
| `.claude/skills/`, `.claude/agents/` | The skills and subagents of the packs you chose |
| `.claude/settings.json` | Permission for Claude Code to run, without asking, the `exo` commands that read, check and record; the ones that change the installation or publish ask first |
| `.exo/config.json` | The project's configuration: agents, packs, tickets, gates per tier, protected branches |
| `.exo/lock.json` | Every generated file with its hash, so exo never overwrites your edits |
| `.exo/skill-registry.md`, `.exo/shared/` | The skill registry and the shared contracts and templates |
| `.exo/githooks/` | The `commit-msg`, `pre-commit` and `pre-push` hooks, active in this clone |
| `.gitignore`, `.gitattributes` | A marked block each: snapshots stay out of git, hooks keep LF line endings |

Commit it. The message has to follow Conventional Commits, because the `commit-msg` hook is already active:

```sh
git add -A
git commit -m "chore: adopt exo"
```

Running `exo init` or `exo sync` again with nothing to change writes nothing. A teammate who clones the repo runs `exo sync` once to activate the hooks in their clone.

Open Claude Code in the project and accept the workspace trust dialog: until then it ignores the project's permissions and asks before every `exo` command. After it, the commands that read, check and record run on their own, and the ones that change the installation ask first ([Claude Code guide](docs/guides/claude-code.md#what-runs-without-asking)).

## 2. Tell the agent about the project (optional)

```text
/project-onboarding
```

It confirms with you the stack, the build, test and lint commands, the conventions and the owners, and writes `.exo/context.md`, the project wiki the other skills read. In an empty project you can skip it for now; a Tier 3 or 4 change asks for it.

For a guided tour of the whole cycle on a small real improvement, with an explanation before each phase, run `/sdd-onboard` instead of the next step.

## 3. Your first change

Ask for the change:

```text
/sdd-new add a health check endpoint that returns the version
```

The agent:

1. checks the branch: on `main` it proposes a branch for the change first;
2. names the change (`add-health-check`), asking for the ticket if the project uses them;
3. creates it with `exo change new`, which writes `specs/add-health-check/` and its AI Usage Record;
4. classifies its risk with `exo fitness classify`, from 1 (low) to 4 (critical);
5. drafts `proposal.md` and stops for your approval.

From there, `/sdd-continue` runs the next phase, `/sdd-ff` drafts the rest of the plan at once, and `/sdd-status` shows where every change is. The tier decides the phases:

| Tier | Phases |
|---|---|
| 1 | new, apply, verify (light), archive |
| 2 | new, spec with a test spec, apply, verify, archive |
| 3 | new, explore if needed, propose, spec, design, tasks, apply, verify in fresh context, archive |
| 4 | Tier 3, plus a mandatory `judgment-day` before archive |

The tier also decides the gates: by default none in Tier 1, `contract_check` and `code_review` in Tier 2, plus `security_review` and `threat_model` in Tier 3, and `secure_coding_check` in Tier 4 (`governance.gates` in `.exo/config.json`). A gate that is not approved needs someone with the `tech_lead` role (`governance.roles`).

You can follow the change from the terminal as well:

```sh
exo change list
exo change status add-health-check
```

## 4. Before the pull request

```sh
exo check --change add-health-check
exo check --base main
```

The first checks the change's artifacts, record, tier and gates; the second checks everything that changed against `main`, including a secret scan of the diff. `/sdd-archive` then merges the change's spec delta into the living specs (`specs/capabilities/`), moves the change to `specs/archive/`, commits and prepares the pull request.

Run the same check in CI. On GitHub Actions, for example:

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
      - run: pip install "exo-harness @ git+https://github.com/julimonte03/exo-harness@v1.0.0"
      - run: exo check --base "origin/$BASE_REF"
        env:
          BASE_REF: ${{ github.base_ref }}
```

Pin exo to a release tag, as above: without one, CI installs whatever the default branch has that day, and your pipeline changes without a review. `.exo/shared/ci-and-review.md` in your project has the same step for other CI systems, and how to publish the gates as PR comments with `exo gate publish`. The command that publishes them comes from the project's config, so it runs only after you approve it on your machine: in a terminal `exo gate publish` shows it and asks; without one, `exo gate publish --approve-command '<the exact command>'` approves that text, which must match `review.publish_command`, and runs it. A different command asks again, so a pipeline that writes the expected command runs nothing when a branch changes it.

## Adopting an existing project

In a repo that already has code, start with a clean working tree (commit or stash your changes), then:

```sh
cd my-existing-app
exo init
```

`exo init` keeps your files: it adds its rules to your `AGENTS.md` inside a marked block, adds `@AGENTS.md` to the top of an existing `CLAUDE.md` when Claude Code is a target, keeps your line endings, and stops without writing anything if a file it would generate already exists with other content. It also offers the `discovery` pack for reverse engineering: add it to the pack list when asked, or pass it with the rest:

```sh
exo init --packs core,sdd,quality,security,python,discovery --yes
```

Then, in your agent:

```text
/exo-adopt
```

`/exo-adopt` reads the code (and never changes it), recovers as-is specs with evidence for every requirement, the project wiki and the architecture decisions, audits their precision, and ends with a backlog of changes you confirm. It runs one unit at a time and resumes where it left off. The [adoption guide](docs/guides/adoption.md) covers the depths, what it writes and what it never touches.

If the repo already had agent configuration (`CLAUDE.md`, `.claude/`, Copilot instructions, `.cursor/rules/`, MCP configs), ask for the `context-config-audit` skill: it reports, without changing anything, conflicts with exo's rules, permissions that are too broad, secrets and suspicious instructions.

## Next

- [Claude Code](docs/guides/claude-code.md), [GitHub Copilot](docs/guides/copilot.md) and [other agents](docs/guides/other-agents.md).
- [Troubleshooting](docs/guides/troubleshooting.md).
- `exo --help` and `exo <command> --help` for every command.
