# exo

**A governed, spec-driven development engine for AI coding agents, installed per project.**

exo puts one set of rules, skills and subagents into your repository and generates, for each AI coding agent your team uses, exactly the files that agent reads. The agent then works through a spec-driven cycle whose ceremony grows with the risk of the change, and calls the `exo` CLI to record what it did, check its artifacts and respect the project's gates.

- **Agent-agnostic.** Dedicated adapters for <!-- exo-count:agents -->2<!-- /exo-count --> agents (Claude Code and GitHub Copilot), plus a base that any agent reading `AGENTS.md` can use (Cursor, Codex, Gemini CLI, Devin and others).
- **Spec-driven development proportional to risk.** Every change gets a risk tier from 1 to 4; the tier decides the phases, the required artifacts and the gates.
- **Governance you can enforce.** Git hooks for Conventional Commits, staged secrets and protected branches, and `exo check` for your CI.
- **Existing codebases too.** `/exo-adopt` recovers as-is specs from code with evidence on every claim, audits their precision and never touches your code.
- **Safe to install and to remove.** Every generated file is tracked with its hash; your edits are never overwritten without `--force`, a snapshot comes before every change, and `exo uninstall` leaves the project as it was.
- **Small footprint.** Python 3.10 or later, standard library only, on Windows, macOS and Linux.

## Install

macOS and Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 | iex
```

The installer installs the latest release (or the `main` branch while there is none):

- with [uv](https://docs.astral.sh/uv/), it runs `uv tool install` from the git repository (this needs git);
- without uv, it creates a virtual environment in your user data folder and installs the release wheel after checking it against the release's `SHA256SUMS`; if it cannot download them, it installs nothing. This needs Python 3.10 or later, and `curl` on macOS and Linux.

Then it puts `exo` on your `PATH` (it says so, and you open a new terminal) and runs `exo doctor`. It never overwrites another program called `exo`; it warns if another one comes first on your `PATH`, and `exo doctor` reports it. Running the installer again updates exo.

**Options.** Adopt a project right after installing with `--init DIR` (`-Init DIR` in PowerShell), add the semantic memory extra with `--with-vector` (`-WithVector`), or leave the `PATH` alone with `--no-path` (`-NoPath`):

```sh
curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh | sh -s -- --init ~/code/my-project
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1))) -Init C:\code\my-project
```

**Pin a version** with `EXO_REF` (a release tag, a branch or a commit). In a pipe, the variable goes on the `sh` side:

```sh
curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh | EXO_REF=v1.0.0 sh
```

```powershell
$env:EXO_REF = 'v1.0.0'; irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 | iex
```

A branch or a commit installs from git, so it needs git and has no `SHA256SUMS` to check. `sh install.sh --help` lists every option and variable.

### Review the installer before running it

Piping a script into a shell runs it without a look. To read it first:

```sh
curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh -o install.sh
less install.sh
sh install.sh
```

```powershell
irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 -OutFile install.ps1
notepad install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

The scripts download only over `https`, and refuse a redirect to another protocol (`EXO_REPO_URL`, which points them to another repository or a mirror, must be an `https://` URL unless it is on your own machine). Without uv they install no wheel whose checksum does not match the release's `SHA256SUMS`.

### Run it without installing

With uv and git:

```sh
uvx --from git+https://github.com/julimonte03/exo-harness exo init
uvx --from git+https://github.com/julimonte03/exo-harness@v1.0.0 exo init
```

Keep `--from`: `uvx exo` runs a different package from PyPI that is also called `exo`. The git hooks and your agent call `exo` from the `PATH`, so for everyday use, install it.

exo is not on PyPI yet. Once it is published as `exo-harness`, `uvx --from exo-harness exo init` will work too.

## First steps

In the root of a git repository:

```sh
exo init
```

`exo init` detects the agents you use and the stack, suggests packs, asks for your ticket pattern (or none), and shows what it will write before writing it. `exo init --agents claude-code --yes` does the same without questions. Commit what it generates: the team shares the rules and the skills. Each teammate runs `exo sync` once in their clone to activate the git hooks.

Then, in your agent:

