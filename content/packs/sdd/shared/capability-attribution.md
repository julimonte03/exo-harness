# Capability attribution

Every change keeps a record of the AI capabilities it used: `<change-root>/ai-usage-record.json`. The schema is `.exo/shared/schemas/ai-usage-record.schema.json`. The record answers, for a reviewer or an audit: which skills, subagents, commands and judges took part, who asked for each one, and what was decided.

## Who writes it

- `exo change new` creates it, with `capabilities_used` already holding the command itself.
- Every phase adds what it used before returning its envelope, with `exo change record`. Never edit the JSON by hand: the command validates it against the schema, writes it atomically, and never duplicates an entry.

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-spec", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add skills_used '"sdd-spec"'
exo change record <change> --add decisions '{"summary": "Tier 2 kept after review", "by": "human"}'
exo change record <change> --set purpose '"Let users sign in with SSO."'
```

The value is JSON: strings go in double quotes inside the single quotes.

## `capabilities_used`

Required and never empty. One entry per capability, the first time it is used:

| Field | Values |
|---|---|
| `name` | the skill, subagent, command, judge or MCP server name, for example `sdd-verify`, `sdd-verifier`, `exo specs merge` |
| `type` | `skill`, `subagent`, `tool`, `command`, `judge`, `mcp` |
| `activation` | `requested`: the person asked for it by name or with a command; `auto`: the agent, a rule or the phase map chose it |
| `resolution` | for skills: `paths-injected`, `fallback-registry`, `fallback-path` or `none` (`.exo/shared/skill-resolver.md`) |
| `note` | optional detail, for example the degradation sentence |

An entry with the same `name` and `type` counts as already recorded: the first activation stays.

## Other fields

| Field | What goes there |
|---|---|
| `skills_used` | names of the skills read in full while working on the change |
| `knowledge_used` | sources consulted before making claims: `{"source": "code" \| "docs" \| "memory" \| "mcp", "ref": "<path:line, URL or memory id>"}` |
| `judges_invoked` | `{"name": "judge-security", "result": "<short outcome>"}` |
| `decisions` | `{"summary": "...", "rationale": "...", "by": "human" \| "agent"}`, including every tier change |
| `dismissed_followups` | findings the person decided not to fix: `{"judge", "rule", "reason"}` and optionally `id` |
| `gates` | gate results, from F5: `{"name", "status": "pass" \| "fail" \| "waived" \| "skipped"}` |
| `purpose` | one sentence: what the change is for |

`ticket_key` and `epic_key` hold the exact IDs the person confirmed; they are set by `exo change new` and do not change.

## Check

`exo check --change <change>` validates the record against its schema and fails if it is missing, unreadable, or its `change_name` does not match the folder.
