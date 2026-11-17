---
name: incident-response
description: >-
  Runs a production incident in order: declare it with a severity from SEV1
  to SEV4, name the roles (incident commander, communications, operations),
  keep a timestamped timeline, mitigate first and look for the root cause
  later, send status updates on a fixed cadence, and close with resolution
  criteria and a blameless postmortem with verifiable actions. Every command
  that changes a system (rollback, restart, scaling, feature flag, failover)
  is proposed with its effect and its undo, and runs only after the person
  approves it. Use it when something is broken in production, an alert fires,
  users report errors, or someone is deciding whether to roll back, and to
  write the postmortem afterwards. Triggers: "incident", "production is
  down", "prod outage", "something broke in production", "an alert fired",
  "SEV1", "P1", "should we roll back", "users are getting errors", "write the
  postmortem".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-specs
---

# incident-response

Stop the bleeding first, understand it later. This skill keeps the response ordered while people are under pressure: one severity, clear roles, one timeline, mitigation before root cause, and a postmortem that turns the incident into fixes.

## Result

- **An incident record:** severity, roles, impact, a timestamped timeline, the hypotheses tried, the actions taken with who approved them, and the status updates sent. It lives where the team runs incidents; this skill keeps a copy in the answer and, when the person asks, in a file.
- **A mitigation** that brings the user-facing signal back to normal, verified with a number, not a feeling.
- **A blameless postmortem** for SEV1 and SEV2 (SEV3 when the team asks), from `references/postmortem-template.md`, with actions that have an owner and a check.

## When

- Production (or a shared environment people depend on) is broken or degraded, an alert fired, users report errors, or a recent change looks guilty and someone asks about a rollback.
- Later, to write the postmortem of an incident that is already resolved.
- **Not for:** a bug in a development or test environment with no users affected (skill:debug-systematically); planned maintenance; a question about a log query alone (skill:kibana-logs).
- **A security incident** (a breach, leaked credentials, data exposed): follow the organization's security incident process too, tell the person to involve the security team now, and preserve evidence (do not delete logs, rotate before you clean up). This skill coordinates; it does not do forensics.

## Rules

- **The person decides, the agent supports.** The incident commander is a person. The agent works as scribe and analyst: it keeps the timeline, reads logs and metrics, lists options, and drafts updates.
- **No change without approval.** Read-only diagnostics (log queries, metrics, `kubectl get`, `describe` and `logs` on workloads, `git log`) run when your tools and access allow it, except the ones the next rule forbids. Every command that changes a system is proposed as a block with what it does, its risk, its undo and the signal that proves it worked; it runs only after the person says yes, by them or by you. Destructive actions (deleting data, dropping a queue, a failover with possible data loss) also need the incident commander's explicit approval, recorded in the timeline.
- **Never read credentials.** Read-only is not enough when a command puts a secret in the context: no Secret objects in any form (`kubectl get secret`, `kubectl describe secret`, `-o yaml` or `-o json` on secrets), no `-o yaml` or `-o json` on config maps that hold credentials, no `kubectl exec`, and no `env`, `printenv` or anything else that dumps environment variables. Of environment variables, read only the names; `describe pod` prints literal values, so take only its state and events. When a value matters, the person checks it.
- **Mitigate before root cause.** When a safe mitigation exists (rolling back the change that correlates with the start), propose it now; the full explanation can wait.
- **One change at a time** during mitigation, each with its verification, so you know what worked.
- **Clean what you paste.** Logs and tickets carry personal data and secrets: apply skill:prompt-hygiene before anything reaches the conversation, an update or a document. When the security pack is not installed, say `security/prompt-hygiene not installed — applying inline criteria` and apply the inline criteria of `.exo/shared/phase-skill-map.md`.
- **Blameless, always.** Describe what the system allowed, never who failed. No names in the record or the postmortem: roles.

## 1. Triage and declare (first minutes)

