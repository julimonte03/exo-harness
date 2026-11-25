---
name: ai-usage-record
description: >-
  Keeps the AI Usage Record of an SDD change (ai-usage-record.json) up to date
  with `exo change record`: the skills, subagents, commands and judges used,
  who asked for each one, how each skill was resolved, degradations, decisions
  including tier changes, and the findings the person dismissed. Use it at the
  end of every SDD phase, whenever a skill, subagent, command or judge is used
  on a change, when a decision is made, or when the person decides not to fix
  a finding. Triggers: "record this", "update the AI usage record", "what AI
  did this change use", "audit trail", "capabilities used".
metadata:
  exo-pack: core
  exo-execution: inline
---

# ai-usage-record

## Result

`<change-root>/ai-usage-record.json` tells a reviewer or an auditor which skills, subagents, commands and judges took part in the change, who asked for each one, how each skill was resolved, and what was decided. It is written only with `exo change record`, it matches `.exo/shared/schemas/ai-usage-record.schema.json`, and `exo check --change <change>` passes on it.

The fields and their values are defined in `.exo/shared/capability-attribution.md`. This skill says when to fill them and how.

## When to record

| Moment | What to add |
|---|---|
| A skill was read in full and used | `skills_used`, and a `capabilities_used` entry with `"type": "skill"` and its `resolution` |
| A skill is missing and degraded | a `capabilities_used` entry with `"resolution": "none"` and the degradation sentence as `note`; not in `skills_used`, because it was not read |
| A subagent did part of the work | `capabilities_used` with `"type": "subagent"` |
| An `exo` command acted on the change (`exo fitness classify`, `exo speclint`, `exo specs merge`, `exo check`) | `capabilities_used` with `"type": "command"` |
| An engine tool was called through the MCP server | `capabilities_used` with `"type": "tool"` |
| Another MCP server was consulted | `capabilities_used` with `"type": "mcp"`, and what it answered in `knowledge_used` |
| A judge reviewed the work | `judges_invoked` with the short outcome, and `capabilities_used` with `"type": "judge"` |
| A source supported a claim | `knowledge_used` (skill:context-retrieval) |
| The person or the agent decided something | `decisions`, including every tier change |
| The person decided not to fix a finding | `dismissed_followups` |
| A phase ends | whatever of the above is not recorded yet, before the envelope |

Routine shell commands (git, editors, running the tests) are not capabilities: do not record them. Test results go to `verify-record.md`.

## How

```bash
exo change record <change> \
  --add skills_used '"test-strategy"' \
  --add capabilities_used '{"name": "test-strategy", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
```

- `--add FIELD JSON` appends to a list field: `skills_used`, `knowledge_used`, `capabilities_used`, `judges_invoked`, `decisions`, `dismissed_followups`, `gates`. Repeat `--add` to write several entries in one call.
- `--set purpose JSON` sets the purpose. It is the only field `--set` accepts.
- The value is JSON: a string goes in double quotes inside the single quotes (`'"sdd-spec"'`), an object as `'{"name": "..."}'`. If your shell drops the inner double quotes (Windows PowerShell 5.1 does when it calls a program), write the JSON to a file and pass `@<file>` instead (`.exo/shared/sdd-phase-common.md`, section I).
- The command validates the result against the schema and writes it atomically. If the result would not match, nothing is written: read the error, fix the value and run it again.
- An entry already present is not added twice. In `capabilities_used`, an entry with the same `name` and `type` counts as present, so the first activation stays.
- Never edit the JSON by hand. If the command says the file is unreadable, tell the person; do not rewrite it from memory.

### activation

- `requested`: the person asked for it by name or with a command (`/sdd-new`, "use test-strategy", "run the security judge").
- `auto`: the agent, a rule or the phase map chose it.

If the person did not name it, it is `auto`.

### resolution

How a skill was found (`.exo/shared/skill-resolver.md`): `paths-injected`, `fallback-registry`, `fallback-path` or `none`. Set it on every entry that was resolved as a skill, which includes judges. Subagents, commands, tools and MCP servers have no resolution.

### Examples

```bash
# A missing skill: the note is the exact sentence you said
exo change record <change> --add capabilities_used '{"name": "secure-coding-baseline", "type": "skill", "activation": "auto", "resolution": "none", "note": "security/secure-coding-baseline not installed — applying inline criteria"}'

# A subagent and an engine command
exo change record <change> \
  --add capabilities_used '{"name": "sdd-verifier", "type": "subagent", "activation": "auto"}' \
  --add capabilities_used '{"name": "exo specs merge", "type": "command", "activation": "auto"}'

# A judge
exo change record <change> \
  --add capabilities_used '{"name": "judge-security", "type": "judge", "activation": "auto", "resolution": "paths-injected"}' \
  --add judges_invoked '{"name": "judge-security", "result": "2 findings: 1 fixed, 1 dismissed"}'

# Decisions: a tier raised by the agent, a tier lowered with the person's confirmation
exo change record <change> --add decisions '{"summary": "Tier raised from 2 to 3", "rationale": "the spec adds a payment field (fitness signal from the spec phase)", "by": "agent"}'
exo change record <change> --add decisions '{"summary": "Tier lowered from 3 to 2", "rationale": "the person confirmed it in writing: yes, lower it to Tier 2", "by": "human"}'

# A finding the person decided not to fix
exo change record <change> --add dismissed_followups '{"id": "JCR-2", "judge": "judge-code-reviewer", "rule": "error-handling", "reason": "the caller retries; see src/api/handler.py:88"}'

# The purpose, when exo change new ran without --purpose
exo change record <change> --set purpose '"Let employees sign in with SSO."'
```

## What counts as a decision

- Every tier change. A raise is `"by": "agent"` when the orchestrator made it; a lower tier needs the person's literal confirmation and is `"by": "human"`.
- A scope change, or an approach chosen between alternatives, that the person approved.
- Running a Tier 3 verify without isolation, which needs the person's explicit approval (`.exo/shared/agent-capabilities.md`).

Keep `summary` to one line and put the why in `rationale`.

## Dismissed findings

- Only when the person decided not to fix it. The `reason` is theirs, not yours.
- Copy `judge`, `rule` and, when the finding has one, `id` exactly as the finding shows them: in `exo change followups <change> --json`, or in the judge's answer or `verify-record.md` for a finding that is not a followup. That is how the engine matches the dismissal to the finding.

## Fields you do not write

- `ticket_key` and `epic_key`: `exo change new` sets them with the exact IDs the person confirmed, and they do not change.
- `change_name`, `attribution_schema_version` and `updated_at`: the engine writes them.
- `gates`: the results of the quality gates. Record only a gate that actually ran, with its real status.

## Who records

- The session that runs the phase records what it used before it returns its envelope.
- A subagent lists what it used, and how it resolved each skill, in its envelope notes (`.exo/shared/skill-resolver.md`, Report); the orchestrator records those lines. Read-only subagents never write the record.
- Without an orchestrator, the agent records its own work.

## Check

```bash
exo change ai-usage <change> --json
exo check --change <change>
```

- `exo change ai-usage` shows the record as it is. Compare it with what the phase did: every skill in the envelope notes (`Skills:` and `Degraded:`) has its entry, and so does every subagent, command and judge.
- `exo check --change` fails if the record is missing, unreadable or invalid against its schema, or if its `change_name` does not match the folder.

## Rules

- No change, no record. Outside an SDD change there is nothing to write; never create the file by hand: `exo change new` creates it.
- Never record what did not happen, and never leave a degradation out.
- No secrets, credentials or personal data in any field.
