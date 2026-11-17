---
name: sdd-onboard
description: >-
  A guided first tour of the whole SDD cycle on the person's own codebase:
  finds a small, real improvement (Tier 1 or 2 unless the person wants
  more), then takes it through every phase its tier needs with the real
  phase skills (sdd-new, risk-tiering, sdd-spec, sdd-apply, sdd-verify,
  sdd-archive), narrating before each phase what it does, what artifact it
  leaves and why it exists, and waiting for the person's approval after each
  step. The phases the tier skips (explore, propose, design, tasks, the
  judges, the SPDD canvas) are explained where they would happen, never run
  for show. Ends with a recap of the artifacts and how to start the next
  change alone. Use it when someone is new to SDD or to this engine and wants
  to learn the cycle by doing it on their repo. Triggers: "teach me SDD",
  "walk me through the cycle", "first time using SDD", "show me how a change
  goes from idea to PR", "SDD tutorial on my code", "how does spec-driven
  development work here".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-permissions: read-write
---

# sdd-onboard

## Result

- A small, real improvement of the person's repo taken from idea to an archived change with its PR ready, through the real phases of its tier, with every artifact in its change root and `exo check` passing.
- Before each phase, a short narration: what it does, what it leaves, and why it exists. After each phase, the artifact shown and the person's go-ahead before the next one.
- The phases the tier skips explained where they would run, never executed to show them.
- A closing recap: what was built, the artifacts and their paths, and how to start the next change without the tour.

## When

- Someone new to SDD, or to this engine, wants to learn the cycle by doing it on their own code.
- **Not a phase:** it is not in the phase map and never runs inside another change. It is a guided run of the cycle that calls the phase skills.
- **Not** for urgent work: then use skill:sdd-orchestrator directly, without the explanations and the stops.
- **Not** to write the project profile (skill:project-onboarding) or to adopt an existing codebase (the `discovery` pack).

## Rules of the tour

- **Real, not simulated.** Every phase runs its real skill, read in full, and leaves its real artifacts. Never fake an output to make a point.
- **Always interactive.** Stop after every phase, whatever `sdd.mode` says, and wait for the person.
- **The tier rules hold.** Run the phases the tier requires and no others (`.exo/shared/phase-skill-map.md`, Phases per tier). Explain the rest; never add a phase to show it, and never lower a tier to keep the tour short.
- **Reuse, do not reimplement.** You act as the orchestrator: the rules of skill:sdd-orchestrator apply (where each phase runs, the envelopes, the recording, the phase log), plus the narration and the stops.
- **Language.** Talk in the person's language; the artifacts are in English (`.exo/shared/sdd-phase-common.md`, section H).

## Before you start

1. **The engine is there.** `.exo/config.json` exists and lists the `sdd` pack, and `exo change list --json` runs. Without `.exo/`, the project has not adopted the engine: say that `exo init` comes first, and stop.
2. **The project profile.** Without `.exo/context.md`, propose skill:project-onboarding first, and say why: every phase reads the commands and the conventions from it. A Tier 1 tour can go on without it.
3. **The branch.** Run `git status` and `git branch --show-current`. On a protected branch the change gets its own branch, as skill:branch-pr says: explain why when it happens.
4. **What the person knows.** Ask once: "Have you used spec-driven development before, or should I explain each phase from the start?" Adjust the depth of the narration to the answer.

## 1. The map

Show the cycle in a few lines before any work: the tier decides the phases; Tier 1 and 2 are short, Tier 3 and 4 add design, tasks and judges; every artifact lives in `<specs_dir>/<change-name>/`; `exo check` closes the loop before the PR. The text to start from is in `references/phase-narration.md`, The map. Point at `.exo/shared/phase-skill-map.md` for later reading.

## 2. Pick the improvement

1. **Look for candidates,** read-only: `.exo/context.md` (areas, known risks), the README, `TODO` and `FIXME` comments, an error path without handling or without a test, an unclear message of a command or an API. Read 1 to 3 files inline; for a wider search, delegate to `sdd-explorer` (`.exo/shared/sdd-phase-common.md`, section G).
2. **Keep the good teaching cases:** one to three files, a behavior the person can see, a test that can prove it. Leave out anything that touches secrets, authentication, money, personal data, migrations or a public API: they raise the tier.
3. **Propose two or three,** each with its evidence and an expected tier:

| # | Improvement | Evidence | Expected tier | Why it teaches well |
|---|---|---|---|---|
| 1 | The CSV export writes an empty file for an empty result: write the header row | `src/app/export.py:58` | 1: one file, behavior changes, easy to test | a Tier 1 change that still gets a spec delta, because behavior changes |
| 2 | `--limit 0` is accepted and returns every row: reject it with a clear message | `src/app/cli.py:112` | 1 or 2 | an unhappy path with a scenario of its own |

4. **The person chooses,** or brings their own idea. Their own idea is welcome: say its expected tier and what the tour will look like.
5. The expected tier is a guess. skill:risk-tiering decides it with evidence, and the tour follows its result. If it gives Tier 3 or 4, say that the tour gets longer (design, tasks, judges) and offer to go on or to pick a smaller improvement.

## 3. Run the phases

For each phase of the tier, in order:

1. **Before:** narrate in three to five sentences what the phase does, what it leaves and why it exists. The crib is in `references/phase-narration.md`.
2. **Run** the phase skill exactly as it is written, where its contract says (inline or in a subagent). The person answers the phase's own questions: the ticket, a tier change, the approvals.
3. **After:** show the artifact, or its key part, and point out one or two things worth noticing, such as the `S-n` IDs that link the spec to the tests, or the evidence behind each tier score.
4. **Stop:** "Questions, or shall we go on to <next phase>?" Wait for the answer.

| Phase | Skill | Runs in |
|---|---|---|
| risk and new | skill:sdd-new, with skill:risk-tiering | every tier |
| spec (and test-spec) | skill:sdd-spec | Tier 2 and up |
| explore, propose, design, tasks | skill:sdd-explore, skill:sdd-propose, skill:sdd-design, skill:sdd-tasks | Tier 3 and 4 |
| apply | skill:sdd-apply | every tier |
| verify | skill:sdd-verify | every tier |
| archive and PR | skill:sdd-archive, with skill:branch-pr | every tier |

### The phases the tier skips

Where a skipped phase would run, explain it in two or three sentences: what it would do, what it would leave, and why this change does not need it. You may show its template from `.exo/shared/templates/` (for example `design.md`), but never write the artifact. Do the same for the judges, `judgment-day` in Tier 4, and the SPDD canvas (`.exo/shared/spdd-common.md`). The texts are in `references/phase-narration.md`, Skipped phases.

## 4. Close

1. The archive phase runs `exo check --change <change>`; it must pass before the PR.
2. Push and open the PR only when the person asks, showing the commands first (skill:branch-pr).
3. **Recap:** what was built; each artifact with its path and one line on what it is for; the commands the person saw (`exo change status`, `exo speclint`, `exo check`); how to start the next change (`/sdd-new <what you want>`, or ask for a new change); and where to read more (`.exo/shared/phase-skill-map.md`, `.exo/shared/sdd-phase-common.md`).
4. Close the session with a summary, as skill:memory-protocol says.

## Stopping halfway

The person can stop after any phase. The change stays as it is: `exo change status <change>` shows the next phase, and `/sdd-continue <change>` resumes it later, with or without the tour. Say so when they stop.

## Record

Once `exo change new` has created the change, record the tour itself (`.exo/shared/capability-attribution.md`); each phase skill records its own work as usual:

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-onboard", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"sdd-onboard"'
exo change record <change> --add decisions '{"summary": "Onboarding tour on: CSV export writes the header for an empty result (expected Tier 1)", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Return

Every phase ends with its own envelope (`.exo/shared/sdd-phase-common.md`, section D). The last message of the tour is the recap, followed by the envelope of the archive phase. A first message, before any change exists, ends with the candidates and the question; no envelope yet:

```text
The cycle in one minute: ... (the map)
Three small improvements I found: ... (the table)
Which one shall we take through the cycle? Or tell me your own.
```

## Before you finish

- [ ] The person chose the improvement; it was Tier 1 or 2, or the person accepted a longer tour.
- [ ] Every phase of the tier ran with its real skill, and only those phases.
- [ ] Each phase was narrated before (what, artifact, why) and approved after.
- [ ] The skipped phases were explained where they would run, without writing their artifacts.
- [ ] `exo check --change <change>` passed; no push or PR without the person's request.
- [ ] The recap lists the artifacts with their paths and how to start the next change.