1. **What is broken, for whom, since when.** The user-facing symptom ("checkout returns 500 for about 30% of requests since 14:05 UTC"), the services and regions involved, and the share of users affected. Use UTC everywhere.
2. **Pick the severity** with the table below. When in doubt, take the higher one; lower it later as you learn. If the team already has its own scale (P0 to P4, or names), use theirs and map it once in the record.
3. **Name the roles** (next section). In a small team one person holds several; say who holds which.
4. **Open the timeline** (section 6) and the place where the team coordinates (an incident channel, a call, a ticket: whatever they use).

| Severity | Impact | Response |
|---|---|---|
| SEV1 | A core journey is down or unusable for many users, data is being lost or corrupted, or a security breach is in progress | All hands now; incident commander named at once; updates every 15 to 30 minutes; postmortem required |
| SEV2 | A core journey is badly degraded, or down for a subset of users, with no easy workaround | On-call plus the owning team; updates every 30 to 60 minutes; postmortem required |
| SEV3 | Partial degradation with a workaround, or a non-core feature down | On-call during working hours; updates when the status changes; postmortem if the team asks |
| SEV4 | No user impact yet, but a risk (a disk filling up, a certificate about to expire, a failing redundant node) | A ticket with an owner and a date; no incident call |

More detail per severity, the duties of each role and the update templates are in `references/severity-and-roles.md`.

## 2. Roles

| Role | Does | Does not |
|---|---|---|
| Incident commander (IC) | Owns the incident: sets the severity, decides the next action, approves changes, calls for help, declares it resolved | Debug hands-on; when the IC starts typing commands, the coordination stops |
| Communications lead | Sends status updates on the cadence, answers stakeholders, keeps people out of the working channel | Speculate about the cause |
| Operations lead | Diagnoses and applies the approved mitigations; asks for more hands when needed | Change things without telling the IC |
| Scribe | Keeps the timeline: time, who, what was seen, what was done, what was decided | Filter or interpret; the raw sequence matters |

The agent can be the scribe and help the operations lead. Hand the IC role to a person explicitly when one is not named.

## 3. Mitigate

Start from what changed: most incidents follow a change. Check, for the window before the start, deploys, configuration and feature flag changes, infrastructure changes, certificate and secret rotations, traffic shifts, and changes in a dependency. Then pick the mitigation, usually in this order:

| Option | When | Verify with |
|---|---|---|
| Roll back the last change (deploy, config, flag) | The start correlates with a change | The error rate and latency return to the baseline |
| Turn off the feature or shed load | A new or optional feature is failing, or traffic exceeds capacity | The core journey recovers while the feature is off |
| Fail over to another region, zone or replica | One location or instance is unhealthy | Traffic is served from the healthy location within the SLO |
| Scale out or up | Saturation (CPU, memory, connections, queue depth) with healthy code | Saturation falls and latency follows |
| Restart | A process is stuck (deadlock, leak) and the cause is unknown | The process stays healthy for a while; note it as a temporary fix |

Propose each step like this, and wait for the yes:

```text
Proposed: roll back checkout-api from v2.41.0 to v2.40.3
Why: errors started 14:05 UTC, 2 minutes after the v2.41.0 deploy; no other change in the window
Command: <the project's rollback command, for example its deploy tool or kubectl rollout undo deployment/checkout-api -n <namespace>>
Risk: v2.41.0 added a column that v2.40.3 ignores; no data loss expected
Undo: redeploy v2.41.0 with the same pipeline
Verify: 5xx ratio of checkout-api below 0.5% for 10 minutes (dashboard <name>)
Approve? (yes / no)
```

Use the commands the project really has (its deploy pipeline, scripts, runbooks in skill:runbook-writer format). When a runbook exists for the alert, follow it and note any step that was wrong.

## 4. Diagnose in parallel

- While the operations lead mitigates, look for the cause without blocking the mitigation: logs with skill:kibana-logs or skill:log-analysis, metrics, traces, the diff of the suspect change, and recent alerts.
- **Delegate the investigation.** "An incident or a production error" is a mandatory delegation trigger of its own (trigger 4 of `.exo/shared/sdd-phase-common.md`, section G), whatever the number of files: with subagents and the sdd pack, send the reading of code, logs and history to `sdd-explorer` (read-only), with a brief cleaned as skill:prompt-hygiene says, and keep the coordination here. Without subagents, read in small batches (`.exo/shared/agent-capabilities.md`).
- Write each hypothesis in the timeline with how it was tested and the result, including the ones that were wrong.

