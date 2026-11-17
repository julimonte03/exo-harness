# The six checks

What `context-config-audit` looks for in each check, with the rule ID for the Rule column and the usual severity. Next to the rule ID, cite the public reference when one fits: a CWE, or the OWASP Top 10 for LLM Applications 2025 (`LLM01:2025` Prompt Injection, `LLM02:2025` Sensitive Information Disclosure, `LLM06:2025` Excessive Agency).

The patterns are described, not quoted: this file is a skill reference too, and the engine's pre-check would flag the literal phrases.

## CCA-RULES: conflicts with the engine's rules

Compare every rule outside the engine's block with the block (the `core` block of `AGENTS.md`).

- **High: it weakens a control.**
  - Skipping or switching off git hooks, retrying a blocked commit with `--no-verify`, force pushes, direct pushes to a protected branch.
  - Destructive commands without asking first: deleting, overwriting, resetting, rewriting history.
  - Writing credentials anywhere, or personal data into memory, code, commits or prompts.
  - Calling work done with failing checks, skipping CI, approving gates or lowering a tier without the person.
- **Medium: it contradicts a convention.**
  - A commit format other than Conventional Commits, or taking the ticket from the branch name instead of from the person.
  - Working beyond the request ("refactor whatever you touch"), or claims without evidence.
  - Skipping the SDD cycle for changes that are not trivial, in a project with the `sdd` pack.
- **Medium: it contradicts another configuration file,** or `.exo/context.md`, on the same subject: two test commands, two branch conventions, two languages for commits.
- **Low:** stale text that no longer matches the repository but changes nothing the engine enforces.

The suggestion is to remove or rewrite the rule outside the block. Never suggest editing the engine's block: it is generated, and a manual change to it shows up in `exo status`.

## CCA-PERM: permissions that are too broad

**Claude Code** (`.claude/settings.json` and a versioned `.claude/settings.local.json`):

| Setting | Finding | Severity |
|---|---|---|
| `permissions.allow` | A shell tool (`Bash`, `PowerShell`) with no pattern, or a pattern that matches every command | High |
| `permissions.allow` | Patterns for commands that delete, publish or act remotely (`rm`, `git push`, package publishes, cloud and cluster CLIs, `ssh`, download tools) | High when unbounded; Medium for a bounded pattern |
| `permissions.allow` | `WebFetch` or another network tool for every domain | Medium |
| `permissions.defaultMode` | `bypassPermissions`, committed for the whole team | High |
| `permissions.defaultMode` | `acceptEdits`, committed for the whole team | Medium |
| `permissions.additionalDirectories` | A folder outside the repository (the home folder, a drive root) | High |
| `permissions.deny` | Nothing keeps the agent from reading `.env` files (for example `Read(./.env)` and `Read(./.env.*)`) | Low |
| `enableAllProjectMcpServers` | `true`: any server later added to `.mcp.json` starts without approval | Medium |

**Other agents:** the same ideas in their own settings.
- An approval policy that never asks, combined with a sandbox that allows everything (Codex): High.
- Auto-approval of every tool or terminal command in `.vscode/settings.json`: High.
- An auto-approval limited to a list of read-only commands: Low.

**Subagents and skills:**
- A subagent without `tools` inherits every tool: Medium when its role only reads or reviews.
- `tools` or `allowed-tools` broader than the purpose, such as shell or write access for a reviewer: Medium.

**MCP servers:**
- A server started from a package without a pinned version (a runner such as `npx -y` or `uvx` with no version, or `@latest`): Medium.
- A remote server (`url`, an HTTP or SSE type) that receives the repository's data, when the project has not enabled it: High. The engine's rules send nothing to a remote service without an explicit setting.
- A filesystem server rooted outside the repository, or a database server with write credentials to a shared environment: High.

**Hooks:**
- A hook that downloads and runs code, sends data out or reads credential files: Critical (`SR-EXFIL`, `SR-SCRIPT`).
- A hook that approves every tool call on its own, changes `core.hooksPath` or git config, or edits the agent's settings: High (`SR-BYPASS`, `SR-AGENT`).
- A hook that runs a script: read the script, which is configuration too.

