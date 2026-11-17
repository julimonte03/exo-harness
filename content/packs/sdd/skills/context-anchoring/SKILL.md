---
name: context-anchoring
description: >-
  Keeps a living decision document for an SDD change, an "ADR in progress",
  in <change-root>/context-anchor.md: the decisions made so far with their
  date and who made them, the alternatives ruled out, the assumptions, the
  open questions and the next step. It survives the end of a session, a
  context compaction and a change of person, because it is a file committed
  with the change and not only the agent's memory, which belongs to one user
  on one machine. Every later phase reads it first and updates it before it
  ends. Use it when a change spans several sessions or developers, when
  decisions pile up faster than the artifacts record them, or when someone
  picks up a change that someone else started. It is not a final decision
  record: a closed, hard-to-reverse decision goes to an ADR. Triggers: "keep a
  decision log for this change", "where did we leave this change", "hand this
  change over", "pick up where we left off", "living document for this
  feature", "track what we decided".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-permissions: write-specs
---

# context-anchoring

## Result

- `<change-root>/context-anchor.md`, in the format of `references/anchor-format.md`: Now (status, phase, next step), Decisions, Ruled out, Assumptions, Open questions and Log.
- Read at the start of every session on the change, and updated before it ends and whenever a decision is made.
- Optionally mirrored in memory, as skill:memory-protocol says.

## When

- **Design phase, Conditional** (`.exo/shared/phase-skill-map.md`, row design): the change spans several sessions or developers.
- **Any phase, on request:** the person asks to keep a decision log, to hand the change over, or to pick it up from someone else.
- **Every later phase, once the file exists:** its presence is the trigger. Read it first; update it before the phase ends.
- **Not** for a Tier 1 change done in one session: the proposal and the AI Usage Record already hold what matters. Say so if the person asks, and start it anyway if they still want it.

## Why a file, not only memory

The engine's memory is per user and per machine: one database that another developer, or the same person on another computer, never sees. The anchor is a file in the change root, committed with the change: it travels with the branch and the pull request, any agent can read it, and it is archived with the change. Memory is a mirror, never the only copy.

## Who writes it

| Session | Updates the anchor |
|---|---|
| the inline phases (new, propose, spec, design, tasks, archive) and the orchestrator | the session itself |
| a subagent (`sdd-explorer`, `sdd-implementer`, `sdd-verifier`, `sdd-judge`) | nobody inside the subagent: it lists its decisions, assumptions and questions in its envelope notes, and the orchestrator adds them |

- The anchor is the one file of the change that belongs to no phase, and only this skill edits it.
- It never edits proposal.md, spec.md, design.md, canvas.md, tasks.md or the code. A decision that changes one of them goes to the phase that owns it; the anchor records the decision and where it landed.

## Start the anchor

1. Run `exo change status <change> --json` for the name, the tier, the phase and the artifacts.
2. If `<change-root>/context-anchor.md` already exists, read it and update it instead.
3. Create it from the template in `references/anchor-format.md`.
4. **Seed it from what exists,** citing the source of each entry:
   - the decisions in proposal.md (Approach) and design.md, with the alternatives they rejected;
   - the `decisions` of the AI Usage Record (`exo change ai-usage <change> --json`);
   - what the person said in this conversation.
   Date each decision when it was made; when you cannot tell, use the artifact and say so (`from design.md`).
5. Write Now: the status, the phase and the next step.
6. Show the person Now and the Decisions, and ask whether something is missing or wrong.

## Update the anchor

Right away when a decision is made, and at the end of each session or phase that works on the change:

- **Decision** (`D-n`): what, why, who decided, the date, and where it landed (`design.md, Data Shapes`). The alternatives it rejected go to Ruled out, with the reason.
- **Only a person decides.** A choice the agent made goes to Assumptions until a person confirms it.
- **A decision changes:** never delete it. Mark it `Superseded by D-n` and add the new one.
- **Assumption** (`A-n`): what is taken as true, how to check it, and its status (open, confirmed, or wrong and what changed).
- **Open question** (`Q-n`): what, who can answer it, and which phase needs it. Once answered, mark it `Answered: D-n` (or `A-n`) and write the answer there.
- **Now:** rewrite it every time: status, phase, and one next step, with who does it and where to start reading.
- **Log:** one line per session: date, phase, who, what happened.

Keep it short: a new reader gets the state from Now in a minute. When the Log passes about 30 lines, fold the oldest entries into one summary line.

## Resume from the anchor

At the start of a session on the change, or after a context compaction:

1. Read `context-anchor.md` first (Now and Open questions), then run `exo change status <change> --json`.
2. Compare it with the artifacts. A decision the artifacts contradict, or a next step that is already done, is a mismatch: tell the person and let them settle it; never pick a side silently.
3. Continue from the next step, and add a Log line when the session ends.

## Memory mirror

- Mirror the anchor as skill:memory-protocol says, with a stable topic key, so a second save updates it:

```bash
exo mem save --type decision --title "add-volume-discount: context anchor" --topic-key sdd/add-volume-discount/context-anchor --content - < specs/add-volume-discount/context-anchor.md
```

- Point the change's state artifact at it (`sdd/<change-name>/state`, `.exo/shared/memory-convention.md`): `anchor: <change-root>/context-anchor.md`.
- With `sdd.persistence: memory` or `none` there are no files: the anchor would reach only this user. Tell the person, and offer to write the file anyway.

## What never goes in

- Secrets, credentials, personal or customer data, and raw production logs (`.exo/shared/data-protection.md`). Name the kind of data and where it lives instead.
- People appear by handle or role, as the team writes them in commits (`@<handle>`, `tech_lead`), never by email or phone number.

## At archive

- skill:sdd-archive moves the whole change folder, the anchor included. Before that, set the status to `closed` and write the final Now: what was decided and where each decision landed.
- A decision worth keeping beyond the change (hard to reverse) is a candidate for `architecture-decision-record`, the Conditional of archive (pack `design`). The anchor gives it the context, the decision and the alternatives. When that skill is missing, say `design/architecture-decision-record not installed — applying inline criteria` and follow its criteria in `.exo/shared/phase-skill-map.md`.

## Record

Before the envelope of the phase (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "context-anchoring", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"context-anchoring"'
exo change record <change> --add decisions '{"summary": "Discount tiers are constants in code, not a table", "rationale": "nobody edits them today and a table needs a migration", "by": "human"}'
```

- `activation` is `requested` when the person asked for the decision log.
- A person's decision goes both to the anchor (the working context) and to the record's `decisions` (the audit trail).
- In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Return

The phase that loaded this skill reports it in its envelope (`.exo/shared/sdd-phase-common.md`, section D):

```yaml
artifacts:
  - path: specs/add-volume-discount/context-anchor.md
    summary: "Anchor: 2 decisions, 2 ruled out, 1 open question; next: tasks"
notes: >-
  Skills: context-anchoring (fallback-registry). Anchor mirrored in memory (sdd/add-volume-discount/context-anchor).
```

## Before you finish

- [ ] The file follows `references/anchor-format.md`, and Now has the phase and one concrete next step.
- [ ] Every decision has a date, who made it and where it landed; agent choices are Assumptions until confirmed.
- [ ] Ruled-out alternatives have their reason; open questions name who can answer them.
- [ ] Nothing deleted: changed decisions are marked superseded.
- [ ] No secrets, personal data, emails or raw logs.
- [ ] No other artifact of the change edited.
- [ ] Recorded, and mirrored in memory when the project uses memory.
