# Capability attribution

Every change keeps a record of the AI capabilities it used: `<change-root>/ai-usage-record.json`. The schema is `.exo/shared/schemas/ai-usage-record.schema.json`. The record answers, for a reviewer or an audit: which skills, subagents, commands and judges took part, who asked for each one, and what was decided.

## Who writes it

- `exo change new` creates it, with `capabilities_used` already holding the command itself.
- A phase that runs inline adds what it used before returning its envelope, with `exo change record`. A phase that runs in a subagent lists it in its envelope notes, and the orchestrator records it: subagents never run `exo change record`.
- Never edit the JSON by hand: the command validates it against the schema, writes it atomically, and never duplicates an entry.

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-spec", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add skills_used '"sdd-spec"'
exo change record <change> --add decisions '{"summary": "Tier 2 kept after review", "by": "human"}'
exo change record <change> --set purpose '"Let users sign in with SSO."'
```

The value is JSON: strings go in double quotes inside the single quotes. In Windows PowerShell 5.1, write it to a file and pass `@<file>` (`.exo/shared/sdd-phase-common.md`, section I).

## `capabilities_used`

Required and never empty. One entry per capability, the first time it is used:

| Field | Values |
|---|---|
| `name` | the skill, subagent, command, judge or MCP server name, for example `sdd-verify`, `sdd-verifier`, `exo specs merge` |
| `type` | `skill`; `subagent`; `tool`: an engine tool called through MCP; `command`: an `exo` command or another CLI run in the terminal; `judge`: a judge review, also when it degraded to inline criteria; `mcp`: another MCP server |
| `activation` | `requested`: the person asked for it by name or with a command; `auto`: the agent, a rule or the phase map chose it |
| `resolution` | for skills: `paths-injected`, `fallback-registry`, `fallback-path` or `none` (`.exo/shared/skill-resolver.md`) |
| `note` | optional detail, for example the degradation sentence |

An entry with the same `name` and `type` counts as already recorded: the first activation stays.

## Other fields

| Field | What goes there |
|---|---|
| `skills_used` | names of the skills read in full while working on the change |
| `knowledge_used` | sources consulted before making claims: `{"source": "code" \| "docs" \| "memory" \| "mcp", "ref": "<path:line, URL or memory id>"}` |
| `judges_invoked` | `{"name": "judge-security", "result": "<short outcome>"}`; the Tier 3 review is `{"name": "judgment-day", "result": "approved"}` once the person approves it, or `"escalated: <why>"` |
| `decisions` | `{"summary": "...", "rationale": "...", "by": "human" \| "agent"}`, including every tier change |
| `dismissed_followups` | findings the person decided not to fix, and the ones automatic mode deferred: `{"judge", "rule", "reason"}` and optionally `id` |
| `gates` | gate results: `{"name", "status": "pass" \| "fail" \| "waived" \| "skipped"}`; `pass` for APPROVED, `fail` for ESCALATED, `waived` once the `tech_lead` accepts it |
| `purpose` | one sentence: what the change is for |

`ticket_key` and `epic_key` hold the exact IDs the person confirmed; they are set by `exo change new` and do not change.

## Conventions other phases read

`.exo/shared/sdd-status-contract.md` derives the next phase from these entries, so record them exactly and only when the phase returned `status: ok`:

- `phases_done`: `exo change record <change> --phase-done <phase>`.
- `judges_invoked`: the `judgment-day` result in Tier 3.
- `skills_used`: the phase skill and the skills it loaded.

## Findings

Judge findings go to `<change-root>/followups.json` with `exo change record <change> --followup '<json>'` (`.exo/shared/judge-common.md`, section F); the verifier's own findings stay in `verify-record.md`, section Issues Found. The person decides each one, except the Medium and Low ones in automatic mode:

- **Fixed:** once the fix is in, `exo change record <change> --fixed <id>` marks it.
- **Dismissed:** it goes to `dismissed_followups` with its `id`, the `judge` and `rule` the finding shows, and their reason. A dismissal with an `id` covers only that finding.
- **Deferred (automatic mode only):** a Medium or Low finding is decided by its severity: it goes to `dismissed_followups` like a dismissal, with the reason `deferred to a followup (automatic mode): <id>`, and `pr.md` lists it under Known followups. A Medium or Low issue of Issues Found is deferred with a decision whose summary starts the same way (`sdd-verify`, Judges).

`exo change followups <change> --status open|fixed|dismissed|all` lists them.

## Check

`exo check --change <change>` validates the record against its schema and fails if it is missing, unreadable, or its `change_name` does not match the folder.
