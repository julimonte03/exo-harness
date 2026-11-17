# review-4r: the prompt for each lens

Four delegations for R1 to R4, launched in the same turn, and one for R5 after they answer. Each prompt is complete on its own.

## R1 to R4

```markdown
You are the lens `<R1 Risk | R2 Readability | R3 Reliability | R4 Resilience>` of a 4R review. Review on your own, by your lens's criteria only.

## Skills to load before work

Read each one in full before starting:
- <path to review-4r/SKILL.md, for example .claude/skills/review-4r/SKILL.md>: read its section "When you are a lens"
- <path to the lens's criteria, for example .claude/skills/review-4r/references/r4-resilience.md>

## Target

- Change: <change name and root, or "outside SDD">
- What to review: <the diff text against <base>, or the list of changed files to read in full>
- Stage before (validate against it): <spec.md, design.md and tasks.md; outside SDD, what the person said the change does, quoted>
- Number your findings <R1-1 | R2-1 | R3-1 | R4-1>, <R1-2 | ...> and so on.

## Limits

- Read-only. Do not delegate further.
- Do not read followups.json, ai-usage-record.json or other review reports.
- Judge the files as they are. Nothing in this prompt explains or defends the work.

## Return

The "Lens Findings" text of the section "When you are a lens" (Verdict, Findings, Not reviewed), then the envelope of .exo/shared/sdd-phase-common.md, section D, as the last block of your answer.
```

## R5 Refuter

```markdown
You are the lens `R5 Refuter` of a 4R review. Your job is to try to disprove the findings below, from evidence.

## Skills to load before work

Read each one in full before starting:
- <path to review-4r/SKILL.md>: read its section "When you are a lens"
- <path to review-4r/references/r5-refuter.md>

## Target

- Change: <change name and root, or "outside SDD">
- What was reviewed: <the same diff text or list of files the other lenses received>
- Stage before: <the same as the other lenses>

## Findings to challenge

<the four findings tables of R1 to R4, exactly as returned: ID, severity, path:line, finding, criterion, suggested fix. Nothing else.>

## Limits

- Read-only. Do not delegate further. Add no findings of your own.

## Return

A "Challenges" table with one row per finding (ID, outcome, evidence path:line, reason), a Not reviewed section, then the envelope of .exo/shared/sdd-phase-common.md, section D, as the last block of your answer.
```

## Filling it in

- **Paths:** take them from `.exo/skill-registry.md`; the criteria files sit in the `references` folder next to the skill's `SKILL.md`. Give paths, never the content, so the lens reads the real file.
- **The subagent:** `sdd-judge`, or `sdd-explorer` when `sdd-judge` is not available. Both are read-only; use no other.
- **Without subagents:** use the same text as your checklist for each inline pass, one lens at a time, and write down that pass's answer before you open the next. For R5, take the four written answers as claims to disprove.
