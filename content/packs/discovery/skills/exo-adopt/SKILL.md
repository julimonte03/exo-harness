---
name: exo-adopt
description: >-
  Adopts an existing codebase into the governed cycle without touching its
  code: runs the engine's deterministic inventory, structure and plan,
  drives the evidence-based extraction of each unit, the synthesis of as-is
  specs, the project wiki and recovered ADRs, an independent audit of their
  precision, and the person's validation, ending with an adoption backlog
  whose items become SDD changes. Resumes from the engine's state after a
  cut. Use it when a project that already has code starts using the engine,
  when the person runs /exo-adopt, or when `exo discover update` reports
  stale units. Triggers: "adopt this project", "reverse engineer",
  "understand this codebase", "recover the specs", "onboard an existing
  repo", "/exo-adopt".
metadata:
  exo-pack: discovery
  exo-execution: inline
---

# exo-adopt

## Result

- Every unit of the plan extracted and closed (`exo discover status` shows no pending or stale unit), at the depth the person chose.
- At least one as-is spec per capability, with evidence on every requirement, plus the project wiki, the recovered ADRs, the open questions and the technical debt.
- An audit with precision ≥ 90 % per capability in `.exo/discovery/coverage.md`, or the capabilities below it sent back to extraction.
- The capabilities the person validated, and `.exo/discovery/adoption-backlog.md`, with the changes they confirmed created through `sdd-new`.
- Nothing written outside the paths of `.exo/shared/discovery-contract.md`, section G.

## Before you start

1. Read `.exo/shared/discovery-contract.md` in full. Follow it over anything else, and `.exo/shared/data-protection.md` for everything you read.
2. Run `exo discover status --json`.
   - If `outside_changes` lists files, stop: the working tree has changes that are not discovery's. Ask the person to commit or stash them first, so the read-only check means something.
   - If steps already ran, resume from where `status` says (see Resume). Never start over on your own.
3. Load the skills of each stage when you reach it, reading each `SKILL.md` in full: `re-extract`, `re-synthesize`, `re-audit` and `re-adoption-plan`, plus `architecture-decision-record` (pack `design`) for the recovered ADRs and `data-classification` and `prompt-hygiene` (pack `security`). A missing one degrades as `.exo/shared/skill-resolver.md` says, with the inline criteria of `.exo/shared/phase-skill-map.md`.

## R0 to R2: the deterministic steps

```bash
exo discover inventory --json
exo discover structure --json
exo discover plan --depth standard --json
```

- Show the person the inventory (languages, frameworks, entrypoints, tests), the module graph and the plan's estimate: units, lines and tokens per depth (`quick`, `standard`, `deep`). Ask which depth to use. In automatic mode, use `discovery.depth` from `.exo/config.json`.
- `exo discover plan` refuses to rebuild a plan that has closed units. Use `--replan` only when the person asks for it (for example, after big structural changes).

## R3: extraction, one unit at a time

Follow the loop of the contract, section D:

1. `exo discover next --count 1 --json` (up to 3 when your agent can run subagents in parallel).
2. Delegate each unit to the `re-extractor` subagent with the brief below. Without subagents, run `re-extract` inline for each unit and say "no isolation".
3. Write the document the subagent returns, exactly as returned, to the unit's `document` path, then run `exo discover done <unit>`.
4. On errors, send them back to the extractor once with the same brief plus the errors. If they persist, leave the unit pending and add the problem to `.exo/discovery/open-questions.md`.
5. Repeat until `exo discover next` says every unit is closed.

The brief for `re-extractor`:

```markdown
You are extracting the unit `<unit id>` of an existing project, read-only.

## Skills to load before work
- <path of re-extract's SKILL.md, from .exo/skill-registry.md>

## Unit
<the unit's JSON from `exo discover next`: files, tests, detail, flags>

## Return
The full text of `.exo/discovery/units/<unit id>.md`, from .exo/shared/unit-template.md, ready to save.
```

## R4: synthesis

Run `re-synthesize` inline: it groups the units into capabilities and writes the as-is specs, proposes the wiki sections and the recovered ADRs, and fills the open questions and the debt. Check each spec with `exo speclint <spec>`. Show the person the wiki sections and the ADRs before writing them: they own the wiki.

## R5: audit

1. `exo discover sample --json`.
2. Delegate to the `re-auditor` subagent with `re-audit`'s path, the sample items and nothing else: no extraction notes, no conclusions. Without subagents, run `re-audit` inline after a clear break and say "no isolation".
3. Write the verdicts to `.exo/discovery/audit-results.json` and run `exo discover audit @.exo/discovery/audit-results.json`, then `exo discover coverage`.
4. For each capability flagged in `coverage.md`, extract its units again (they are the files its FRs cite), synthesize it again and audit it again. After two rounds, report it to the person as it is.

## R6: validation and adoption

Run `re-adoption-plan` with the person: they walk the capabilities and validate or correct each one, then the adoption gaps become backlog items, and the confirmed ones become changes through `sdd-new`. Interactive mode only: in an unattended run, stop before R6 and report.

## Resume

`exo discover status --json` is the source of truth:

| `status` shows | Continue with |
|---|---|
| no inventory or no structure | R0 or R1 |
| no plan | R2 |
| pending or stale units | R3 |
| every unit done, no as-is spec | R4 |
| specs but no `coverage.md` | R5 |
| a flagged capability in `coverage.md` | R5, step 4 |
| everything audited | R6 |

## Before you finish

- `exo discover status --json` shows no `outside_changes`.
- `exo speclint <specs_dir>/capabilities` passes (warnings are fine).
- Tell the person:
  - the depth;
  - the units closed;
  - the capabilities with their precision;
  - what was validated;
  - the backlog items and the changes created;
  - the open questions that need them.
- Commit `.exo/discovery/`, the specs, the wiki and the ADRs only when the person asks. Use Conventional Commits, for example `docs(discovery): recover the as-is specs of billing`.
