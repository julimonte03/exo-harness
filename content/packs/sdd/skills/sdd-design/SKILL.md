---
name: sdd-design
description: >-
  Writes the technical design of an SDD change (design.md): architecture,
  modules and files, data shapes, sequence of operations, error handling, a
  Test Plan that maps every scenario S-n of the spec delta to a named test,
  migration, and risks with their mitigations. A Tier 3 and 4 phase that runs
  inline, after sdd-spec and before sdd-tasks. Use it when the person asks to
  design the change, write or update design.md, decide how a change will be
  built, or runs /sdd-design, and when the orchestrator reaches the design
  phase.
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: design
  exo-permissions: write-specs
---

# sdd-design

## Result

- `<change-root>/design.md`, started from `.exo/shared/templates/design.md`, with its 8 sections in order and none of them empty.
- A Test Plan that names one test for every `S-n` of the spec delta.
- `exo speclint <change-root>` passes, the Tier 3 and 4 judges have run, and the person approved the design.
- The phase ends with the envelope of `.exo/shared/sdd-phase-common.md`, section D, with `next: tasks`.

## What it writes and what it never touches

- **Writes** only `<change-root>/design.md` and, when the tier's gates include `threat_model` (Tier 3 and 4 by default), `<change-root>/gates/threat_model.md` through `threat-modeling`; plus the memory mirror in `hybrid` and `memory` persistence (section C).
- **Never touches** proposal.md, spec.md, exploration.md, the living specs or the code. If an earlier artifact is wrong (a scenario too vague to test, a requirement that contradicts the code), stop and return `status: needs-input` saying what is wrong: the fix belongs to the phase that owns that file.
- **One exception:** the decision record that `architecture-decision-record` asks for (see Conditionals) lives in the project's docs. Write it only after the person approves its text.

## Before you start

1. Run `exo change status <change> --json` for the tier, the phase and the artifacts. An unknown tier is Tier 4.
2. Design is a Tier 3 and 4 phase (`.exo/shared/phase-skill-map.md`, Phases per tier). In Tier 1 or 2, say so and ask the person before writing a design. Never change the tier yourself: when the evidence says the change is riskier, send a `fitness_signal`.
3. `spec.md` must exist and pass `exo speclint <change-root>/spec.md`. If it does not, return `needs-input`.
4. Load the skills (`.exo/shared/sdd-phase-common.md`, section A): the stack router and `threat-modeling` (Required, see Threat model and gate), and the Conditionals below whose trigger applies, at most 5. Read each `SKILL.md` in full. Without a stack router, follow the commands and conventions in `.exo/context.md`.
5. Read the earlier artifacts as the retrieval mode says (section B): proposal.md, spec.md, exploration.md when present, `.exo/context.md`, and the living specs that the delta modifies or removes (`<specs_dir>/capabilities/<capability>/spec.md`).
6. Read the code the design will touch. Read 1 to 3 files inline; for 4 or more, delegate the reading to `sdd-explorer` (section G) and design from its findings. Without subagents, read in small batches and summarize as you go (`.exo/shared/agent-capabilities.md`).

## Write design.md

Fill every section in English, with `path:line` where you refer to existing code. If a section really does not apply, write `None` and the reason: speclint rejects empty sections.

| Section | What goes there |
|---|---|
| Architecture Overview | The components involved, what each one is responsible for, and how they interact. A diagram if it helps. |
| Modules / Files | Every file to create or modify, with its responsibility. `sdd-tasks` cuts this list into tasks, and `sdd-apply` touches nothing outside it. |
| Data Shapes | Types, schemas, payloads, stored data and their migrations. |
| Sequence Of Operations | The flow step by step, including the unhappy paths. |
| Error Handling | What can fail, how it is detected, and what the user or the caller sees. |
| Test Plan | Every `S-n` of the delta mapped to a named test (below). |
| Migration / Backwards Compatibility | What breaks, for whom, and how it is migrated. `None` when nothing breaks. |
| Risks & Mitigations | Risk, likelihood, impact and mitigation. Threats go here too. |

Design only what the spec asks for. An idea that goes beyond the delta is a question for the person, not a line in the design.

### Test Plan

One line per scenario: the scenario, the test file and test name in the project's convention, and the requirement it proves.

```markdown
- S-1 -> tests/test_login.py::test_signs_in_with_valid_password (CAP-auth-FR-3)
- S-2 -> tests/test_login.py::test_rejects_wrong_password (CAP-auth-FR-3)
- S-3 -> tests/test_login.py::test_locks_after_five_failures (CAP-auth-FR-4)
```

- Every `S-n` of the delta appears, including those of MODIFIED requirements. `exo speclint <change-root>` fails when one is missing.
- Cite only IDs defined in the delta or in the living specs; speclint checks that too.
- The tests may not exist yet: `sdd-apply` writes them. Name them as they will be named.
- A scenario that no automated test can prove still gets a line that says how it is checked and why it is not automated.

