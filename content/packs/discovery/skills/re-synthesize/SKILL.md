---
name: re-synthesize
description: >-
  Turns the closed units of a reverse-engineered project into what the team
  will use: groups the units into capabilities by bounded context and writes
  one as-is spec per capability, with its Status and Source preamble and
  evidence on every requirement; proposes the Architecture (Mermaid context
  and containers), Modules, Main flows and Integrations sections of the
  project wiki and writes each one only after the person approves it;
  recovers the architecture decisions as ADRs with status Recovered; and
  fills the open questions and the technical debt. After `exo discover
  update` or a failed audit, it rewrites only as-is specs, keeping their IDs;
  validated specs change by delta. Runs inline in R4 of exo-adopt. Triggers:
  "synthesize the units", "write the as-is specs", "recover the specs",
  "group the units into capabilities", "re-synthesize".
metadata:
  exo-pack: discovery
  exo-execution: inline
  exo-permissions: write-specs
---

# re-synthesize

## Result

- One `<specs_dir>/capabilities/<capability>/spec.md` per capability, with `Status: as-is`, evidence on every requirement, and `exo speclint` without errors (missing scenarios are warnings).
- Every closed unit in the `Source:` of at least one capability, or named in your report with the reason it has none (pure infrastructure, for example).
- The wiki sections Architecture, Modules, Main flows and Integrations in `.exo/context.md`, each written only after the person approved it.
- The recovered ADRs the person approved, in the inventory's `adr_dir`.
- `.exo/discovery/open-questions.md` and `.exo/discovery/debt.md`.
- Nothing written outside `.exo/shared/discovery-contract.md`, section G.

The contract (sections B, E and G) rules this skill. When they disagree, the contract wins. The formats of every file you write are in `references/formats.md`.

## Before you start

1. `exo discover status --json`. If `outside_changes` lists files, stop and tell the person. Every unit must be `done` or skipped (`exo discover skip`); pending or stale units go back to R3 first (exo-adopt). A skipped unit has no extraction: name it in the capability's open questions instead of guessing its behavior.
2. Read the engine's outputs in `.exo/discovery/`: `inventory.json` (frameworks, entrypoints, tests, CI, migrations, API contracts, infrastructure, `adr_dir`), `structure.json` and `module-graph.mmd`, `hotspots.json`, `plan.json` (units, modules, `criticality`, `detail`), and every `units/<unit>.md`. `specs_dir` is in `.exo/config.json`.
3. Many units: read them in batches and keep a short index as you go (unit, candidate capability, entities, key rules, files cited), so you do not hold every document at once.
4. Existing specs: `exo specs list --json`. A capability with status `as-is-validated`, or with no status (a living spec of the SDD cycle), is never rewritten here (see Synthesize again).
5. For the ADRs, load `architecture-decision-record` (pack `design`) through `.exo/shared/skill-resolver.md`; when it is not installed, say `design/architecture-decision-record not installed — applying inline criteria` and use its row in `.exo/shared/phase-skill-map.md` with the format in `references/formats.md`.

## 1. Group the units into capabilities

- **By bounded context, not by folder:** what the business would name (billing, room-booking, member-accounts). Look at the entities, the operations, the vocabulary of the messages, the entrypoints and routes, and which tables each unit owns.
- **A unit can feed several capabilities,** and a capability several units. A rule goes to the capability where the business sees it.
- **Infrastructure units** (database helpers, configuration, logging, HTTP plumbing) usually make no capability of their own: they go to the wiki (Modules, Integrations), and the rules they enforce go to the capabilities that rely on them.
- **Names:** lowercase kebab-case nouns. The folder name is the one in every ID (`CAP-room-booking-FR-1`).
- In interactive mode, show the person the grouping first (capability, units, one line of purpose) and adjust it if they ask. In automatic mode, go on and report it.

## 2. Write the as-is specs

Use the shape in `references/formats.md`. `exo speclint` and the engine check exactly this:

- **Preamble**, between the `# Capability: <name>` title and `## Purpose`, outside comments: `Status: as-is` and `Source: exo discover; units: <id>, <id>`, with the unit IDs of `plan.json`.
- **`## Purpose`** in one or two sentences, and **`## Requirements`** with one block per FR, `### CAP-<capability>-FR-n: <title>`, numbered from 1.
- **One behavior per FR,** in the present tense, as the system does it today, the odd parts included: this is what it is, not what it should be. A likely bug is described as it is, and goes to `debt.md`.
- **Evidence in every block**, spelled exactly `[Code] path:line`, `[Code] path:start-end`, `[Doc] path` or `[Inferred: high|medium|low]`. A block without one is an error in an as-is spec.
  - Carry the citations of the unit claims that support the FR: `exo discover done` checked them. A new citation only after you read that line.
  - Prefer `[Code]`: `exo discover update` finds the stale capabilities through the files they cite, and `coverage.md` counts as evidenced only the FRs with `[Code]` or `[Doc]`. An FR that is only inferred is probably an open question.
  - Business values as the code has them; secrets and personal data never (contract, section B).