## CCA-DATA: secrets and personal data

The engine's scanner runs on commits and diffs, not on files already in the repository: look by hand for the detectors of `.exo/shared/data-protection.md`, section D.

- **Critical:**
  - a literal credential in `env` or `headers` of an MCP server, in the `env` of a settings file, in a hook command, or in a rule or an example;
  - a connection string with a password;
  - a helper script that prints a literal key.

  The suggestion: an environment reference (`.mcp.json` accepts `${VAR}`), removing the value from the history, and rotating it.
- **High:** personal data of real people (personal emails, phone numbers, identity numbers, customer records) in rules, examples or fixtures of skills. The suggestion: roles and teams, `example.com` and placeholders.
- **Not a finding:** internal host names and service names (Internal data, fine in the repository), placeholders such as `<your-token>` or `${API_KEY}`, and published test data.

## CCA-INJ: suspicious instructions

The patterns of `skill-reviewer`, with their rule IDs (its `skill-reviewer/references/patterns.md`). In agent configuration, look especially for:

- `SR-INJ`: text that tells the agent to set aside its rules, or to keep something from the person, in a rule, a skill, a code comment or a YAML value;
- `SR-HIDE`: HTML comments with orders, invisible characters, encoded text;
- `SR-EXFIL`: rules, hooks or MCP servers that send code, environment variables or conversation content to a remote destination;
- `SR-CRED`: rules that have the agent request secrets or identity documents from the person in the chat, or read credential stores;
- `SR-DESTR`: destructive commands without confirmation;
- `SR-BYPASS`: hooks switched off, checks skipped, waivers added;
- `SR-AGENT`: rules that make the agent change its own settings, permissions, rules or MCP servers, or save orders into persistent memory.

The severity is the one of skill-reviewer's table for that pattern. A third-party skill or subagent also needs its provenance and license checked: recommend a full review with skill-reviewer.

## CCA-REF: references to files that do not exist

Check each one with `git ls-files <path>`: a file that exists only on this machine is missing for everyone else.

- `@path` imports in `AGENTS.md`, `CLAUDE.md` and `copilot-instructions.md`.
- Paths and links in rules: "see docs/architecture.md", "run scripts/setup.sh".
- `applyTo` globs in `.github/instructions/` and `globs` in `.cursor/rules/` that match no versioned file.
- Commands named in rules that the repository does not have: a script missing from the manifest, a Makefile target that does not exist.
- The `command` and `args` of an MCP server, and the commands of hooks, that point to a local script that does not exist.
- Files a skill cites (its references and scripts) that are missing, and skills a subagent or a rule names that are not installed (`exo skills list`).

Medium when a rule or a hook depends on the missing file, since the agent follows a dead instruction; Low for a dead link in prose.

## CCA-DUP: duplicates

- **Rules loaded together:** the same rule in several files that one agent loads at once. Copilot merges `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `copilot-instructions.md` and `.github/instructions/`; Cursor and Devin read both `AGENTS.md` and `CLAUDE.md`. Low; Medium when the copies already differ, which is also a `CCA-RULES` finding.
- **Copies instead of imports:** a `CLAUDE.md` that copies text from `AGENTS.md` instead of importing it with `@AGENTS.md`. Low.
- **Rules the engine already has:** a rule that repeats one of the engine's block. Low: suggest removing the copy.
- **The same skill name twice:** in two skills folders (`.claude/skills/`, `.agents/skills/`, `.github/skills/`) with different content. Copilot uses the first one it finds, silently. Medium. The identical copies the engine mirrors are fine.
- **The same MCP server twice:** in several configs (`.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, `.devin/mcp_config.json`) with different commands or versions. Low; Medium when one copy is pinned and the other is not. Devin imports `.mcp.json` and `.cursor/mcp.json` by default, so it can load both.
