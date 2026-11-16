# judgment-day: the prompt for each judge

Use this template for each of the two delegations to `sdd-judge`, in every round: one for `judge-code-reviewer` and one for `judge-security`. Launch both at the same time, and never put one judge's findings in the other's prompt.

```markdown
You are the judge `<judge-code-reviewer | judge-security>` in round <n> of the judgment day of the SDD change `<change-name>` (Tier 4).

## Skills to load before work

Read each one in full before starting:
- <path to the judge's SKILL.md, for example .claude/skills/judge-security/SKILL.md>
- <judge-security only, when it is installed: the path to security-code-review/SKILL.md>

Report how you resolved each skill (.exo/shared/skill-resolver.md).

## Change

- Change root: <specs_dir>/[<epic>/]<change-name>/
- Phase: judgment. Tier: 4.
- Start from: verify-record.md, section Judgment Day Handoff.
- Stage before: spec.md, design.md (Risks & Mitigations), tasks.md, test-spec.md.
- What to review: <the diff text against <base>, or the list of changed files>
- Your new IDs start at: <JCR-n | JSEC-n>

## Your open findings from round <n-1>

<Rounds 2 and 3 only: your own findings still open, each with its ID, severity, path:line and summary. Nothing from the other judge, and nothing about how they were fixed.>

## Limits

- Read-only. Do not delegate further.
- Do not read followups.json, ai-usage-record.json or earlier judge reports: they hold the other judge's findings.
- Judge the files as they are; nothing in this prompt explains the work or the fixes.

## Return

The findings text your skill describes (Verdict, Findings, Resolved from round 2, Not reviewed), then the envelope of .exo/shared/sdd-phase-common.md, section D, as the last block of your answer.
```

- Take the skill paths from `.exo/skill-registry.md`. Never paste a skill's content into the prompt: give the path, so the judge reads the real file.
- When `security-code-review` is not installed, leave its line out and add: "`security/security-code-review not installed — applying inline criteria`: use the inline criteria of judge-security."
- Without subagents, use the same text as your own checklist for each inline pass, one judge at a time.
