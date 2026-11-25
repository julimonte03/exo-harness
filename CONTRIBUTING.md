# Contributing to exo

Thanks for helping. This file covers the development setup, the checks every change passes, and how to add an adapter, a pack or a skill.

## Setup

You need Python 3.10 or later and git, with `user.name` and `user.email` set (the tests create repositories).

```sh
git clone https://github.com/julimonte03/exo-harness.git
cd exo-harness
python -m pip install -e ".[dev]"
```

The `[dev]` extra brings pytest, pytest-cov and ruff. The `[vector]` and `[static]` extras add the optional memory backends.

| Path | What lives there |
|---|---|
| `src/exo/` | The engine and the CLI (`exo`); standard library only |
| `content/` | What exo installs in projects: `packs/` and `rules/AGENTS.base.md` |
| `tests/` | The suite, its fixtures (`tests/fixtures/`), the adapter goldens (`tests/golden/`) and the skill evals (`tests/skill_evals/`) |
| `docs/` | User guides (`docs/guides/`, in English), and the plan, the ADRs and the agent matrix (in Spanish) |
| `install.sh`, `install.ps1`, `uninstall.sh`, `uninstall.ps1` | The installers |

**When you run exo by hand** on a scratch project, point its user data somewhere disposable, so you do not touch your own memory, persona or backups:

```sh
export EXO_DATA_DIR="$PWD/.scratch-data"
export EXO_MEMORY_DB="$EXO_DATA_DIR/memory.db"
```

The test suite isolates this on its own.

## The checks

Every change passes these, and CI runs them on Windows, macOS and Linux with Python 3.10 to 3.13:

```sh
ruff check .
pytest
exo validate
```