```text
/sdd-new add a health check endpoint
```

The agent names the change, classifies its risk, drafts the proposal and stops for your approval. `/sdd-continue` runs the next phase, `/sdd-ff` drafts the whole plan, and `/sdd-status` shows where each change is.

The full walk-through, for a new project and for an existing one, is in [QUICK-START.md](https://github.com/julimonte03/exo-harness/blob/main/QUICK-START.md).

## Supported agents

| Agent | `--agents` | What exo generates for it |
|---|---|---|
| Claude Code | `claude-code` | Rules in `AGENTS.md` (and an `@AGENTS.md` import if the project has a `CLAUDE.md`), skills in `.claude/skills/`, subagents in `.claude/agents/`, and permission in `.claude/settings.json` to run the `exo` commands that read, check and record without asking |
| GitHub Copilot in VS Code and Copilot CLI | `copilot` | Rules in `AGENTS.md`, skills in `.claude/skills/` and subagents in `.claude/agents/`, which Copilot reads (shared with Claude Code when both are targets) |
| Cursor, Codex, Gemini CLI, Devin | `cursor`, `codex`, `gemini`, `devin` | Rules in `AGENTS.md` and skills in `.agents/skills/`; phases that would use a subagent run inline |
| Any other agent that reads `AGENTS.md` | `generic` | Rules in `AGENTS.md` and skills in `.agents/skills/` |

Every installation also writes the `.exo/` folder (config, lock, skill registry and shared contracts), a block in `.gitignore`, and the git hooks. The optional MCP server (`exo init --mcp`) adds an `.mcp.json` entry for Claude Code and Copilot. Add or remove an agent later with `exo add-agent <agent>` and `exo remove-agent <agent>`.

The guides: [Claude Code](https://github.com/julimonte03/exo-harness/blob/main/docs/guides/claude-code.md), [GitHub Copilot](https://github.com/julimonte03/exo-harness/blob/main/docs/guides/copilot.md) and [other agents](https://github.com/julimonte03/exo-harness/blob/main/docs/guides/other-agents.md).

## Packs

The content ships in <!-- exo-count:packs -->12<!-- /exo-count --> packs with <!-- exo-count:skills -->106<!-- /exo-count --> skills, <!-- exo-count:subagents -->6<!-- /exo-count --> subagents and <!-- exo-count:shared -->20<!-- /exo-count --> shared contracts. A pack installs the packs it requires.

| Pack | Skills | What it covers |
|---|---|---|
| `core` | <!-- exo-count:skills:core -->18<!-- /exo-count --> | Base rules, shared contracts and cross-cutting skills: context retrieval, memory, commits and PRs, project onboarding, skill authoring and review |
| `sdd` | <!-- exo-count:skills:sdd -->20<!-- /exo-count --> | The spec-driven cycle by risk tier, with the optional SPDD overlay (REASONS canvas) |
| `quality` | <!-- exo-count:skills:quality -->11<!-- /exo-count --> | The review of verify and of a diff before committing, blind code and security judges, product, business, frontend and team judges, judgment-day, an excellence committee and a five-lens review |
| `security` | <!-- exo-count:skills:security -->6<!-- /exo-count --> | Secure coding, security review of the diff, threat modeling, data classification and prompt hygiene, on OWASP Top 10:2025 |
| `discovery` | <!-- exo-count:skills:discovery -->5<!-- /exo-count --> | Reverse engineering of an existing codebase: `/exo-adopt` and its stages |
| `design` | <!-- exo-count:skills:design -->5<!-- /exo-count --> | Architecture decision records, diagrams (C4, UML, Mermaid) and an executive style |
| `product` | <!-- exo-count:skills:product -->5<!-- /exo-count --> | Discovery and definition: hypotheses, flows, acceptance criteria, refinement, work items and roadmaps |
| `python` | <!-- exo-count:skills:python -->2<!-- /exo-count --> | Python idioms, typing and pytest, and a Python reviewer |
| `java` | <!-- exo-count:skills:java -->10<!-- /exo-count --> | Java and Spring Boot: REST APIs, architecture, security, JPA, build fixes and code review |
| `frontend` | <!-- exo-count:skills:frontend -->12<!-- /exo-count --> | TypeScript and React, Zod, Tailwind CSS 4, Testing Library, Playwright and WCAG 2.2 audits |
| `ops` | <!-- exo-count:skills:ops -->10<!-- /exo-count --> | Incidents and postmortems, debugging, logs, runbooks, SLOs, capacity and chaos experiments |
| `agentic` | <!-- exo-count:skills:agentic -->2<!-- /exo-count --> | Reviews of systems built on AI agents: reliability and context engineering |

`exo init` suggests `core` and `sdd`, plus `quality` and `security` in a Node, Python or JVM project, and `python`, `java`, `frontend` or `ops` (for Docker or infrastructure files) from the stack it detects. In a repo that already has code it also offers `discovery`. Choose your own with `--packs`, which takes the full list (for example `--packs core,sdd,quality,security,design`), and see what a pack holds with `exo skills list --pack <pack>`.

## Personas

Each person can choose a role overlay that changes what the agent shows them first and how:

```sh
exo persona set tech-lead   # dev, tech-lead, qa or product
exo persona show
exo persona clear
```

The role is stored in your user data folder, never in the repository. At the start of a session the agent reads it and follows `.exo/shared/personas/<role>.md`. A persona never relaxes a rule, a gate, a tier or an approval.

## Keeping a project up to date

After you upgrade exo (run the installer again), bring each project to the new version:

```sh
exo update            # preview: new, modified, renamed and orphaned files, and conflicts with your edits
exo update --apply    # write it, with a snapshot first
```

Files you edited by hand are kept and reported; `--force` overwrites them. Skills and subagents that the new version no longer ships (orphans) are reported and deleted only with `--prune`; `exo sync` keeps them too. `exo doctor` warns when a project's lock was written by another version. `exo status` shows the project at a glance: agents, packs, the lock's version against the engine's, the git hooks, your persona, manual changes to generated files, and each active change with its tier, phase, gates and open followups.

## Memory

`exo mem` is a memory owned by each user: one SQLite database in the user data folder, shared by all your projects and scoped by project. The agent reads it at the start of a session (`exo mem context`), searches it before solving something (`exo mem search`) and saves decisions, fixes and discoveries (`exo mem save`). Search is lexical out of the box; hybrid search needs the `[vector]` extra, a local model (`exo mem model pull`) and an index built with it (`exo mem reindex --provider local`). Nothing leaves your machine unless you allow a remote provider. On Linux and macOS exo creates the data folder readable only by you, and `exo doctor` warns if other users can read it. Never store secrets or personal data in it.

## Remove it

- From a project: `exo uninstall` removes what exo generated and leaves your own files as they were, after saving a backup in your user data folder. It keeps what belongs to the project: `.exo/discovery/`, `.exo/context.md` and `.exo/brand.json`.
- From your machine: `sh uninstall.sh` or `.\uninstall.ps1` from a clone, or piped like the installers. It does not touch your projects.

## More

- [QUICK-START.md](https://github.com/julimonte03/exo-harness/blob/main/QUICK-START.md): from zero to a first change, and adopting an existing project.
- [Adopting an existing project](https://github.com/julimonte03/exo-harness/blob/main/docs/guides/adoption.md) with `/exo-adopt`.
- [Troubleshooting](https://github.com/julimonte03/exo-harness/blob/main/docs/guides/troubleshooting.md): the engine's real error messages and their fixes.
- [CONTRIBUTING.md](https://github.com/julimonte03/exo-harness/blob/main/CONTRIBUTING.md): adapters, packs, skills, tests and evals.
- [The engine's threat model](https://github.com/julimonte03/exo-harness/blob/main/docs/seguridad/threat-model-motor.md) (in Spanish): the installers, the git hooks, the agent's CLI and MCP server, memory, reverse engineering, packs and the eval runner, with their mitigations.
- [CHANGELOG.md](https://github.com/julimonte03/exo-harness/blob/main/CHANGELOG.md).

## License

[MIT](https://github.com/julimonte03/exo-harness/blob/main/LICENSE).
