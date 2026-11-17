---
name: sdd-archive
description: >-
  Closes a verified SDD change: checks its preconditions, merges its spec
  delta into the living specs with exo specs merge, settles with the person
  what the merge cannot (the Purpose of a new capability, clashing text), runs
  the wiki checkpoint, moves the change folder to the archive with git mv,
  commits, and prepares the pull request. Runs inline. Use it when the verify
  Verdict is ready (and, in Tier 4, judgment-day is approved) and the person
  asks to archive, close or finish the change, fold its delta into the living
  specs, open its PR, or runs /sdd-archive, and when the orchestrator reaches
  the archive phase.
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: archive
  exo-permissions: write-specs+git
---

# sdd-archive

## Result

- The change's delta merged into `<specs_dir>/capabilities/`, and every capability it touched passes `exo speclint`.
- The change folder moved with `git mv` to `<specs_dir>/archive/[<epic>/]YYYY-MM-DD-<change-name>/`, so `exo change status <change>` says `archived`.
- One commit with the merge, the move and the wiki update, and the pull request ready with `branch-pr`.
- The envelope of `.exo/shared/sdd-phase-common.md`, section D, with `next: none`.

## What it writes and what it never touches

- **Writes:** the living specs, through `exo specs merge` (by hand only the Purpose of a new capability and wording fixes the person agrees to); `.exo/context.md` when the wiki checkpoint calls for it and the person agrees; the decision record when that conditional applies; the move, the commit and the PR.
- **Never touches:** code, tests, or the content of the change's artifacts: they move as they are. If the delta itself is wrong, stop and return `status: needs-input`: the fix belongs to `sdd-spec`, and the change is verified again.

## Order

**Check, merge, move, commit, PR**, each step only when the one before passed. `exo check --change` runs before the move, so a failure goes back to its phase while the change is still active; it also finds the change after the move, and so does `exo check --base` in CI. The move carries the merged state; the commit and the PR show all of it.

## 1. Preconditions

1. `exo change status <change> --json`: the tier and the artifacts. An unknown tier is Tier 4.
2. The Verdict of verify-record.md is `ready`. Otherwise stop: `next: apply` for `needs-rework`, `next: verify` when there is no record.
3. In Tier 3 and 4 the record comes from a fresh-context verify (`.exo/shared/project-wiki-guard.md`). If it declares "no isolation", the person chose that (`.exo/shared/agent-capabilities.md`): in Tier 4 their approval must be in `decisions`, and the notes say so.
4. In Tier 4, an approved `judgment-day` is in the AI Usage Record (`exo change ai-usage <change> --json`, field `judges_invoked`). Without it, stop with `next: judgment`.
5. No finding is undecided: `exo change followups <change>` lists no open followups, and every finding in `verify-record.md`, Issues Found, is fixed or dismissed by the person (`.exo/shared/capability-attribution.md`, Findings).
6. `exo check --change <change>` passes. An error in an artifact goes back to the phase that owns it.
7. If a `handoff.md` was left in the change root by a verify, delete it: it is not an artifact.

## 2. Merge the delta

1. `exo specs merge <change> --dry-run` shows what would change in each capability, for example `would create specs/capabilities/auth/spec.md: add CAP-auth-FR-3`. Without spec.md there is nothing to merge: in Tier 1 that is fine only when the change does not alter behavior.
2. Read the capability specs it will touch, and look for what the command cannot judge (step 3). Show the dry run to the person.
3. `exo specs merge <change>`. It validates the whole delta first and writes nothing if anything fails: a MODIFIED or REMOVED of an ID that does not exist, an ADDED of an existing ID with other text, a removed ID used again. Any of those means the delta is wrong: return `needs-input`. Merging the same delta again changes nothing.

## 3. What the merge cannot judge

Settle these with the person, and record each decision (`decisions`, `"by": "human"`):

- **A new capability.** The merge creates its `spec.md` with an empty Purpose and says `note: new capability <capability>: write its Purpose in <path>`. Write one or two sentences about what the capability is for, from the proposal's Intent, and confirm them with the person.
- **Text that clashes.** A merged requirement that contradicts or repeats another requirement of the same capability, or that landed in the wrong capability. Fix wording in the living spec when the person agrees; anything that changes behavior needs a new delta, so return `needs-input`.

