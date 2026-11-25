# Changelog

All notable changes to `exo` (distributed as `exo-harness`) are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - Unreleased

Milestone M4: stack packs, the rest of the skill catalog, safe updates between engine versions, installation from GitHub with one command, and a security review of the engine itself.

### Added

- The catalog grows from 41 to 106 skills in 12 packs, with 6 subagents and 20 shared contracts. Six packs are new: `product`, `frontend`, `java`, `python`, `ops` and `agentic` (ADR-0016).
- `java` pack: `backend-and-api`, `backend-engineering`, `java-build-resolver`, `java-coding-standards`, `java-reviewer`, `jpa-patterns`, `security-scan-jkp`, `springboot-patterns`, `springboot-security` and `springboot-verification`, written for Spring Boot 4 and Spring Security 7. `security-scan-jkp` also covers Python.
- `python` pack: `python-patterns` and `python-reviewer`.
- `frontend` pack: `accessibility-audit` and the TypeScript and React stack: `frontend-design`, `frontend-engineering`, `frontend-patterns`, `playwright`, `react-patterns`, `react-testing`, `security-scan-node`, `tailwind-4`, `typescript`, `typescript-reviewer` and `zod`.
- `exo init` suggests the stack packs (`python`, `java`, `frontend`) from the detected stack, also in monorepos (`package.json` workspaces and manifests in subfolders). `product`, `design` and `agentic` are never suggested, because the repo gives no signal for them.
- `ops` pack: `capacity-planning`, `chaos-engineering`, `debug-systematically`, `incident-response`, `kibana-logs`, `log-analysis`, `on-call-handoff`, `root-cause-5whys`, `runbook-writer` and `slo-design`.
- `product` pack: `product-discovery`, `functional-flow-designer`, `work-item-creator`, `refinement-assistant` and `roadmap-generator`. The work-item skills use the project's ticket pattern instead of a specific tracker.
- `agentic` pack: `agentic-reliability-review` and `context-engineering-review`.
- `design` pack: `architecture-diagram-designer`, `diagram-design`, `executive-visual-quality-gate` and `uml-visual-designer`, with a neutral executive style. An optional `.exo/brand.json` replaces it (its shape is in the `executive-style.md` contract), and `exo uninstall` keeps that file.
- `security` pack: `secure-diagram-sanitizer`.
- `core` pack: `parallel-dispatch`, `chained-pr`, `cognitive-doc-design`, `comment-writer`, `issue-creation`, `skill-creator`, `skill-improver` and `software-solution`.
- SPDD overlay in the `sdd` pack: `reasons-canvas-author`, `prompt-spec-review`, `prompt-code-sync`, `context-anchoring` and `sdd-onboard`. A change can carry an optional `canvas.md` with the seven REASONS sections (Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards), checked by `exo speclint`. A logic fix updates the canvas before the code; a refactor updates the code first.
- New judges in the `quality` pack: `judge-product`, `judge-business`, `judge-frontend` and `judge-team` (followup prefixes `JPRD`, `JBIZ`, `JFE` and `JTEAM`). Two on-demand reviews: `excellence-committee`, which convenes only the judges that have something to review, and the five-lens `review-4r`.
- Conditional gates, which depend on the change rather than its tier: `accessibility_review`, written by `accessibility-audit` in verify when the change touches UI files (a Critical or High finding blocks `ready` unless it is dismissed with a reason), and `prompt_spec_review`, which `exo check` requires when the change has a `canvas.md`. Listing either one in `governance.gates` makes it mandatory for that tier.
- A shared CWE to OWASP Top 10:2025 table (`.exo/shared/owasp-2025.md`) for the stack scanners and reviewers. Every OWASP citation now names its edition (for example `A05:2025`).
- Commercial scanners and log platforms are optional steps: without them, the skills use open tools.
- Project documents (diagrams, solution documents, runbooks, SLOs, postmortems) live outside the change folder. During a change, a skill writes them with the person's approval and lists them in the plan, so verify does not count them as drift.
- Skill evals: the 38 cycle, judge and stack skills of this release, plus `pre-commit-review`, ship `trigger`, `no-trigger` and `output` cases in `tests/skill_evals/`. An isolated runner outside the normal suite (`agent_e2e`) runs them against real Claude Code; all 117 cases pass.
- `exo update`: previews what a new engine version changes (new, modified, renamed and orphaned files, and conflicts with your edits) and writes only with `--apply`. Your edits are kept unless you pass `--force`; orphaned skills are deleted only with `--prune` (in a terminal, `--apply` asks). It does not take a project back to an older version without `--force`, and `--json` gives the same information.
- Versioned migrations for `lock.json` (like `config.json` and the memory database); `exo update --apply` saves a migrated `config.json`, with a snapshot first.
- `exo doctor` warns when the lock was written by another engine version.
- `exo status` shows the project at a glance: agents, packs, the lock's version against the engine's (with "run `exo update`" when they differ), the git hooks in this clone, your persona, manual changes to generated files, and each active change with its tier, phase, next phase, gates and open followups. Colors only in a terminal, and never with `NO_COLOR` or `TERM=dumb`; `--json` does not change.
- Role overlays, or personas (ADR-0018): `exo persona set dev|tech-lead|qa|product`, `exo persona show` and `exo persona clear`, with one overlay per role in `.exo/shared/personas/`. The role is stored in the user data folder, never in the repo. At the start of a session the agent runs `exo persona show --json` and follows the overlay, which changes what it shows first and how, and never relaxes a rule, gate, tier or approval.
- Installation from GitHub with one command: `curl -fsSL https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.sh | sh` and `irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 | iex`. Piped or downloaded alone, the installers install the latest release, or the tag, branch or commit in `EXO_REF`, from `EXO_REPO_URL` (GitHub by default). With uv they run `uv tool install` from git; without uv they check the release wheel against the release's `SHA256SUMS` before installing it, and install nothing if it does not match or cannot be downloaded (`install.ps1` computes the hash with .NET, so it also works in a Windows PowerShell started from PowerShell 7, where `Get-FileHash` is missing). They download only over `https` (or from a mirror on the same machine) and refuse a redirect to another protocol, so `install.sh` needs curl rather than wget for that path. `install.sh` creates the user data folder readable only by its owner. They never run a half-downloaded script, and explain how to read them before running them. Run from a clone, they install the clone, as before.
- Running exo without installing it: `uvx --from git+https://github.com/julimonte03/exo-harness exo init`.
- A release workflow: a `v*` tag checks that it matches the engine version, builds and checks the wheel and the sdist, writes `SHA256SUMS`, publishes a GitHub release with them, and publishes `exo-harness` to PyPI by trusted publishing. PyPI is not live yet.
- User documentation in English (D-48): `README.md`, `QUICK-START.md`, `CONTRIBUTING.md`, and guides for Claude Code, GitHub Copilot, other agents, adopting an existing project and troubleshooting in `docs/guides/`.
- `exo validate --docs <path>` checks the Markdown docs of a folder: every count cited between markers (`<!-- exo-count:skills -->`) must match the content, and every `exo <command>` cited in code must exist. A test runs it on the repository's own docs.
- Scenario tests with real agents (`tests/test_agent_scenarios.py`, outside the normal suite): a Tier 1 change, a Tier 3 change and a `quick` adoption, with Claude Code and with GitHub Copilot CLI, checked with `exo speclint`, `exo check` and `exo discover status`.
- exo is open source under the MIT License (`LICENSE`, declared in the package metadata).

