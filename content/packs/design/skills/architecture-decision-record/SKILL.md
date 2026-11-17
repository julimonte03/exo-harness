---
name: architecture-decision-record
description: >-
  Writes and audits architecture decision records (ADRs) in the ADR folder the
  project already uses, or docs/adr/ when it has none: numbered NNNN-<slug>.md
  files with a status (Proposed, Accepted, Superseded by NNNN or Recovered)
  and the sections Context, Decision, Alternatives and Consequences, including
  the Recovered records that reverse engineering rebuilds from the code, with
  their confidence and evidence. Writes only the text the person approved.
  Audits the folder for records without a status, records that contradict
  each other and decisions in the code that no record explains. Use it in the
  design phase for a decision that is hard to reverse, in the archive phase
  for decisions worth keeping, in the synthesis of an adoption, or whenever
  someone wants to record or review a decision. Triggers: "write an ADR",
  "record this decision", "architecture decision record", "document why we
  chose", "supersede the ADR", "audit our ADRs", "decision log".
metadata:
  exo-pack: design
  exo-execution: inline
---

# architecture-decision-record

An ADR records one decision that is hard to reverse: what was decided, why, what else was considered and what it costs. It is short, it lives next to the code, and once accepted it is not rewritten: a later decision supersedes it.

## Result

- **Writing:** one ADR per decision in the project's ADR folder, started from `references/adr-template.md`, with exactly the text the person approved, and cited from where the decision was made (design.md, the AI Usage Record).
- **Auditing:** a findings table in your answer (Severity | File:line | Finding | Rule | Suggestion), with no file changed. Each fix is a new ADR or a status change, written only when the person approves it.

## The folder

1. **The one the project uses:** the first of `docs/adr`, `doc/adr`, `docs/decisions`, `docs/architecture/decisions` and `adr` that holds a `.md` file. In a project adopted with reverse engineering, `adr_dir` in `.exo/discovery/inventory.json` already says which one.
2. **None yet:** use `docs/adr/`, and tell the person you are creating it.
3. **Consistency inside the folder wins.** When its ADRs already follow another naming, template or language, follow theirs and say so. Recovered records keep `-recovered-` in their name in every case.

## The format

- **File:** `<adr folder>/NNNN-<slug>.md`.
  - `NNNN` is the next number after the highest one in the folder, recovered records included, with four digits (`0007`). A number is never reused, not even after a deletion.
  - The slug is the decision in a few lowercase words joined by hyphens: `0007-postgresql-for-orders.md`.
- **Title:** `# NNNN. <the decision, in a few words>`.
- **Header lines:**
  - `Status:` and `Date:`, the day the status last changed;
  - `Change:` with the SDD change, when there is one;
  - `Supersedes:` with the number it replaces, when it replaces one.
- **Sections, in this order:** Context, Decision, Alternatives, Consequences. What goes in each is in `references/adr-template.md`.
- **Language:** English in a new folder; otherwise, the language of its ADRs.
- **No secrets or personal data:** name roles and teams, not people. Say where a secret lives, never its value (`.exo/shared/data-protection.md`).

### Status

| Status | Means | Set by |
|---|---|---|
| `Proposed` | Written down, not decided yet | the design phase, or the person |
| `Accepted` | Decided: the code follows it | the person, explicitly |
| `Superseded by NNNN` | Replaced by ADR NNNN, whose header says `Supersedes:` with this number | the ADR that replaces it |
| `Recovered` | Rebuilt from the code by reverse engineering, not confirmed yet | the synthesis of an adoption |

- **Accepted is final.** To change the decision, write a new ADR with `Supersedes:` and change only the old one's status line, to `Superseded by <new number>`. Fixing a typo or a broken link is fine.
- **Recovered is a hypothesis.** It becomes `Accepted` only when the person confirms it, and its file keeps its name.

## When it runs

