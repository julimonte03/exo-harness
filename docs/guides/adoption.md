# Adopting an existing project

`/exo-adopt` brings a codebase that already exists into the governed cycle. It reads the code, recovers what the system does today as **as-is specs** with evidence for every requirement, writes the project wiki and the architecture decisions it can see, has an independent auditor check their precision, and ends with a backlog of changes that you confirm. It never changes your code.

## Before you start

1. **A git repository with a clean working tree.** Commit or stash your changes first: `/exo-adopt` stops if files outside its own paths change, and git is how it knows. Without git that check is off.
2. **The `discovery` pack.** It requires `core`, `sdd` and `design`, which come with it. In a repo with code, `exo init` offers it; add it to the pack list:

   ```sh
   exo init --packs core,sdd,quality,security,discovery
   ```

   Add your stack packs to the list too (`python`, `java`, `frontend`, `ops`); the note that `exo init` prints shows the full list for your repo. In a project that is already installed, run the same `exo init --packs ...` with every pack you want: `--packs` replaces the list.
3. **An agent session in the project.** With Claude Code or Copilot, the extraction and the audit run in read-only subagents (`re-extractor` and `re-auditor`). Other agents run them inline and say "no isolation".

Then, in your agent:

```text
/exo-adopt
```

## The stages

The engine does the deterministic steps and keeps the state; the agent does the reading and writing, one bounded unit at a time.

| Stage | Who | What happens |
|---|---|---|
| R0 Inventory | the engine (`exo discover inventory`) | Languages, frameworks, entry points, tests, CI, migrations, API contracts, infrastructure, and sensitive files by name only |
| R1 Structure | the engine (`exo discover structure`) | The module graph, hotspots from git churn, and ownership per module |
| R2 Plan | the engine (`exo discover plan`), you pick the depth | Bounded work units with a priority and an estimate |
| R3 Extraction | the `re-extract` skill, one unit at a time | A document per unit; `exo discover done` validates its evidence and runs the secret scanner |
| R4 Synthesis | the `re-synthesize` skill | As-is specs per capability, the wiki, recovered ADRs, open questions and technical debt |
| R5 Audit | the `re-audit` skill, in fresh context | A seeded sample of requirements checked against the code; precision per capability |
| R6 Validation and adoption | the `re-adoption-plan` skill, with you | You validate the capabilities and the ADRs; the gaps you confirm become SDD changes |

Every recovered claim carries its evidence: `[Code] path:line` (or `path:start-end`), `[Doc] path`, or `[Inferred: high|medium|low]`. Claims cite where a value lives and never copy it.

## Depths

R2 splits the code into units at one of three depths. The default is `discovery.depth` in `.exo/config.json` (`standard`). In an interactive session the agent shows you the units, lines and estimated tokens of each depth and lets you choose; you can compare them yourself with `exo discover plan --depth quick --json` (and `standard`, `deep`) before any unit is closed.

| Depth | Units | Extraction |
|---|---|---|
| `quick` | Up to 1200 lines each | In full for the most critical 30 % of the units (authentication, payments, personal data, high fan-in or churn); a summary for the rest |
| `standard` | Up to 800 lines each | Every unit in full, with its tests |
| `deep` | Up to 500 lines each | Every unit in full, with its tests, in smaller units |

Once units are closed, `exo discover plan` does not rebuild the plan; `--replan` does, when you ask for it (for example after a large restructuring).

## What it writes

Only these paths:

- `.exo/discovery/`: the inventory, the structure (`module-graph.mmd` among others), the plan, one document per unit, the audit sample and results, `coverage.md`, `open-questions.md`, `debt.md` and `adoption-backlog.md`. It is meant to be committed: each unit's state is derived from its own record, so two people or two branches do not collide.
- `specs/capabilities/<capability>/spec.md` (under your `specs_dir`): the as-is specs, with `Status: as-is` until you validate them, and `Status: as-is-validated` after.
- `.exo/context.md`: the project wiki, section by section, with your approval.
- Recovered ADRs in the project's ADR folder (the first of `docs/adr`, `doc/adr`, `docs/decisions`, `docs/architecture/decisions` or `adr` that has one), named `NNNN-recovered-<slug>.md`, with the status `Recovered`.

In an unattended run, the wiki sections and the ADRs that need your approval go to `.exo/discovery/pending-approval.md` instead, and R6 waits for you.

## What it never touches

- Your code, tests, configuration and docs. A needed change becomes a backlog item and, if you confirm it, an SDD change on its own branch.
- Your build and your tests: it never runs them. Measuring them is a backlog item.
- Your memory: during discovery the agent does not run `exo mem save`; what it learns is committed in `.exo/discovery/`.

`exo discover status` lists any change outside the allowed paths. Up to R5, if it lists something, the agent stops and tells you. Before R6, commit `.exo/discovery/`, the specs, the wiki and the ADRs on the adoption's own branch; the changes of R6 start after that commit.

## Audit and precision

R5 draws a sample of requirements weighted by criticality and audits it in a fresh context, without the extraction notes. `exo discover coverage` writes `.exo/discovery/coverage.md` with the module coverage and the precision per capability. A capability below 90 % goes back to extraction with `exo discover reopen --capability <name>`, at most twice; after that, the agent reports it to you as it is.

## Interruptions and keeping it current

The state lives in the engine, not in the agent's context. After a cut, a compaction or a new session, run `/exo-adopt` again: it reads `exo discover status` and continues where it stopped. You can look at the state yourself:

```sh
exo discover status
```

When the code changes later, `exo discover update` recomputes the inventory and the structure and marks as stale only the units and capabilities whose files changed; `/exo-adopt` then re-extracts just those. Every new change runs this check too (`sdd-new` does), and says when it will alter a capability that is still `Status: as-is`.

`exo specs merge` refuses to merge a change into an as-is capability that you have not validated yet. `exo uninstall` keeps `.exo/discovery/` and `.exo/context.md`.

## The commands

The agent runs these for you; each has `--help` and `--json`.

| Command | Stage |
|---|---|
| `exo discover status` | Where the adoption is, and writes outside the allowed paths |
| `exo discover inventory`, `exo discover structure`, `exo discover plan` | R0 to R2 |
| `exo discover next`, `exo discover done <unit>`, `exo discover skip <unit> --reason "..."` | R3 |
| `exo discover synthesized <capability>` | R4 |
| `exo discover sample`, `exo discover audit`, `exo discover coverage`, `exo discover reopen` | R5 |
| `exo discover update` | After code changes |