### Changed

- The `review` skill is now `pre-commit-review` (D-40), so it no longer clashes with Claude Code's built-in `/review`. In a project installed with an earlier version, `exo update` shows it as a rename, and the old `review` folder stays until `--prune` deletes it.
- `exo check` checks every gate present in a change's `gates/` folder, not only the ones its tier requires: a gate without a readable verdict is an error, and `ESCALATED` needs `tech_lead` approval, as with required gates.
- `sdd-judge` also reviews the propose and spec phases.
- In automatic mode, rework converges: the judges' findings are decided by severity (Critical and High go back to apply; Medium and Low are recorded as deferred to a followup, so they do not block the archive, and `pr.md` lists them in its new Known followups section, which `exo speclint` requires), a re-verify reviews the fix rather than the whole diff again, and there are at most two rework rounds (each return from verify to apply, for the verdict or for a Critical or High judge finding): on the next one, the cycle stops and asks the person.
- `exo sync` no longer deletes orphaned skills and subagents (ones the content no longer ships): it reports them, and `exo sync --prune` deletes them. `remove-agent`, a pack removed from the config and `uninstall` still remove their own files.
- A `sync` with nothing to change no longer runs git to re-check the hooks when they are already active.
- The engine's own CI moved to GitHub Actions: Windows, macOS and Linux with Python 3.10 to 3.13, running ruff, pytest with coverage, `exo validate` and both `--version` entry points, plus separate jobs for the memory extras, the installers and the build (ADR-0017). `azure-pipelines.yml` remains only as an example. Every action is pinned to a commit SHA, Dependabot proposes their updates, and no workflow expands an expression inside a shell step.
- The `security` pack, the `quality` judges and reviews that reuse it, the citations in `sdd` and `core`, and the engine's gate template cite OWASP Top 10:2025 instead of 2021, with each CWE's category taken from `.exo/shared/owasp-2025.md`. `security-code-review` and `secure-coding-baseline` add checks for A10:2025 Mishandling of Exceptional Conditions.
- The subagents that run commands (`sdd-implementer` and `sdd-verifier`) declare `PowerShell` as well as `Bash`: GitHub Copilot CLI on Windows gives a custom agent no shell with `Bash` alone. `exo validate` reports any subagent, also in a third-party pack, that lists `Bash` without `PowerShell`.
- `exo codeowners` also gives the `tech_lead` entries what the agents read and what git runs: `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.agents/`, `.mcp.json`, `.husky/`, `.pre-commit-config.yaml` and `.gitattributes`.

