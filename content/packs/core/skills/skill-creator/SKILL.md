---
name: skill-creator
description: >-
  In the exo canonical format, creates a new agent skill, as engine content
  (content/packs/<pack>/skills/<name>/) or as a project skill in the
  agent's skills folder. It first checks that a skill is the right tool,
  then defines the job, the triggers and the non-triggers, and writes the
  strict frontmatter (name; a description with what the skill does, when to
  use it and real trigger phrases; metadata with exo-pack, exo-execution and
  exo-permissions), a SKILL.md of at most 500 lines with the details in
  reference files, cross-references that resolve, and synthetic examples.
  Then it checks the result with exo validate and the skill-reviewer gate.
  Use it when someone wants to add a skill, turn a repeated workflow or a
  set of instructions into a skill, or write the next skill of a pack.
  Triggers: "create an exo skill", "add a skill to this exo pack", "write a
  new skill in the exo canonical format", "turn this workflow into an exo
  skill", "scaffold an exo SKILL.md", "make an exo skill out of these
  instructions".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: write-specs
---

# skill-creator

## Result

- **A new skill folder** `<name>/` with `SKILL.md` and, when needed, `references/<topic>.md`, in its place:
  - **engine content:** `content/packs/<pack>/skills/<name>/` in the engine's repository, or `packs/<pack>/skills/<name>/` in any content tree with `packs/` and `rules/`;
  - **a project skill:** the skills folder the project's agents read, `.claude/skills/<name>/` or `.agents/skills/<name>/` (both, when the project uses both), outside the engine's lock.
- **Checks passed:** `exo validate` with no errors and no warnings for engine content, or the manual checks for a project skill, and a skill:skill-reviewer verdict before the skill is merged.
- **Three test prompts** (one that should trigger it, one that should not, one with a checkable output), or the repository's own eval format when it has one.

## When

- **Someone wants a new skill:** "add a skill that ...", "turn this workflow into a skill", "the next skill of the pack".
- **A long prompt or a team procedure** is repeated often enough to deserve one.
- **Not for:** improving an existing skill (skill:skill-improver); vetting a third-party skill (skill:skill-reviewer); a rule every task must follow (it belongs in the project rules, `AGENTS.md`); facts about one project (`.exo/context.md` or memory).

## Inputs

1. **The job,** in the person's words, and two or three real requests it should handle.
2. **Where it goes:** engine content (which pack) or a project skill.
3. **What exists:** `exo skills list` (engine skills), `.exo/skill-registry.md` (installed ones), and the agent's skills folders, to avoid overlaps and name clashes.
4. **The contracts it must respect,** when it touches the SDD cycle or project data: `.exo/shared/sdd-phase-common.md`, `.exo/shared/phase-skill-map.md`, `.exo/shared/skill-resolver.md`, `.exo/shared/capability-attribution.md` and `.exo/shared/data-protection.md`.
5. **For engine content,** the rules of that repository (its `AGENTS.md`): language, size, licenses, evals.

## Steps

The skeletons are in `references/skill-template.md`, the guide to descriptions and triggers in `references/description-and-triggers.md`, and the full list of checks with the validator's messages in `references/checks.md`.

### 1. Check that a skill is the right tool

| The need | Better as |
|---|---|
| A rule every task follows | The project rules (`AGENTS.md`) |
| Facts about this project | `.exo/context.md` or memory |
| One more step in an existing skill | An edit to that skill (skill:skill-improver) |
| A deterministic check | A script or a test the project runs |
| A procedure the agent loads on demand for a recognizable kind of request | **A skill** |

If an existing skill already covers most of the job, propose extending it instead, and stop here unless the person still wants a new one.

### 2. Define the job