- `pytest` measures coverage and fails below 85 %. For a single file, without the threshold: `pytest --no-cov tests/test_validate.py`.
- `exo validate` checks the content: pack manifests, skill frontmatter against the Agent Skills standard, `skill:` references, cited files, shared contracts, the 60-line limit of the base rules, secret patterns, and a pre-check for suspicious instructions (warnings that a person reviews).
- `exo validate --docs . --docs docs/guides` checks the user docs (a test runs it too; see [Docs](#docs)).
- The `perf` tests (performance targets) run in the normal suite.
- `pytest -m installer --no-cov` runs the real installers, which need the network. CI runs them in a job of their own.
- Adapter golden tests: after a deliberate change to what an adapter generates, regenerate them with `pytest --update-golden` and review the diff before committing.
- The engine's own workflows pin every `uses:` to a commit SHA and never put a `${{ }}` expression inside a `run:` (it goes in `env:`); `tests/test_workflows.py` checks both.

### Evals with real agents

Two sets of tests run real agents against fixture projects. They are outside the normal suite and CI (marker `agent_e2e`), cost model usage, and take minutes per case (the scenarios, much longer):

```sh
pytest -m agent_e2e tests/test_skill_evals.py --no-cov -k pre-commit-review
pytest -m agent_e2e tests/test_agent_scenarios.py --no-cov --basetemp <folder>
```

- **Skill evals** (`tests/test_skill_evals.py`) run Claude Code once per case of `tests/skill_evals/<skill>/evals.json` and check that the skill loads (`trigger`), does not load (`no-trigger`), or loads and produces what the case checks (`output`). `EXO_EVALS_MAX_TURNS` (default 40) and `EXO_EVALS_TIMEOUT` (default 1800 seconds) bound each case, and the results go, one JSON line per case, to `EXO_EVALS_REPORT` (or `skill-evals.jsonl` in pytest's temporary folder) for human review. The format of `evals.json` is documented at the top of `tests/_skill_evals.py`; `tests/test_skill_evals_schema.py`, which runs in the normal suite, checks it.
- **Scenarios** (`tests/test_agent_scenarios.py`) run a Tier 1 change, a Tier 3 change and a `quick` adoption with Claude Code and with GitHub Copilot CLI, and check the result with the engine (`exo speclint`, `exo check`, `exo discover status`), not with the agent's answer. `EXO_SCENARIOS_AGENTS` (`claude-code,copilot` by default; a missing agent is skipped), `EXO_SCENARIOS`, `EXO_SCENARIOS_TIMEOUT` and `EXO_SCENARIOS_REPORT` narrow and bound them; the other variables are at the top of the file. Each run leaves its project, its stream and its data in the `--basetemp` folder for review.

They need `claude` and, for the scenarios, `copilot` installed and signed in. Each case runs isolated:

- the fixture is copied to a temporary folder with its own git history, and `exo init` installs the case's packs there;
- `EXO_DATA_DIR` and `EXO_MEMORY_DB` point into that folder, so your memory and persona are not used;
- git reads an empty global config (`GIT_CONFIG_GLOBAL`) and no system config, so the agent cannot change yours, and `git push` is denied;
- Claude Code runs with `--setting-sources project,local` (none of your user settings, skills, plugins, hooks or `CLAUDE.md`) and `--strict-mcp-config` with no MCP servers;
- Copilot CLI runs with its own `COPILOT_HOME` for the run (your signed-in account, without your personal skills) and its built-in MCP servers off.

## Rules that matter when you contribute

- **Standard library only** in `src/exo/`. The exceptions are `memory/backends/` and `memory/embeddings/`, which import their packages lazily and fail with a clear message when the extra is missing.
- **Python 3.10.** No APIs from 3.11 or later without a fallback (for example `tomllib`).
- **Visible names come from `src/exo/_meta.py`**: the project folder, the environment prefix, the distribution and data folder name. `tests/test_meta.py` fails if a module writes them as literals.
- **Language.** Everything exo installs in a project (rules, skills, subagents, templates) and every CLI message is in English, and so are the user docs. Code comments, docstrings, the plan and the ADRs are in Spanish.
- **Tests first.** Every new behavior and every fixed bug comes with a test that failed before the change. Fixtures are synthetic: never real secrets or personal data.
- **Safe writes.** Atomic writes (a temporary file and `os.replace`), in binary, preserving the person's line endings; nothing written when nothing changes; a snapshot before mutating a managed file; never overwriting a file the person edited without `--force`.
- **Adapters are pure**: they compute operations and never write.
- **Agent permissions stay narrow.** A permission an adapter writes covers only the commands the skills run on their own (reading, checking, recording), never the ones that change the installation, delete or export memory, or run a command from the project's config. The reasons are in the engine's threat model, `docs/seguridad/threat-model-motor.md`.
- **Skills are copied byte for byte**, never templated.
- **Messages are actionable**: what happened, why, and what to do.
- **Conventional Commits**, one commit per reviewable unit, through a pull request with CI green.

## Adding a skill

1. Create `content/packs/<pack>/skills/<skill>/SKILL.md`:

   ```markdown
   ---
   name: my-skill
   description: >-
     What it does, in one or two sentences. Use it when the person asks to ...,
     or says "...", "...".
   metadata:
     exo-pack: <pack>
     exo-execution: inline
     exo-permissions: read-only
   ---

   # my-skill

   ## Result
   ...
   ```

   - `name` equals the folder: kebab-case, up to 64 characters, unique in the whole content.
   - `description` (up to 1024 characters) carries explicit triggers in English: agents pick the skill by it.
   - Only the standard fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) go at the top; everything of exo's goes in `metadata` with the `exo-` prefix. `exo-execution` is `inline` or `subagent` (with `exo-subagent` naming it). `exo-permissions` says what the skill may do: `read-only`, `write-specs` or `write-code`, optionally followed by `+` and what it adds, such as `read-only+tests`, `read-only+record` or `write-specs+git`; the template of the `skill-creator` skill lists the values in use. `exo validate` checks only that every `metadata` value is a string: these values are for whoever reviews the skill.
   - Up to 500 lines; details go in `references/`, and every `references/...` file it cites must exist.
   - A reference to another skill is written `skill:<name>`, and that skill's pack must be the same one or listed in `requires` or `optional` of the pack's manifest.
   - A contract it cites under `.exo/shared/` must ship in the same pack or in one it requires.

2. If the skill belongs to an SDD phase, add it to the phase map: `content/packs/core/shared/phase-skill-map.md`.
3. Add its evals in `tests/skill_evals/<skill>/evals.json`, with `trigger`, `no-trigger` and `output` cases, and run them.
4. Run `exo validate` and the suite. If the count of skills changed, update the count markers of the docs (see [Docs](#docs)).

The `skill-creator` and `skill-reviewer` skills in the `core` pack help you write and review one. Do not copy text from third-party skills without a compatible license and attribution.

## Adding a pack

1. Create `content/packs/<pack>/pack.json`:

   ```json
   {
     "name": "my-pack",
     "version": "0.1.0",
     "description": "What the pack covers, in English.",
     "requires": ["core"],
     "optional": ["security"]
   }
   ```

   `name` equals the folder, `version` is semver, `requires` installs with it and `optional` lets its skills reference skills of a pack that may not be installed. Folders that start with `_` are support files, not packs.

2. Add its `skills/`, and if it has them, `agents/` and `shared/` (contracts and schemas, installed in `.exo/shared/`). A subagent has a `name` and a `description`, and one that runs commands lists both `Bash` and `PowerShell` in `tools`: Copilot CLI on Windows gives no shell with `Bash` alone, and `exo validate` reports it.
3. If `exo init` should suggest it from the stack, add the signal in `src/exo/installer/stack.py`.
4. Add a row to the pack table in `README.md`, with its count marker, and an entry in `CHANGELOG.md`.

## Adding an adapter

An adapter gives an agent the files it reads. Check the agent's official docs first and record what you verified, with the source and the date, in `docs/agent-matrix.md`.

1. Write `src/exo/adapters/<agent>.py` with a class that has an `id`, a `capabilities()` and a `plan(ctx)` that returns operations (`WriteFile`, `MergeBlock`, `MergeKey`, `MergeListItem` from `exo.installer.ops`). It may look at whether a file exists, but it never writes: the installer applies, deduplicates and tracks the operations in the lock. `claude_code.py` and `copilot.py` are short examples, and `base.py` has the helpers for mirroring skills and subagents.
2. Register it in `ADAPTERS` in `src/exo/adapters/__init__.py`, and take it out of `GENERIC_ONLY` if it was there.
3. Add its detection signals (files, executables, environment variables) to `SIGNALS` in `src/exo/adapters/detect.py`.
4. If it reads `.claude/skills/` and `.claude/agents/`, add it to `CLAUDE_DIR_AGENTS` in `src/exo/adapters/base.py`; otherwise its skills go to `.agents/skills/`.
5. Add golden cases to `tests/test_adapters.py`, generate them with `pytest --update-golden` and review them. A second agent must not change what the first one gets.
6. Add a guide in `docs/guides/` and a row in the supported agents table of `README.md`.

## Docs

The user docs are in English and are checked by `exo validate --docs`, which reads the Markdown files of a folder (not its subfolders). `tests/test_validate_docs.py` runs it on the repository root and `docs/guides/`.

- **Counts.** A number that comes from the content goes between count markers, and must match:

  ```markdown
  The content ships <!-- exo-count:skills -->106<!-- /exo-count --> skills.
  ```

  The keys are `packs`, `skills`, `subagents`, `shared` (contracts), `agents` (agents with a dedicated adapter) and `skills:<pack>`. Markers inside code, like the one above, are examples and are not checked. Do not put markers in `CHANGELOG.md`: its numbers belong to each release.

- **Commands.** Every `exo <command>` cited in code (a code block or inline code), at the start of a command or after a shell operator, `python -m` or `uvx --from <package>`, must be a real subcommand.

Every command, flag and path a doc names must exist: check it with `exo <command> --help` or in the code.

## License

exo is released under the [MIT License](LICENSE). By contributing, you agree that your contributions are licensed under it.
