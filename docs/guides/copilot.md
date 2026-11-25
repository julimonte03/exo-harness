# exo with GitHub Copilot

GitHub Copilot has a dedicated adapter that covers **Copilot in VS Code** (agent mode) and **Copilot CLI**. Install exo in a project with Copilot as a target:

```sh
exo init --agents copilot
```

`exo init` also picks Copilot on its own when it finds Copilot files in the repo (`.github/copilot-instructions.md`, `.github/instructions/`, `.github/agents/`, `.github/skills/`, `.github/prompts/` or `.vscode/mcp.json`) or when it runs inside Copilot CLI. Add it to a project that is already installed with `exo add-agent copilot`.

## What exo generates

Copilot reads the same conventions as Claude Code, so exo writes no Copilot-specific files:

| Path | What it is | How Copilot reads it |
|---|---|---|
| `AGENTS.md` | The always-on rules, inside a marked block | Copilot CLI and the VS Code chat read `AGENTS.md` as project instructions |
| `.claude/skills/<skill>/` | Each skill of the installed packs, byte for byte | A project skills folder for Copilot CLI and VS Code |
| `.claude/agents/<subagent>.md` | The subagents of the installed packs | Custom agents in Claude's format, which Copilot CLI and VS Code read |
| `.mcp.json` | Only with the optional MCP server (`exo init --mcp`): an `exo` entry under `mcpServers`, with `"tools": ["*"]`, which Copilot requires | Project MCP config for Copilot CLI and VS Code |

Plus what every agent gets: the `.exo/` folder, the git hooks and a block in `.gitignore`. Your own `.github/copilot-instructions.md` and `.github/instructions/` stay as they are; Copilot reads them together with `AGENTS.md`.

With Claude Code also a target, both agents share these files and exo writes each one once.

The subagents that run commands (`sdd-implementer` and `sdd-verifier`) declare both `Bash` and `PowerShell` in their `tools`: Copilot CLI on Windows gives a custom agent no shell with `Bash` alone.

## Skills with the same name

Copilot looks for project skills in `.github/skills/` first, then `.agents/skills/`, then `.claude/skills/`, and uses the first skill it finds with a given name, without a warning. A skill of yours in `.github/skills/` with the name of an exo skill (for example `sdd-new`) hides exo's. Rename yours, or move it out of `.github/skills/`; `exo skills list` shows the names exo uses.

## Working with it

Open the project in VS Code and use the Copilot chat in agent mode, or run `copilot` in the project folder. Skills work as slash commands, and Copilot also picks one when your request matches its description:

| You want to | Run |
|---|---|
| Start a change | `/sdd-new <what you want>` |
| Run the next phase | `/sdd-continue` |
| Draft the whole plan | `/sdd-ff` |
| See where each change is | `/sdd-status` |
| Describe the project for the agent | `/project-onboarding` |
| Adopt an existing codebase | `/exo-adopt` (pack `discovery`) |

The agent drives exo through the terminal (`exo change status --json`, `exo check`, `exo mem search`). Copilot asks before it runs each command: that is Copilot's own tool approval, and exo does not write a Copilot permission rule yet. Approve the commands as they come, or allow them with Copilot's options for tool approval ([Copilot CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference)). Keep asking for the ones that change the installation (`exo init`, `exo sync`, `exo update`, `exo uninstall`, `exo restore`) or run a command from the project's config (`exo gate publish`): that way a prompt injection in a file the agent reads cannot run them without you seeing it.

**Trust.** Copilot CLI loads a project's MCP servers only in a folder you trust, and VS Code only in a trusted workspace. Without the MCP server, exo needs no trust settings in Copilot.

### Non-interactive runs (`copilot -p`)

With `-p` and `--no-ask-user` there is nobody to approve a command, so Copilot runs only what its `--allow-tool` rules cover and denies the rest.

**Allow exo by subcommand, never as a whole.** A rule for every `exo` command, such as `shell(exo:*)`, also lets the agent run `exo init --publish-command '<command>'` and then `exo gate publish --approve-command '<command>'` without asking: a prompt injection in a file the agent reads (code under review, a ticket, a page) could make it run any command on your machine. Allow only the subcommands that exo lets Claude Code run without asking ([What runs without asking](claude-code.md#what-runs-without-asking)), with one `--allow-tool` rule each:

```text
shell(exo change:*)     shell(exo check:*)      shell(exo speclint:*)   shell(exo specs:*)
shell(exo fitness:*)    shell(exo discover:*)   shell(exo skills:*)     shell(exo doctor:*)
shell(exo status:*)     shell(exo validate:*)   shell(exo p0:*)         shell(exo codeowners:*)
shell(exo hook:*)       shell(exo version:*)    shell(exo persona show:*)
shell(exo mem save:*)   shell(exo mem search:*) shell(exo mem get:*)    shell(exo mem list:*)
shell(exo mem context:*) shell(exo mem session:*) shell(exo mem stats:*)
```

For example, `copilot -p "<request>" --no-ask-user --allow-tool 'shell(exo change:*)' --allow-tool 'shell(exo check:*)' ...`. This syntax is not verified with every version: check your Copilot version's rule syntax ([Copilot CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference)) before you rely on it. If your version does not match a rule with two words, a command it does not cover is denied and the run stops, which fails safe. Keep `shell(exo:*)` for a throwaway sandbox, such as a container or a temporary clone with no credentials and nothing you need, and never use it in a repository or on a machine you care about.

With Copilot CLI 1.0.114, rules such as `shell(exo:*)` and `shell(git:*)` did **not** cover:
- commands chained with `;`, and PowerShell scripts with variables, loops or pipelines;
- git with options before the subcommand, such as `git --no-pager log` (also with a `shell(git --no-pager:*)` rule);
- a git range such as `git diff main...HEAD`, which Copilot reads as a path.

In an unattended run, tell the agent in the request to run single, simple commands, to read and write files with its file tools and to pass JSON to exo as `'@file'`, and set `GIT_PAGER=cat`. A decision that belongs to a person (accepting a risk as the `tech_lead`, for example) still stops the cycle, as it should. In an interactive session Copilot simply asks.

## The optional MCP server

The CLI is the main interface. To expose the same functions as MCP tools:

```sh
exo init --mcp
```

It adds to `.mcp.json` an `exo` server that runs `exo mcp` over stdio. Copilot CLI and VS Code with its default agent harness (the Copilot harness) read `.mcp.json`; exo does not write `.vscode/mcp.json`.

## What is not covered

The Copilot cloud agent on GitHub.com is not a target: exo generates nothing specific for it.

## Check the installation

```sh
exo doctor
exo status
```

If something fails, see [Troubleshooting](troubleshooting.md).
