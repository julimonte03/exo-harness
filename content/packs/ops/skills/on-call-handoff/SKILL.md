---
name: on-call-handoff
description: >-
  Writes the on-call shift handoff in a fixed format, so the next person
  starts with the same picture: overall status, open incidents and their
  next step, what was resolved, mitigations and temporary changes that must
  be undone, noisy or silenced alerts, changes deployed and planned, the
  watch-list of risks, pending tasks with owners, and questions for the
  incoming person. Gathers the facts from incident records, deploy history,
  alerts and the repository, and marks anything it could not verify. Use it
  at the end of an on-call shift or rotation, when an incident spans shifts,
  or when someone takes over the pager. Triggers: "on-call handoff", "end of
  shift", "hand over the pager", "handoff notes", "pass the on-call", "what
  happened during my shift", "start of the rotation", "write the shift
  summary", "who is taking over on-call".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-specs
---

# on-call-handoff

A handoff fails when something important lives only in the outgoing person's head: a flag left off, an alert silenced until Monday, a job that will run tonight. This skill collects those facts in a fixed format that the incoming person can scan in two minutes.

## Result

- **A handoff note** in the format below, every section present, with "None" where there is nothing to say.
- Every item that needs action has an owner (a role or the incoming person) and a time.
- Facts that could not be verified are listed under **Unverified**, never presented as true.
- It goes in the answer by default; in a file when the project keeps handoffs in the repository (section Where it goes).

## When

- The end of an on-call shift or rotation, an incident that continues into the next shift, or someone taking over the pager mid-shift.
- **Not for:** running an active incident (skill:incident-response; this skill hands it over, it does not drive it); a weekly status report for management; a postmortem.

## Rules

- **Facts with sources.** Each item points at where it can be checked: an incident record, a deploy, a commit, an alert, a dashboard, a ticket.
- **Verify before writing.** Check the current state of each open item (is the flag still off, is the alert still silenced) instead of copying an earlier note.
- **No personal contact data.** Escalation goes to roles and rotations ("payments on-call", "database team rotation"), never personal phone numbers or emails.
- **No secrets or customer data.** Clean anything you paste from logs or tickets (skill:prompt-hygiene; when the security pack is not installed: `security/prompt-hygiene not installed — applying inline criteria`, with the inline criteria of `.exo/shared/phase-skill-map.md`).
- **Read-only on systems.** Gathering facts uses read-only queries, never one that reads a credential (Secret objects, environment dumps, `kubectl exec`: skill:incident-response, Rules); the handoff never changes a system. A temporary change that should be undone is listed with its undo, for the person to decide.
- **The note complements a conversation.** Recommend a short live handoff; the incoming person confirms they read it.

## Steps

### 1. Frame

The service or rotation, the outgoing and incoming roles, and the shift window in UTC (`2026-03-02T08:00Z` to `2026-03-02T20:00Z`).

### 2. Gather

Ask the outgoing person for what you cannot read, and read what you can:

- **Incidents:** records opened, updated or resolved in the window; postmortems pending. Use the incident timelines of skill:incident-response when they exist.
- **Changes:** deploys in the window (the deploy tool's history, release tags, `git log --since=<start> --until=<end> --format='%cI %h %s'` on the default branch), configuration and feature flag changes, infrastructure changes.
- **Alerts:** what fired and how often, what flapped, what was silenced and until when, and what should have fired but did not.
- **Temporary measures:** flags turned off, replicas added, rate limits changed, jobs paused, manual workarounds, silences.
- **Upcoming:** deploys, maintenance windows, batch jobs, certificate or credential expiries, expected traffic peaks (skill:capacity-planning), change freezes.
- **Pending work:** tickets, follow-ups from incidents, runbook fixes (skill:runbook-writer).

### 3. Verify

For every open item and temporary measure, check its current state with a read-only query or ask the outgoing person to confirm. What you cannot confirm goes to Unverified, with who could confirm it.

### 4. Write

Use the format below; the full template with an example is in `references/handoff-template.md`. Keep each line short; link instead of pasting.

### 5. Review and hand over

Read the note with the outgoing person, fix what is wrong, and suggest a short live handoff. The incoming person acknowledges it (a reply, a reaction, a line in the file); that moment is when the pager changes hands.

## Format

```markdown
# On-call handoff: <service or rotation>

- **Shift:** 2026-03-02T08:00Z to 2026-03-02T20:00Z
- **From:** <outgoing role> **To:** <incoming role>
- **Status:** green | yellow | red. <one sentence: the one thing to watch>

## Open incidents
| ID | Severity | State | Current mitigation | Next step | Owner |
|---|---|---|---|---|---|

## Resolved this shift
| ID | Severity | Summary | Postmortem |
|---|---|---|---|

## Temporary changes to undo
| What | Why | Undo by | How to undo | Owner |
|---|---|---|---|---|

## Alerts
- Noisy or flapping: <alert, count, proposed fix>
- Silenced: <alert, until when, why>
- Missing: <what should have alerted and did not>

## Changes
- Deployed this shift: <service, version, time>
- Planned next shift: <what, when>; freezes: <window or none>

## Watch-list
- <risk, the signal to watch, the threshold that means act>

## Pending tasks
| Task | Owner | Due | Ticket |
|---|---|---|---|

## Escalation
- <area>: <role or rotation>

## Questions for the incoming person
- <decision or context they need>

## Unverified
- <item, who could confirm it>
```

- **Status:** green when nothing is open; yellow when something is open but mitigated or stable (an incident in monitoring, a risk being watched); red when an incident is active, that is, not mitigated yet, or a risk is likely to fire during the next shift.
- **Tickets** follow `tickets.pattern` in `.exo/config.json` when the project has one; use the IDs the person gives, never invented ones.

## Where it goes

- **By default, the answer:** most teams paste the handoff where they coordinate.
- **In the repository** when the project already keeps handoffs there (look for `docs/oncall/`, `oncall/handoffs/` or `docs/handoffs/`) or the person names a path: `YYYY-MM-DD-<rotation>.md` in that folder. Without such a folder, propose one (`docs/oncall/`) and create it only after the person says yes: handoffs in the repository are the team's choice.
- **Inside an SDD change,** a handoff is a project document, never a file of the change root: any phase may write it with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C); until then, it stays in the answer.

## Record

Handoffs usually happen outside SDD changes, so there is nothing to record. Inside one (an incident fix that spans shifts), an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "on-call-handoff", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). A recurring trap noticed during the shift (an alert that always flaps after a deploy) is worth saving with skill:memory-protocol as a `gotcha`.

## Before you finish

- [ ] Every section is present; empty ones say "None".
- [ ] Open incidents and temporary changes were verified now, or are under Unverified.
- [ ] Every temporary change has an undo, a time and an owner.
- [ ] Escalation names roles or rotations, with no personal contact data.
- [ ] No secrets or customer data in the note.