- **Result:** what exists when the skill is done: a file, an answer, a gate, a record.
- **Triggers:** five to eight phrasings real people use. **Non-triggers:** two or three similar requests that belong to another skill, with its name.
- **Inputs** and what to do when one is missing (ask once with a default, stop, or degrade).
- **Where it runs:** `inline` by default; `subagent` only when one of the existing subagents has the right tools (for example `sdd-judge` for a read-only review).
- **Permissions:** one value of the vocabulary (step 4).
- **Inside an SDD change:** a skill that is not a phase never edits a phase's artifact; it returns text for the phase that owns it. Its own files are project documents, never files of the change root, written with the person's approval once the plan lists them (design.md, Modules / Files, in Tier 3; the Scope of proposal.md in Tier 1 and 2), so verify does not count them as drift (`.exo/shared/sdd-phase-common.md`, section C).

### 3. Name it

- kebab-case (`a-z`, `0-9`, single hyphens), up to 64 characters, equal to its folder.
- It says the job: `invoice-numbering-check`, not `helper` or `utils`.
- Unique across the engine packs and the project's skills. A project skill named like an engine skill blocks the installation of that pack: the engine never overwrites a file it did not generate.

### 4. Write the frontmatter

Only the Agent Skills fields: `name`, `description` and `metadata` (the standard also has `license`, `compatibility` and `allowed-tools`; use them only when needed). Everything of the engine goes in `metadata`, as strings with the `exo-` prefix:

| Key | Values |
|---|---|
| `exo-pack` | The pack that ships it. Leave it out in a project skill, which belongs to no pack |
| `exo-execution` | `inline`, or `subagent` together with `exo-subagent: <subagent name>` |
| `exo-phase` | Only for a skill of the SDD cycle or one of its gates: the phase it serves (`init`, `risk`, `new`, `explore`, `propose`, `spec`, `design`, `tasks`, `apply`, `verify`, `archive`, `judgment`, `status` or `orchestrate`). Leave it out in any other skill |
| `exo-permissions` | The most the skill may do (below) |

| `exo-permissions` | The skill may |
|---|---|
| `read-only` | Read and answer; it writes nothing |
| `read-only+tests` | Read, and run tests, linters or builds without changing anything |
| `read-only+record` | Read, and add entries to a change's AI Usage Record |
| `read-only+gate` | Read, and write only its gate file |
| `read-only+classify` | Read, and write the change's tier through `exo fitness classify` |
| `read-only+exo-init` | Read, and set up the project with `exo init` |
| `write-code` | Write code and tests |
| `write-specs` | Write project artifacts and documents (specs, docs, plans) |
| `write-specs+tests` | Write documents, and run tests, linters or builds |
| `write-specs+git` | Write documents and run git operations (branches, commits) |

Prefer a value already in use; a new combination is a decision for the pack's owner.

The description: up to 1024 characters, in English, saying what the skill does, then "Use it when ...", then `Triggers: "...", "..."` with real phrases. Specific enough not to load on unrelated requests, and different from its neighbors (`references/description-and-triggers.md`).

### 5. Write the body

The sections, in this order (`references/skill-template.md`): the title, Result, When (with what it is not for), Inputs, the Steps, Return (the output format with a short example), Rules, Record (inside an SDD change), and Before you finish (a checklist).

- English, second person, imperative, short sentences: "Read ...", "Write ...".
- Exact commands with real flags; a default for every question; a stop condition for every step that can fail.
- Say what happens when an input or a tool is missing: ask once, stop with `needs-input`, or degrade and say so.

### 6. Keep it short

- At most 500 lines in `SKILL.md`; aim for 150 to 300.
- Move long examples, catalogs, templates and rubrics to `references/<topic>.md`, one level deep, each cited by its exact relative path from `SKILL.md`. Every cited file exists, and every file in the folder is cited.

### 7. Make the references resolve

- `skill:<name>` only for skills of the same pack, or of a pack in its `requires` or `optional` (`pack.json`). Any other skill goes in backticks with its pack, and if the new skill relies on it, with the sentence `<pack>/<skill> not installed — applying inline criteria` and the inline criteria to apply (`.exo/shared/skill-resolver.md`).
- Paths under `.exo/shared/` only for contracts of its own pack or of a pack it requires (`core` always ships).
- A skill the phase map should load needs a row in `phase-skill-map.md`, and, in an optional pack, its row of inline criteria: in the engine's repository, propose both to the owner of the map.

