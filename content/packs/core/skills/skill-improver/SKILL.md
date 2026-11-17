---
name: skill-improver
description: >-
  Audits an existing agent skill and proposes concrete improvements; by
  default it only audits and edits nothing until the person approves. It
  checks the description and its triggers (what, when, overlap with
  neighbors), the frontmatter and metadata (standard fields, exo- values,
  permissions that match what the body does), the structure (Result, When,
  Steps, Return, Record, a checklist, at most 500 lines with details in
  references/), ambiguous or missing steps, examples, limits and safety, and
  coherence with the engine's contracts (artifact ownership, the phase map,
  degradation, records, data protection, ticket patterns). It returns
  findings with a before and after for each, applies only the approved ones,
  then checks again. Use it when a skill misfires or never triggers, gives
  inconsistent results, grew too long, or before publishing a pack.
  Triggers: "improve this skill", "audit our skills", "why doesn't this
  skill trigger", "this skill is too long", "refactor the SKILL.md", "skill
  quality check".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: write-specs
---

# skill-improver

## Result

- **An audit:** a one-line verdict (`Good`, `Needs work` or `Rework`), a findings table (ID `SI-n`, severity, `file:line`, dimension, finding), and for each finding the exact text before and after.
- **One question:** apply all, some (by ID), or none. The default is none.
- **With approval:** only the approved changes applied, the checks run again, and a summary of what changed. Without approval, nothing is edited.

## When

- **A skill misfires:** it loads on unrelated requests, never loads, or gives different results for the same request.
- **A skill grew** past 300 lines, or past 500.
- **A contract changed** (`.exo/shared/`) and the skills that cite it need to follow.
- **Before publishing a pack,** or in a periodic review of the project's skills.
- **Not for:** writing a new skill (skill:skill-creator); the supply-chain gate before installing or merging a skill (skill:skill-reviewer); changing the engine's contracts themselves.

## Inputs

1. **The skill folder,** read raw and in full: `SKILL.md`, every file in `references/`, and any script.
2. **Where it lives** (next section): engine content, an engine skill installed in a project, or the project's own skill. The installed engine skills are listed in `.exo/lock.json`; `exo skills diff --target <skills folder>` shows whether an installed copy already differs from the engine's.
3. **Its neighbors:** `exo skills list` and `.exo/skill-registry.md`, to judge overlaps.
4. **The contracts** it cites, or should cite: `.exo/shared/sdd-phase-common.md`, `.exo/shared/phase-skill-map.md`, `.exo/shared/skill-resolver.md`, `.exo/shared/capability-attribution.md`, `.exo/shared/data-protection.md`.
5. **The evidence of the problem,** when the person has it: the request that misfired, the output that was wrong.

## Where changes go

| The skill is | Changes go to |
|---|---|
| Engine content, in the engine's repository or a pack repository | The skill's files, on a branch, through review |
| An engine skill installed in a project | **Not the installed copy.** The next `exo sync` refuses to overwrite a modified file without `--force`, and the fix would be lost for every other project. Propose the change to the engine's content (skill:issue-creation can write it up). If the person still wants a local change, it is their decision, knowing that sync will report the conflict |
| The project's own skill | Its files, on a branch |

## Steps

The checks of each dimension, with example findings and fixes, are in `references/audit-rubric.md`; the audit format, with a full example, in `references/audit-output.md`.

### 1. Read everything raw

Read every file of the folder, frontmatter and comments included. Count the lines of `SKILL.md`. Note which references it cites and which files nobody cites.

### 2. Run the mechanical checks

- **In a content tree:** `exo validate` (or `exo validate --root <tree>`) and keep the errors and warnings of this skill.
- **A project skill:** the manual checks of skill:skill-creator (frontmatter, name, description length, size, cited references, invisible characters).

Each error or warning becomes a finding.

### 3. Audit the dimensions