| Who | Trigger | What this skill does |
|---|---|---|
| `sdd-design` | A decision of the design that is hard to reverse: a data store, a framework, an API style, a security mechanism, a boundary between modules | Drafts the ADR as `Proposed`. Once the person approves the text, writes it, lists it in design.md, Modules / Files (so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C)), and links it from Architecture Overview |
| `sdd-archive` | Decisions worth keeping: the ADRs design.md links, and the `decisions` of the AI Usage Record | Moves the change's `Proposed` ADRs to `Accepted` and writes the missing ones, with the person's approval, pointing to the archived design.md |
| `re-synthesize` (pack `discovery`) | A decision the code shows, during an adoption | Writes it as a recovered ADR (see Recovered records) |
| The person | "write an ADR", "audit our ADRs" | Writes the ADR they ask for, or audits the folder |

- **Not every decision needs one.** A decision that is easy to reverse, local to one module, or already fixed by a standard of the team stays in design.md.
- **Automatic mode** (`sdd.mode: auto`): do not write it. Leave the draft in design.md, Architecture Overview, marked `ADR pending approval`, and list it in the envelope notes. The archive phase writes it at its stop before the PR, once the person approves it.

## Write an ADR

1. **Number.** Find the folder and the next number (above).
2. **Related ADRs.** Read the ADRs on the same topic. A decision that contradicts an `Accepted` one supersedes it; otherwise it is not a new decision.
3. **Facts first.** Gather the forces, the constraints and the alternatives really considered, each with its `path:line` or its source (skill:context-retrieval). Never invent an alternative to fill the section.
4. **Draft** from `references/adr-template.md`: one decision per ADR, about a page.
5. **Approval.** Show the person the full text and the file name, and ask "Write this ADR as it is?". Write it only after a yes. Otherwise adjust it and ask again.
6. **Links.** Link it from where the decision was made: design.md (Architecture Overview) in the design phase, and the AI Usage Record:

   ```bash
   exo change record <change> --add decisions '{"summary": "ADR 0007: PostgreSQL for orders", "by": "human"}'
   ```

7. **Supersede.** When it replaces another ADR, change the old one's status line in the same commit.
8. **Commit** it with the change, or as its own unit outside a change (skill:work-unit-commits), for example `docs(adr): record PostgreSQL for orders`.

## Recovered records

During an adoption, `re-synthesize` (pack `discovery`) records as ADRs the decisions the code shows. They describe what the code does, not why it was decided, so they stay hypotheses until the person confirms them.

- **File:** `NNNN-recovered-<slug>.md`, numbered with the rest of the folder. The name matters: during an adoption, `exo discover status` reports every change outside `.exo/discovery/`, the capability specs, the wiki and `<adr folder>/*-recovered-*.md`.
- **Header:** `Status: Recovered`, `Confidence: high|medium|low`, `Source:` with the discovery units it comes from, and `Date:`.
- **Evidence:** every claim carries its marker, as section B of the discovery contract (pack `discovery`) says:
  - `[Code] path:line` or `[Code] path:start-end`;
  - `[Doc] path`;
  - `[Inferred: high|medium|low]`.

  Cite the place, never copy a value.
- **What the code cannot tell** (the alternatives, the original reason) is `[Inferred: low]` or an open question for the person, never invented.

How to set the confidence, and an example, are in `references/adr-template.md`.

## Audit the folder

Read-only: list, read and search, and write nothing. The checks, with their rule IDs and severities, are in `references/audit.md`:

1. **Without a status:** an ADR with no status line, or with one outside the folder's vocabulary.
2. **Contradictions:** two `Accepted` ADRs that decide opposite things, a `Superseded by` that points to nothing, an `Accepted` ADR the code no longer follows.
3. **Decisions without an ADR:** what the code shows was decided (data stores, frameworks, messaging, authentication, API style, deployment) and no ADR explains.
4. **Form:** numbering, names, missing sections, and recovered ADRs without confidence or evidence.

Report each finding with its `file:line` and a suggested fix, then offer the fixes: the ADRs to write (`Proposed`, or `Recovered` during an adoption) and the status lines to change. Write each one only when the person approves its text.

## Record

Inside an SDD change, a phase that runs inline records the skill (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it. `activation` is `requested` when the person asked for the ADR, and `auto` when the phase map chose it:

```bash
exo change record <change> --add capabilities_used '{"name": "architecture-decision-record", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"architecture-decision-record"'
```

Tell the person which ADRs were written or changed, with their status, and which ones are still drafts waiting for approval.