## 5. Communicate

Updates follow the cadence of the severity, even when nothing changed. Each one has the impact, what is being done, and the time of the next update:

```text
[SEV2] Checkout errors: update 3 (14:40 UTC)
Impact: about 30% of checkout attempts failed between 14:05 and 14:32 UTC; payments are not duplicated.
Status: mitigated. We rolled back the 14:03 release; errors are back to normal since 14:32. We keep monitoring.
Next update: 15:10 UTC, or sooner if anything changes.
```

- No guesses about the cause in updates, no names, no customer data, no internal secrets.
- External or customer-facing messages go through whoever owns them in the organization; draft, do not publish.

## 6. Timeline

One line per event, in UTC, appended as things happen; never rewrite past lines, add a correction instead.

```text
14:03 Deploy of checkout-api v2.41.0 completes (pipeline run <id>)
14:05 Alert "checkout 5xx ratio > 2%" fires; on-call acknowledges at 14:07
14:09 SEV2 declared; IC: on-call engineer; ops: payments team; scribe: agent
14:15 Hypothesis: the new release. Evidence: 5xx only on pods running v2.41.0
14:18 Rollback proposed (see block); IC approves 14:19
14:32 5xx ratio back under 0.5%; mitigated
15:05 Resolved after 30 minutes at baseline; postmortem owner: payments tech lead
```

## 7. Resolve and close

- **Resolution criteria:** the user-facing signal is back at its baseline or its SLO (skill:slo-design) for an agreed period (30 minutes is common), the alerts cleared, queues and backlogs drained, and data consistency checked when writes were affected.
- **Temporary measures** (a flag turned off, extra replicas, a silenced alert) are listed with an owner and a date to undo them.
- **An incident that spans shifts** gets a handoff (skill:on-call-handoff).
- **The real fix** goes through the project's normal flow: with the sdd pack, a change of its own, classified by skill:risk-tiering like any other. The incident record is its evidence; never ship a hotfix that skips review because the pressure is gone.

## 8. Postmortem

Within five working days for SEV1 and SEV2. Start from `references/postmortem-template.md`; write it as `YYYY-MM-DD-<slug>.md` in the folder the project uses for postmortems (look for `docs/postmortems/`, `postmortems/` or `docs/incidents/`). If there is none, propose `docs/postmortems/` and create it only after the person says yes; until then, keep the postmortem in the answer.

1. **Summary, impact and timeline,** from the record: duration, users affected, error budget consumed.
2. **Detection and response:** how it was noticed (alert, user report), time to detect, to mitigate and to resolve, and what helped or slowed the response.
3. **Root cause and contributing factors** with skill:root-cause-5whys: the trigger, why it was not caught earlier, and why the impact was as large as it was.
4. **What went well, what went badly, where we got lucky.**
5. **Actions:** each one removes or detects a cause, with an owner role, a due date and a check that proves it is done. With `tickets.pattern` in `.exo/config.json`, the person files them and gives you the IDs; never invent one.
6. **Review** with the people involved, then share it as the team usually does.

Inside an SDD change, the postmortem is a project document, never a file of the change root: any phase may write it with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3 and 4; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C); until then, keep it in the answer. Outside one, write it as above, and save what others will need with skill:memory-protocol (`exo mem save --type bugfix` with the symptom, the cause and the fix), without personal data.

## Record

Inside an SDD change (for example, a hotfix change), an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "incident-response", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"incident-response"'
exo change record <change> --add decisions '{"summary": "Rolled back checkout-api to v2.40.3 during the SEV2", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record.

## Before you finish

- [ ] The severity is set, the roles are named, and the IC is a person.
- [ ] Every command that changed a system has a proposal, an approval and a verification in the timeline.
- [ ] The resolution criteria are met with numbers, and temporary measures have an owner and a date.
- [ ] Nothing pasted, written or sent carries secrets, personal data or names.
- [ ] For SEV1 and SEV2, the postmortem exists or has an owner and a date, and its actions have checks.