## Threat model and gate

`threat-modeling` is Required in every design whose tier lists the gate `threat_model` in `governance.gates` (Tier 3 and 4 by default; `.exo/shared/phase-skill-map.md`, Gates). Its threats, each with its mitigation and residual risk, go to Risks & Mitigations, and its gate to `<change-root>/gates/threat_model.md`, started from `.exo/shared/templates/gate.md`. When the skill is not installed, say the degradation sentence and still write both from its inline criteria: `exo check` requires the gate.

## Conditionals

Apply each one whose trigger holds (`.exo/shared/phase-skill-map.md`, row design). When the skill is not installed, say the degradation sentence, apply its inline criteria and record it (`.exo/shared/skill-resolver.md`).

| Trigger | Skill | Where its output goes |
|---|---|---|
| A decision that is hard to reverse | `architecture-decision-record` | A short record (context, decision, alternatives, consequences) in the project's docs, linked from Architecture Overview |
| Large architecture | `software-solution` | Components, responsibilities and integration points in Architecture Overview, before the details |
| Several sessions or developers | `context-anchoring` | The decisions so far in the change's state memory (`.exo/shared/memory-convention.md`) |

For example: `design/architecture-decision-record not installed — applying inline criteria`.

## Judges (Tier 3 and 4)

Once design.md passes speclint, run the design judges, each one as its own read-only delegation to `sdd-judge`, never inside this context:

- `judge-security` and `judge-code-reviewer` always; `judge-frontend` when the change touches UI.
- The prompt starts with `## Skills to load before work` and the judge's `SKILL.md` path. A judge that is not installed degrades (`quality/judge-security not installed — applying inline criteria`) and the prompt carries its inline criteria from the map.
- Pass the change name, the change root, design.md, and the stage before it (spec.md and proposal.md), so the judge checks the design against them. Ask for findings with severity and `path:line`, and give each judge the first free ID of its prefix (from `exo change followups <change> --status all`).
- Without subagents, run each judge inline after the design, as a separate pass with that judge's criteria, and say "no isolation".

Record each finding with `exo change record <change> --followup '<json>'` (`.exo/shared/judge-common.md`, section F) and show them to the person. Fix the accepted ones in design.md, run speclint again and mark them with `--fixed <id>`. The findings the person decides not to fix go to `dismissed_followups`, with their `id`.

## Check and approve

1. `exo speclint <change-root>` passes. It lints every artifact in the folder and checks that the Test Plan covers the delta. An error in another phase's file means `needs-input`.
2. Show a short summary: the approach, the files, the riskiest point, and what the judges found.
3. Approval follows `.exo/shared/sdd-phase-common.md`, section H. In interactive mode, ask "Adjust anything or continue?" and wait: the answer approves the design. Adjust, lint again, and ask again until the person approves.

## Record

Before the envelope, add what you used to the AI Usage Record (`.exo/shared/capability-attribution.md`). `activation` is `requested` when the person called this skill by name, `auto` otherwise.

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-design", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"sdd-design"'
exo change record <change> --add capabilities_used '{"name": "threat-modeling", "type": "skill", "activation": "auto", "resolution": "none", "note": "security/threat-modeling not installed — applying inline criteria"}'
exo change record <change> --add capabilities_used '{"name": "sdd-judge", "type": "subagent", "activation": "auto"}'
exo change record <change> --add capabilities_used '{"name": "judge-security", "type": "judge", "activation": "auto", "resolution": "none", "note": "quality/judge-security not installed — applying inline criteria"}'
exo change record <change> --add judges_invoked '{"name": "judge-security", "result": "2 findings: 1 fixed, 1 dismissed"}'
exo change record <change> --add dismissed_followups '{"id": "JSEC-2", "judge": "judge-security", "rule": "rate limiting", "reason": "the API gateway already limits the login route"}'
exo change record <change> --add decisions '{"summary": "Design approved", "by": "human"}'
```

- In `hybrid` and `memory` persistence, save design.md with the topic key `sdd/<change-name>/design`. In every mode, update the state artifact (`.exo/shared/memory-convention.md`).
- Decisions the person made go to memory as skill:memory-protocol says.

## End

Finish with the envelope, as the last thing in the answer:

```yaml
status: ok
phase: design
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/design.md
    summary: 4 files, 3 scenarios mapped to tests, 2 risks with mitigations
notes: >-
  Isolation: inline; judges in subagents.
  Skills: sdd-design (fallback-registry), threat-modeling (none: security/threat-modeling not installed — applying inline criteria).
  Judges: judge-security 2 findings (1 fixed, 1 dismissed); judge-code-reviewer none.
next: tasks
```

Then skill:sdd-tasks turns the design into the plan.