### 8. Make it safe

- Nothing that `exo validate` or skill:skill-reviewer flags: downloading and running code in one step, sending data to an external address, asking the person for credentials or identity documents, text that tells the agent to drop its instructions or to hide something from the person, invisible characters, and literal Unicode escapes.
- **Synthetic examples:** `<placeholder>` values; no secrets, tokens, card numbers (not even published test ones), real emails or identity documents.
- **No hard dependency on a vendor:** an organization's tools are optional steps with an open fallback; ticket IDs follow `tickets.pattern`; CI and pull requests stay host-agnostic.
- **Never install anything** from a skill: when a tool is missing, the skill names the command the person could run and goes on by hand.
- **Scripts** only when a step must be deterministic: small, readable, no network, and described in `SKILL.md`.
- **No third-party text** without a compatible license and its attribution.

### 9. Write the test prompts

Three short requests the person can try in a fresh session, none of them naming the skill:

- **trigger:** a real request that should load it;
- **no-trigger:** a similar request that belongs to another skill;
- **output:** a request whose result can be checked (a file written, a phrase in the answer).

A repository with its own eval format (the engine's has one for its packs) uses it, as its `AGENTS.md` says.

### 10. Check it

1. **Engine content:** `exo validate --root content` in the engine's repository (without `--root`, it validates the content packaged with the installed exo, not your working tree), or `exo validate --root <tree>` for another content tree. No errors and no warnings; then the repository's own tests.
2. **A project skill:** `exo validate` does not apply to a loose skills folder. Run the manual checks of `references/checks.md`.
3. **skill:skill-reviewer** on the new folder, always, before it is merged. An `ESCALATED` verdict needs the `tech_lead` role.

### 11. Deliver

Show the folder tree with the line count of each file, the description, the checks and the reviewer's verdict. Commit it as the project's rules say (skill:work-unit-commits). Never copy it to a user-level folder or another project without the person asking.

## Return

```text
New skill: invoice-numbering-check (project skill)

.claude/skills/invoice-numbering-check/
  SKILL.md                      142 lines
  references/series-rules.md     61 lines

Description: 612 characters, 6 triggers. Neighbors checked: none overlaps.
Checks: frontmatter parses, name = folder, references resolve, no invisible characters.
skill-reviewer: APPROVED, no findings.
Test prompts:
  trigger:    "check that the invoice numbers in this export have no gaps"
  no-trigger: "write an invoice template"
  output:     "check numbering in tests/fixtures/invoices.csv and list the gaps" -> the answer lists A-000124
```

## Rules

- **One job per skill,** with a description that says when to load it and when not to.
- **The canonical format,** always: strict frontmatter, `exo-` metadata, at most 500 lines, details in `references/`.
- **Resolvable references** only; everything else degrades out loud.
- **Safe and synthetic:** nothing the validator or the reviewer flags; no real data in examples.
- **Reviewed before merged:** skill:skill-reviewer runs on every new skill.

## Record

Inside an SDD change whose diff adds a skill, a phase that runs inline records it before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it. In verify, the phase map also loads skill:skill-reviewer for that diff:

```bash
exo change record <change> --add capabilities_used '{"name": "skill-creator", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"skill-creator"'
exo change record <change> --add capabilities_used '{"name": "exo validate", "type": "command", "activation": "auto"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record.

## Before you finish

- [ ] A skill is the right tool, and no existing skill covers the job.
- [ ] The name is kebab-case, unique, and equal to the folder.
- [ ] The frontmatter has only standard fields; the description says what, when and its triggers, within 1024 characters.
- [ ] `SKILL.md` has Result, When, Steps, Return, Record and Before you finish, within 500 lines.
- [ ] Every `references/` file is cited and exists; every `skill:` reference resolves; other skills degrade out loud.
- [ ] Examples are synthetic; nothing the validator or the reviewer flags.
- [ ] `exo validate` (or the manual checks) and skill:skill-reviewer passed; the three test prompts are written.