### Security

- The engine's threat model, `docs/seguridad/threat-model-motor.md` (in Spanish): the remote installers, the release and CI, the git hooks, the agent's CLI and the MCP server, memory, reverse engineering, skills and packs, `update` and `sync`, personas, the eval runners and the `EXO_*` variables, each threat with its mitigation or its accepted risk.
- Claude Code's project permission covers only the `exo` commands that the skills run on their own (reading, checking and recording). The commands that change the installation, delete, reindex or export memory, or run a command from the project's config ask the person first.
- `exo gate publish` runs `review.publish_command` only after the person approves that exact command on their machine: in a terminal it shows the command and asks, and `--approve-command '<command>'` approves exactly that text, which must match the configured command, so a CI pipeline pins the command it accepts. The approval is kept in the user data folder, never in the repo, and a different command asks again.
- The `openai-compatible` and Ollama embeddings providers no longer follow redirects, so the API key and the memory text never reach another address, and `EXO_EMBEDDINGS_URL` must be `https` unless it points to this machine.
- On Linux and macOS, the user data folder is created readable only by its owner, and the memory database, `persona.json`, the approved commands, the uninstall backups and `exo mem export --output` are written for the owner only. `exo doctor` warns when other users can read the data folder.
- The runners of the agent evals give git an empty global config and deny `git push`, so an agent cannot change the person's git config or publish anything.

### Fixed

- A gate file saved as UTF-16 no longer aborts `exo check`, and an unreadable gate is reported instead of stopping the check.
- Stack detection works in a project that a parent repository ignores.
- A `lock.json` whose `agents` or `packs` is not a list of names (for example `null`) gives an error that names the file and how to restore a snapshot, instead of a traceback or a list read letter by letter.

## [0.2.0] - 2026-11-17

Milestone M3: reverse engineering and adoption of existing projects.

### Added

