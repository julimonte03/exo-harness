# exo with Claude Code

Claude Code has a dedicated adapter. Install exo in a project with Claude Code as a target:

```sh
exo init --agents claude-code
```

`exo init` also picks Claude Code on its own when it finds `CLAUDE.md` or `.claude/` in the repo, or when it runs inside a Claude Code session. Add it to a project that is already installed with `exo add-agent claude-code`.

## What exo generates

| Path | What it is |
|---|---|
| `AGENTS.md` | The always-on rules, inside a marked block |
| `CLAUDE.md` | Only if the project already has one: exo adds `@AGENTS.md` at the top, inside a marked block, and leaves the rest as it is |
| `.claude/skills/<skill>/` | Each skill of the installed packs, copied byte for byte |
| `.claude/agents/<subagent>.md` | The subagents of the installed packs |
| `.claude/settings.json` | Permission, for Bash and PowerShell, to run without asking the `exo` commands that read, check and record (see [What runs without asking](#what-runs-without-asking)), merged with your settings |
| `.mcp.json` | Only with the optional MCP server (`exo init --mcp`): an `exo` entry under `mcpServers` |

Plus what every agent gets: the `.exo/` folder, the git hooks and a block in `.gitignore`.

### Why there is usually no `CLAUDE.md`

Claude Code 2.1.281 and later read `AGENTS.md` when a project has no `CLAUDE.md`, so exo does not create one. `exo doctor` checks your version (the `claude-code` line). With an older Claude Code, either update it or create the import:

```sh
exo init --claude-md --yes
```

## Trust the workspace

Claude Code applies a project's permissions only after you accept the workspace trust dialog. Open Claude Code once in the project and accept it; until then it asks before every `exo` command. `exo doctor` shows the state in the `claude-trust` line.

## What runs without asking

The permission in `.claude/settings.json` covers the `exo` commands that the skills run on their own: the ones that read, check and record. exo adds one `Bash(exo <command>:*)` item and one `PowerShell(exo <command>:*)` item for each of these:

| Group | Commands |
|---|---|
| Changes and specs | `exo change`, `exo fitness`, `exo speclint`, `exo specs`, `exo check` |
| Adoption | `exo discover` |
| Project state | `exo status`, `exo doctor`, `exo skills`, `exo validate`, `exo p0`, `exo codeowners`, `exo hook`, `exo version`, `exo persona show` |
| Memory | `exo mem save`, `exo mem search`, `exo mem get`, `exo mem list`, `exo mem context`, `exo mem session`, `exo mem stats` |

Everything else asks you first:
- the commands that change the installation: `exo init`, `exo sync`, `exo update`, `exo uninstall`, `exo restore`, `exo add-agent`, `exo remove-agent`, `exo inject`, `exo registry`;
- `exo gate publish`, which runs the command in the project's config;
- the memory commands that delete, reindex, export or import, and `exo persona set|clear`.

That is on purpose: a prompt injection in a file the agent reads cannot rewrite the project's config or run a configured command without you seeing it. `exo gate publish` also runs the configured command only after you approve its exact text on your machine (see [`ci-and-review.md`](../../content/packs/core/shared/ci-and-review.md), section D). Projects installed with an older exo had `Bash(exo:*)`; `exo sync` replaces it with this list.

## Working with it

Skills are slash commands, and Claude Code also loads one on its own when your request matches its description.

| You want to | Run |
|---|---|
| Start a change | `/sdd-new <what you want>` |
| Run the next phase | `/sdd-continue` |
| Draft the whole plan | `/sdd-ff` |
| See where each change is | `/sdd-status` |
| Take a guided tour of the cycle | `/sdd-onboard` |
| Describe the project for the agent | `/project-onboarding` |
| Adopt an existing codebase | `/exo-adopt` (pack `discovery`) |
| Review a diff before committing | `/pre-commit-review` (pack `quality`) |

The review skill is called `pre-commit-review` so it does not clash with Claude Code's built-in `/review`.

**Subagents.** The phases that need a fresh context run in the subagents that exo installs: `sdd-explorer`, `sdd-verifier` and `sdd-judge` only read, `sdd-implementer` writes the code of the apply phase, and `re-extractor` and `re-auditor` (pack `discovery`) only read.

**The CLI.** The agent drives exo through the terminal (`exo change status --json`, `exo check`, `exo mem search`), with the permission described above. At the start of a session the rules tell it to run `exo persona show --json` and `exo mem context`; exo installs no Claude Code hooks.

**Memory.** `exo mem` is per user, so Claude Code sessions in all your projects share it, each scoped to its project.

## The optional MCP server

The CLI is the main interface. If you prefer MCP tools, enable the server when installing:

```sh
exo init --mcp
```

It adds to `.mcp.json` an `exo` server that runs `exo mcp` over stdio, with the same functions and the same input validation as the CLI. Claude Code asks you to approve a project MCP server the first time, and an organization policy can block it; the CLI keeps working either way.

## With Copilot in the same project

Claude Code and GitHub Copilot read the same `.claude/skills/` and `.claude/agents/`, so with both as targets exo writes each file once:

```sh
exo init --agents claude-code,copilot
```

Removing one of them with `exo remove-agent` keeps the files the other one still needs.

## Check the installation

```sh
exo doctor
exo status
```

If something fails, see [Troubleshooting](troubleshooting.md).