Then run `exo speclint <specs_dir>/capabilities/<capability>/spec.md` for every capability the merge touched. `exo specs list` shows each one with its counts.

## 4. Decisions worth keeping

When the change made a decision worth keeping, apply `architecture-decision-record`. When it is not installed, say `design/architecture-decision-record not installed — applying inline criteria` and add a short record (context, decision, alternatives, consequences) to the project's ADR folder (`docs/adr/` when it has none), pointing to the change's archived design.md. The archived artifacts are not edited.

## 5. Wiki checkpoint before the PR

Run the "Before the PR" checkpoint of `.exo/shared/project-wiki-guard.md`:

1. **Wiki update.** If the change altered something `.exo/context.md` describes (a command, a dependency, a convention, an area), propose the update and apply it in this change when the person agrees, or ask them to. With `.exo/discovery/` in the project, also run `exo discover update --json` and propose the update of the stale units and capabilities, as the guard says.
2. **Branch clean.** Checked right after the commit (step 8).
3. **Fresh review done.** Checked in step 1.3.
4. **Checks pass.** Checked in step 1.6, before the move.

Report the result in the envelope notes, for example `wiki guard: branch feat/PROJ-123-add-login, clean; context.md updated`.

## 6. Record

Before the move, so the record travels with the folder (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-archive", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "exo specs merge", "type": "command", "activation": "auto"}'
exo change record <change> --add skills_used '"sdd-archive"'
exo change record <change> --add decisions '{"summary": "Purpose of the new capability auth approved", "by": "human"}'
```

`activation` is `requested` when the person called this skill by name.

## 7. Move the change

Use today's date, and keep the epic folder when the change has one. `git mv` needs the parent folder, and moves only what git tracks: add the change's untracked files first.

```bash
mkdir -p specs/archive/PROJ-77
git add specs/PROJ-77/PROJ-123-add-login
git mv specs/PROJ-77/PROJ-123-add-login specs/archive/PROJ-77/2026-11-14-PROJ-123-add-login
```

If the epic folder is now empty (`specs/PROJ-77/` in the example), remove it with `rmdir`: git does not track empty folders, and an empty one on disk is noise.

Then `exo change status <change>` must say `phase: archived`.

## 8. Commit and check

1. Write the PR description with `branch-pr` first: `pr.md` in the archived change root (`exo change status <change> --json` gives its `path`). Then commit the merged specs, the moved folder with `pr.md`, the wiki update and the decision record as `work-unit-commits` says: Conventional Commits, with the ticket when the project has one.
2. `git status`: everything that belongs to the change is committed, and nothing else is (the wiki checkpoint's "Branch clean").
3. `exo check --base <base>` (what CI runs) passes: it checks the archived change and lints the capability specs the merge touched.

## 9. Pull request

- Always stop and ask the person before opening the PR, in interactive and automatic mode alike (section H).
- Open it with `branch-pr`, with the `pr.md` committed in step 8. It follows `.exo/shared/templates/pr.md`: Summary, Ticket, Changes, Test Plan (the commands and results of verify-record.md) and Checklist.
- Never push to a protected branch and never force-push.
- `branch-pr` ships in `core`, which `sdd` requires. If it is missing, the installation is incomplete: say so, suggest `exo doctor`, and give the person the PR text to open it themselves.

## End

Update the state artifact (`done: archive · next: none`, `.exo/shared/memory-convention.md`) and save the decisions the person made, as skill:memory-protocol says. Then finish with the envelope:

```yaml
status: ok
phase: archive
change_name: PROJ-123-add-login
artifacts:
  - path: specs/capabilities/auth/spec.md
    summary: created; CAP-auth-FR-3 and CAP-auth-FR-4 added; Purpose written with the person
  - path: specs/archive/PROJ-77/2026-11-14-PROJ-123-add-login/
    summary: change folder moved with git mv
notes: >-
  Isolation: inline. Skills: sdd-archive (fallback-registry), branch-pr (fallback-registry).
  wiki guard: branch feat/PROJ-123-add-login, clean; context.md updated (new auth area).
  exo check --change passed before the move; exo check --base origin/main passed after the commit.
  PR: opened with the person's OK.
next: none
```

The cycle ends here. A later change on the same behavior starts again with `sdd-new`, and its delta builds on these living specs.
