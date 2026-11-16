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
  stale units or capabilities. Triggers: "adopt this project", "reverse
  engineer", "understand this codebase", "recover the specs", "onboard an
  existing repo", "/exo-adopt".
metadata:
  exo-pack: discovery
  exo-execution: inline
---

# exo-adopt

## Result

- Every unit of the plan closed or explicitly skipped (`exo discover status` shows no pending or stale unit), at the depth the person chose.
- At least one as-is spec per capability, with evidence on every requirement, plus the project wiki, the recovered ADRs, the open questions and the technical debt.
- An audit of the whole sample with precision ≥ 90 % per capability in `.exo/discovery/coverage.md`, or the capabilities below it sent back to extraction.
- The capabilities the person validated, and `.exo/discovery/adoption-backlog.md`, with the changes they confirmed created through `sdd-new`.
- Nothing written outside the paths of `.exo/shared/discovery-contract.md`, section G, up to R6.

## Before you start

1. Read `.exo/shared/discovery-contract.md` in full. Follow it over anything else, including the always-on memory rule: during discovery, do not save memory (`exo mem save`, `exo mem session summary`). What you learn goes to `.exo/discovery/`. Reading memory (`exo mem context`, `exo mem search`) is fine.
2. Apply `.exo/shared/data-protection.md` to everything you read.
3. Run `exo discover update --json` when a plan exists, then `exo discover status --json`.
   - If `outside_changes` lists files, stop: the working tree has changes that are not discovery's. Ask the person to commit or stash them first, so the read-only check means something.
   - If `outside_changes` is `null`, the project is not a git repository: the read-only check is off. Tell the person, and be twice as careful about section G.
   - If `outside_changes_error` is set, git failed: report it and stop.
   - If steps already ran, resume from where `status` says (see Resume). Never start over on your own.
4. Load the skills of each stage when you reach it, reading each `SKILL.md` in full: `re-extract`, `re-synthesize`, `re-audit` and `re-adoption-plan`, plus `architecture-decision-record` (pack `design`) for the recovered ADRs and `data-classification` and `prompt-hygiene` (pack `security`).
   - A missing one degrades as `.exo/shared/skill-resolver.md` says, with the inline criteria of `.exo/shared/phase-skill-map.md`.
   - There is no change to record it in: say the degradation in your final report.

## R0 to R2: the deterministic steps

```bash
exo discover inventory --json
exo discover structure --json
exo discover plan --json
```

- `plan` without `--depth` uses `discovery.depth` from `.exo/config.json`.
- **Interactive mode:** while no unit is closed, run `exo discover plan --depth <d> --json` once per depth (`quick`, `standard`, `deep`) to compare units, lines and tokens. Show the person the inventory (languages, frameworks, entrypoints, tests), the module graph and those estimates, then write the plan with the depth they pick.
- `exo discover plan` refuses to rebuild a plan that has closed units. Use `--replan` only when the person asks for it (for example, after big structural changes).

## R3: extraction, one unit at a time

Follow the loop of the contract, section D:

1. `exo discover next --count 1 --json` (up to 3 when your agent can run subagents in parallel).
2. Delegate each unit to the `re-extractor` subagent with the brief below. Without subagents, run `re-extract` inline for each unit and say "no isolation".
3. Write the document the subagent returns, exactly as returned, to the unit's `document` path, then run `exo discover done <unit>`.
4. On errors, send them back to the extractor once with the same brief plus the errors.
   - If they persist, run `exo discover skip <unit> --reason "<why>"` and add the unit to `.exo/discovery/open-questions.md`.
   - A skipped unit leaves the loop and counts as not covered. `exo discover reopen <unit>` brings it back.
5. Repeat until `exo discover next` says there is nothing left to extract.

The brief for `re-extractor`:

```markdown
You are extracting the unit `<unit id>` of an existing project, read-only.

## Skills to load before work
- <path of re-extract's SKILL.md, from .exo/skill-registry.md>

## Unit
<the unit's whole JSON object from `exo discover next`: id, files, tests, detail, status, changed, document, flags>

## Return
The full text of `.exo/discovery/units/<unit id>.md`, from .exo/shared/unit-template.md, ready to save.
```

## R4: synthesis

Run `re-synthesize` inline. It:
- groups the closed units into capabilities and writes the as-is specs;
- records each one with `exo discover synthesized <capability>`;
- proposes the wiki sections and the recovered ADRs;
- fills the open questions and the debt.

Check the specs with `exo check`: it lints every capability spec, and warnings are fine. Show the person the wiki sections and the ADRs before writing them: they own the wiki. In an unattended run without that approval, they go to `.exo/discovery/pending-approval.md` instead.

## R5: audit

1. `exo discover sample --json`.
2. Delegate to the `re-auditor` subagent with `re-audit`'s path and **every** item of the sample, and nothing else: no extraction notes, no conclusions. Without subagents, run `re-audit` inline after a clear break and say "no isolation".
3. Write the verdicts to `.exo/discovery/audit-results.json` and run, with the quotes (they keep PowerShell from breaking the `@`):

   ```bash
   exo discover audit '@.exo/discovery/audit-results.json'
   exo discover coverage
   ```

   If `audit` reports IDs not audited yet, R5 is not done: audit them before going on.
4. For each capability flagged in `coverage.md`:
   - send its units back with `exo discover reopen --capability <name>`. That reopens the units whose files its FRs cite, or else the units of its `Source:` line;
   - extract them again (R3), synthesize the capability again (R4), then sample and audit the whole sample again;
   - stop after two such rounds and report the capability to the person as it is. `exo discover status --json` counts the syntheses in `rounds`: the first synthesis is 1, so two rounds of reopening end at 3.

## Before R6

- `exo discover status --json` shows no `outside_changes`: this is the read-only check of R0 to R5.
- Commit `.exo/discovery/`, the specs, the wiki and the ADRs on the adoption's own branch, with the person's permission. Use Conventional Commits, for example `docs(discovery): recover the as-is specs of billing`. The changes of R6 start after that commit, each on its own branch, as `sdd-new` says.

## R6: validation and adoption

Run `re-adoption-plan` with the person. It walks, in this order:
1. `.exo/discovery/pending-approval.md` first, if it exists;
2. the capabilities, which the person validates or corrects one by one;
3. the recovered ADRs, which the person confirms;
4. the adoption gaps, which become backlog items. The confirmed ones become changes through `sdd-new`.

R6 runs in interactive mode only: in an unattended run, stop before it and report. The changes R6 creates are outside discovery's paths, as expected: the read-only check is the one before R6.

## Resume

`exo discover status --json` is the source of truth:

| `status` shows | Continue with |
|---|---|
| no inventory or no structure | R0 or R1 |
| no plan | R2 |
| pending or stale units | R3 |
| `skipped` units with `changed` files | Ask the person: `exo discover reopen <unit>` sends them back to R3 |
| `unsynthesized_units` (closed units no capability lists in its `Source:`), or `stale_capabilities` (their cited code changed since `exo discover synthesized`) | R4 for them |
| `unrecorded_capabilities` (specs with a `Status:` preamble that were never recorded) | R4: check them and run `exo discover synthesized <capability>` |
| specs, and `coverage` false or `audit_missing` | R5 |
| `flagged` capabilities | R5, step 4, unless their `rounds` reached 3 |
| everything audited | Before R6, then R6 |

## Before you finish

- Tell the person:
  - the depth;
  - the units closed and the units skipped, with their reason;
  - the capabilities with their precision;
  - what was validated;
  - the backlog items and the changes created;
  - the open questions that need them;
  - any skill that degraded.