1. **Description and triggers:** says what, when, and real trigger phrases; specific; does not overlap a neighbor; within 1024 characters.
2. **Frontmatter and metadata:** only standard fields; `exo-pack`, `exo-execution` and `exo-permissions` present and true. A `read-only` skill whose steps write files is a finding.
3. **Structure and size:** Result first, When with what it is not for, numbered Steps, Return with a short example, Record inside a change, a closing checklist; at most 500 lines, aiming at 300, with the details in references.
4. **Steps:** vague verbs ("handle", "ensure", "as needed", "properly"), missing order, questions without a default, failures without a stop condition, commands without their exact flags, and decisions the agent takes that belong to the person.
5. **Examples:** present, short, consistent with the rules, and synthetic.
6. **Limits and safety:** what it never does; confirmation before destructive commands; data protection; nothing installed; nothing the validator flags; no hard dependency on a vendor.
7. **Coherence with the contracts:** artifact ownership, the phase map and its triggers, the exact degradation sentence, the record commands, ticket IDs from `tickets.pattern`, host-agnostic CI and PRs, and English for anything installed in projects.
8. **References:** every `skill:` reference resolves for its pack; every `.exo/shared/` path is a contract its pack can reach; no dead or orphan reference files.

### 4. Rate each finding

- **High:** the skill does something harmful or against a contract: writes another phase's artifact, invents IDs, asks for credentials, fails validation, or loads on everything.
- **Medium:** it misfires or gives inconsistent results: an ambiguous step, a missing stop condition, an overlap with a neighbor, more than 500 lines, no output format.
- **Low:** readability and style.

### 5. Write the fixes

For each finding, quote the text as it is (`file:line`) and write the replacement:

- the smallest change that fixes it, in the skill's own voice;
- the same scope: no new features, no new steps the job does not need;
- the same meaning: a change of behavior is a question for the person, not a silent fix.

Propose a full rewrite only with the verdict `Rework`, and only after the person agrees.

### 6. Give the audit and ask

Give the audit (`references/audit-output.md`) and ask: "Apply all, some (list the IDs), or none?" Never edit before the answer. In an unattended run, deliver the audit and stop.

### 7. Apply the approved changes

- Only the approved IDs, as written in the report; nothing else.
- Run step 2 again and recount the lines.
- When the description changed, check the triggers against the neighbors again.

### 8. Close

- Summarize: the IDs applied, the files changed, the checks.
- Run skill:skill-reviewer on the changed skill before it is merged.
- Commit as the project's rules say (skill:work-unit-commits).

## Return

```markdown
**skill-improver: release-notes** · Verdict: Needs work (1 High, 2 Medium, 1 Low)

| ID | Severity | File:line | Dimension | Finding |
|---|---|---|---|---|
| SI-1 | High | release-notes/SKILL.md:44 | Coherence | Writes `proposal.md` of the change, which belongs to the propose phase |
| SI-2 | Medium | release-notes/SKILL.md:3 | Description | No triggers; "helps with releases" overlaps `branch-pr` |
| SI-3 | Medium | release-notes/SKILL.md:61 | Steps | "Handle missing tags appropriately": no default, no stop condition |
| SI-4 | Low | release-notes/SKILL.md:12 | Structure | No Return section with the output format |

**SI-3**
Before (line 61): "Handle missing tags appropriately."
After: "If the repository has no tag since the last release, stop and ask the person which commit the notes start from; never guess it."

Apply all, some (list the IDs), or none?
```

## Rules

- **Audit first.** Nothing is edited without the person's approval of the specific IDs.
- **Small, scoped changes** that keep the skill's meaning and voice.
- **Installed engine skills** are fixed in the engine's content, not in the project's copy.
- **Every finding has evidence:** `file:line` and the quoted text.
- **The same bar as a new skill:** what skill:skill-creator requires applies to every change.

## Record

Inside an SDD change whose diff changes a skill, record it before the phase envelope (`.exo/shared/capability-attribution.md`); in verify, the phase map loads skill:skill-reviewer for that diff:

```bash
exo change record <change> --add capabilities_used '{"name": "skill-improver", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"skill-improver"'
exo change record <change> --add decisions '{"summary": "release-notes skill: SI-1, SI-3 applied; SI-2 and SI-4 declined", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record.

## Before you finish

- [ ] Every file of the skill was read raw; the mechanical checks ran.
- [ ] All eight dimensions were audited; each finding has a severity, `file:line` and a before and after.
- [ ] Nothing was edited without the person approving the IDs.
- [ ] Applied changes are only the approved ones; the checks ran again and pass.
- [ ] An installed engine skill was fixed upstream, not in the project's copy, unless the person decided otherwise.
- [ ] skill:skill-reviewer ran on the changed skill before merging.
