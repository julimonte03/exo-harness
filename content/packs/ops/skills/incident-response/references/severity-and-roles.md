# Severity, roles and updates

Detail for `incident-response`. The short table in `SKILL.md` is enough to declare; this file helps with the borderline cases.

## Choosing the severity

Ask these questions in order and stop at the first yes:

1. Is data being lost, corrupted or exposed, or is a security breach in progress? **SEV1.**
2. Is a core journey (sign in, checkout, payments, the main API) down or unusable for most users? **SEV1.**
3. Is a core journey badly degraded (errors or latency far above the SLO), or down for a region, a tenant or a segment of users? **SEV2.**
4. Is a non-core feature down, or a core one degraded with a workaround users can follow? **SEV3.**
5. Is there a risk with no user impact yet? **SEV4.**

Adjust the answer with:

- **Duration and trend.** A SEV3 that keeps growing becomes a SEV2. Re-assess at every update.
- **Contractual exposure.** If an SLA with customers is at risk, raise one level.
- **Error budget.** A burn rate that would spend the monthly budget within hours is at least SEV2 (skill:slo-design).
- **Downgrade openly.** Lowering the severity is a decision of the IC, written in the timeline with its reason.

### Mapping another scale

If the organization uses P0 to P4, colors or names, write the mapping once at the top of the record, for example `P1 = SEV2 for this incident`, and keep using the organization's labels in its own channels.

## Roles in detail

### Incident commander

- States the severity, the roles and the cadence of updates at the start.
- Keeps a short loop: "What do we know? What are we trying? When do we check again?"
- Approves every change to a system and every external message.
- Calls in more people early: an expert, the owner of a dependency, a manager for customer-facing decisions.
- Hands the role over explicitly ("You are IC now") when leaving or at a shift change.
- Declares the incident resolved and names the postmortem owner.

### Communications lead

- Sends updates on time, even "no change, next update at 15:10 UTC".
- Keeps one channel for working and another for stakeholders, so the responders are not interrupted.
- Coordinates customer-facing messages with whoever owns them (support, the status page owner); drafts are not published without that owner.

### Operations lead

- Runs diagnostics and the approved mitigations, one change at a time.
- Says out loud (in the channel) what they are about to do and what they saw after.
- Asks for a second operations person when two lines of work are needed.

### Scribe

- Writes the timeline as it happens: time in UTC, the actor by role, the observation or the action, the decision and who made it.
- Records the hypotheses that were wrong too: they save time in the postmortem.
- Never edits past lines: adds a correction with its own time.

## Update templates

### First update

```text
[SEV<n>] <short title>: investigating (<time> UTC)
Impact: <what users see, which journey, how many, since when>
Status: we are investigating. Roles: IC <role>, communications <role>.
Next update: <time> UTC.
```

### Progress

```text
[SEV<n>] <short title>: update <n> (<time> UTC)
Impact: <current impact; say if it is growing, stable or shrinking>
Status: <what is being tried; what was ruled out>
Next update: <time> UTC.
```

### Mitigated

```text
[SEV<n>] <short title>: mitigated (<time> UTC)
Impact: <the window of impact and what users saw>
Status: <what was done>; we keep monitoring before calling it resolved.
Next update: <time> UTC.
```

### Resolved

```text
[SEV<n>] <short title>: resolved (<time> UTC)
Impact: <total window and scope>
Resolution: <what fixed it; whether a permanent fix is pending>
A postmortem will follow (owner: <role>, by <date>).
```

## Timeline line format

```text
<HH:MM> <actor by role> <what was seen, done or decided> [<evidence: dashboard, query, pipeline run, commit>]
```

Keep evidence references to dashboards, saved queries, pipeline runs and commits. Never paste raw log lines with customer data into the timeline: point at the query that finds them.

## Common traps

- **Debugging instead of mitigating:** a correlated change exists and nobody proposed a rollback after 15 minutes.
- **Several people changing things at once:** nobody knows which change helped.
- **Silence:** an update skipped because "nothing changed" makes stakeholders open side channels.
- **Declaring victory early:** the graph dipped for two minutes; wait for the agreed period.
- **Forgetting the temporary measures:** a feature flag left off for weeks, an alert silenced forever.