- **Scenarios only from the project's tests:** when a unit's Tests section shows a test of the behavior, write `#### Scenario: <title>` with Given, When and Then, and cite the test on the Then line. No `S-n` IDs: they belong to change deltas. Without a test, leave the FR without a scenario; speclint warns, and the gap feeds the characterization tests of R6.
- **NFRs** (`CAP-<capability>-NFR-n`) for measurable limits the code sets (a timeout, a page size, a retry count), with evidence. The audit samples FRs only.
- **Check each spec:** `exo speclint <specs_dir>/capabilities/<capability>/spec.md`. Fix every error; warnings about missing scenarios are expected.
- **Record it:** `exo discover synthesized <capability>` once the spec passes. The engine keeps the hashes of the files its FRs cite, and reports the capability as stale when that code changes, until you synthesize it again.

## 3. Synthesize again

After `exo discover update --json` (its `stale_capabilities`), or for a capability that `coverage.md` flagged, once its units were extracted again:

- **`Status: as-is`:** rewrite it from the current units. Keep the ID of every FR that still holds and update its text and evidence; a new behavior takes the next free number; an FR that no longer holds moves to `## Removed Requirements` with its heading, the line `Removed by re-synthesis after the code changed.` and a `Reason:` line, so its ID is never reused. Update `Source:`.
- **`Status: as-is-validated`, or no status:** do not edit it. Under the capability's heading in `open-questions.md`, list each difference (the FR, what the code does now, the evidence), and tell the person that the spec follows through an SDD change (`sdd-new`) whose delta modifies those requirements, merged with `exo specs merge`.
- **New files without a unit** (`new_files`): rebuilding the plan with `exo discover plan --replan` is the person's call.

## 4. Propose the wiki sections

`.exo/context.md` belongs to the person (`.exo/shared/project-wiki-guard.md`). Follow the structure of skill:project-onboarding: find it in `.exo/skill-registry.md` and read `project-onboarding/references/context-template.md`. Its sections win over the shapes in `references/formats.md`.

| Section | From |
|---|---|
| Architecture | One Mermaid diagram of the context and the containers, as `project-onboarding`'s template says: the people and external systems outside, what runs on its own inside (apps, databases, queues, workers), from `inventory.json` and the units' Integrations, with the evidence of each element under the diagram |
| Modules | `structure.json` and `plan.json`: each module, what it does (the units' Responsibilities), its capabilities, and a link to `.exo/discovery/module-graph.mmd` |
| Main flows | Three to five flows that cross modules, from an entrypoint to storage or an external system, one step per line with its evidence |
| Integrations | External services, databases, queues and files: what each one is for and where its configuration is read, citing the place, never the value |

- **One section at a time:** show its text, ask "Write this section?", and write only that section. Replace the section if it exists and keep everything else byte for byte. Never regenerate the file.
- **No `.exo/context.md` yet:** create it with the title `# Project context` and the approved sections. The rest of the profile (Stack, Commands, Conventions, Areas, Risks) is `project-onboarding`'s: it runs the tests, which discovery does not do (contract, section A), so it becomes an item of the adoption backlog.
- **Unattended run:** write nothing to the wiki. Put the proposed sections in `.exo/discovery/pending-approval.md`; R6 walks them with the person.

## 5. Recover the ADRs

- **What counts:** decisions that are hard to reverse and that the code or the configuration shows: the language and frameworks, the database and its migrations, the architecture style (layers, modules, a monorepo), authentication, the API style, messaging, deployment, and conventions the code enforces everywhere.
- **One ADR per decision,** in `<adr_dir>/NNNN-recovered-<slug>.md`, with `adr_dir` from `inventory.json` (when `adr_dir_exists` is false, the folder is new). `NNNN` is the next free four-digit number in that folder.
- **Content:** status `Recovered` and a confidence (`high`, `medium` or `low`); the decision as the code shows it, with evidence; the reasons and the alternatives only when a document records them, otherwise marked inferred or left as open questions. Follow the project's own ADR format when it has one.
- **Show each ADR to the person** and write only the ones they approve. Never edit the project's existing ADRs. Unattended: put them in `pending-approval.md` too.

## 6. Open questions and debt

- **`open-questions.md`:** the Open questions of every unit, plus the conflicts you found while grouping (two units that disagree, a rule with two values), grouped by capability, each with its source unit and location. Keep the questions already answered, marked as answered.
- **`debt.md`:** what you observed, each item with its evidence: critical paths without tests (from the Tests sections), hard-coded credentials (location only), swallowed errors, the same rule duplicated in two units, cycles in the module graph (the edges of `structure.json`), hotspots (large files with high churn in `hotspots.json`), and dead or duplicated code. R6 turns the items that block adoption into backlog items.

## Before you finish

- `exo speclint` passes on every spec you wrote (warnings are fine).
- `exo discover status --json` shows no `outside_changes`.
- Report:
  - the capabilities, with their units and how many FRs;
  - the units without a capability, and why;
  - the wiki sections and ADRs written, and the ones pending;
  - how many open questions and debt items there are.
