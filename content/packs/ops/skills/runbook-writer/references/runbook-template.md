# Runbook template

Copy this into the runbook file. Keep the order: what a responder needs first comes first. Remove the guidance lines in italics once the section is written.

```markdown
# Runbook: <alert name or symptom>

- **Service:** <service>
- **Owner:** <team or role>
- **Alert:** `<alert name>`: <expression or condition, threshold, duration>
- **Dashboards:** <names or relative links>
- **Last tested:** YYYY-MM-DD, <read-through | dry run in <environment> | GameDay>
- **Last updated:** YYYY-MM-DD

## What it means

One or two sentences: what is failing, and what users see. *Example: "More than 5% of checkout requests fail. Customers cannot pay."*

## Impact and urgency

- Who is affected and how badly.
- Suggested severity: SEV<n> (raise it if <condition>).
- How fast it gets worse if nobody acts.

## First checks (5 minutes)

1. <read-only check, exact command or dashboard, expected value>
2. <read-only check>
3. <read-only check>

## Diagnosis

*A decision tree of observable checks. Each leaf is a mitigation (M1, M2, ...) or Escalation.*

1. <question with an observable answer>
   - <answer>: go to M1.
   - <answer>: go to 2.
2. ...

## Mitigations

### M1. <name> [read-only | changes state]

*Run only with the incident commander's go-ahead (changing steps).*

1. <command> (read-only)
   Expected: <output>
2. <command>
   Expected: <output>
3. Verify: <signal, threshold, time to wait>.
   If it does not recover: <next mitigation or Escalation>.
Undo: <command or procedure>, or "No undo: <why it is safe>".

### M2. ...

## Rollback

How to return to the state before the runbook was applied, step by step, if a mitigation made things worse.

## Escalation

| When | To (role or rotation) | Hand over |
|---|---|---|
| No improvement after 20 minutes | <service owner rotation> | Checks done, steps run, times |
| A destructive step is needed | <service owner> and the incident commander | Why, the backup or way back |
| Data may be lost or exposed | <security or data owner role> | What, since when |

## Prerequisites

- Access: <roles, groups, VPN, cluster contexts>, and how to request them ahead of time.
- Tools: <CLIs and versions the commands assume>.
- Credentials: <where they come from: the secret store, the CLI login>; never paste them.

## Background

How the component works, why the alert exists, known causes from past incidents (with links to postmortems), and the design decisions that explain the steps.

## Open questions

- <commands marked (unverified), steps nobody has tested, owners to confirm>

## Changelog

| Date | Change | Why |
|---|---|---|
```

## Quality checklist

- A person new to the service can follow it without asking anyone.
- The first screen fits on a laptop: what it means, the impact, the first checks.
- Every command is copyable as is, after replacing visible placeholders.
- Every changing step is marked, asks for the go-ahead, and has an undo.
- Every step says what success looks like and what to do if it does not appear.
- Escalation has a time limit, not only "if stuck".
- No secrets, no personal data, no personal contact details.
- The runbook says when it was last tested and how.
