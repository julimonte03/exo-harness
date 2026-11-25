# exo with other agents (AGENTS.md)

Agents without a dedicated adapter get exo's agent-agnostic base: the rules in `AGENTS.md` and the skills, in the [Agent Skills](https://agentskills.io/specification) format, in `.agents/skills/`, the folder these agents share. exo knows four of them by name, and `generic` covers any other agent that reads `AGENTS.md`:

| Agent | `--agents` | Detected by |
|---|---|---|
| Cursor | `cursor` | `.cursor/` or `.cursorrules` in the repo, or running inside Cursor's agent |
| Codex CLI | `codex` | `.codex/` or `AGENTS.override.md` in the repo, or running inside Codex |
| Gemini CLI | `gemini` | `GEMINI.md` or `.gemini/` in the repo, or running inside Gemini CLI |
| Devin (Devin Local and Devin CLI, formerly Windsurf) | `devin` | `.devin/`, `.windsurf/` or `.windsurfrules` in the repo, or running inside Devin |
| Anything else that reads `AGENTS.md` | `generic` | Installed when no agent is detected |

```sh
exo init --agents codex
exo init --agents cursor,claude-code
exo add-agent gemini
```

## What exo generates

| Path | What it is |
|---|---|
| `AGENTS.md` | The always-on rules, inside a marked block; your own content outside it stays as it is |
| `.agents/skills/<skill>/` | Each skill of the installed packs, copied byte for byte |
| `.exo/` | Config, lock, skill registry, shared contracts and templates |
| `.exo/githooks/` | The git hooks, active in this clone |

When Claude Code or Copilot is also a target, the skills go to both `.claude/skills/` and `.agents/skills/`: real copies tracked by the lock, never symlinks, so they work the same on Windows.

**No subagents.** These agents get no subagent files. The skills that ask for a fresh context or for delegation (explore, verify, the judges, the extraction of `/exo-adopt`) run inline, and the agent says so in its answer ("no isolation"). For the fresh-context verify of Tier 3 and 4 changes, the cycle offers a handoff to a new session.

**No MCP config.** exo writes MCP config only for Claude Code and Copilot. The CLI is the main interface and needs none; if you want the optional MCP server in another agent, register `exo mcp` (stdio) in that agent's own MCP settings.

## Per agent

- **Gemini CLI** reads `GEMINI.md` by default. To make it read `AGENTS.md`, add this to `.gemini/settings.json` (exo prints the same note when Gemini is a target):

  ```json
  {"context": {"fileName": ["AGENTS.md", "GEMINI.md"]}}
  ```

- **Codex CLI** reads `AGENTS.md` and `.agents/skills/` as they are.
- **Cursor** reads `AGENTS.md` and `.agents/skills/` as they are.
- **Devin** reads `AGENTS.md` and `.agents/skills/` as they are.

## Working with it

Ask for what you want in plain words; the agent picks a skill when your request matches its description. To call one by name, use your agent's own way of invoking skills, or say it: "use the sdd-new skill to add a health check endpoint".

| You want to | Skill |
|---|---|
| Start a change | `sdd-new` |
| Run the next phase | `sdd-continue` |
| Draft the whole plan | `sdd-ff` |
| See where each change is | `sdd-status` |
| Describe the project for the agent | `project-onboarding` |
| Adopt an existing codebase | `exo-adopt` (pack `discovery`) |

The agent drives exo through the terminal (`exo change status --json`, `exo check`, `exo mem search`): allow it to run `exo` in your agent's settings, or approve the commands as they come.

## Check the installation

```sh
exo doctor
exo status
```

If something fails, see [Troubleshooting](troubleshooting.md).
