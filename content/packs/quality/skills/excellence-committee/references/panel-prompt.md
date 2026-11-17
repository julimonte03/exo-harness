# excellence-committee: the prompt for each judge

One delegation to `sdd-judge` per judge, all launched in the same turn. Fill this template once per judge; each prompt is complete on its own, and none mentions another judge's work.

```markdown
You are the judge `<judge name>` on the panel of an excellence committee. Review on your own, by your judge's criteria only.

## Skills to load before work

Read each one in full before starting:
- <path to the judge's SKILL.md, for example .claude/skills/judge-product/SKILL.md>
- <only when installed: the skills this judge reuses, for example the path to product-discovery/SKILL.md>

Report how you resolved each skill (.exo/shared/skill-resolver.md).

## Target

- Change: <change name and root, or "outside SDD">. Phase: <the change's current phase, or "on request">. Tier: <tier, or "n/a">.
- What to review: <the artifacts, the diff text against <base>, or the list of changed files to read in full>
- Stage before (validate against it): <the artifacts of .exo/shared/judge-common.md, section C; outside SDD, the purpose and plan the person gave, quoted as they wrote them>
- Your new IDs start at: <JCR-n | JSEC-n | JPRD-n | JBIZ-n | JTEAM-n | JFE-n>

## Limits

- Read-only. Do not delegate further.
- Do not read followups.json, ai-usage-record.json or earlier judge reports: they hold other judges' findings.
- Judge the files as they are. Nothing in this prompt explains or defends the work.

## Return

The findings text your skill describes (Verdict, Findings, Not reviewed), then the envelope of .exo/shared/sdd-phase-common.md, section D, as the last block of your answer.
```

## Filling it in

- **Skill paths:** take them from `.exo/skill-registry.md`. Give paths, never a skill's content, so the judge reads the real file.
- **Reused skills:** `security-code-review` for `judge-security`; `product-discovery` for `judge-product`; `accessibility-audit` and `frontend-design` for `judge-frontend`. When one is not installed, leave its line out and write: "`<pack>/<skill> not installed — applying inline criteria`: use the inline criteria of your judge skill."
- **The purpose outside SDD:** quote what the person said about who the change is for and why. Do not add your reading of it.
- **The diff:** paste the text when it fits; otherwise list the changed files and say they must be read in full.
- **Without subagents:** use the same text as your checklist for each inline pass, one judge at a time, and write down that pass's findings before you open the next.
