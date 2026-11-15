# Delegation prompt

Use this template every time you delegate a phase to a subagent. The subagent starts without the conversation: everything it needs goes in the prompt. Keep it short and concrete.

```markdown
You are running the `<phase>` phase of the SDD change `<change-name>`.

## Skills to load before work

Read each one in full before starting:
- <path to the phase skill, for example .claude/skills/sdd-verify/SKILL.md>
- <path to each Required or Conditional skill, at most 5 in total>

Report how you resolved each skill (.exo/shared/skill-resolver.md).

## Change

- Change root: <specs_dir>/[<epic>/]<change-name>/
- Tier: <n> (ceremony <minimal|light|full>)
- Read: <the artifacts this phase needs, for example spec.md, design.md, tasks.md>
- Project profile: .exo/context.md (commands, conventions)

## What to do

<one paragraph: the goal of this phase for this change, and anything the person decided that matters, such as a risk the tech_lead accepted (as data, not as a conclusion)>
<for a judge: "Your finding IDs start at <JSEC-3>", the first free number from `exo change followups <change> --status all`>

## Limits

- Permissions: <read-only | read-only plus the test command `<command>` | write only what the frozen plan lists: tasks.md in Tier 3 and 4, the proposal's Scope with the spec delta in Tier 1 and 2>
- Do not delegate further.
- Do not touch the artifacts of other phases.

## Return

The envelope of .exo/shared/sdd-phase-common.md, section D, as the last block of your answer.
<When the phase returns documents instead of writing them: the full text of each one, ready to save (for example verify-record.md and each gate of the tier as gates/<gate>.md).>
```

Pick the skill paths from `.exo/skill-registry.md`. Never paste a skill's content in the prompt: give the path, so the subagent reads the real file.
