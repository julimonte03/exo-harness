# Audit output

The audit `skill-improver` returns in step 6, and the summary after applying the approved changes. The example audits a synthetic project skill, `release-notes`.

## Verdicts

| Verdict | When |
|---|---|
| Good | No High or Medium finding |
| Needs work | At least one High or Medium finding, fixable with targeted edits |
| Rework | The job, the description and the steps disagree with each other, or most steps need rewriting; a full rewrite is proposed, and done only if the person agrees |

## Template

````markdown
**skill-improver: <skill>** · Verdict: <Good | Needs work | Rework> (<n> High, <n> Medium, <n> Low)

<One or two sentences: the main problem and the effect it has.>

| ID | Severity | File:line | Dimension | Finding |
|---|---|---|---|---|
| SI-1 | ... | ... | ... | ... |

## Fixes

**SI-1** · <dimension>
Before (<file:line>):
> <the exact current text>

After:
> <the replacement>

Why: <one line: what this changes for the agent or the reader>.

<one block per finding>

## Checks

- exo validate (or the manual checks): <result for this skill>
- Size: SKILL.md <n> lines; references: <list with lines>

Apply all, some (list the IDs), or none?
````

## Example

````markdown
**skill-improver: release-notes** · Verdict: Needs work (1 High, 2 Medium, 1 Low)

The skill writes into a phase artifact and has no triggers, so it both loads on the wrong requests and breaks artifact ownership when it does.

| ID | Severity | File:line | Dimension | Finding |
|---|---|---|---|---|
| SI-1 | High | release-notes/SKILL.md:44 | Coherence | Step 4 appends the notes to the change's `proposal.md`, which only the propose phase writes |
| SI-2 | Medium | release-notes/SKILL.md:3 | Description | "Helps with releases": no triggers; overlaps `branch-pr` on "prepare the PR" |
| SI-3 | Medium | release-notes/SKILL.md:61 | Steps | "Handle missing tags appropriately": no default and no stop condition |
| SI-4 | Low | release-notes/SKILL.md:12 | Structure | No Return section; the output format is only implied |

## Fixes

**SI-1** · Coherence
Before (release-notes/SKILL.md:44):
> 4. Append the notes to the change's proposal.md under a new Release Notes section.

After:
> 4. Write the notes to `CHANGELOG.md` under the next version heading. Inside an SDD change, never edit the change's artifacts: `CHANGELOG.md` is a project document, written with the person's approval once the plan lists it (`.exo/shared/sdd-phase-common.md`, section C).

Why: the proposal belongs to its phase; speclint would also reject the extra section.

**SI-2** · Description
Before (release-notes/SKILL.md:3):
> description: Helps with releases.

After:
> description: >-
>   Writes release notes from the commits since the last tag, grouped by
>   Conventional Commits type, with breaking changes first, into
>   CHANGELOG.md. Use it when a version is about to be tagged or someone
>   asks what changed since the last release. Triggers: "write the release
>   notes", "update the changelog", "what changed since the last release",
>   "prepare the notes for v2.3".

Why: names the result and the moment; the triggers no longer include "prepare the PR".

**SI-3** · Steps
Before (release-notes/SKILL.md:61):
> Handle missing tags appropriately.

After:
> If the repository has no tag since the last release, stop and ask the person which commit the notes start from; never guess it.

Why: the agent was choosing a starting commit on its own.

**SI-4** · Structure
Before (release-notes/SKILL.md:12): no Return section.

After: a Return section with a five-line example of a version heading and two grouped entries.

Why: the format varied between runs.

## Checks

- Manual checks (project skill): frontmatter parses; name equals the folder; description 31 characters (after SI-2: 402); no invisible characters.
- Size: SKILL.md 88 lines; no references.

Apply all, some (list the IDs), or none?
````

## After applying

```markdown
Applied: SI-1, SI-3 (approved). Not applied: SI-2, SI-4 (declined).
Files changed: release-notes/SKILL.md (2 edits).
Checks: manual checks pass; SKILL.md 89 lines.
Next: skill-reviewer on release-notes before merging.
```