- `discovery` pack to understand an existing project without touching its code. Its entry point is `/exo-adopt`, which runs the deterministic stages, leads extraction, synthesis, audit and validation with the person, and resumes where it left off. It comes with `re-extract`, `re-synthesize`, `re-audit` and `re-adoption-plan`, and the read-only subagents `re-extractor` and `re-auditor`. `exo init` offers the pack only when the repo already has code.
- `design` pack, starting with `architecture-decision-record` for recovered ADRs, and `context-config-audit` in `core`, which audits the agent configuration a repo already had. The catalog has 41 skills in 6 packs and 6 subagents.
- `exo discover inventory`: languages, frameworks, entry points, tests, CI, database migrations, API contracts, infrastructure and sensitive files (by name only, never their content).
- `exo discover structure`: module graph (`module-graph.mmd`), hotspots from git churn and ownership per module.
- `exo discover plan`: bounded work units with priority and an effort estimate. It does not replace a plan with closed units unless you pass `--replan`.
- Deterministic results: the same repo gives the same bytes on every run, file hashes ignore line endings so Windows and Linux agree, and committing the results does not change them. The file list comes from `git ls-files`, minus vendored, generated and binary files and whatever `discovery.ignore` lists.
- A unit loop driven by the CLI, so it survives context compaction, interruptions and agent changes: `exo discover next`, `exo discover done` (validates the evidence markers and runs the secret scanner), `exo discover skip <unit> --reason`, `exo discover reopen` (a unit, or a capability's units with `--capability`) and `exo discover synthesized <capability>`.
- Evidence on every recovered claim: `[Code] path:line` (or `path:start-end`), `[Doc] path` or `[Inferred: high|medium|low]`. Claims cite the location and never copy a value.
- Independent audit: `exo discover sample` draws a seeded sample of requirements weighted by criticality, `exo discover audit` records the verdicts and `exo discover coverage` reports precision per capability, so low-precision capabilities go back to extraction.
- `exo discover status` (read-only) shows what is done, skipped, stale or missing to finish the adoption, and warns about changes outside the allowed paths. `exo discover update` marks as stale only the units and capabilities whose files changed.
- The pipeline state lives in `.exo/discovery/` and is meant to be committed. There is no shared state file: each unit's state is derived from its own record, so two people or two branches do not collide, and an interrupted extraction is simply redone.
- As-is capability specs: a preamble with `Status: as-is` or `Status: as-is-validated` and `Source:` (the units it came from). A requirement in an as-is spec without evidence or an inference marker is an error.
- Reverse engineering writes only to `.exo/discovery/`, `specs/capabilities/`, `.exo/context.md` (by section, with the person's approval) and recovered ADRs (`*-recovered-*`). It never runs the project's build or tests and does not write to memory.
- `discovery_status` tool on the optional MCP server.

### Changed

- Spec problems have a severity (`error` or `warning`) that `exo speclint`, `exo check` and the `pre-commit` hook respect. A requirement with evidence but no scenario is a warning.
- `exo specs merge` refuses to merge into an as-is capability that a person has not validated yet.
- `exo uninstall` keeps `.exo/discovery/` and `.exo/context.md`, and says so.

### Fixed

- The `pre-commit` hook no longer blocks `.npmrc` as a credentials file (many repos commit it with only the registry URL); a token inside it is still caught by the scanner.

## [0.1.0] - 2026-11-16

Milestone M2: governance. First version that installs a complete harness: rules, skills, the SDD cycle, memory and gates. It ships 34 skills in 4 packs (`core`, `sdd`, `quality`, `security`) and 4 subagents.

### Added

#### Installation and project adoption

- One-command installers, `install.sh` and `install.ps1` (Windows). They use `uv tool install` when uv is available, or a virtual environment in the user data folder otherwise; add the launcher to the user `PATH` (on Windows, keeping the registry value type); never overwrite another `exo`; run `exo doctor`; and can adopt a project in the same step (`--init` / `-Init`). `uninstall.sh` and `uninstall.ps1` revert them.
- `exo init` adopts a project: it detects the agents in use, suggests packs from the detected stack and asks for the ticket pattern. `--agents claude-code,copilot` and `--yes` run it without questions. `exo sync`, `exo status`, `exo add-agent`, `exo remove-agent` and `exo uninstall` manage the installation afterwards.
- Every generated file is tracked in `.exo/lock.json` with its hash. A second `init` or `sync` reports no changes, writes nothing and creates no snapshot.
- Hand-edited generated files are reported as conflicts: the command exits with 1 and writes nothing. `--force` overwrites them after a snapshot, but never touches a file of yours that is not in the lock. `--dry-run` lists the files without writing.
- Your own files stay byte for byte identical outside exo's marked blocks, including CRLF line endings, in `AGENTS.md`, `CLAUDE.md` and `.gitignore`.
- Changes are transactional: a snapshot is taken before writing and restored if a command fails half-way, and a broken config or one with a newer schema stops the command instead of removing agent files.
- `exo uninstall` returns the project to its original state, because the lock records what exo created in each file, and keeps a backup in the user data folder.
- Deterministic, deduplicated project snapshots with `exo backups list`, `exo backups pin` and `exo backups unpin`; `exo restore` saves the current state before restoring, and extraction rejects path traversal, absolute paths, links and devices.

#### Agents

- An agent-agnostic base: a rules block in `AGENTS.md`, the skill registry (`.exo/skill-registry.md`) and shared contracts in `.exo/shared/`, so any agent that reads `AGENTS.md` gets the rules and skills.
- Claude Code adapter: an `@AGENTS.md` block in the project's `CLAUDE.md` when it has one, skills in `.claude/skills/`, subagents in `.claude/agents/` and the `Bash(exo:*)` and `PowerShell(exo:*)` permissions in `.claude/settings.json`. `exo doctor` warns when the workspace is not trusted, since project permissions apply only then.
- GitHub Copilot adapter (VS Code and Copilot CLI): Copilot reads `AGENTS.md`, the skills in `.claude/skills/` and the subagents in `.claude/agents/`, shared with Claude Code when both are targets.
- Cursor, Codex, Gemini and Devin are detected and covered by the base: when one of them is a target, skills are also copied to `.agents/skills/`. Copies are byte for byte and tracked by the lock, never symlinks (ADR-0006, ADR-0007).
- The CLI is the agent's interface to the engine (ADR-0005). An optional MCP server, `exo mcp`, exposes the same functions with the same input validation; it is off by default and adapters write MCP config only when `.exo/config.json` has `"mcp": {"enabled": true}`.

#### Engine tools

- `exo validate` checks the content: pack manifests, skill frontmatter against the Agent Skills standard, `skill:` references, cited reference files, the 60-line limit of the base rules and secret patterns.
- `exo fitness classify --evidence-json` assigns a risk tier from seven dimensions scored 0 to 3, using rules FM-00 to FM-30. Missing or unreadable evidence gives Tier 4.
- `exo speclint` checks the required headings, ID formats and cross-references of SDD artifacts, with `--json` output.
- `exo skills list`, `exo skills info`, `exo skills diff`, `exo change list`, `exo change status`, `exo change followups` and `exo change ai-usage`.
- `exo doctor` checks Python, platform, console encoding, `PATH`, embedded content, disk space and its own self-tests, plus per-agent and memory checks.

#### Memory

- `exo mem`: a per-user memory in one SQLite database in the user data folder (override with `EXO_MEMORY_DB`), shared by all your projects and scoped by the project detected from its git remote. It includes `exo mem save`, `exo mem search`, `exo mem context`, `exo mem session summary` and `exo mem export`, among others: 15 operations, the same over the CLI and the optional MCP server, which can both use the database at the same time (ADR-0009). `exo mem save` shows similar existing memories.
- Lexical search (FTS5) always works without extras. With the `[vector]` extra (sqlite-vec and FastEmbed) and a model, search is hybrid; the default comes from a documented experiment, where hybrid search reached a Recall@5 of 80.0 against 62.2 for lexical (ADR-0010). model2vec is available as an alternative in the `[static]` extra.
- Models are downloaded only with `exo mem model pull` and then run locally, offline. The provider and model are stored in the database and changed with `exo mem reindex --provider ...`. Indexes are derived data: `exo mem reindex` rebuilds them from SQLite without losing anything.
- Nothing leaves the machine without permission: a remote provider (`openai-compatible`, or Ollama on another host) needs `--allow-remote`.
- No session hooks: the `memory-protocol` skill and the `AGENTS.md` rules tell the agent to run `exo mem context` at the start and close with `exo mem session summary`.
- Memory has no secret filter and `exo mem export` exports content as is; the rules tell agents never to store secrets or personal data.

#### SDD cycle and living specs

- `core` and `sdd` packs with the cycle: `sdd-orchestrator`, `sdd-init`, `sdd-new`, `sdd-explore`, `sdd-propose`, `sdd-spec`, `sdd-design`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-archive`, `sdd-status`, `sdd-continue`, `sdd-ff` and `risk-tiering`, plus `context-retrieval`, `ai-usage-record`, `test-strategy`, `code-generation`, `branch-pr`, `work-unit-commits`, `project-onboarding` and `memory-protocol`.
- Subagents `sdd-explorer`, `sdd-implementer`, `sdd-verifier` and `sdd-judge`: explore, verify and the judges run read-only with fresh context, and apply runs in `sdd-implementer`. In an agent without subagents, every phase runs inline and declares "no isolation".
- Ceremony proportional to risk: the tier decides the required artifacts (Tier 2 and up require `test-spec.md`). Only the orchestrator re-classifies; an upgrade is automatic, and a downgrade needs the person's literal confirmation (`--confirm-downgrade`).
- `exo change new` creates a change and its AI Usage Record. `exo change record --phase-done` records each phase, and `exo change status` computes `next_phase`, so a change resumes across sessions.
- Living specs per capability in `specs/capabilities/<capability>/spec.md`, with `CAP-<capability>-FR-n` IDs. A change's `spec.md` is a delta with ADDED, MODIFIED and REMOVED requirements (ADR-0013).
- `exo specs merge <change>` merges a delta by ID: it validates everything before writing, is idempotent, keeps tombstones under `## Removed Requirements` so IDs are never reused, and preserves line endings. `exo specs list` lists the capabilities.
- `exo check` verifies the changes touched by the diff: speclint, the AI Usage Record and the artifacts each tier requires. `--base` compares against the merge base.
- Tickets without any tracker integration: each project sets a ticket pattern (a regular expression and an example). The ID is validated and normalized in change and epic names (`AB#123` becomes `AB-123`), and without a pattern there are no tickets (ADR-0012).

#### Governance, security and gates

- Always-on rules in `AGENTS.md`, kept to at most 60 lines.
- Git hooks, installed by `exo init` in `.exo/githooks` and activated with `core.hooksPath`: `commit-msg` (Conventional Commits, with the ticket as a `Refs:` footer), `pre-commit` (secrets, personal data and credential files in what is staged) and `pre-push` (pushes to protected branches, force-pushes and deletion of protected branches). If the project uses husky or the pre-commit framework, exo adds its steps there instead of replacing them. `exo uninstall` reverts `core.hooksPath`.
- Data protection without an organization profile: secrets and credentials are always blocked (Critical); cards (Luhn) and IBAN (mod 97) are flagged as Restricted, which a waiver can allow; country ID documents, email and phone are optional detectors.
- `exo check` is the gate a CI runs (`exo check --base <target branch>`): config, speclint, an AI Usage Record with a non-empty `capabilities_used`, required artifacts, the `judgment-day` record in Tier 4, the configured gates with their verdicts (a `blocked` verdict fails) and a secret scan of the diff. It exits non-zero when anything fails.
- Gates are change artifacts (`<change-root>/gates/<gate>.md`) with a fixed format and a marker. `exo gate publish` builds one text per gate and runs the project's `review.publish_command` once per gate, or prints the texts; `--dry-run` shows them.
- No platform integrations: the repo host is detected from the remote (`github`, `azure-devops`, `gitlab` or `other`) and stored in the config, and the CI and review contract includes examples for common platforms.
- `exo p0`, a minimum regression gate: the scanner on a synthetic dataset, input validation and active git hooks, ending in `P0 GATE: PASSED`.
- `quality` pack: `harness-review`, `review`, `judgment-day`, `judge-code-reviewer` and `judge-security`, with a shared contract for judges. Judge findings are tracked as followups that can be marked fixed or dismissed with a reason.
- `security` pack: `secure-coding-baseline`, `security-code-review`, `threat-modeling`, `data-classification` and `prompt-hygiene`; `skill-reviewer` in `core`, backed by a deterministic pre-check in `exo validate`.

#### Language

- Everything exo installs or generates in a project (rules, skills, subagents, templates, SDD artifacts) and all CLI messages are in English (ADR-0011). The agent still answers in the language the person uses.

## [0.0.1] - 2026-10-30

Foundations.

### Added

- The `exo-harness` package, which provides the `exo` command (the name `exo` is taken on PyPI). It requires Python 3.10 or later and has no runtime dependencies.
- `exo --version` and `python -m exo --version`.
- Fixed names for what exo writes: the `.exo/` project folder, the `EXO_` prefix for environment variables, and a per-user data folder named `exo-harness`, which avoids clashing with an unrelated tool that uses `~/.exo` (ADR-0001).
- An agent compatibility matrix (`docs/agent-matrix.md`) for Claude Code, Copilot CLI, VS Code, the Copilot cloud agent, Cursor, Codex, Gemini and Devin: rules files, skill and subagent folders, MCP config, hooks, commands and environment variables, each with its source or marked as not verified.
- Development setup: the `[dev]` extra with pytest (with coverage) and ruff, and LF line endings across the repo.
- The first architecture decision records: name and layout, Python with a standard-library core, a canonical source with per-agent adapters, and the relationship with upstream projects (ADR-0001 to ADR-0004).
