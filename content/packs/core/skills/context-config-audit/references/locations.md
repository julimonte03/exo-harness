# Where agents keep their configuration

The project-level configuration files that `context-config-audit` reads, and which agents load each one. The engine verified these conventions on 2026-10-29; agents change them often, so a file that is not listed here but clearly configures an agent is read too.

## Rules (always-on and per path)

| Path | Loaded by | Look at |
|---|---|---|
| `AGENTS.md`, at the root and nested | Copilot, Cursor, Codex and Devin; Claude Code when there is no `CLAUDE.md`; Gemini when `context.fileName` lists it | The engine's `core` block; every rule outside it; `@path` imports |
| `AGENTS.override.md` | Codex, before `AGENTS.md` in the same folder | Rules that override the ones above |
| `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md` | Claude Code; Copilot, Cursor and Devin also read `CLAUDE.md` | Rules; the `@AGENTS.md` import; text copied from `AGENTS.md` |
| `.claude/rules/**/*.md` | Copilot | Rules |
| `.github/copilot-instructions.md` | Copilot (CLI, VS Code and the cloud agent) | Rules; `@path` imports |
| `.github/instructions/**/*.instructions.md` | Copilot | Rules; the `applyTo` globs |
| `.cursor/rules/**/*.mdc`, `.cursorrules` (legacy) | Cursor; Devin also reads `.cursor/rules/` | Rules; `alwaysApply` and `globs`. A rule file with the `.md` extension is ignored by Cursor |
| `GEMINI.md` | Gemini; Copilot | Rules |
| `.devin/rules/`, `.windsurf/rules/`, `.windsurfrules` | Devin (formerly Windsurf) | Rules |

## Settings, permissions and hooks

| Path | Loaded by | Look at |
|---|---|---|
| `.claude/settings.json`, `.claude/settings.local.json` | Claude Code; their hooks also run in Copilot, Cursor and Devin | `permissions` (`allow`, `ask`, `deny`, `defaultMode`, `additionalDirectories`), `hooks`, `env`, the MCP switches |
| `.github/hooks/*.json`, `.github/copilot/settings.json` | Copilot | Hooks: their `bash` and `powershell` commands |
| `.cursor/hooks.json` | Cursor | Hooks |
| `.codex/config.toml`, `.codex/hooks.json` | Codex, only in trusted projects | Approval and sandbox settings, `[mcp_servers.<name>]`, hooks |
| `.gemini/settings.json` | Gemini, only in trusted folders | `mcpServers`, `hooks`, `context.fileName` |
| `.devin/config.json`, `.devin/hooks.v1.json` | Devin | Hooks and settings |
| `.vscode/settings.json` | VS Code | The chat and agent settings: auto-approval of tools and terminal commands, instruction and hook locations |

## MCP servers

| Path | Loaded by | Look at |
|---|---|---|
| `.mcp.json` | Claude Code, Copilot; Devin imports it | `mcpServers`: `command`, `args`, `env`, `url`, `headers` |
| `.github/mcp.json` | Copilot CLI | The same |
| `.vscode/mcp.json` | VS Code (key `servers`) | The same |
| `.cursor/mcp.json` | Cursor; Devin imports it | The same |
| `.devin/mcp_config.json` | Devin | The same |

## Skills, subagents and commands

| Path | Loaded by | Look at |
|---|---|---|
| `.claude/skills/*/` | Claude Code, Copilot, Cursor, Devin | Every file of each skill the engine did not mirror |
| `.agents/skills/*/` | Codex, Gemini, Cursor, Copilot, Devin | The same |
| `.github/skills/*/`, `.cursor/skills/*/`, `.gemini/skills/*/`, `.devin/skills/*/` | Their agent | The same |
| `.claude/agents/*.md` | Claude Code, Copilot, VS Code, Cursor | `tools` (missing means every tool), `mcpServers`, `hooks`, the instructions |
| `.github/agents/*.agent.md`, `.cursor/agents/`, `.codex/agents/*.toml`, `.gemini/agents/`, `.devin/agents/` | Their agent | The same |
| `.claude/commands/*.md`, `.cursor/commands/`, `.gemini/commands/*.toml`, `.github/prompts/*.prompt.md` | Their agent | The instructions, and the commands they run |

## What the engine generates

`.exo/lock.json` lists them. With Claude Code and Copilot as targets, for example:
- the `core` block of `AGENTS.md`, and the `@AGENTS.md` import at the start of an existing `CLAUDE.md`;
- the skills in `.claude/skills/` or `.agents/skills/`, and the subagents in `.claude/agents/`;
- the `Bash(exo <command>:*)` and `PowerShell(exo <command>:*)` items of `permissions.allow` in `.claude/settings.json`, one per engine command an agent may run without asking (reading, checking and recording; never `init`, `sync`, `update`, `uninstall` or `gate publish`);
- the `exo` entry of `.mcp.json`, only when the engine's MCP server is enabled;
- the files in `.exo/`.

Everything else in those files is the repository's own, and it is what this skill audits.
